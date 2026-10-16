"""
Voix du film « Huit voix » : synthèse vocale neuronale hors ligne, puis traitement en chuchotement.

Moteur : Kokoro-82M (poids sous licence Apache 2.0, entraîné uniquement sur des données libres ou sans droits —
https://huggingface.co/hexgrad/Kokoro-82M), exécuté localement avec kokoro-onnx (pip install kokoro-onnx).
Pour l'allemand, le néerlandais et le roumain, que Kokoro ne parle pas, on lui donne directement la prononciation
(alphabet phonétique) : il dit « Nacht », « nacht » et « noapte » avec ses propres voix.
La voix française (ff_siwis) vient du corpus SIWIS (CC BY 4.0) : attribution dans footage/CREDITS_SON_VOIX.md.

Chuchotement : on garde l'enveloppe spectrale de la voix (les formants, ce qui fait les voyelles et les consonnes)
et on remplace la vibration des cordes vocales par un souffle — exactement ce qui se passe quand on chuchote.
Techniquement : TFCT, lissage cepstral de chaque trame (on retire les harmoniques de la hauteur de voix),
excitation par un bruit à phase aléatoire, resynthèse par recouvrement-addition ; puis souffle aigu accentué,
grave coupé, et une part de la voix d'origine pour la présence (voix « soufflée »).
Chaque réglage a été validé par reconnaissance vocale automatique (faster-whisper) : le mot reste compris.

    python3 scripts/voices.py            → build/voices/out/*.wav (48 kHz) + build/voices/out/manifest.json
"""
import json
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / 'build' / 'voices' / 'kokoro'
OUT = ROOT / 'build' / 'voices' / 'out'
SR = 48000
KOKORO = 'https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/'

# nom → voix Kokoro, langue (None : texte donné en phonétique), texte, vitesse, rendu, réglages du rendu
# rendu : 'whisper' (chuchoté), 'breathy' (voix posée et soufflée), 'voice' (voix posée, très proche)
# réglages : (lissage cepstral, part de voix d'origine, suivi d'enveloppe, durée du N gardé voisé en attaque)
# Tous validés par reconnaissance vocale automatique à l'aveugle (faster-whisper « small ») : le mot est compris.
W = (70, 0.3, True, 0.07)
LINES = {
    'intro':  ('ff_siwis', 'fr-fr', 'La nuit a une odeur.', 0.9, 'whisper', (70, 0.55, True, 0.0)),
    'w_fr':   ('ff_siwis', 'fr-fr', 'Nuit.', 1.0, 'whisper', W),
    'w_it':   ('im_nicola', 'it', 'Notte !', 0.8, 'whisper', W),
    'w_es':   ('ef_dora', 'es', '¡Noche!', 1.0, 'whisper', W),
    'w_en':   ('bm_lewis', 'en-gb', 'Night.', 0.8, 'whisper', W),
    'w_pt':   ('pm_alex', 'pt-br', 'Noite.', 1.0, 'whisper', W),
    'w_ro':   ('if_sara', None, 'nwˈapte.', 1.0, 'whisper', W),      # noapte
    'w_de':   ('em_alex', None, 'nˈaxt.', 0.8, 'whisper', W),        # Nacht
    'w_nl':   ('af_heart', None, 'nˈaxt.', 0.8, 'whisper', W),       # nacht
    'vo_fin': ('ff_siwis', 'fr-fr', "Dans toutes les langues, la nuit s'écrit ène plus huit.", 0.85, 'breathy', (90, 0.3, True)),
    'vo_tag': ('ff_siwis', 'fr-fr', 'Maison de parfums nocturne.', 0.85, 'breathy', (90, 0.25, True)),
}


def ensure_models():
    MODELS.mkdir(parents=True, exist_ok=True)
    for f in ('kokoro-v1.0.onnx', 'voices-v1.0.bin'):
        if not (MODELS / f).exists():
            subprocess.run(['curl', '-s', '-L', '-C', '-', '--retry', '4', '-o', str(MODELS / f), KOKORO + f], check=True)


_TTS = None


def synth(voice, lang, text, speed):
    """Synthèse Kokoro (24 kHz) → 48 kHz, mono, float64."""
    global _TTS
    if _TTS is None:
        from kokoro_onnx import Kokoro
        ensure_models()
        _TTS = Kokoro(str(MODELS / 'kokoro-v1.0.onnx'), str(MODELS / 'voices-v1.0.bin'))
    if lang:
        a, sr = _TTS.create(text, voice=voice, speed=speed, lang=lang)
    else:
        a, sr = _TTS.create(text, voice=voice, speed=speed, is_phonemes=True)
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-f', 'f32le', '-ar', str(sr), '-ac', '1', '-i', '-',
                          '-af', 'aresample=resampler=soxr', '-f', 'f32le', '-ar', str(SR), '-'],
                         input=np.asarray(a, np.float32).tobytes(), capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).astype(np.float64)


def stft(x, n=2048, h=256):
    w = np.hanning(n)
    pad = np.concatenate([np.zeros(n), x, np.zeros(n)])
    frames = np.lib.stride_tricks.sliding_window_view(pad, n)[::h] * w
    return np.fft.rfft(frames, axis=1), w


def istft(S, w, length, n=2048, h=256):
    frames = np.fft.irfft(S, n, axis=1) * w
    out = np.zeros(len(frames) * h + n)
    norm = np.zeros_like(out)
    for i, f in enumerate(frames):
        out[i * h:i * h + n] += f
        norm[i * h:i * h + n] += w ** 2
    out /= np.maximum(norm, 1e-6)
    return out[n:n + length]


