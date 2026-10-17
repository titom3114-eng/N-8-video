"""
« Nuits » avec la voix chuchotée : la voix de femme de « Huit voix » (celle qui chuchote « La nuit a une odeur »)
dit « la nuit » dans la langue de chaque ville, puis « La nuit s'écrit… N plus huit. »

Même voix pour toutes les langues : Kokoro-82M (Apache 2.0), voix « ff_siwis » ; pour les langues étrangères on lui
donne la prononciation (alphabet phonétique), elle les dit donc avec la même voix. Même traitement que dans
« Huit voix » : chuchotement (scripts/voices.py, render 'whisper'), avec une part de voix pour garder le souffle humain.
Pour chaque mot, plusieurs variantes (prononciation, débit, dosage) ; une reconnaissance vocale à l'aveugle
(faster-whisper « small ») garde la plus chuchotée de celles qui sont bien comprises.

    python3 scripts/voice_chuchote.py [mot …]   → build/voices/nuits_chuchote/<mot>.wav + choix.json
"""
import json
import re
import sys
import unicodedata
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import voices as V  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build' / 'voices' / 'nuits_chuchote'
SR = V.SR
VOICE = 'ff_siwis'

# mot → (langue pour la vérification, variantes [(langue Kokoro ou None = phonétique, texte)])
WORDS = {
    'nuit':     ('fr', [('fr-fr', 'Nuit.')]),
    'notte':    ('it', [('it', 'Notte.'), (None, 'nˈɔtːe.'), (None, 'nˈɔtːe!'), ('it', 'Notte !'), (None, 'nˈɔt.te.'),
                        (None, 'nˈotːe!')]),
    'layl':     ('ar', [(None, 'lˈajl.'), (None, 'lˈajl!'), (None, 'lˈajːl.'), (None, 'lˈɛjl.'), (None, 'lˈaɪl!'),
                        (None, 'lˈejl.')]),
    'night':    ('en', [('en-gb', 'Night.'), ('en-us', 'Night.'), (None, 'nˈaɪt!')]),
    'noche':    ('es', [('es', 'Noche.'), ('es', '¡Noche!'), (None, 'nˈotʃe.')]),
    'nacht':    ('de', [(None, 'nˈaxt.'), (None, 'nˈaxt!'), (None, 'nˈaːxt.')]),
    'noite':    ('pt', [('pt-br', 'Noite.'), (None, 'nˈojtɨ.'), (None, 'nˈoɪtə.')]),
    'nacht_nl': ('nl', [(None, 'nˈaxt.'), (None, 'nˈɑxt.'), (None, 'nˈɑxt!'), (None, 'nˈaχt.'), (None, 'nˈɑχt!'),
                        ('nl', 'Nacht.')]),
    'natt':     ('sv', [(None, 'nˈat.'), (None, 'nˈatː.'), (None, 'nˈat!')]),
    'noapte':   ('ro', [(None, 'nwˈapte.'), (None, 'nˈɔapte.'), (None, 'nwˈapte!')]),
    'nychta':   ('el', [(None, 'nˈixta.'), (None, 'nˈiçta.'), (None, 'nˈixta!')]),
    'fin':      ('fr', [('fr-fr', "La nuit s'écrit… ène plus huit.")]),
}
TARGET = {'nuit': 'nuit', 'notte': 'notte', 'layl': 'ليل', 'night': 'night', 'noche': 'noche', 'nacht': 'nacht',
          'noite': 'noite', 'nacht_nl': 'nacht', 'natt': 'natt', 'noapte': 'noapte', 'nychta': 'νιχτα',
          'fin': "la nuit s'ecrit n plus huit"}
ALIASES = {'natt': {'nat'}, 'layl': {'الليل'}}
SPEEDS = (0.9, 1.0)
DOSES = (0.45, 0.55, 0.65, 0.75)    # part de voix d'origine : 0,55 = le réglage de « La nuit a une odeur »
FIN_GAP = 0.3                       # « La nuit s'écrit… » silence « … N plus huit. »


