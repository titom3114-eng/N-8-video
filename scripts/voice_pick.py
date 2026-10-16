"""
Choisit, pour chaque mot de scripts/voice_words.py, la meilleure prise : on isole la première occurrence du mot
(le modèle a tendance à le répéter), puis une reconnaissance vocale à l'aveugle (faster-whisper « small ») vérifie
qu'il est bien compris ; à égalité, la prise la plus sûre (meilleure vraisemblance) l'emporte.

    python3 scripts/voice_pick.py      → build/voices/nuits/<mot>.wav (48 kHz, mono) + choix.json
"""
import json
import re
import subprocess
import sys
import unicodedata
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'build' / 'voices' / 'cb'
OUT = ROOT / 'build' / 'voices' / 'nuits'
SR = 48000
ASR_LANG = {'nuit': 'fr', 'notte': 'it', 'layl': 'ar', 'night': 'en', 'noche': 'es', 'nacht': 'de', 'noite': 'pt',
            'nacht_nl': 'nl', 'natt': 'sv', 'noapte': 'ro', 'nychta': 'el', 'fin': 'fr', 'fin_court': 'fr'}
TARGET = {'nuit': 'nuit', 'notte': 'notte', 'layl': 'ليل', 'night': 'night', 'noche': 'noche', 'nacht': 'nacht',
          'noite': 'noite', 'nacht_nl': 'nacht', 'natt': 'natt', 'noapte': 'noapte', 'nychta': 'νυχτα',
          'fin': "dans toutes les langues la nuit s'ecrit n plus huit", 'fin_court': "la nuit s'ecrit n plus huit"}
SENTENCES = {'fin', 'fin_court'}
ALIASES = {'natt': {'nat', 'natten'}, 'layl': {'ليل', 'الليل'}}
GAP = {'natt': 0.25, 'notte': 0.2}
# « natt » : la voix ne prononce un [a] ouvert que dans « natten » ; on coupe juste après le « tt » → « natt »
CUT = {'natt': 0.40}   # occlusion longue (« natten », « notte ») : ne pas couper le mot en deux


def load(p):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(p), '-f', 'f32le', '-ac', '1', '-ar', str(SR), '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).astype(np.float64)


