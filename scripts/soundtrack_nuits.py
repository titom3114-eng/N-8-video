"""
Bande-son du film N+8 « Nuits » (96 BPM), synthétisée et calée sur la chronologie du film.

    python3 scripts/soundtrack_nuits.py build/nuits/cues.json build/nuits/soundtrack.wav

Paris : groove feutré, piano électrique, contrebasse, balais — ambiance de bar.
Rome  : chœur, cloches, pluie, pierre mouillée.
Oman  : percussions sur cadre (maqsum), oud pincé en mode hijaz, nappe sombre, puissance.
Villes : montée rythmique, impacts sur chaque ville.
Finale : silence net, puis accord final sur le logo.
"""
import json
import sys

import numpy as np

from soundtrack import (SR, secs, shaped_noise, pan_st, add_at, adsr, note_hz, pad_note, bell, thump,
                        band_sweep, reverb_ir, convolve, write_wav)


# ---------------------------------------------------------------- instruments
def kick(vel=1.0):
    n = int(0.45 * SR)
    t = secs(n)
    f = 44 + 86 * np.exp(-t * 28)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7.5)
    y[:120] += np.random.default_rng(1).standard_normal(120) * 0.3 * np.exp(-np.arange(120) / 25)
    return y * vel


def brush(seed, vel=1.0, length=0.22):
    n = int(length * SR)
    t = secs(n)
    y = shaped_noise(n, seed, 900, 7000) * np.exp(-t * 14) * 0.7
    y += np.sin(2 * np.pi * 185 * t) * np.exp(-t * 30) * 0.4
    return y * np.minimum(1, t / 0.004) * vel


def hat(seed, vel=1.0, open_=False):
    n = int((0.22 if open_ else 0.05) * SR)
    t = secs(n)
    return shaped_noise(n, seed, 6500, 15000) * np.exp(-t * (12 if open_ else 70)) * vel


def shaker(seed, vel=1.0):
    n = int(0.08 * SR)
    t = secs(n)
    return shaped_noise(n, seed, 3500, 9000) * np.sin(np.pi * np.clip(t / 0.08, 0, 1)) ** 2 * vel


def doum(vel=1.0):
    n = int(0.6 * SR)
    t = secs(n)
    f = 62 + 40 * np.exp(-t * 20)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 5)
    y += shaped_noise(n, 3, 80, 600) * np.exp(-t * 30) * 0.25
    return y * vel


def tek(seed, vel=1.0):
    n = int(0.12 * SR)
    t = secs(n)
    y = shaped_noise(n, seed, 1800, 7000) * np.exp(-t * 45) * 0.8 + np.sin(2 * np.pi * 420 * t) * np.exp(-t * 40) * 0.4
    return y * vel


def upright(freq, dur, vel=1.0):
    n = int(dur * SR)
    t = secs(n)
    ph = 2 * np.pi * freq * t * (1 + 0.004 * np.exp(-t * 20))
    y = np.sin(ph) + 0.35 * np.sin(2 * ph) + 0.12 * np.sin(3 * ph)
    return y * np.minimum(1, t / 0.006) * np.exp(-t * 2.2) * vel


def rhodes(freq, dur, vel=1.0, seed=0):
    n = int(dur * SR)
    t = secs(n)
    idx = 2.4 * vel * np.exp(-t * 4) + 0.35
    car = np.sin(2 * np.pi * freq * t + idx * np.sin(2 * np.pi * freq * t))
    tine = 0.12 * vel * np.sin(2 * np.pi * freq * 7.0 * t) * np.exp(-t * 14)
    env = (1 - np.exp(-t * 300)) * np.exp(-t * 1.1) * adsr(n, 0.0, 0.15)
    y = (car * 0.8 + tine) * env * vel
    trem = 0.5 + 0.5 * np.sin(2 * np.pi * 4.2 * t + seed)
    return np.stack([y * (0.75 + 0.25 * trem), y * (0.75 + 0.25 * (1 - trem))])