def whisperize(x, lifter=46, seed=1):
    """Enveloppe spectrale (lissage cepstral) × souffle à phase aléatoire."""
    S, w = stft(x)
    mag = np.abs(S) + 1e-9
    ceps = np.fft.irfft(np.log(mag), axis=1)
    ceps[:, lifter:-lifter] = 0
    env = np.exp(np.fft.rfft(ceps, axis=1).real)
    rng = np.random.default_rng(seed)
    noise = np.exp(1j * rng.uniform(0, 2 * np.pi, S.shape))
    return istft(env * noise, w, len(x))


def env_follow(y, x, ms=4.0):
    """Impose au souffle l'enveloppe temporelle fine de la voix : les silences d'occlusion (t, p, k) restent nets,
    et aucun souffle ne précède l'attaque (l'analyse spectrale étale le son de quelques millisecondes)."""
    k = max(1, int(ms * SR / 1000))
    ker = np.ones(k) / k
    ex = np.sqrt(np.convolve(x ** 2, ker, mode='same'))
    ey = np.sqrt(np.convolve(y ** 2, ker, mode='same'))
    return y * np.clip(ex / (ey + 1e-4 * ex.max()), 0, 4)


def shelf(x, f0, gain_db, high=True):
    n = 1 << (len(x) - 1).bit_length()
    f = np.fft.rfftfreq(n, 1 / SR)
    g = 10 ** (gain_db / 20)
    s = 1 / (1 + (f0 / np.maximum(f, 1)) ** 2) if high else 1 / (1 + (np.maximum(f, 1) / f0) ** 2)
    return np.fft.irfft(np.fft.rfft(x, n) * (1 + (g - 1) * s), n)[:len(x)]


def highpass(x, f0):
    n = 1 << (len(x) - 1).bit_length()
    f = np.fft.rfftfreq(n, 1 / SR)
    return np.fft.irfft(np.fft.rfft(x, n) / np.sqrt(1 + (f0 / np.maximum(f, 1)) ** 4), n)[:len(x)]


def trim(x, thr_db=-45):
    e = np.abs(x)
    k = int(0.01 * SR)
    env = np.convolve(e, np.ones(k) / k, mode='same')
    idx = np.nonzero(env > env.max() * 10 ** (thr_db / 20))[0]
    if not len(idx):
        return x
    a, b = max(0, idx[0] - int(0.03 * SR)), min(len(x), idx[-1] + int(0.12 * SR))
    y = x[a:b].copy()
    f = int(0.012 * SR)
    y[:f] *= np.linspace(0, 1, f)
    y[-f:] *= np.linspace(1, 0, f)
    return y


def nrm(x):
    return x / (np.abs(x).max() + 1e-9)


def onset(x, thr_db=-30):
    e = np.sqrt(np.convolve(x ** 2, np.ones(240) / 240, mode='same'))
    i = np.nonzero(e > e.max() * 10 ** (thr_db / 20))[0]
    return int(i[0]) if len(i) else 0


def render(kind, x, prm):
    """prm : lissage cepstral, part de voix d'origine, suivi d'enveloppe, durée (s) du N gardé voisé au début du mot."""
    if kind == 'voice' or not prm:
        return trim(nrm(shelf(x, 180, 3.0, high=False)) * 0.89)
    lifter, orig = prm[0], prm[1]
    follow = prm[2] if len(prm) > 2 else True
    nasal = prm[3] if len(prm) > 3 else 0.0
    w = whisperize(x, lifter=lifter, seed=1 if kind == 'whisper' else 3)
    if follow:
        w = env_follow(w, x)
    if kind == 'whisper':
        w = shelf(highpass(w, 180), 3500, 4.0)          # souffle
        v = x
    else:
        w = shelf(highpass(w, 150), 3500, 3.0)
        v = shelf(x, 180, 3.0, high=False)              # présence grave, voix de près
    # part de voix : 'orig' partout, sauf sur l'attaque du mot (le N nasal reste voisé, sinon il devient un souffle)
    g = np.full(len(x), orig)
    if nasal:
        t = (np.arange(len(x)) - onset(x)) / SR
        g = np.maximum(g, np.clip(1 - (t - nasal) / 0.05, 0, 1) * (t > -0.05))
    y = g * nrm(v) + (1 - g) * nrm(w)
    if kind == 'breathy':
        y = level(y)
    return trim(nrm(y) * 0.89)


def level(y, win=0.04, amount=0.45, max_db=9.0):
    """Nivelage doux des syllabes (une phrase dite tout bas : les fins de mots ne doivent pas s'éteindre)."""
    k = int(win * SR)
    e = np.sqrt(np.convolve(y ** 2, np.ones(k) / k, mode='same'))
    e = np.maximum(e / (e.max() + 1e-9), 10 ** (-max_db / 20 / amount) * 0.25)
    g = np.minimum(e ** -amount, 10 ** (max_db / 20))
    g = np.convolve(g, np.ones(k) / k, mode='same')
    return y * g


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    only = [a for a in sys.argv[1:] if not a.startswith('-')]
    manifest = {}
    for name, (voice, lang, text, speed, kind, prm) in LINES.items():
        if only and name not in only:
            continue
        x = synth(voice, lang, text, speed)
        y = render(kind, x, prm)
        pcm = (np.clip(y, -1, 1) * 32767).astype('<i2')
        with wave.open(str(OUT / f'{name}.wav'), 'wb') as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes(pcm.tobytes())
        manifest[name] = {'text': text, 'voice': voice, 'lang': lang or 'IPA', 'kind': kind, 'duration': round(len(y) / SR, 3)}
        print(f"{name:8s} {voice:10s} {kind:8s} {len(y) / SR:5.2f} s  « {text} »")
    old = json.loads((OUT / 'manifest.json').read_text()) if (OUT / 'manifest.json').exists() else {}
    (OUT / 'manifest.json').write_text(json.dumps({**old, **manifest}, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
