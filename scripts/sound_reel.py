"""
Bande-son de « Nuits » en images réelles.

- Musique : « Disturbing Night » (Coverr, licence Coverr : usage commercial libre), montée sur la grille du film
  (85,32 BPM) d'après footage/edl.json → "music" : chaque segment du film reprend la piste à un temps donné,
  raccords sur les mesures, fondu final.
- Ambiances par lieu : rue de Paris la nuit puis rumeur feutrée du bar, pluie et cloches de Rome, vent du désert
  et grillons à Oman, ville la nuit pour les autres capitales.
- Bruitages réels (Mixkit, Sound Effects Free License) calés plan par plan sur les événements exportés par
  src/reel.js : allumette, molette du briquet, braise et cendre, souffle de fumée, verre, versement, glaçon,
  gouttes, encensoir et chœur, cloche, citron qui plonge, eau, braises, flamme, goutte d'ambre, vent et sable…
- Impacts graves aux entrées de ville, montée inversée avant Paris, impact du logo.
- Réverbération propre à chaque lieu, musique légèrement abaissée sous les bruitages, limiteur doux.

    python3 scripts/sound_reel.py build/reel/cues.json build/reel/soundtrack.wav
    python3 scripts/sound_reel.py build/teaser/cues.json build/teaser/soundtrack.wav footage/edl_teaser.json
"""
import json
import subprocess
import sys
import urllib.request
from functools import lru_cache
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from soundtrack import SR, reverb_ir, convolve, write_wav  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SFX = ROOT / 'footage' / 'sfx'