def choir(freq, dur, seed):
    n = int(dur * SR)
    t = secs(n)
    rng = np.random.default_rng(seed)
    out = np.zeros((2, n))
    form = lambda f: (np.exp(-((f - 720) / 140) ** 2) + 0.55 * np.exp(-((f - 1150) / 160) ** 2) + 0.22 * np.exp(-((f - 2650) / 260) ** 2))
    for v, cents in enumerate((-9, 0, 8)):
        f0 = freq * 2 ** (cents / 1200)
        vib = 1 + 0.004 * np.sin(2 * np.pi * (4.6 + v * 0.3) * t + rng.random() * 6)
        ph = 2 * np.pi * np.cumsum(f0 * vib) / SR
        y = np.zeros(n)
        for k in range(1, int(5000 / f0)):
            a = form(k * f0) / k ** 0.25 + 0.02 / k
            y += a * np.sin(k * ph + rng.random() * 6)
        out += pan_st(y, (v - 1) * 0.5)
    return out * adsr(n, 1.1, 1.6, 1.5) / 3


def oud(freq, dur, seed, vel=1.0):
    """Corde pincée (Karplus-Strong) au timbre boisé."""
    n = int(dur * SR)
    N = max(2, int(round(SR / freq)))
    rng = np.random.default_rng(seed)
    y = np.zeros(n + N + 1)
    burst = rng.uniform(-1, 1, N)
    burst = np.convolve(burst, [0.35, 0.4, 0.25], mode='same')
    y[1:N + 1] = burst
    dec = 0.9965
    for s in range(N + 1, n + N + 1, N):
        e = min(s + N, n + N + 1)
        y[s:e] = dec * 0.5 * (y[s - N:e - N] + y[s - N - 1:e - N - 1])
    out = y[1:n + 1]
    body = np.exp(-secs(400) * 160) * np.sin(2 * np.pi * 210 * secs(400))
    out = out + 0.25 * np.convolve(out, body, mode='full')[:n] / 40
    return out * adsr(n, 0.001, 0.05) * vel


def flame_noise(dur, seed):
    n = int(dur * SR)
    t = secs(n)
    return shaped_noise(n, seed, 120, 900) * (0.7 + 0.3 * np.sin(2 * np.pi * 7 * t + seed)) * adsr(n, 0.05, 0.4)


def breath(dur, seed, lo=300, hi=2400):
    n = int(dur * SR)
    t = np.clip(secs(n) / dur, 0, 1)
    return shaped_noise(n, seed, lo, hi) * np.sin(np.pi * t) ** 1.5


def clink(seed, f0=2600):
    y = np.zeros(int(0.8 * SR))
    for k, r in enumerate((1.0, 1.52, 2.31, 3.1)):
        b = bell(f0 * r, 0.8, seed + k)
        y += b * (0.6 / (k + 1))
    return y * np.exp(-secs(len(y)) * 4)


def crackle_env(n, seed, density):
    rng = np.random.default_rng(seed)
    y = np.zeros(n)
    idx = rng.integers(0, n, int(density * n / SR))
    y[idx] = rng.uniform(-1, 1, len(idx))
    return np.convolve(y, np.exp(-np.arange(60) / 9), mode='same')