def norm(s):
    s = s.lower().translate(str.maketrans({'υ': 'ι', 'ύ': 'ι', 'η': 'ι', 'ή': 'ι', 'ί': 'ι'}))
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = s.replace('8', 'huit').replace('ène', 'n').replace('n+', 'n plus ')
    s = re.sub(r"[^\w' ]", ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


def asr_model():
    from faster_whisper import WhisperModel
    return WhisperModel('small', device='cpu', compute_type='int8', cpu_threads=4)


def transcribe(m, y, lang, prompt=None):
    a = np.interp(np.linspace(0, len(y) - 1, int(len(y) * 16000 / SR)), np.arange(len(y)), y).astype(np.float32)
    a = np.concatenate([np.zeros(4000, np.float32), a, np.zeros(8000, np.float32)])
    segs, _ = m.transcribe(a, language=lang, beam_size=5, condition_on_previous_text=False, initial_prompt=prompt)
    segs = list(segs)
    return ' '.join(s.text.strip() for s in segs), (float(np.mean([s.avg_logprob for s in segs])) if segs else -9.0)


def env_db(x, win=0.01):
    k = int(win * SR)
    e = np.sqrt(np.convolve(x ** 2, np.ones(k) / k, mode='same')) + 1e-9
    return 20 * np.log10(e / e.max())


def syllables(y, thr=-20):
    """Passages au-dessus de `thr` dB (les syllabes), séparés par des creux d'au moins 30 ms."""
    loud = env_db(y) > thr
    runs, i, n = [], 0, len(y)
    while i < n:
        if loud[i]:
            j = i
            while j < n and loud[j]:
                j += 1
            if runs and i - runs[-1][1] < int(0.03 * SR):
                runs[-1][1] = j
            else:
                runs.append([i, j])
            i = j
        else:
            i += 1
    return runs


def add_pause(y, gap=FIN_GAP):
    """« La nuit s'écrit… N plus huit » : silence inséré au creux qui précède « ène » (antépénultième syllabe)."""
    r = syllables(y)
    if len(r) < 4:
        return y
    e = env_db(y)
    a, b = r[-4][1], r[-3][0]
    i = a + int(np.argmin(e[a:b])) if b > a else a
    f = int(0.006 * SR)
    p, q = y[:i].copy(), y[i:].copy()
    p[-f:] *= np.linspace(1, 0, f)
    q[:f] *= np.linspace(0, 1, f)
    return np.concatenate([p, np.zeros(int(gap * SR)), q])


def last_onset(y):
    """Attaque de la dernière syllabe (« huit »)."""
    r = syllables(y)
    return float(r[-1][0] / SR) if r else len(y) / SR - 0.3


def stress_last(y, slow=0.78, gain_db=5.0):
    """« huit » chuchoté est bref et faible : on le dit un peu plus lentement et un peu plus fort (dernier mot de la phrase)."""
    import subprocess
    r = syllables(y)
    i = max(0, r[-1][0] - int(0.05 * SR))
    tail = y[i:]
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-f', 'f64le', '-ar', str(SR), '-ac', '1', '-i', '-', '-af', f'atempo={slow}',
                          '-f', 'f64le', '-'], input=tail.astype(np.float64).tobytes(), capture_output=True, check=True).stdout
    tail = np.frombuffer(raw, np.float64) * 10 ** (gain_db / 20)
    f = int(0.01 * SR)
    tail[:f] *= np.linspace(0, 1, f)
    head = y[:i].copy()
    head[-f:] *= np.linspace(1, 0, f)
    return np.concatenate([head[:-f], head[-f:] + tail[:f], tail[f:]])


def save(path, y):
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
    for key, (alang, variants) in WORDS.items():
        if only and key not in only:
            continue
        best = None
        for lang, text in variants:
            for speed in SPEEDS:
                x = V.synth(VOICE, lang, text, speed)
                for dose in DOSES:
                    y = V.render('whisper', x, (70, dose, True, 0.07 if key != 'fin' else 0.0))
                    if key == 'fin':
                        y = stress_last(add_pause(y))
                    t, lp = transcribe(m, y, alang, "La nuit s'écrit N plus huit." if key == 'fin' else None)
                    ok = norm(t) in {norm(TARGET[key])} | ALIASES.get(key, set())
                    # la plus chuchotée parmi les prises comprises, puis la plus sûre
                    score = (ok, -dose, lp)
                    print(f"  {key:8s} {text:34s} v{speed} voix {dose:.2f} : « {t} » {lp:.2f} {'OK' if ok else '--'}", flush=True)
                    if best is None or score > best[0]:
                        best = (score, y, dict(texte=text, langue=lang or 'phonétique', vitesse=speed, part_de_voix=dose,
                                               compris=t, ok=ok))
        y = best[1] / (np.abs(best[1]).max() + 1e-9) * 0.89
        save(OUT / f'{key}.wav', y)
        info = {**best[2], 'duree': round(len(y) / SR, 3)}
        if key == 'fin':
            info['huit'] = round(last_onset(y), 3)
        choice[key] = info
        print(f"{key}: « {info['compris']} » {'compris' if info['ok'] else 'NON COMPRIS'} — {info}", flush=True)
    (OUT / 'choix.json').write_text(json.dumps(choice, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