# Bruitages : fichier Mixkit, niveau relatif (dB), durée ('dur' = celle du plan), départ dans le fichier,
# filtres, alignement (onset = attaque du son sur l'événement, peak = point culminant sur l'événement), envoi réverbe.
FX = {
    'match':   [dict(f=2590, db=-3, len=2.4, onset=True, rev=0.25)],
    'zippo':   [dict(f=2641, db=-7, len=0.5, onset=True), dict(f=1334, db=-4, len=1.0, onset=True, delay=0.07, rev=0.2)],
    'crackle': [dict(f=1330, db=-9, len='dur', start=3.0, hp=700, lp=9000, rev=0.15)],
    'ash':     [dict(f=1330, db=-5, len=0.8, start=7.0, hp=1200, lp=9000, rev=0.1)],
    'exhale':  [dict(f=2661, db=-8, len=1.0, onset=True, lp=2600, rev=0.3), dict(f=1458, db=-15, len=1.0, onset=True, delay=0.05)],
    # inspiration (on « sent ») : montée lente, coupure nette, un peu plus grave
    'inhale':  [dict(f=2237, db=-9, start=0.08, len=0.5, rate=0.86, lp=7000, rev=0.3)],
    'squeeze': [dict(f=3215, db=-6, len=1.2, onset=True, rev=0.2)],
    'steps':   [dict(f=1270, db=-11, len='dur', start=2.0, rev=0.3)],
    'glass':   [dict(f=2936, db=-7, len=1.4, onset=True, rev=0.3)],
    'pour':    [dict(f=142, db=-4, len='dur', onset=True, rev=0.2)],
    'ice':     [dict(f=2834, db=-6, len=1.6, onset=True, rev=0.25)],
    'swoosh':  [dict(f=2604, db=-9, len=1.6, onset=True, rev=0.3)],
    'drops':   [dict(f=1264, db=-10, len='dur', start=1.0, rev=0.25)],
    'choir':   [dict(f=664, db=-6, peak=True, tail=1.6, rev=0.4)],
    'bell':    [dict(f=619, db=-8, len=5.5, onset=True, rev=0.45)],
    'candle':  [dict(f=1346, db=-15, len='dur', onset=True, rev=0.2)],
    'splash':  [dict(f=1311, db=-4, len=1.0, onset=True, rev=0.2), dict(f=1321, db=-13, len=2.0, onset=True, delay=0.15)],
    'water':   [dict(f=1203, db=-12, len='dur', start=1.0, rev=0.3)],
    'coals':   [dict(f=1329, db=-10, len='dur', start=2.0, lp=9000, rev=0.2)],
    'fire':    [dict(f=1349, db=-7, len=2.6, onset=True, rev=0.25)],
    'gust':    [dict(f=1167, db=-9, len=3.0, onset=True, rev=0.2)],
    'sand':    [dict(f=1494, db=-9, len=1.0, onset=True, rev=0.2)],
    'drop':    [dict(f=3179, db=-4, len=2.2, onset=True, rev=0.35)],
    'chimes':  [dict(f=2014, db=-13, len=2.2, onset=True, rev=0.4)],
    'glitter': [dict(f=2352, db=-19, len=2.6, onset=True, hp=1800, rev=0.4)],
    'rumble':  [dict(f=2297, db=-6, len=3.0, onset=True, rev=0.1)],
    'whoosh':  [dict(f=(1490, 1462, 2607), db=-12, len=0.8, onset=True, rev=0.15)],
    'hit':     [dict(f=549, db=-2, len=4.0, onset=True, rev=0.3), dict(f=2297, db=-10, len=2.5, onset=True)],
    'riser':   [dict(f=784, db=-5, peak=True, pre=1.1, tail=1.2, rev=0.2)],
    'logo':    [dict(f=2897, db=-2, len=6.0, onset=True, rev=0.35), dict(f=619, db=-14, len=6.0, onset=True, delay=0.25, rev=0.5)],
}
# ambiances par section : fichier, niveau moyen (dBFS), départ dans le fichier, filtres
BEDS = {
    'intro':  [dict(f=1177, db=-31)],
    'paris':  [dict(f=2678, db=-31, start=12.0)],
    'roma':   [dict(f=1251, db=-27, start=2.0), dict(f=370, db=-31, start=18.0)],
    'oman':   [dict(f=1158, db=-27, start=6.0), dict(f=2475, db=-38, start=10.0, hp=1500)],
    'villes': [dict(f=2678, db=-30, start=60.0)],
    'finale': [dict(f=1177, db=-33, start=20.0, delay=2.1)],   # après le silence
}
BAR = dict(f=444, db=-27, start=30.0, lp=2400)        # rumeur du bar, à partir du plan marqué "bar"
ROOMS = {'intro': (2.6, 2.0), 'paris': (1.1, 0.8), 'roma': (3.2, 2.0), 'oman': (2.2, 1.4), 'villes': (1.4, 1.0), 'finale': (4.0, 2.4)}
REF = -10.5          # niveau (dBFS, fenêtre la plus forte de 0,3 s) d'un bruitage à 0 dB
MUSIC_RMS = -21.0    # niveau moyen de la musique sur la partie rythmée
STEMS = ROOT / 'build' / 'reel' / 'stems' if '--stems' in sys.argv else None


@lru_cache(maxsize=None)
def load(path):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), '-f', 'f32le', '-ac', '2', '-ar', str(SR), '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).T.astype(np.float64)


def sfx(fid):
    p = SFX / f'{fid}.wav'
    if not p.exists():
        subprocess.run([sys.executable, str(ROOT / 'scripts' / 'footage' / 'mixkit_sfx.py'), 'get', str(fid)], check=True)
    return load(p)


def db(x):
    return 10 ** (x / 20)


def fft_filter(x, hp=None, lp=None, order=2):
    if not hp and not lp:
        return x
    n = x.shape[1]
    nf = 1 << (n - 1).bit_length()
    f = np.fft.rfftfreq(nf, 1 / SR)
    g = np.ones_like(f)
    if hp:
        g *= 1 / np.sqrt(1 + (hp / np.maximum(f, 1e-3)) ** (2 * order))
    if lp:
        g *= 1 / np.sqrt(1 + (f / lp) ** (2 * order))
    return np.fft.irfft(np.fft.rfft(x, nf) * g, nf)[:, :n]


