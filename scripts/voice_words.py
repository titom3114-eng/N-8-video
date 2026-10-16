"""
Une seule voix pour « Nuits » : la même femme dit « la nuit » dans chaque langue.

Moteur : Chatterbox Multilingual (Resemble AI, licence MIT, https://github.com/resemble-ai/chatterbox), voix intégrée
du modèle (aucune voix de personne réelle n'est clonée), exécuté hors ligne. Les sorties portent le filigrane
inaudible « Perth » de Resemble AI (usage responsable de la synthèse vocale).

Un modèle autorégressif a tendance à répéter un mot isolé (« Nuit. Nuit ? ») : on génère plusieurs prises par mot,
puis scripts/voice_pick.py garde la meilleure première occurrence, vérifiée par reconnaissance vocale.

Environnement à part (Python 3.11, torch CPU) :
    uv venv build/tts-venv --python python3.11
    uv pip install --python build/tts-venv/bin/python torch==2.6.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cpu
    uv pip install --python build/tts-venv/bin/python chatterbox-tts==0.1.7 "setuptools<81"
    build/tts-venv/bin/python scripts/voice_words.py [mot …]        → build/voices/cb/<mot>_<prise>.wav
"""
import sys
from pathlib import Path

import torch
import torchaudio

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build' / 'voices' / 'cb'

# mot → prises : [(langue du modèle, texte, nombre de prises, durée maximale en s), …]
# (plusieurs écritures pour un même mot quand la première ne donne pas une prononciation nette)
WORDS = {
    'nuit':      [('fr', 'Nuit.', 6, 2.4)],
    'notte':     [('it', 'Notte.', 6, 2.4)],
    'layl':      [('ar', 'ليل.', 6, 2.4), ('ar', 'لَيْل.', 6, 2.4), ('ar', 'لَيْلْ!', 6, 2.4)],
    'night':     [('en', 'Night.', 6, 2.4)],
    'noche':     [('es', 'Noche.', 6, 2.4)],
    'nacht':     [('de', 'Nacht.', 6, 2.4)],
    'noite':     [('pt', 'Noite.', 6, 2.4)],
    'nacht_nl':  [('nl', 'Nacht.', 6, 2.4)],
    'natt':      [('sv', 'Natt.', 6, 2.4), ('no', 'Natt.', 6, 2.4), ('da', 'Nat.', 6, 2.4),
                  ('fr', 'Natte.', 6, 2.4), ('de', 'Natt.', 6, 2.4),   # le français « natte » se dit exactement [nat]
                  ('es', 'Nat.', 6, 2.4), ('it', 'Nat.', 6, 2.4),      # [a] bien ouvert des voyelles espagnoles et italiennes
                  ('sv', 'Natten.', 6, 2.4), ('sv', 'Natt, natt.', 6, 2.4)],
    'noapte':    [('it', 'Noapte.', 6, 2.4)],     # le roumain n'est pas dans le modèle : lecture italienne, très proche
    'nychta':    [('el', 'Νύχτα.', 6, 2.4)],
    'fin':       [('fr', "Dans toutes les langues, la nuit s'écrit ène plus huit.", 6, 8.0)],
    # dans le silence avant le logo : « huit » tombe sur l'impact
    'fin_court': [('fr', "La nuit s'écrit… ène plus huit.", 8, 5.0), ('fr', "La nuit s'écrit N plus huit.", 6, 5.0),
                  ('fr', "La nuit s'écrit : N plus 8.", 6, 5.0), ('fr', "La nuit s'écrit… Enne. Plus. Huit.", 6, 5.0)],
}


def main():
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS
    torch.set_num_threads(4)
    OUT.mkdir(parents=True, exist_ok=True)
    m = ChatterboxMultilingualTTS.from_pretrained(device='cpu')
    inference = m.t3.inference
    only = [a for a in sys.argv[1:] if not a.startswith('-')]
    first = '--from' in sys.argv and int(sys.argv[sys.argv.index('--from') + 1]) or 0
    only = [a for a in only if not a.isdigit()]
    for key, variants in WORDS.items():
        if only and key not in only:
            continue
        n = 0
        for lang, text, takes, max_s in variants:
            # borne la génération (25 jetons de parole par seconde) : une prise qui s'égare s'arrête vite
            m.t3.inference = lambda *a, _mx=int(max_s * 25), **k: inference(*a, **{**k, 'max_new_tokens': _mx})
            for take in range(takes):
                if n >= first and not (OUT / f'{key}_{n}.wav').exists():
                    torch.manual_seed(1000 + take)
                    wav = m.generate(text, language_id=lang, exaggeration=0.45, cfg_weight=0.35, temperature=0.7)
                    torchaudio.save(str(OUT / f'{key}_{n}.wav'), wav, m.sr)
                    print(key, n, lang, text, round(wav.shape[-1] / m.sr, 2), flush=True)
                n += 1


if __name__ == '__main__':
    main()
