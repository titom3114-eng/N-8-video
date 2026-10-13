"""
Bande-son du film N+8 « La nuit », synthétisée et synchronisée sur la chronologie
exportée par le film (build/cues.json : événements + enveloppes d'ambiance).

    python3 scripts/soundtrack.py build/cues.json build/soundtrack.wav

Uniquement numpy : pluie, vent, ville, eau, gouttes sur la vitre, bourdonnement et
grésillements des enseignes, étincelles, voiture qui passe, impacts, pulsations,
nappe harmonique sombre (ré mineur), silence, puis accord final sur le logo.
"""
import json
import sys
import wave

import numpy as np

SR = 48000


# ---------------------------------------------------------------- outils
def secs(n):
    return np.arange(n) / SR


def rms_norm(x):
    r = np.sqrt(np.mean(x ** 2)) + 1e-12
    return x / r


def shaped_noise(n, seed, lo, hi, slope=0.0):
    """Bruit filtré par FFT : passe-bande doux [lo, hi], pente spectrale en dB/oct approx."""
    rng = np.random.default_rng(seed)
    x = rng.standard_normal(n)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1 / SR)
    f[0] = 1.0
    h = 1.0 / (1.0 + (lo / f) ** 4) / (1.0 + (f / hi) ** 4)
    if slope:
        h *= (f / 1000.0) ** (slope / 6.0)
    return rms_norm(np.fft.irfft(X * h, n))


def pan_st(x, p):
    p = np.clip(p, -1, 1)
    a = (p + 1) * np.pi / 4
    return np.stack([x * np.cos(a), x * np.sin(a)])


def add_at(bus, sig, t, gain=1.0, pan=0.0):
    """Ajoute un signal mono (pané) ou stéréo dans le bus à l'instant t."""
    i0 = int(round(t * SR))
    st = pan_st(sig, pan) if sig.ndim == 1 else sig
    n = st.shape[1]
    if i0 >= bus.shape[1] or i0 + n <= 0:
        return
    s0 = max(0, -i0)
    i0 = max(0, i0)
    n = min(n - s0, bus.shape[1] - i0)
    bus[:, i0:i0 + n] += gain * st[:, s0:s0 + n]


def adsr(n, a, r, curve=2.0):
    e = np.ones(n)
    na, nr = int(a * SR), int(r * SR)
    if na > 0:
        e[:na] = (np.arange(na) / na) ** curve
    if nr > 0:
        e[-nr:] *= (1 - np.arange(nr) / nr) ** curve
    return e


def note_hz(name):
    names = {'C': -9, 'C#': -8, 'Db': -8, 'D': -7, 'D#': -6, 'Eb': -6, 'E': -5, 'F': -4, 'F#': -3, 'Gb': -3,
             'G': -2, 'G#': -1, 'Ab': -1, 'A': 0, 'A#': 1, 'Bb': 1, 'B': 2}
    p, o = name[:-1], int(name[-1])
    return 440.0 * 2 ** ((names[p] + (o - 4) * 12) / 12)


# ---------------------------------------------------------------- timbres
TABLE = 4096


def wavetable(bright):
    ph = np.arange(TABLE) / TABLE
    w = np.zeros(TABLE)
    for k in range(1, 15):
        w += np.sin(2 * np.pi * k * ph) / k * np.exp(-k / bright)
    return w / np.max(np.abs(w))


TAB_DARK, TAB_BRIGHT = wavetable(1.6), wavetable(4.5)


def osc(freq, n, seed, table):
    rng = np.random.default_rng(seed)
    f = np.full(n, freq) * (1 + 0.0015 * np.sin(2 * np.pi * (0.13 + rng.random() * 0.1) * secs(n) + rng.random() * 6))
    ph = (np.cumsum(f) / SR + rng.random()) % 1.0
    return np.interp(ph * TABLE, np.arange(TABLE + 1), np.append(table, table[0]))


