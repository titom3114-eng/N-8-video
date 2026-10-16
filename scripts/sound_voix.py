"""
Bande-son de « Huit voix ».

La nuit chuchote son nom dans huit langues. Chaque chapitre : un battement de cœur quand le N apparaît, le mot
chuchoté au moment où N + huit devient « nuit », puis la ville s'ouvre (son ambiance arrive avec l'image) et son
odeur a un bruit (souffle de cigare, versement, encensoir, orange pressée, talons sous la pluie, métro, feu, eau).
Le chœur : les huit voix se superposent en nuée, le cœur accélère, montée — coupure nette, silence.
Dans le silence, la voix, tout près : « Dans toutes les langues, la nuit s'écrit… N plus huit. » Sur « huit »,
le logo frappe et la musique revient. « Maison de parfums nocturne. »

- Voix : scripts/voices.py (synthèse Kokoro hors ligne + chuchotement), build/voices/out/*.wav.
- Musique : « Cinematic Visions » (Coverr, licence Coverr), montée sur la grille du film (110 BPM).
- Bruitages et ambiances : Mixkit (Sound Effects Free License).

    python3 scripts/sound_voix.py build/voix/cues.json build/voix/soundtrack.wav [footage/edl_voix.json] [--stems]
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from soundtrack import SR, reverb_ir, convolve, write_wav  # noqa: E402
import sound_reel as R  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
VOICES = ROOT / 'build' / 'voices' / 'out'
STEMS = ROOT / 'build' / 'voix' / 'stems' if '--stems' in sys.argv else None
db = R.db

FX = dict(R.FX)
FX.update({
    # cœur : un battement sourd, chaud (on le sent plus qu'on ne l'entend)
    'heart':  [dict(f=490, db=-3, len=0.9, onset=True, lp=1600, rev=0.1)],
    # vaporisateur de parfum : un « pschit » court et aérien
    'spray':  [dict(f=3215, db=-9, start=0.12, len=0.42, hp=1400, rev=0.35)],
    'squish': [dict(f=3167, db=-7, len=0.9, onset=True, rev=0.2)],
    'heels':  [dict(f=542, db=-9, len='dur', start=0.05, rev=0.4)],
    # la lettre s'ouvre : souffle qui culmine sur la coupe
    'thru':   [dict(f=(1490, 1462, 2607), db=-15, peak=True, pre=0.45, tail=0.2, rev=0.2)],
    'swoosh': [dict(f=2604, db=-9, len=1.2, onset=True, rev=0.3)],
    # le logo : la montée culmine exactement sur « huit », doublée d'un dernier battement de cœur, très grave
    'logo':   [dict(f=2897, db=-4, peak=True, pre=1.5, tail=2.8, rev=0.35), dict(f=498, db=-7, len=3.0, onset=True, lp=900, rev=0.2)],
})
# ambiance de chaque ville : elle s'ouvre avec la fenêtre (plan "window") et s'arrête à la fin de la ville
BEDS = {
    'intro':     [dict(f=1177, db=-40)],
    'paris':     [dict(f=444, db=-35, start=30.0, lp=1400)],              # rumeur très feutrée d'un bar
    'roma':      [dict(f=1251, db=-31, start=2.0)],                       # pluie fine sur la pierre
    'madrid':    [dict(f=1789, db=-32, start=3.0, hp=1500)],              # grillons d'une nuit d'été
    'london':    [dict(f=2393, db=-31, start=1.0)],                       # pluie
    'lisboa':    [dict(f=2678, db=-29, start=4.0), dict(f=1206, db=-36, start=10.0, lp=3000)],   # tram, et le fleuve
    'bucuresti': [dict(f=1177, db=-33, start=12.0)],                      # vent sourd
    'berlin':    [dict(f=2681, db=-27, start=8.6)],                       # la rame du U-Bahn entre en station
    'amsterdam': [dict(f=1603, db=-32, start=6.0), dict(f=1203, db=-36, start=2.0)],   # vélo, eau des canaux
    'finale':    [dict(f=1177, db=-46, start=20.0, delay=0.25)],
}
ROOMS = {'intro': (1.6, 1.2), 'paris': (1.1, 0.8), 'roma': (3.0, 1.8), 'madrid': (1.0, 0.7), 'london': (1.6, 1.0),
         'lisboa': (1.4, 0.9), 'bucuresti': (2.4, 1.4), 'berlin': (2.0, 1.2), 'amsterdam': (1.4, 0.9),
         'choeur': (3.4, 2.0), 'finale': (2.2, 1.4)}
MUSIC_RMS = -24.0     # musique en retrait : ce sont les voix qui mènent
VOICE_REF = -11.0     # niveau (fenêtre la plus forte de 0,3 s) d'une voix à 0 dB


def voice(name):
    return R.load(VOICES / f'{name}.wav')[0]


def pan2(x, pan):
    a = (pan + 1) * np.pi / 4
    return np.stack([x * np.cos(a), x * np.sin(a)]) * np.sqrt(2)


def render_voice(ev):
    x = voice(ev['file'])
    if ev.get('split'):   # silence inséré dans la phrase (« la nuit s'écrit… N plus huit »)
        k = int(ev['split'] * SR)
        f = int(0.008 * SR)
        a, b = x[:k].copy(), x[k:].copy()
        a[-f:] *= np.linspace(1, 0, f)
        b[:f] *= np.linspace(0, 1, f)
        x = np.concatenate([a, np.zeros(int(ev.get('gap', 0.25) * SR)), b])
    if ev.get('rate'):
        n = int(len(x) / ev['rate'])
        x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x)
    st = pan2(x, ev.get('pan', 0.0))
    # très proche : une seule réflexion courte, comme une voix à l'oreille
    er = np.zeros_like(st)
    d = int(0.011 * SR)
    er[0, d:] = st[1, :-d] * 0.18
    er[1, d + 37:] = st[0, :-(d + 37)] * 0.18
    st = st + er
    st *= db(VOICE_REF + ev.get('db', 0)) / R.peak_window_rms(st)
    return st


def chorus_cloud(t0, t1, seed=8):
    """La nuée : les huit voix reviennent de plus en plus serrées, de partout, jusqu'à la coupure."""
    rng = np.random.default_rng(seed)
    names = ['w_fr', 'w_it', 'w_es', 'w_en', 'w_pt', 'w_ro', 'w_de', 'w_nl']
    n = int((t1 - t0 + 1.0) * SR)
    out = np.zeros((2, n))
    t, k = 0.15, 0
    while t < t1 - t0 - 0.12:
        p = t / (t1 - t0)
        x = voice(names[k % 8])
        r = rng.uniform(0.9, 1.1)
        x = np.interp(np.linspace(0, len(x) - 1, int(len(x) / r)), np.arange(len(x)), x)
        st = pan2(x, rng.uniform(-0.95, 0.95))
        g = db(-21 + 13 * p) / (np.sqrt((x ** 2).mean()) + 1e-9) * db(-12)
        R.place(out, st * g, t)
        t += max(0.045, 0.30 * (1 - p) ** 1.6) * rng.uniform(0.7, 1.3)
        k += 1 + int(rng.integers(0, 3))
    # s'ouvre dans l'aigu en montant
    lo = R.fft_filter(out, lp=1800)
    tt = np.arange(n) / SR / (t1 - t0)
    mix = lo * (1 - np.clip(tt, 0, 1)) + out * np.clip(tt, 0, 1)
    return mix