# ---------------------------------------------------------------- construction
def build(cues):
    dur = cues['duration']
    N = int(np.ceil(dur * SR))
    t = secs(N)
    bpm = cues['music']['bpm']
    B = 60.0 / bpm
    sec = {s['name']: s for s in cues['music']['sections']}
    env = cues['env']
    rate = env['rate']

    def E(key, smooth=0.06):
        arr = np.array(env[key], dtype=float)
        x = np.interp(t, np.arange(len(arr)) / rate, arr)
        k = max(1, int(smooth * SR))
        return np.convolve(x, np.ones(k) / k, mode='same') if k > 1 else x

    drums = np.zeros((2, N))   # batterie (réverbe courte)
    music = np.zeros((2, N))   # instruments (réverbe courte)
    hall = np.zeros((2, N))    # chœur, cloches (réverbe longue)
    fx = np.zeros((2, N))      # bruitages
    amb = np.zeros((2, N))     # ambiances

    def beat_t(name, b):
        return sec[name]['start'] + b * B

    # ---- INTRO : nappe grave, un accord de piano sur la phrase
    for j, nn in enumerate(['D2', 'A2', 'F3']):
        add_at(music, pad_note(note_hz(nn), 5.6, 500 + j, att=2.5, rel=1.5, bright=0.15), 0.0, 0.05)
    for nn in ['F3', 'A3', 'C4', 'E4']:
        add_at(music, rhodes(note_hz(nn), 4.0, 0.55, 1), 2.65, 0.05)

    # ---- PARIS : 6 mesures
    chords_p = [('D', ['F3', 'A3', 'C4', 'E4'], ['D2', 'F2', 'A2', 'C3']),
                ('D', ['F3', 'A3', 'C4', 'E4'], ['D2', 'A1', 'C2', 'E2']),
                ('Bb', ['F3', 'A3', 'D4', 'E4'], ['Bb1', 'D2', 'F2', 'A2']),
                ('Bb', ['F3', 'A3', 'D4', 'G4'], ['Bb1', 'F2', 'G2', 'A2']),
                ('G', ['F3', 'Bb3', 'D4', 'A4'], ['G1', 'Bb1', 'D2', 'F2']),
                ('A', ['G3', 'C#4', 'F4', 'Bb4'], ['A1', 'C#2', 'E2', 'G2'])]
    swing = 0.12
    for bar, (_, voic, bass) in enumerate(chords_p):
        b0 = bar * 4
        add_at(drums, kick(0.95), beat_t('paris', b0), 0.55)
        if bar % 2:
            add_at(drums, kick(0.6), beat_t('paris', b0 + 1.5), 0.45)
        add_at(drums, brush(10 + bar, 0.9), beat_t('paris', b0 + 2), 0.32, -0.1)
        for e in range(8):
            tt = beat_t('paris', b0 + e * 0.5 + (swing if e % 2 else 0))
            add_at(drums, hat(20 + bar * 8 + e, 0.6 if e % 2 == 0 else 0.35), tt, 0.09, 0.35)
        for k, bn in enumerate(bass):
            add_at(music, upright(note_hz(bn), B * 1.1, 0.9 if k == 0 else 0.7), beat_t('paris', b0 + k), 0.2, -0.05)
        for nn in voic:
            add_at(music, rhodes(note_hz(nn), B * 2.2, 0.8, bar), beat_t('paris', b0), 0.045)
            add_at(music, rhodes(note_hz(nn), B * 0.9, 0.45, bar + 3), beat_t('paris', b0 + 2.5 + swing), 0.03)

    # ---- ROMA : 6 mesures, chœur et cloches
    chords_r = [(['G2', 'D3', 'Bb3', 'D4'], ['G1', 'D2', 'G2', 'Bb2']),
                (['Eb3', 'G3', 'Bb3', 'D4'], ['Eb2', 'Bb1', 'Eb2', 'G2']),
                (['C3', 'G3', 'Eb4', 'D4'], ['C2', 'G1', 'C2', 'Eb2']),
                (['D3', 'G3', 'A3', 'C4'], ['D2', 'A1', 'D2', 'C2']),
                (['G2', 'D3', 'Bb3', 'A3'], ['G1', 'D2', 'G2', 'F2']),
                (['D3', 'F#3', 'A3', 'C4'], ['D2', 'A1', 'F#2', 'A2'])]
    for bar, (voic, bass) in enumerate(chords_r):
        b0 = bar * 4
        add_at(drums, kick(0.8), beat_t('roma', b0), 0.45)
        add_at(drums, kick(0.5), beat_t('roma', b0 + 2.5), 0.3)
        add_at(drums, brush(40 + bar, 0.7, 0.3), beat_t('roma', b0 + 2), 0.24, 0.1)
        for e in range(4):
            add_at(drums, hat(60 + bar * 4 + e, 0.4), beat_t('roma', b0 + e + 0.5 + swing), 0.07, 0.4)
        for k, bn in enumerate(bass):
            add_at(music, upright(note_hz(bn), B * 1.2, 0.8), beat_t('roma', b0 + k), 0.17)
        for j, nn in enumerate(voic):
            add_at(hall, choir(note_hz(nn), B * 4.6, 700 + bar * 4 + j), beat_t('roma', b0), 0.06)
        for nn in voic[1:]:
            add_at(music, rhodes(note_hz(nn) * 2, B * 1.5, 0.35, bar), beat_t('roma', b0 + 1), 0.02)

    # ---- OMAN : maqsum, oud en hijaz, nappe sombre
    o0 = sec['oman']['start']
    for j, nn in enumerate(['D2', 'A2', 'D3']):
        add_at(music, pad_note(note_hz(nn), 15.6, 800 + j, att=1.5, rel=1.0, bright=0.4), o0, 0.07)
    add_at(music, pad_note(note_hz('Eb3'), 5.5, 810, att=2.0, rel=2.0, bright=0.4), o0 + 7.5, 0.05)
    riffs = {
        'A': ['D4', 'Eb4', 'F#4', 'G4', 'A4', 'G4', 'F#4', 'Eb4'],
        'B': ['D4', None, 'A3', 'Bb3', 'A3', 'G3', 'F#3', 'G3'],
        'C': ['A4', 'Bb4', 'A4', 'G4', 'F#4', 'G4', 'A4', 'D5'],
        'D': ['C5', 'Bb4', 'A4', 'G4', 'F#4', 'Eb4', 'D4', None],
    }
    for bar, rk in enumerate(['A', 'B', 'A', 'C', 'D', 'B']):
        b0 = bar * 4
        for step, kind in ((0, 'D'), (1, 'T'), (3, 'T'), (4, 'D'), (6, 'T'), (7, 't')):
            tt = beat_t('oman', b0 + step * 0.5)
            if kind == 'D':
                add_at(drums, doum(1.0), tt, 0.5)
                add_at(drums, kick(0.9), tt, 0.35)
            else:
                add_at(drums, tek(100 + bar * 8 + step, 1.0 if kind == 'T' else 0.5), tt, 0.2, 0.25 if step % 2 else -0.25)
        for e in range(16):
            add_at(drums, shaker(200 + bar * 16 + e, 0.8 if e % 4 == 2 else 0.45), beat_t('oman', b0 + e * 0.25), 0.05, 0.5)
        for e, nn in enumerate(riffs[rk]):
            if nn is None:
                continue
            tt = beat_t('oman', b0 + e * 0.5)
            add_at(music, oud(note_hz(nn), 1.1, 300 + bar * 8 + e, 1.0 if e % 2 == 0 else 0.75), tt, 0.16, 0.15)
            if bar >= 3 and e % 4 == 3:
                add_at(music, oud(note_hz(nn) * 2 ** (1 / 12), 0.3, 900 + bar * 8 + e, 0.6), tt + B * 0.25, 0.08, 0.15)
        add_at(music, upright(note_hz('D1') * 2, B * 1.8, 1.0), beat_t('oman', b0), 0.28)
        add_at(music, upright(note_hz('D1') * 2, B * 0.9, 0.8), beat_t('oman', b0 + 2), 0.2)

    # ---- VILLES : montée
    v0 = sec['villes']['start']
    for b in range(8):
        add_at(drums, kick(1.0), v0 + b * B, 0.55)
        add_at(drums, hat(400 + b, 0.7, open_=True), v0 + b * B + B / 2, 0.08, 0.3)
        for q in range(4):
            add_at(drums, hat(420 + b * 4 + q, 0.5), v0 + b * B + q * B / 4, 0.06, -0.3)
    for q in range(16):
        add_at(drums, brush(480 + q, 0.4 + q / 20, 0.12), v0 + 4 * B + q * B / 4, 0.18)
    riser = band_sweep(8 * B, 300, 7000, 77) * np.clip(secs(int(8 * B * SR)) / (8 * B), 0, 1) ** 2.5
    add_at(music, riser, v0, 0.12)
    for j, nn in enumerate(['D3', 'A3', 'D4', 'F4']):
        add_at(music, pad_note(note_hz(nn), 8 * B + 0.1, 600 + j, att=1.0, rel=0.05, bright=0.6), v0, 0.04)
    for b in range(8):
        add_at(music, upright(note_hz('D2'), B * 0.9, 1.0), v0 + b * B, 0.2)

    # ---- FINALE : silence, révélation, accord
    f0 = sec['finale']['start']
    for j, nn in enumerate(['D2', 'A2', 'F3', 'E4', 'A4']):
        add_at(hall, pad_note(note_hz(nn), dur - f0 - 0.8, 950 + j, att=2.4, rel=3.5, bright=0.3), f0 + 0.9, 0.07)
    for nn, dt in (('D4', 0.0), ('F4', 0.35), ('A4', 0.7), ('E5', 1.05)):
        add_at(music, rhodes(note_hz(nn), 3.5, 0.6, 9), f0 + 1.45 + dt, 0.045)

    # ---- bruitages
    for k, e in enumerate(sorted(cues['events'], key=lambda e: e['t'])):
        ty, tt = e['type'], e['t']
        if ty == 'strike':
            n = int(0.14 * SR)
            add_at(fx, shaped_noise(n, k, 1800, 8000) * np.exp(-secs(n) * 18), tt, 0.35, 0.3)
            add_at(fx, band_sweep(0.6, 400, 1600, k) * np.exp(-secs(int(0.6 * SR)) * 4), tt + 0.03, 0.25, 0.3)
            add_at(fx, crackle_env(int(0.5 * SR), k, 120), tt, 0.15, 0.3)
        elif ty == 'flame':
            add_at(fx, flame_noise(e['dur'], k), tt, 0.12, 0.25)
        elif ty in ('puff', 'exhale'):
            add_at(fx, breath(1.4, k), tt, 0.16, 0.1)
        elif ty == 'clink':
            add_at(fx, clink(k), tt, 0.12, -0.3)
        elif ty == 'pour':
            d = e['dur']
            n = int(d * SR)
            x = secs(n)
            rng = np.random.default_rng(k)
            gurg = np.repeat(rng.random(int(d * 30) + 1), int(SR / 30) + 1)[:n]
            gurg = np.convolve(gurg, np.ones(400) / 400, mode='same')
            y = shaped_noise(n, k, 500, 2200) * (0.4 + 0.6 * gurg)
            for q in range(10):
                y += 0.25 * np.sin(2 * np.pi * np.cumsum(np.full(n, 380 + 160 * (x / d))) / SR + q) * np.exp(-((x - q * d / 10) % (d / 10)) * 30)
            add_at(fx, y * adsr(n, 0.05, 0.2), tt, 0.1, 0.05)
        elif ty == 'lighter':
            add_at(fx, shaped_noise(int(0.03 * SR), k, 3000, 12000), tt, 0.3, 0.3)
            add_at(fx, flame_noise(1.0, k), tt + 0.05, 0.1, 0.3)
        elif ty == 'ice':
            add_at(fx, clink(k, 1800), tt, 0.18)
            n = int(0.35 * SR)
            add_at(fx, shaped_noise(n, k, 900, 5000) * np.exp(-secs(n) * 12), tt, 0.15)
        elif ty == 'ember':
            add_at(fx, breath(0.9, k, 200, 1500), tt, 0.1)
            add_at(fx, crackle_env(int(0.9 * SR), k, 80), tt, 0.12)
        elif ty == 'bell':
            for q, (fq, a) in enumerate(((note_hz('D3'), 1.0), (note_hz('A3'), 0.5), (note_hz('D4') * 1.19, 0.3))):
                add_at(hall, bell(fq, 7.0, k * 10 + q), tt, 0.08 * a)
        elif ty == 'step':
            n = int(0.1 * SR)
            add_at(fx, shaped_noise(n, k, 80, 900) * np.exp(-secs(n) * 45), tt, 0.3, -0.4 + 0.15 * (k % 6))
            add_at(fx, shaped_noise(int(0.05 * SR), k + 1, 2500, 9000) * np.exp(-secs(int(0.05 * SR)) * 60), tt + 0.01, 0.08, 0)
        elif ty == 'chain':
            for q in range(3):
                add_at(fx, bell(3200 + 900 * q, 0.35, k * 3 + q) * np.exp(-secs(int(0.35 * SR)) * 12), tt + q * 0.03, 0.04, -0.2 + q * 0.2)
        elif ty == 'drop':
            n = int(0.5 * SR)
            x = secs(n)
            fq = 520 + 900 * (1 - np.exp(-x * 60))
            add_at(fx, np.sin(2 * np.pi * np.cumsum(fq) / SR) * np.exp(-x * 16), tt, 0.22)
            add_at(hall, bell(note_hz('A5'), 3.0, k), tt, 0.04)
        elif ty == 'flash':
            add_at(fx, thump(90, 40, 0.6, 6), tt, 0.3)
            n = int(0.25 * SR)
            add_at(fx, shaped_noise(n, k, 2000, 12000) * np.exp(-secs(n) * 16), tt, 0.1, 0.4 if e.get('i', 0) % 2 else -0.4)
        elif ty == 'reveal':
            add_at(fx, thump(60, 32, 3.0, 1.4), tt, 0.4)
        elif ty == 'logo':
            add_at(hall, bell(note_hz('D5'), 7.0, k), tt, 0.09)
            add_at(hall, bell(note_hz('A5'), 6.0, k + 1), tt + 0.18, 0.05)

    # ---- ambiances
    room, city, rain, church, water, wind, fire = (E(kk) for kk in ('room', 'city', 'rain', 'church', 'water', 'wind', 'fire'))
    for ch in range(2):
        rng = np.random.default_rng(1000 + ch)
        babble = np.zeros(N)
        for v in range(10):
            sy = np.repeat(rng.random(int(dur * 5) + 2), int(SR / 5) + 1)[:N]
            sy = np.convolve(sy, np.ones(2400) / 2400, mode='same') ** 3
            babble += shaped_noise(N, 1100 + ch * 20 + v, 250 + v * 40, 1100 + v * 60) * sy
        amb[ch] += room * 0.035 * babble / 3
        amb[ch] += city * 0.03 * shaped_noise(N, 1200 + ch, 30, 300)
        amb[ch] += rain * (0.05 * shaped_noise(N, 1300 + ch, 400, 9000, slope=-3) + 0.03 * crackle_env(N, 1310 + ch, 300))
        amb[ch] += church * 0.02 * shaped_noise(N, 1400 + ch, 60, 400)
        amb[ch] += water * 0.07 * shaped_noise(N, 1500 + ch, 800, 9000, slope=-2) * (0.8 + 0.2 * np.sin(2 * np.pi * 0.7 * t + ch))
        amb[ch] += wind * 0.07 * shaped_noise(N, 1600 + ch, 120, 900) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.13 * t + ch) * np.sin(2 * np.pi * 0.05 * t))
        amb[ch] += fire * (0.06 * crackle_env(N, 1700 + ch, 120) + 0.03 * shaped_noise(N, 1710 + ch, 80, 500))

    # ---- mixage
    short_ir = reverb_ir(1.6, seed=21, rt_low=1.3, rt_high=0.6)
    long_ir = reverb_ir(4.5, seed=31, rt_low=4.0, rt_high=1.8)
    mix = drums + 0.22 * convolve(drums, short_ir)
    mix += music + 0.35 * convolve(music, short_ir)
    mix += hall + 0.8 * convolve(hall, long_ir)
    mix += fx + 0.3 * convolve(fx, short_ir)
    mix += amb
    f_start = sec['finale']['start']
    cut = np.clip((f_start - t) / 0.01, 0, 1)
    pre = mix * cut
    # après la coupe : seulement ce qui commence dans la finale
    post_mask = t >= f_start
    post = np.zeros_like(mix)
    fin_hall = np.zeros((2, N)); fin_music = np.zeros((2, N)); fin_fx = np.zeros((2, N))
    fin_hall[:, post_mask] = hall[:, post_mask]; fin_music[:, post_mask] = music[:, post_mask]; fin_fx[:, post_mask] = fx[:, post_mask]
    post = fin_hall + 0.8 * convolve(fin_hall, long_ir) + fin_music + 0.35 * convolve(fin_music, short_ir) + fin_fx + 0.3 * convolve(fin_fx, short_ir)
    mix = pre + post
    fade = np.minimum(1, t / 0.8) * np.clip((dur - t) / 2.0, 0, 1)
    mix *= fade
    mix = np.tanh(mix * 1.5) / 1.5
    mix /= np.max(np.abs(mix)) + 1e-9
    return mix * 0.89


def main():
    cues = json.load(open(sys.argv[1]))
    st = build(cues)
    write_wav(sys.argv[2], st)
    print(f'Bande-son écrite : {sys.argv[2]} ({st.shape[1] / SR:.2f} s)')


if __name__ == '__main__':
    main()