def pad_note(freq, dur, seed, att=2.5, rel=3.0, bright=0.35):
    n = int(dur * SR)
    t = secs(n)
    out = np.zeros((2, n))
    for v, cents in enumerate((-7, 0, 7)):
        fq = freq * 2 ** (cents / 1200)
        lfo = 0.5 + 0.5 * np.sin(2 * np.pi * 0.07 * t + v * 2.1 + seed)
        b = np.clip(bright * (0.6 + 0.8 * lfo), 0, 1)
        sig = (1 - b) * osc(fq, n, seed * 13 + v, TAB_DARK) + b * osc(fq, n, seed * 13 + v + 50, TAB_BRIGHT)
        out += pan_st(sig, (v - 1) * 0.55)
    return out * adsr(n, att, rel) / 3


def bell(freq, dur=4.5, seed=0):
    n = int(dur * SR)
    t = secs(n)
    rng = np.random.default_rng(seed)
    ratios = [1.0, 2.0, 2.76, 4.07, 5.43, 0.5]
    amps = [1.0, 0.42, 0.22, 0.1, 0.05, 0.25]
    decs = [dur * 0.5, dur * 0.28, dur * 0.18, dur * 0.1, dur * 0.07, dur * 0.4]
    y = np.zeros(n)
    for r, a, d in zip(ratios, amps, decs):
        y += a * np.sin(2 * np.pi * freq * r * t + rng.random() * 6) * np.exp(-t / d)
    y *= np.minimum(1, t / 0.004)
    return y


def thump(f0=72, f1=36, dur=0.9, decay=5.5):
    n = int(dur * SR)
    t = secs(n)
    f = f1 + (f0 - f1) * np.exp(-t * 9)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * decay) * np.minimum(1, t / 0.003)
    return y


def crackle(dur, seed, density=90, buzz=0.5):
    """Grésillement d'une enseigne qui s'allume : claquements + bourdonnement haché."""
    n = int(dur * SR)
    rng = np.random.default_rng(seed)
    y = np.zeros(n)
    k = rng.poisson(density * dur)
    for _ in range(k):
        i = rng.integers(0, max(1, n - 400))
        ln = rng.integers(40, 320)
        burst = rng.standard_normal(ln) * np.exp(-np.arange(ln) / (ln / 4)) * rng.uniform(0.2, 1.0)
        y[i:i + ln] += burst
    y = np.diff(y, prepend=0)
    t = secs(n)
    hum = (np.sign(np.sin(2 * np.pi * 100 * t)) * 0.3 + np.sin(2 * np.pi * 100 * t)) * 0.5
    gate = np.repeat(rng.random(int(np.ceil(dur / 0.042)) + 1) > 0.45, int(0.042 * SR))[:n].astype(float)
    gate = np.convolve(gate, np.ones(96) / 96, mode='same')
    y = y * 0.6 + hum * gate * buzz * 0.35
    return y * adsr(n, 0.002, 0.05, 1)


def band_sweep(dur, f_start, f_end, seed, bands=10):
    n = int(dur * SR)
    t = secs(n) / dur
    centers = np.geomspace(min(f_start, f_end) * 0.7, max(f_start, f_end) * 1.3, bands)
    path = np.exp(np.log(f_start) + (np.log(f_end) - np.log(f_start)) * t)
    y = np.zeros(n)
    for i, c in enumerate(centers):
        nb = shaped_noise(n, seed + i, c / 1.5, c * 1.5)
        w = np.exp(-((np.log(path) - np.log(c)) ** 2) / (2 * 0.35 ** 2))
        y += nb * w
    return y


def reverb_ir(sec=3.4, seed=7, rt_low=3.0, rt_high=1.3):
    n = int(sec * SR)
    t = secs(n)
    out = []
    for ch in range(2):
        lo = shaped_noise(n, seed + ch, 40, 2500) * np.exp(-t * 6.91 / rt_low)
        hi = shaped_noise(n, seed + 10 + ch, 2500, 12000) * np.exp(-t * 6.91 / rt_high)
        ir = (lo + 0.5 * hi) * np.minimum(1, t / 0.02)
        for d, g in ((0.011, 0.5), (0.019, 0.35), (0.027, 0.3), (0.041, 0.2)):
            ir[int(d * SR) + ch * 7] += g * 8
        out.append(ir / np.sqrt(np.sum(ir ** 2)))
    return np.stack(out)


def convolve(bus, ir):
    n = bus.shape[1] + ir.shape[1] - 1
    nf = 1 << (n - 1).bit_length()
    out = np.zeros((2, bus.shape[1]))
    for c in range(2):
        y = np.fft.irfft(np.fft.rfft(bus[c], nf) * np.fft.rfft(ir[c], nf), nf)
        out[c] = y[:bus.shape[1]]
    return out