def music_bus(edl, N):
    m = edl['music']
    beat = 60 / edl['bpm']
    src = R.load(R.music_file(m))
    out = np.zeros((2, N))
    segs = m['map']
    xf = int(0.03 * SR)
    for i, (fb, tb, *opt) in enumerate(segs):   # [temps du film, temps de la piste (None = silence), gain dB facultatif]
        if tb is None:
            continue
        gain = db(opt[0]) if opt else 1.0
        f0 = fb * beat
        f1 = segs[i + 1][0] * beat if i + 1 < len(segs) else N / SR
        s0 = m['beat0'] + tb * beat
        before_silence = i + 1 < len(segs) and segs[i + 1][1] is None
        xo = int(0.02 * SR) if before_silence else xf     # coupure franche avant le silence
        a, b = int(round(s0 * SR)) - xf, int(round((s0 + f1 - f0) * SR)) + (0 if before_silence else xf)
        x = src[:, max(0, a):b].copy()
        w = np.ones(x.shape[1])
        after_silence = i > 0 and segs[i - 1][1] is None
        w[:xf] = 1 if i == 0 or after_silence else np.sin(np.linspace(0, np.pi / 2, xf)) ** 2
        w[-xo:] = np.cos(np.linspace(0, np.pi / 2, xo)) ** 2
        R.place(out, x * w * gain, f0 - (0 if (i == 0 or after_silence) else xf / SR))
    rms = np.sqrt((out[:, np.abs(out).max(0) > 1e-4] ** 2).mean()) + 1e-9   # niveau moyen de tout ce qui joue
    out *= db(MUSIC_RMS) / rms
    t = np.arange(N) / SR
    out *= np.minimum(1, t / 1.2) * np.clip((N / SR - t) / m.get('end_fade', 2.0), 0, 1)
    return out