def norm(s):
    # grec : ι, υ, η se prononcent tous [i] (« νύχτα » s'entend aussi bien écrit « νίχτα »)
    s = s.lower().translate(str.maketrans({'υ': 'ι', 'ύ': 'ι', 'η': 'ι', 'ή': 'ι', 'ί': 'ι'}))
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = s.replace('8', 'huit').replace('ène', 'n').replace('n+', 'n plus ')
    s = re.sub(r"[^\w' ]", ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


def envelope_db(x, win=0.01):
    k = int(win * SR)
    e = np.sqrt(np.convolve(x ** 2, np.ones(k) / k, mode='same')) + 1e-9
    return 20 * np.log10(e / e.max())


def first_word(x, gap=0.12, floor=-38):
    """Première occurrence : de l'attaque jusqu'au premier silence d'au moins `gap` secondes."""
    e = envelope_db(x)
    on = np.nonzero(e > -30)[0]
    if not len(on):
        return None
    a = on[0]
    quiet = e < floor
    n_gap = int(gap * SR)
    i, run = a, 0
    while i < len(x):
        run = run + 1 if quiet[i] else 0
        if run >= n_gap:
            b = i - n_gap
            break
        i += 1
    else:
        b = len(x) - 1
    return fade(x[max(0, a - int(0.03 * SR)):min(len(x), b + int(0.08 * SR))])


def fade(y, fi=0.01, fo=0.06):
    y = y.copy()
    a, b = int(fi * SR), int(fo * SR)
    y[:a] *= np.linspace(0, 1, a)
    y[-b:] *= np.linspace(1, 0, b) ** 1.5
    return y


def asr_model():
    from faster_whisper import WhisperModel
    return WhisperModel('small', device='cpu', compute_type='int8', cpu_threads=4)


def transcribe(m, y, lang, words=False):
    a = np.interp(np.linspace(0, len(y) - 1, int(len(y) * 16000 / SR)), np.arange(len(y)), y).astype(np.float32)
    a = np.concatenate([np.zeros(4000, np.float32), a, np.zeros(8000, np.float32)])
    segs, _ = m.transcribe(a, language=lang, beam_size=5, condition_on_previous_text=False, word_timestamps=words,
                           initial_prompt="La nuit s'écrit N plus huit." if lang == 'fr' and words else None)
    segs = list(segs)
    text = ' '.join(s.text.strip() for s in segs)
    lp = float(np.mean([s.avg_logprob for s in segs])) if segs else -9.0
    return text, lp, ([w for s in segs for w in s.words] if words else [])


def cut_sentence(m, x, lang, last='huit'):
    """Phrase : on coupe juste après son dernier mot (une prise peut continuer au-delà)."""
    text, lp, words = transcribe(m, x, lang, words=True)
    end = None
    for w in words:
        if norm(w.word).endswith(last) or norm(w.word) == '8':
            end = w.end - 0.25
            break
    if end is None:
        return None, text, lp
    e = envelope_db(x)
    b = int((end + 0.05) * SR)
    # fin du mot : premier vrai silence après l'horodatage
    while b < len(x) - 1 and e[b] > -38:
        b += 1
    on = np.nonzero(e > -30)[0]
    return fade(x[max(0, on[0] - int(0.03 * SR)):min(len(x), b + int(0.08 * SR))]), text, lp


def save(path, y):
    y = y / (np.abs(y).max() + 1e-9) * 0.89
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(y, -1, 1) * 32767).astype('<i2').tobytes())


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    m = asr_model()
    only = [a for a in sys.argv[1:] if not a.startswith('-')]
    choice = json.loads((OUT / 'choix.json').read_text()) if (OUT / 'choix.json').exists() else {}
    for key, lang in ASR_LANG.items():
        if only and key not in only:
            continue
        takes = sorted(SRC.glob(f'{key}_[0-9]*.wav'))
        best = None
        for p in takes:
            x = load(p)
            if key in SENTENCES:
                y, text, lp = cut_sentence(m, x, lang)
                if y is None:
                    print(f'  {p.name}: « {text} » (pas de fin nette)')
                    continue
                text, lp, _ = transcribe(m, y, lang)
            else:
                y = first_word(x, gap=GAP.get(key, 0.12))
                if y is None:
                    continue
                text, lp, _ = transcribe(m, y, lang)
            d = len(y) / SR
            ok = norm(text) in {norm(TARGET[key])} | ALIASES.get(key, set()) and (key in SENTENCES or 0.25 < d < 1.3)
            score = (ok, lp)
            print(f"  {p.name}: {d:4.2f} s « {text} » {lp:.2f} {'OK' if ok else '--'}", flush=True)
            if best is None or score > best[0]:
                best = (score, p.name, y, text, d)
        if best and key in CUT:
            y = fade(best[2][:int(CUT[key] * SR)], fo=0.03)
            text, lp, _ = transcribe(m, y, lang)
            ok = norm(text) == norm(TARGET[key])
            print(f"  coupé à {CUT[key]} s : « {text} » {'OK' if ok else '--'}")
            best = ((ok, lp), best[1] + f' (coupé à {CUT[key]} s)', y, text, len(y) / SR)
        if best:
            save(OUT / f'{key}.wav', best[2])
            choice[key] = {'prise': best[1], 'compris': best[3], 'ok': best[0][0], 'duree': round(best[4], 3)}
            print(f"{key}: {best[1]} « {best[3]} » {'compris' if best[0][0] else 'NON COMPRIS'}", flush=True)
    (OUT / 'choix.json').write_text(json.dumps(choice, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