# ---------------------------------------------------------------- construction
def build(cues):
    dur = cues['duration']
    N = int(np.ceil(dur * SR))
    t = secs(N)
    env = cues['env']
    rate = env['rate']

    def E(key, smooth=0.04):
        arr = np.array(env[key], dtype=float)
        x = np.interp(t, np.arange(len(arr)) / rate, arr)
        k = max(1, int(smooth * SR))
        if k > 1:
            x = np.convolve(x, np.ones(k) / k, mode='same')
        return x

    events = sorted(cues['events'], key=lambda e: e['t'])
    t_sil = next(e['t'] for e in events if e['type'] == 'silence')

    amb = np.zeros((2, N))      # ambiances (sans réverbe)
    pre = np.zeros((2, N))      # musique + effets avant le silence (réverbe, coupés net)
    post = np.zeros((2, N))     # musique + effets après le silence
    dry = np.zeros((2, N))      # effets secs

    # --- pluie (claire / étouffée derrière la vitre)
    rain_env, muffle = E('rain', 0.08), E('muffle', 0.02)
    for ch in range(2):
        bright = shaped_noise(N, 100 + ch, 300, 8000, slope=-3)
        dull = shaped_noise(N, 110 + ch, 80, 900, slope=-2)
        patter = shaped_noise(N, 120 + ch, 1500, 7000)
        rng = np.random.default_rng(130 + ch)
        drops = np.zeros(N)
        idx = rng.integers(0, N, int(dur * 260))
        drops[idx] = rng.uniform(-1, 1, len(idx))
        drops = np.convolve(drops, np.exp(-np.arange(90) / 18), mode='same')
        r = rain_env * (1 - muffle) * (0.065 * bright + 0.016 * patter + 0.035 * drops)
        r += rain_env * muffle * 0.09 * dull
        amb[ch] += r
    # --- gouttes sur la vitre
    de = E('drops', 0.05)
    rng = np.random.default_rng(140)
    for tt in np.sort(rng.uniform(0, dur, int(dur * 7))):
        k = int(tt * SR)
        if de[min(k, N - 1)] < 0.05:
            continue
        add_at(amb, bell(rng.uniform(1300, 2600), 0.25, int(tt * 100)) * np.exp(-secs(int(0.25 * SR)) * 30), tt, 0.03 * de[k], rng.uniform(-0.6, 0.6))
    # --- vent, ville
    wind, city = E('wind', 0.2), E('city', 0.2)
    for ch in range(2):
        w = shaped_noise(N, 150 + ch, 120, 700) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.11 * t + ch) * np.sin(2 * np.pi * 0.047 * t + 1))
        amb[ch] += 0.08 * wind * w
        amb[ch] += 0.05 * city * shaped_noise(N, 160 + ch, 30, 260)
    # --- eau (clapotis)
    water = E('water', 0.1)
    for ch in range(2):
        wv = shaped_noise(N, 170 + ch, 90, 900)
        mod = 0.5 + 0.5 * np.sin(2 * np.pi * 0.62 * t + ch * 1.3) * np.sin(2 * np.pi * 0.27 * t + 0.4 + ch)
        amb[ch] += 0.14 * water * wv * mod ** 2
    rng = np.random.default_rng(180)
    for tt in np.sort(rng.uniform(0, dur, int(dur * 3))):
        k = int(tt * SR)
        if water[min(k, N - 1)] > 0.2:
            add_at(amb, bell(rng.uniform(700, 1400), 0.3, k) * np.exp(-secs(int(0.3 * SR)) * 18), tt, 0.04 * water[k], rng.uniform(-0.5, 0.5))
    # --- bourdonnement des enseignes
    hum = E('hum', 0.05)
    hs = sum(a * np.sin(2 * np.pi * f * t + i) for i, (f, a) in enumerate(((100, 1), (150, 0.35), (200, 0.5), (300, 0.22), (400, 0.12))))
    hs *= 1 + 0.15 * np.sin(2 * np.pi * 7.3 * t)
    amb += pan_st(0.04 * hum * hs + 0.006 * hum * shaped_noise(N, 190, 2000, 8000), 0.0)

    # --- musique : nappe sombre
    chords = [
        (0.0, 10.4, ['D2', 'A2', 'D3', 'F3'], 0.22),
        (10.0, 20.9, ['Bb1', 'F2', 'D3', 'C4'], 0.32),
        (20.5, 26.7, ['G1', 'D2', 'Bb2', 'D3'], 0.3),
        (26.3, 32.4, ['Eb2', 'Bb2', 'D3', 'G3'], 0.32),
        (32.0, 37.9, ['A1', 'E2', 'A2', 'D3'], 0.34),
        (37.6, t_sil, ['D2', 'A2', 'D3', 'F3', 'A3'], 0.45),
    ]
    for i, (a, b, notes, br) in enumerate(chords):
        for j, nn in enumerate(notes):
            d = b - a + (3.0 if b < t_sil else 0.05)
            add_at(pre, pad_note(note_hz(nn), d, i * 10 + j, att=2.0 if i else 3.5, rel=2.8 if b < t_sil else 0.02, bright=br), a, 0.075)
    # sous-basse continue
    sub = np.sin(2 * np.pi * note_hz('D1') * t) * np.minimum(1, t / 4.0)
    sub *= (t < t_sil)
    pre += pan_st(0.09 * sub, 0)
    # final : ré mineur (add9), très lent
    logo_t = next(e['t'] for e in events if e['type'] == 'logo')
    for j, nn in enumerate(['D2', 'A2', 'F3', 'E4', 'A4']):
        add_at(post, pad_note(note_hz(nn), dur - logo_t + 1.5, 300 + j, att=2.2, rel=4.5, bright=0.3), logo_t - 1.2, 0.07)
    drone = pad_note(note_hz('D2'), dur - t_sil - 1.0, 290, att=4.0, rel=3.0, bright=0.15)
    add_at(post, drone, t_sil + 1.0, 0.05)

    # --- événements
    surge_notes = ['D5', 'F5', 'A5', 'C6', 'A4', 'C5', 'D5', 'F5', 'G5', 'A5']
    surge_i = 0
    for k, e in enumerate(events):
        ty, tt = e['type'], e['t']
        bus = pre if tt < t_sil else post
        g, p = e.get('gain', 1.0), e.get('pan', 0.0) * 0.6
        if ty == 'flick':
            add_at(dry, crackle(0.55, k, 110, 0.6), tt, 0.16 * g, p)
            add_at(bus, crackle(0.55, k + 1000, 40, 0.0), tt, 0.05 * g, p)
        elif ty == 'off':
            c = crackle(0.5, k, 90, 0.7)
            add_at(dry, c * np.linspace(1, 0.2, len(c)), tt, 0.14 * g, p)
        elif ty == 'spark':
            add_at(dry, crackle(0.25, k, 260, 0.2), tt, 0.22 * g, p)
            n = int(0.6 * SR)
            add_at(dry, shaped_noise(n, k, 3000, 11000) * np.exp(-secs(n) * 9), tt + 0.03, 0.06 * g, p)
            for q in range(4):
                add_at(bus, bell(note_hz('A6') * (1 + 0.37 * q), 0.4, k + q), tt + 0.03 + q * 0.05, 0.015 * g, p)
        elif ty == 'slide':
            d = e.get('dur', 1.0) + 0.4
            s = band_sweep(d, 700, 1600, k)
            add_at(bus, s * np.sin(np.pi * np.clip(secs(len(s)) / d, 0, 1)) ** 2, tt - 0.1, 0.035 * g, p)
        elif ty == 'snap':
            add_at(dry, crackle(0.08, k, 400, 0.0), tt, 0.16 * g, p)
            add_at(bus, bell(2100, 0.3, k), tt, 0.02 * g, p)
        elif ty == 'surge':
            nn = surge_notes[min(surge_i, len(surge_notes) - 1)]
            surge_i += 1
            add_at(bus, bell(note_hz(nn), 5.0, k), tt, 0.05 * g, 0)
            add_at(bus, thump(60, 40, 2.0, 1.8), tt - 0.05, 0.12 * g, 0)
        elif ty == 'cut':
            add_at(dry, thump(80, 38, 0.8, 7), tt, 0.22 * g, 0)
            n = int(0.12 * SR)
            add_at(dry, shaped_noise(n, k, 60, 600) * np.exp(-secs(n) * 30), tt, 0.1 * g, 0)
        elif ty == 'pulse':
            add_at(dry, thump(70, 42, 0.7, 8), tt, 0.3, 0)
            add_at(dry, thump(64, 40, 0.6, 9), tt + 0.19, 0.18, 0)
        elif ty == 'car':
            d = e['dur']
            n = int(d * SR)
            x = np.clip(secs(n) / d, 0, 1)
            env_c = np.exp(-((x - 0.5) ** 2) / (2 * 0.17 ** 2))
            body = shaped_noise(n, k, 60, 1200) * 0.8 + shaped_noise(n, k + 1, 2500, 7000) * 0.5
            st = np.stack([body * env_c * np.cos((x * 1.8 - 0.9 + 1) * np.pi / 4), body * env_c * np.sin((x * 1.8 - 0.9 + 1) * np.pi / 4)])
            add_at(amb, st, tt, 0.09)
        elif ty in ('whoosh', 'focus', 'tilt'):
            d = e['dur']
            s = band_sweep(d, 300, 3200 if ty == 'whoosh' else 1400, k)
            x = np.clip(secs(len(s)) / d, 0, 1)
            env_w = x ** 2.2 if ty == 'whoosh' else np.sin(np.pi * x) ** 2
            add_at(bus, s * env_w, tt, 0.16 if ty == 'whoosh' else 0.04, 0)
        elif ty == 'riser':
            d = e['dur']
            n = int(d * SR)
            x = np.clip(secs(n) / d, 0, 1)
            s = band_sweep(d, 400, 5000, k) * x ** 2
            for q, base in enumerate(('A3', 'D4', 'E4')):
                f = note_hz(base) * 2 ** (x * 0.9)
                s += 0.25 * np.sin(2 * np.pi * np.cumsum(f) / SR) * x ** 1.5 * (1 + 0.5 * np.sin(2 * np.pi * (4 + 10 * x) * secs(n)))
            add_at(pre, s, tt, 0.12, 0)
        elif ty == 'arch':
            d = e['dur']
            for q, nn in enumerate(['D5', 'F5', 'A5', 'C6', 'D6', 'E6']):
                add_at(post, bell(note_hz(nn), 4.0, k + q), tt + q * d / 6, 0.03, (q - 2.5) * 0.15)
            s = band_sweep(d + 0.5, 800, 4000, k)
            add_at(post, s * np.sin(np.pi * np.clip(secs(len(s)) / (d + 0.5), 0, 1)) ** 2, tt, 0.03, 0)
        elif ty == 'logo':
            add_at(post, bell(note_hz('D5'), 7.0, k), tt + 0.1, 0.09, 0)
            add_at(post, bell(note_hz('A4'), 7.0, k + 1), tt + 0.1, 0.05, -0.2)
            add_at(post, thump(55, 36, 3.5, 1.1), tt, 0.25, 0)

    # --- espace et mixage
    ir = reverb_ir()
    pre_w = pre + 0.55 * convolve(pre, ir)
    post_w = post + 0.6 * convolve(post, ir)
    dry_w = dry + 0.25 * convolve(dry, ir)
    amb_w = amb + 0.15 * convolve(amb, ir)
    cut = np.clip((t_sil - t) / 0.012, 0, 1)          # silence net
    mix = pre_w * cut + post_w + dry_w + amb_w
    fade = np.minimum(1, t / 1.0) * np.clip((dur - t) / 2.2, 0, 1)
    mix *= fade
    mix = np.tanh(mix * 1.6) / 1.6
    mix /= np.max(np.abs(mix)) + 1e-9
    return mix * 0.89


def write_wav(path, st):
    rng = np.random.default_rng(1)
    tpdf = (rng.random(st.shape) - rng.random(st.shape)) / 32768
    data = np.clip(st + tpdf, -1, 1)
    pcm = (data.T * 32767).astype('<i2')
    with wave.open(path, 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def main():
    src, dst = sys.argv[1], sys.argv[2]
    cues = json.load(open(src))
    st = build(cues)
    write_wav(dst, st)
    print(f'Bande-son écrite : {dst} ({st.shape[1] / SR:.2f} s)')


if __name__ == '__main__':
    main()