def build(cues, edl):
    dur = cues['duration']
    N = int(np.ceil((dur + 0.05) * SR))
    secs_ = cues['music']['sections']
    scenes = cues['scenes']
    names = [s['name'] for s in secs_]
    dry = {n: np.zeros((2, N)) for n in names}
    send = {n: np.zeros((2, N)) for n in names}
    voices_bus = np.zeros((2, N))
    vsend = np.zeros((2, N))
    vsend_cloud = np.zeros((2, N))
    beds = np.zeros((2, N))
    edl_shots = {sh['id']: sh for sec in edl['sections'] for sh in sec['shots']}

    # ambiances : chaque ville s'entend quand sa fenêtre s'ouvre
    for s in secs_:
        a, b = s['start'], s['end']
        win = [sc for sc in scenes if sc['section'] == s['name'] and edl_shots[sc['id']].get('window')]
        if win and s['name'] != 'choeur':
            a = win[0]['start']
        if s['name'] == 'finale':
            continue
        for spec in BEDS.get(s['name'], []):
            a2 = a + spec.get('delay', 0)
            n = int((b - a2 + 0.3) * SR)
            if n > SR // 10:
                R.place(beds, R.bed(spec, n, a2), a2 - 0.05)

    count = {}
    for ev in cues['events']:
        if ev['section'] == 'finale':
            continue
        if ev['type'] == 'vo':
            st = render_voice(ev)
            R.place(voices_bus, st, ev['t'])
            R.place(vsend, st * ev.get('rev', 0.05), ev['t'] + 0.03)    # pré-délai : la voix reste devant
            continue
        if ev['type'] not in FX:
            continue
        k = count[ev['type']] = count.get(ev['type'], -1) + 1
        for spec in FX[ev['type']]:
            x, t0 = R.render_fx(spec, ev, k)
            R.place(dry[ev['section']], x, t0)
            R.place(send[ev['section']], x * spec.get('rev', 0.2), t0)

    # la nuée du chœur, du premier mot-fenêtre jusqu'à la coupure
    ch = next(s for s in secs_ if s['name'] == 'choeur')
    cloud = chorus_cloud(ch['start'], ch['end'])
    R.place(voices_bus, cloud, ch['start'])
    R.place(vsend_cloud, cloud * 0.55, ch['start'])

    fx_dry = sum(dry.values())
    wet = np.zeros((2, N))
    for name, bus in send.items():
        if np.any(bus):
            rt_lo, rt_hi = ROOMS.get(name, (2.0, 1.2))
            wet += convolve(bus, reverb_ir(sec=min(4.5, rt_lo * 1.3), seed=11 + len(name), rt_low=rt_lo, rt_high=rt_hi)) * 0.9
    wet += convolve(vsend, reverb_ir(sec=1.6, seed=5, rt_low=1.1, rt_high=0.7)) * 0.8        # pièce intime
    wet += convolve(vsend_cloud, reverb_ir(sec=3.0, seed=4, rt_low=2.4, rt_high=1.3)) * 0.8   # la nuée : vaste

    # musique : sous les voix (−11 dB) et sous les bruitages (−5 dB)
    music = music_bus(edl, N)
    ev_v = R.envelope(voices_bus, 0.03)
    ev_f = R.envelope(fx_dry, 0.03)
    duck = (1 - 0.72 * np.clip(ev_v / db(VOICE_REF - 12), 0, 1)) * (1 - 0.45 * np.clip(ev_f / db(R.REF - 10), 0, 1))
    duck = R.smooth(duck, int(0.2 * SR))
    la = int(0.1 * SR)                       # anticipation : la musique s'efface juste avant la voix
    duck = np.concatenate([duck[la:], np.full(la, duck[-1])])
    music *= duck

    # coupure nette à la fin du chœur : tout s'arrête, réverbérations comprises ; puis la finale (la voix, le logo)
    t_cut = ch['end']
    gate = np.ones(N)
    i0 = int(t_cut * SR)
    f = int(0.02 * SR)
    gate[i0 - f:i0] = np.linspace(1, 0, f)
    gate[i0:] = 0
    fin = next(s for s in secs_ if s['name'] == 'finale')
    fin_v, fin_vs, fin_fx, fin_send, fin_bed = (np.zeros((2, N)) for _ in range(5))
    for ev in cues['events']:
        if ev['section'] != 'finale':
            continue
        if ev['type'] == 'vo':
            st = render_voice(ev)
            R.place(fin_v, st, ev['t'])
            R.place(fin_vs, st * ev.get('rev', 0.08), ev['t'] + 0.03)
        elif ev['type'] in FX:
            for spec in FX[ev['type']]:
                x, t0 = R.render_fx(spec, ev, 0)
                R.place(fin_fx, x, t0)
                R.place(fin_send, x * spec.get('rev', 0.2), t0)
    for spec in BEDS['finale']:
        a2 = fin['start'] + spec.get('delay', 0)
        R.place(fin_bed, R.bed(spec, int((fin['end'] - a2 + 0.3) * SR), a2), a2)
    fin_wet = convolve(fin_vs, reverb_ir(sec=2.0, seed=6, rt_low=1.4, rt_high=0.9)) * 0.7 \
        + convolve(fin_send, reverb_ir(sec=4.0, seed=9, rt_low=3.0, rt_high=1.8)) * 0.9
    music_fin = music.copy()
    music_fin[:, :i0] = 0
    music *= gate

    voices_all = voices_bus * gate + fin_v
    fx_all = fx_dry * gate + fin_fx
    beds_all = beds * gate + fin_bed
    wet_all = wet * gate + fin_wet
    music_all = music + music_fin
    mix = music_all + beds_all + fx_all + wet_all + voices_all
    if STEMS:
        STEMS.mkdir(parents=True, exist_ok=True)
        for name, x in (('musique', music_all), ('ambiances', beds_all), ('bruitages', fx_all), ('voix', voices_all),
                        ('reverb', wet_all)):
            write_wav(str(STEMS / f'{name}.wav'), np.clip(x, -1, 1))
    return R.limit(mix)


