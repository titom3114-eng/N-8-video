"""
Bande-son du montage « Nuits » en images réelles (120 BPM, coupes rapides).

    python3 scripts/soundtrack_reel.py build/reel/cues.json build/reel/soundtrack.wav

Même univers que « Nuits », plus nerveux : groove demi-temps à 120 BPM, charleston en doubles croches,
piano électrique et contrebasse à Paris, chœur et cloches à Rome, maqsum, oud et nappe sombre à Oman,
montée sur les villes, silence net puis accord final sur le logo. Bruitages calés sur les plans.
"""
import json
import sys

import numpy as np

from soundtrack import (SR, secs, shaped_noise, pan_st, add_at, adsr, note_hz, pad_note, bell, thump,
                        band_sweep, reverb_ir, convolve, write_wav)
from soundtrack_nuits import (kick, brush, hat, shaker, doum, tek, upright, rhodes, choir, oud, flame_noise,
                              breath, clink, crackle_env)


def build(cues):
    dur = cues['duration']
    N = int(np.ceil(dur * SR))
    t = secs(N)
    B = 60.0 / cues['music']['bpm']
    sec = {s['name']: s for s in cues['music']['sections']}
    shots = {s['id']: s for s in cues['scenes']}
    bars = lambda name: int(round((sec[name]['end'] - sec[name]['start']) / (4 * B)))
    bt = lambda name, b: sec[name]['start'] + b * B

    drums, music, hall, fx, amb = (np.zeros((2, N)) for _ in range(5))

    # ---- intro : nappe grave + accord
    for j, nn in enumerate(['D2', 'A2', 'F3']):
        add_at(music, pad_note(note_hz(nn), sec['intro']['end'] + 0.6, 500 + j, att=1.5, rel=1.0, bright=0.15), 0.0, 0.05)
    for nn in ['F3', 'A3', 'C4', 'E4']:
        add_at(music, rhodes(note_hz(nn), 3.0, 0.55, 1), 1.5, 0.05)
    add_at(music, band_sweep(1.2, 300, 3000, 9) * np.clip(secs(int(1.2 * SR)) / 1.2, 0, 1) ** 2, sec['intro']['end'] - 1.2, 0.08)

    # ---- PARIS
    chords_p = [(['F3', 'A3', 'C4', 'E4'], ['D2', 'F2', 'A2', 'C3']), (['F3', 'A3', 'C4', 'E4'], ['D2', 'A1', 'C2', 'E2']),
                (['F3', 'A3', 'D4', 'E4'], ['Bb1', 'D2', 'F2', 'A2']), (['F3', 'A3', 'D4', 'G4'], ['Bb1', 'F2', 'G2', 'A2']),
                (['F3', 'Bb3', 'D4', 'A4'], ['G1', 'Bb1', 'D2', 'F2']), (['F3', 'Bb3', 'D4', 'A4'], ['G1', 'D2', 'F2', 'D2']),
                (['G3', 'C#4', 'F4', 'Bb4'], ['A1', 'C#2', 'E2', 'G2']), (['G3', 'C#4', 'E4', 'A4'], ['A1', 'E2', 'G2', 'C#2'])]
    sw = 0.1
    for bar in range(bars('paris')):
        voic, bass = chords_p[bar % len(chords_p)]
        b0 = bar * 4
        add_at(drums, kick(1.0), bt('paris', b0), 0.55)
        add_at(drums, kick(0.7), bt('paris', b0 + 1.5), 0.42)
        if bar % 2:
            add_at(drums, kick(0.6), bt('paris', b0 + 3.5), 0.35)
        add_at(drums, brush(10 + bar, 1.0), bt('paris', b0 + 2), 0.36, -0.1)
        for e in range(16):
            add_at(drums, hat(20 + bar * 16 + e, 0.65 if e % 4 == 0 else (0.45 if e % 2 == 0 else 0.25)),
                   bt('paris', b0 + e * 0.25 + (sw * 0.5 if e % 2 else 0)), 0.08, 0.35)
        for k, bn in enumerate(bass):
            add_at(music, upright(note_hz(bn), B * 1.05, 0.95 if k == 0 else 0.75), bt('paris', b0 + k), 0.22, -0.05)
        for nn in voic:
            add_at(music, rhodes(note_hz(nn), B * 1.6, 0.8, bar), bt('paris', b0), 0.045)
            add_at(music, rhodes(note_hz(nn), B * 0.6, 0.5, bar + 3), bt('paris', b0 + 1.5), 0.03)
            add_at(music, rhodes(note_hz(nn), B * 0.6, 0.45, bar + 5), bt('paris', b0 + 2.5 + sw), 0.028)

    # ---- ROMA
    chords_r = [(['G2', 'D3', 'Bb3', 'D4'], ['G1', 'D2', 'G2', 'Bb2']), (['Eb3', 'G3', 'Bb3', 'D4'], ['Eb2', 'Bb1', 'Eb2', 'G2']),
                (['C3', 'G3', 'Eb4', 'D4'], ['C2', 'G1', 'C2', 'Eb2']), (['D3', 'G3', 'A3', 'C4'], ['D2', 'A1', 'D2', 'C2']),
                (['G2', 'D3', 'Bb3', 'A3'], ['G1', 'D2', 'G2', 'F2']), (['Eb3', 'G3', 'Bb3', 'D4'], ['Eb2', 'Bb1', 'G2', 'Bb2']),
                (['D3', 'F#3', 'A3', 'C4'], ['D2', 'A1', 'F#2', 'A2'])]
    for bar in range(bars('roma')):
        voic, bass = chords_r[bar % len(chords_r)]
        b0 = bar * 4
        add_at(drums, kick(0.9), bt('roma', b0), 0.5)
        add_at(drums, kick(0.6), bt('roma', b0 + 2.5), 0.34)
        add_at(drums, brush(40 + bar, 0.85, 0.3), bt('roma', b0 + 2), 0.3, 0.1)
        for e in range(8):
            add_at(drums, hat(60 + bar * 8 + e, 0.5 if e % 2 else 0.3), bt('roma', b0 + e * 0.5 + (sw if e % 2 else 0)), 0.07, 0.4)
        for k, bn in enumerate(bass):
            add_at(music, upright(note_hz(bn), B * 1.1, 0.85), bt('roma', b0 + k), 0.19)
        for j, nn in enumerate(voic):
            add_at(hall, choir(note_hz(nn), B * 4.6, 700 + bar * 4 + j), bt('roma', b0), 0.06)
        for nn in voic[1:]:
            add_at(music, rhodes(note_hz(nn) * 2, B * 1.2, 0.35, bar), bt('roma', b0 + 1), 0.02)

    # ---- OMAN
    o0, o1 = sec['oman']['start'], sec['oman']['end']
    for j, nn in enumerate(['D2', 'A2', 'D3']):
        add_at(music, pad_note(note_hz(nn), o1 - o0 + 0.6, 800 + j, att=1.0, rel=0.6, bright=0.4), o0, 0.07)
    add_at(music, pad_note(note_hz('Eb3'), (o1 - o0) * 0.45, 810, att=1.5, rel=1.5, bright=0.4), o0 + (o1 - o0) * 0.4, 0.05)
    riffs = {
        'A': ['D4', 'Eb4', 'F#4', 'G4', 'A4', 'G4', 'F#4', 'Eb4'],
        'B': ['D4', None, 'A3', 'Bb3', 'A3', 'G3', 'F#3', 'G3'],
        'C': ['A4', 'Bb4', 'A4', 'G4', 'F#4', 'G4', 'A4', 'D5'],
        'D': ['C5', 'Bb4', 'A4', 'G4', 'F#4', 'Eb4', 'D4', None],
    }
    order = ['A', 'B', 'A', 'C', 'D', 'B', 'C']
    for bar in range(bars('oman')):
        b0 = bar * 4
        for step, kind in ((0, 'D'), (1, 'T'), (3, 'T'), (4, 'D'), (6, 'T'), (7, 't')):
            tt = bt('oman', b0 + step * 0.5)
            if kind == 'D':
                add_at(drums, doum(1.0), tt, 0.52)
                add_at(drums, kick(0.95), tt, 0.38)
            else:
                add_at(drums, tek(100 + bar * 8 + step, 1.0 if kind == 'T' else 0.5), tt, 0.22, 0.25 if step % 2 else -0.25)
        for e in range(16):
            add_at(drums, shaker(200 + bar * 16 + e, 0.8 if e % 4 == 2 else 0.45), bt('oman', b0 + e * 0.25), 0.05, 0.5)
        for e, nn in enumerate(riffs[order[bar % len(order)]]):
            if nn is None:
                continue
            tt = bt('oman', b0 + e * 0.5)
            add_at(music, oud(note_hz(nn), 0.9, 300 + bar * 8 + e, 1.0 if e % 2 == 0 else 0.75), tt, 0.17, 0.15)
            if bar >= 3 and e % 4 == 3:
                add_at(music, oud(note_hz(nn) * 2 ** (1 / 12), 0.25, 900 + bar * 8 + e, 0.6), tt + B * 0.25, 0.08, 0.15)
        add_at(music, upright(note_hz('D1') * 2, B * 1.6, 1.0), bt('oman', b0), 0.3)
        add_at(music, upright(note_hz('D1') * 2, B * 0.8, 0.85), bt('oman', b0 + 2), 0.22)

    # ---- VILLES
    v0, v1 = sec['villes']['start'], sec['villes']['end']
    nb = int(round((v1 - v0) / B))
    for b in range(nb):
        add_at(drums, kick(1.0), v0 + b * B, 0.58)
        add_at(drums, hat(400 + b, 0.7, open_=True), v0 + b * B + B / 2, 0.08, 0.3)
        for q in range(4):
            add_at(drums, hat(420 + b * 4 + q, 0.5), v0 + b * B + q * B / 4, 0.06, -0.3)
    for q in range(16):
        add_at(drums, brush(480 + q, 0.4 + q / 20, 0.1), v0 + (nb / 2) * B + q * B / 4, 0.18)
    rl = v1 - v0
    add_at(music, band_sweep(rl, 300, 7000, 77) * np.clip(secs(int(rl * SR)) / rl, 0, 1) ** 2.5, v0, 0.12)
    for j, nn in enumerate(['D3', 'A3', 'D4', 'F4']):
        add_at(music, pad_note(note_hz(nn), rl + 0.05, 600 + j, att=0.8, rel=0.05, bright=0.6), v0, 0.04)
    for b in range(nb):
        add_at(music, upright(note_hz('D2'), B * 0.9, 1.0), v0 + b * B, 0.2)

    # ---- FINALE
    f0 = sec['finale']['start']
    for j, nn in enumerate(['D2', 'A2', 'F3', 'E4', 'A4']):
        add_at(hall, pad_note(note_hz(nn), dur - f0 - 0.6, 950 + j, att=2.2, rel=3.0, bright=0.3), f0 + 0.7, 0.07)
    for nn, dt in (('D4', 0.0), ('F4', 0.3), ('A4', 0.6), ('E5', 0.9)):
        add_at(music, rhodes(note_hz(nn), 3.2, 0.6, 9), f0 + 1.35 + dt, 0.045)

    # ---- bruitages
    for k, e in enumerate(sorted(cues['events'], key=lambda e: e['t'])):
        ty, tt = e['type'], e['t']
        if ty == 'strike':
            n = int(0.14 * SR)
            add_at(fx, shaped_noise(n, k, 1800, 8000) * np.exp(-secs(n) * 18), tt, 0.35, 0.2)
            add_at(fx, band_sweep(0.6, 400, 1600, k) * np.exp(-secs(int(0.6 * SR)) * 4), tt + 0.03, 0.25, 0.2)
            add_at(fx, crackle_env(int(0.5 * SR), k, 120), tt, 0.15, 0.2)
        elif ty == 'puff':
            add_at(fx, breath(1.2, k), tt, 0.16, 0.1)
        elif ty == 'clink':
            add_at(fx, clink(k), tt, 0.12, -0.3)
        elif ty == 'pour':
            d = e['dur']
            n = int(d * SR)
            x = secs(n)
            rng = np.random.default_rng(k)
            gurg = np.convolve(np.repeat(rng.random(int(d * 30) + 1), int(SR / 30) + 1)[:n], np.ones(400) / 400, mode='same')
            y = shaped_noise(n, k, 500, 2200) * (0.4 + 0.6 * gurg)
            y += 0.2 * np.sin(2 * np.pi * np.cumsum(380 + 220 * (x / d)) / SR) * (0.5 + 0.5 * np.sin(2 * np.pi * 9 * x))
            add_at(fx, y * adsr(n, 0.05, 0.2), tt, 0.1, 0.05)
        elif ty == 'lighter':
            add_at(fx, shaped_noise(int(0.03 * SR), k, 3000, 12000), tt, 0.3, 0.3)
            add_at(fx, flame_noise(0.8, k), tt + 0.05, 0.1, 0.3)
        elif ty == 'ice':
            add_at(fx, clink(k, 1800), tt, 0.18)
            n = int(0.35 * SR)
            add_at(fx, shaped_noise(n, k, 900, 5000) * np.exp(-secs(n) * 12), tt, 0.15)
        elif ty == 'bell':
            for q, (fq, a) in enumerate(((note_hz('D3'), 1.0), (note_hz('A3'), 0.5), (note_hz('D4') * 1.19, 0.3))):
                add_at(hall, bell(fq, 7.0, k * 10 + q), tt, 0.08 * a)
        elif ty == 'step':
            n = int(0.1 * SR)
            add_at(fx, shaped_noise(n, k, 80, 900) * np.exp(-secs(n) * 45), tt, 0.3, -0.4 + 0.25 * (k % 4))
            add_at(fx, shaped_noise(int(0.05 * SR), k + 1, 2500, 9000) * np.exp(-secs(int(0.05 * SR)) * 60), tt + 0.01, 0.08)
        elif ty == 'chain':
            for q in range(3):
                add_at(fx, bell(3200 + 900 * q, 0.35, k * 3 + q) * np.exp(-secs(int(0.35 * SR)) * 12), tt + q * 0.03, 0.04, -0.2 + q * 0.2)
        elif ty == 'coals':
            d = e['dur']
            add_at(fx, crackle_env(int(d * SR), k, 140) * adsr(int(d * SR), 0.1, 0.3), tt, 0.1)
        elif ty == 'drop':
            n = int(0.5 * SR)
            x = secs(n)
            add_at(fx, np.sin(2 * np.pi * np.cumsum(520 + 900 * (1 - np.exp(-x * 60))) / SR) * np.exp(-x * 16), tt, 0.22)
            add_at(hall, bell(note_hz('A5'), 3.0, k), tt, 0.04)
        elif ty == 'flash':
            add_at(fx, thump(90, 40, 0.5, 7), tt, 0.3)
            n = int(0.2 * SR)
            add_at(fx, shaped_noise(n, k, 2000, 12000) * np.exp(-secs(n) * 18), tt, 0.1, 0.4 if k % 2 else -0.4)
        elif ty == 'reveal':
            add_at(fx, thump(60, 32, 3.0, 1.4), tt, 0.4)
        elif ty == 'logo':
            add_at(hall, bell(note_hz('D5'), 7.0, k), tt, 0.09)
            add_at(hall, bell(note_hz('A5'), 6.0, k + 1), tt + 0.18, 0.05)

    # ---- ambiances par section (et feu de l'encensoir à oud)
    def env_of(name, a0=0.15):
        e = np.zeros(N)
        s0, s1 = int(sec[name]['start'] * SR), int(sec[name]['end'] * SR)
        e[s0:s1] = 1
        k = int(a0 * SR)
        return np.convolve(e, np.ones(k) / k, mode='same')
    paris, roma, oman = env_of('paris'), env_of('roma'), env_of('oman')
    fire = np.zeros(N)
    for sid in ('o03', 'o04'):
        if sid in shots:
            s0 = int(shots[sid]['start'] * SR); s1 = int((shots[sid]['start'] + shots[sid]['dur']) * SR)
            fire[s0:s1] = 1
    for ch in range(2):
        rng = np.random.default_rng(1000 + ch)
        babble = np.zeros(N)
        for v in range(10):
            sy = np.repeat(rng.random(int(dur * 5) + 2), int(SR / 5) + 1)[:N]
            sy = np.convolve(sy, np.ones(2400) / 2400, mode='same') ** 3
            babble += shaped_noise(N, 1100 + ch * 20 + v, 250 + v * 40, 1100 + v * 60) * sy
        amb[ch] += paris * (0.03 * babble / 3 + 0.02 * shaped_noise(N, 1200 + ch, 30, 300))
        amb[ch] += roma * (0.045 * shaped_noise(N, 1300 + ch, 400, 9000, slope=-3) + 0.025 * crackle_env(N, 1310 + ch, 300))
        amb[ch] += oman * 0.06 * shaped_noise(N, 1600 + ch, 120, 900) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.13 * t + ch))
        amb[ch] += fire * (0.05 * crackle_env(N, 1700 + ch, 120) + 0.025 * shaped_noise(N, 1710 + ch, 80, 500))

    # ---- mixage : tout coupe net à l'entrée de la finale, puis seul le final résonne
    short_ir = reverb_ir(1.4, seed=21, rt_low=1.1, rt_high=0.5)
    long_ir = reverb_ir(4.5, seed=31, rt_low=4.0, rt_high=1.8)
    cut = (t < f0).astype(float)
    cut = np.convolve(cut, np.ones(480) / 480, mode='same')
    pre_mask, post_mask = t < f0, t >= f0

    def bus(x, ir, wet, mask):
        y = np.zeros_like(x)
        y[:, mask] = x[:, mask]
        return y + wet * convolve(y, ir)
    pre = bus(drums, short_ir, 0.2, pre_mask) + bus(music, short_ir, 0.3, pre_mask) + bus(hall, long_ir, 0.8, pre_mask) \
        + bus(fx, short_ir, 0.3, pre_mask) + amb
    post = bus(music, short_ir, 0.3, post_mask) + bus(hall, long_ir, 0.8, post_mask) + bus(fx, short_ir, 0.3, post_mask)
    mix = pre * cut + post
    mix *= np.minimum(1, t / 0.5) * np.clip((dur - t) / 2.0, 0, 1)
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