def smooth(v, k):
    """Moyenne glissante centrée (somme cumulée : coût linéaire)."""
    k = max(1, int(k))
    c = np.concatenate([[0.0], np.cumsum(v)])
    i = np.arange(len(v))
    lo, hi = np.clip(i - k // 2, 0, len(v)), np.clip(i - k // 2 + k, 0, len(v))
    return (c[hi] - c[lo]) / np.maximum(1, hi - lo)


def envelope(x, win=0.01):
    return np.sqrt(np.maximum(0, smooth((x ** 2).mean(0), win * SR)))


def peak_window_rms(x, win=0.3):
    e = envelope(x, win)
    return float(e.max()) + 1e-9


def place(bus, x, t0, gain=1.0):
    i0 = int(round(t0 * SR))
    if i0 >= bus.shape[1]:
        return
    if i0 < 0:
        x = x[:, -i0:]
        i0 = 0
    n = min(x.shape[1], bus.shape[1] - i0)
    if n > 0:
        bus[:, i0:i0 + n] += gain * x[:, :n]


def shape(x, fade_in=0.004, fade_out=0.25):
    n = x.shape[1]
    a, b = min(n, int(fade_in * SR)), min(n, int(fade_out * SR))
    w = np.ones(n)
    if a:
        w[:a] = np.linspace(0, 1, a)
    if b:
        w[n - b:] *= np.linspace(1, 0, b) ** 1.5
    return x * w


def render_fx(spec, ev, k):
    """Retourne (signal, temps de départ) pour un bruitage."""
    fid = spec['f'][k % len(spec['f'])] if isinstance(spec['f'], tuple) else spec['f']
    src = sfx(fid)
    start = int(spec.get('start', 0) * SR)
    if spec.get('onset'):
        e = envelope(src, 0.005)
        hit = np.nonzero(e > 0.12 * e.max())[0]
        start = max(0, int(hit[0]) - int(0.012 * SR)) if len(hit) else 0
    length = spec.get('len')
    if length == 'dur':
        length = ev['dur'] + 0.35
    x = src[:, start:start + int(length * SR)] if length else src[:, start:]
    if spec.get('rate'):  # < 1 : plus grave et plus lent (rééchantillonnage)
        n = int(x.shape[1] / spec['rate'])
        xi = np.linspace(0, x.shape[1] - 1, n)
        x = np.stack([np.interp(xi, np.arange(x.shape[1]), c) for c in x])
    if spec.get('peak') and spec.get('tail'):  # on coupe peu après le point culminant
        x = x[:, :int(np.argmax(envelope(x, 0.02))) + int(spec['tail'] * SR)]
    if spec.get('peak') and spec.get('pre'):   # et la montée ne commence que peu avant
        pk = int(np.argmax(envelope(x, 0.02)))
        x = shape(x[:, max(0, pk - int(spec['pre'] * SR)):], fade_in=0.35, fade_out=0.0)
    x = fft_filter(x, spec.get('hp'), spec.get('lp'))
    x = shape(x, fade_out=min(0.6, 0.3 * x.shape[1] / SR))
    x = x * db(REF + spec['db'] + ev.get('db', 0)) / peak_window_rms(x)
    t0 = ev['t'] + spec.get('delay', 0)
    if spec.get('peak'):
        t0 = ev['t'] - float(np.argmax(envelope(x, 0.02))) / SR
    return x, t0


def music_file(m):
    """Fichier de la musique ; l'original WAV (footage/music/*.wav) est prioritaire s'il a été déposé."""
    p = ROOT / m['file']
    wav = p.with_suffix('.wav')
    if wav.exists():
        return wav
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(m['url'], headers={'User-Agent': 'Mozilla/5.0'})
        p.write_bytes(urllib.request.urlopen(req, timeout=120).read())
    return p


def music_bus(cues, edl, N):
    m = edl['music']
    beat = 60 / edl['bpm']
    src = load(music_file(m))
    out = np.zeros((2, N))
    segs = m['map']
    xf = int(0.03 * SR)
    for i, (fb, tb) in enumerate(segs):
        if tb is None:  # silence (respiration avant le logo)
            continue
        f0 = fb * beat
        f1 = segs[i + 1][0] * beat if i + 1 < len(segs) else N / SR
        s0 = m['beat0'] + tb * beat
        before_silence = i + 1 < len(segs) and segs[i + 1][1] is None
        xo = int(0.12 * SR) if before_silence else xf      # arrêt net mais pas sec avant le silence
        a, b = int(round(s0 * SR)) - xf, int(round((s0 + f1 - f0) * SR)) + (0 if before_silence else xf)
        x = src[:, max(0, a):b].copy()
        w = np.ones(x.shape[1])
        w[:xf] = np.sin(np.linspace(0, np.pi / 2, xf)) ** 2 if i else 1
        w[-xo:] = np.cos(np.linspace(0, np.pi / 2, xo)) ** 2
        place(out, x * w, f0 - xf / SR)
    # niveau : moyenne de la partie rythmée ramenée à MUSIC_RMS
    beat_entry = int(segs[1][0] * beat * SR)
    rms = np.sqrt((out[:, beat_entry:beat_entry + 20 * SR] ** 2).mean()) + 1e-9
    out *= db(MUSIC_RMS) / rms
    t = np.arange(N) / SR
    out *= np.minimum(1, t / 0.6) * np.clip((N / SR - t) / m.get('end_fade', 2.0), 0, 1)
    return out


def bed(spec, n, start_s):
    src = sfx(spec['f'])
    s = int(spec.get('start', 0) * SR) % max(1, src.shape[1] - n - 1)
    x = src[:, s:s + n]
    if x.shape[1] < n:
        x = np.concatenate([x, src[:, :n - x.shape[1]]], axis=1)
    x = fft_filter(x, spec.get('hp'), spec.get('lp'))
    rms = np.sqrt((x ** 2).mean()) + 1e-9
    return shape(x * db(spec['db']) / rms, fade_in=0.35, fade_out=0.35)


def build(cues, edl):
    dur = cues['duration']
    N = int(np.ceil((dur + 0.05) * SR))
    secs_ = cues['music']['sections']
    dry = {s['name']: np.zeros((2, N)) for s in secs_}
    send = {s['name']: np.zeros((2, N)) for s in secs_}
    beds = np.zeros((2, N))

    # ambiances de lieu
    for s in secs_:
        a, b = s['start'], s['end']
        for spec in BEDS.get(s['name'], []):
            a2 = a + spec.get('delay', 0)
            place(beds, bed(spec, int((b - a2 + 0.4) * SR), a2), a2 - 0.2)
    bar = [e for e in cues['events'] if e['type'] == 'bar']
    for e in bar:
        sec = next(s for s in secs_ if s['name'] == e['section'])
        place(beds, bed(BAR, int((sec['end'] - e['t'] + 0.3) * SR), e['t']), e['t'])

    # bruitages
    count = {}
    for ev in cues['events']:
        if ev['type'] not in FX:
            continue
        k = count[ev['type']] = count.get(ev['type'], -1) + 1
        for spec in FX[ev['type']]:
            x, t0 = render_fx(spec, ev, k)
            place(dry[ev['section']], x, t0)
            place(send[ev['section']], x * spec.get('rev', 0.2), t0)

    fx_dry = sum(dry.values())
    wet = np.zeros((2, N))
    for name, bus in send.items():
        if np.any(bus):
            rt_lo, rt_hi = ROOMS.get(name, (2.0, 1.2))
            wet += convolve(bus, reverb_ir(sec=min(4.5, rt_lo * 1.3), seed=11 + len(name), rt_low=rt_lo, rt_high=rt_hi)) * 0.9

    # musique, abaissée jusqu'à 6 dB sous les bruitages
    music = music_bus(cues, edl, N)
    e = envelope(fx_dry, 0.03)
    thr = db(REF - 10)
    duck = 1 - 0.5 * np.clip(e / thr, 0, 1)
    k = int(0.25 * SR)
    duck = smooth(duck, k)
    music *= duck

    mix = music + beds + fx_dry + wet
    if STEMS:
        STEMS.mkdir(parents=True, exist_ok=True)
        for name, x in (('musique', music), ('ambiances', beds), ('bruitages', fx_dry), ('reverb', wet)):
            write_wav(str(STEMS / f'{name}.wav'), np.clip(x, -1, 1))
    return limit(mix)


def limit(x, crest=11.0, ceiling=-1.5):
    """Limiteur à anticipation : crêtes ramenées à `crest` dB au-dessus du niveau moyen, puis plafond `ceiling` dBFS
    (le passage à −14 LUFS dans scripts/mux.py ne fait ensuite presque plus bouger les crêtes)."""
    x = fft_filter(x, lp=18000, order=4)
    level = 10 * np.log10((x ** 2).mean() + 1e-12)
    thr = db(level + crest)
    # crêtes « vraies » : on regarde aussi entre les échantillons (sur-échantillonnage ×2)
    n = x.shape[1]
    up = np.fft.irfft(np.fft.rfft(x, axis=1), 2 * n, axis=1) * 2
    pk = np.maximum(np.abs(x).max(0), np.abs(up[:, 1::2]).max(0))
    need = np.minimum(1, thr / np.maximum(pk, 1e-9))
    w = int(0.012 * SR)
    pad = np.concatenate([np.ones(w), need, np.ones(w)])
    g = np.lib.stride_tricks.sliding_window_view(pad, 2 * w + 1).min(1)   # anticipation et maintien
    g = smooth(g, int(0.006 * SR))                                        # attaque douce
    rel = smooth(g, int(0.08 * SR))                                       # relâchement
    g = np.minimum(g, rel)
    y = x * g
    y = np.tanh(y / thr * 0.9) * thr / 0.9                                 # écrêtage doux résiduel
    up = np.fft.irfft(np.fft.rfft(y, axis=1), 4 * n, axis=1) * 4
    return y * db(ceiling) / (np.abs(up).max() + 1e-9)


def credits(edl):
    idx_p = ROOT / 'build' / 'reel' / 'sfx' / 'index.json'
    idx = json.loads(idx_p.read_text()) if idx_p.exists() else {}
    ids = sorted({f for specs in FX.values() for sp in specs for f in (sp['f'] if isinstance(sp['f'], tuple) else (sp['f'],))}
                 | {sp['f'] for specs in BEDS.values() for sp in specs} | {BAR['f']})
    m = edl['music']
    lines = ['# Crédits du son', '', f"Musique : « {m['title']} » — {m['source']} ({m['page']}) — {m['license']}.",
             'Montée sur le tempo du film (raccords sur les mesures), sans autre modification.', '',
             'Effets sonores : Mixkit — Mixkit Sound Effects Free License (https://mixkit.co/license/#sfxFree) :',
             'usage commercial, publicité en ligne, télévision et radio autorisés, sans attribution.', '',
             '| N° Mixkit | Titre |', '|---|---|']
    lines += [f"| {i} | {idx.get(str(i), {}).get('title', '—')} |" for i in ids]
    (ROOT / 'footage' / 'CREDITS_SON.md').write_text('\n'.join(lines) + '\n')


def main():
    src, dst = sys.argv[1], sys.argv[2]
    edl_path = Path(sys.argv[3]) if len(sys.argv) > 3 and not sys.argv[3].startswith('--') else ROOT / 'footage' / 'edl.json'
    cues = json.load(open(src))
    edl = json.loads(edl_path.read_text())
    if edl_path.stem == 'edl':
        credits(edl)
    st = build(cues, edl)
    write_wav(dst, st)
    print(f'Bande-son écrite : {dst} ({st.shape[1] / SR:.2f} s)')


if __name__ == '__main__':
    main()