def credits(edl):
    idx_p = ROOT / 'build' / 'reel' / 'sfx' / 'index.json'
    idx = json.loads(idx_p.read_text()) if idx_p.exists() else {}
    used = {e['n'] if isinstance(e, dict) else e for sec in edl['sections'] for sh in sec['shots'] for e in sh.get('sfx', [])}
    ids = sorted({f for k in used if k in FX for sp in FX[k] for f in (sp['f'] if isinstance(sp['f'], tuple) else (sp['f'],))}
                 | {sp['f'] for specs in BEDS.values() for sp in specs})
    m = edl['music']
    sys.path.insert(0, str(ROOT / 'scripts'))
    from voices import LINES
    lines = ['# Crédits du son — « Huit voix »', '',
             f"Musique : « {m['title']} » — {m['source']} ({m['page']}) — {m['license']}.",
             'Montée sur le tempo du film (raccords sur les mesures), sans autre modification.', '',
             'Voix : synthèse vocale neuronale hors ligne Kokoro-82M (https://huggingface.co/hexgrad/Kokoro-82M),',
             'poids sous licence Apache 2.0, modèle entraîné uniquement sur des données libres ou sans droits ;',
             'exécuté localement (kokoro-onnx, licence MIT), puis chuchotement (scripts/voices.py).',
             'Aucune voix de personne réelle n’est imitée ; usage commercial autorisé.', '',
             '| Voix | Réplique | Voix Kokoro |', '|---|---|---|']
    lines += [f"| {k} | {v[2]} | {v[0]} |" for k, v in LINES.items()]
    lines += ['', 'Attribution (CC BY 4.0) : la voix française « ff_siwis » de Kokoro est issue du corpus SIWIS',
              '(SIWIS French Speech Synthesis Database, https://datashare.ed.ac.uk/handle/10283/2353, CC BY 4.0).', '',
              'Effets sonores : Mixkit — Mixkit Sound Effects Free License (https://mixkit.co/license/#sfxFree) :',
              'usage commercial, publicité en ligne, télévision et radio autorisés, sans attribution.', '',
              '| N° Mixkit | Titre |', '|---|---|']
    lines += [f"| {i} | {idx.get(str(i), {}).get('title', '—')} |" for i in ids]
    (ROOT / 'footage' / 'CREDITS_SON_VOIX.md').write_text('\n'.join(lines) + '\n')


def main():
    src, dst = sys.argv[1], sys.argv[2]
    edl_path = Path(sys.argv[3]) if len(sys.argv) > 3 and not sys.argv[3].startswith('--') else ROOT / 'footage' / 'edl_voix.json'
    cues = json.load(open(src))
    edl = json.loads(edl_path.read_text())
    credits(edl)
    st = build(cues, edl)
    write_wav(dst, st)
    print(f'Bande-son écrite : {dst} ({st.shape[1] / SR:.2f} s)')


if __name__ == '__main__':
    main()
