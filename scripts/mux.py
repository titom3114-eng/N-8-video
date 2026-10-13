"""
Assemble les films finaux : vidéo master + bande-son normalisée (−14 LUFS, −1,5 dBTP),
encodage H.264 deux passes (~10 Mb/s) prêt pour la diffusion.

    python3 scripts/mux.py
"""
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD, OUT = ROOT / 'build', ROOT / 'output'
TARGET = dict(I=-14, TP=-1.5, LRA=11)
FILMS = [('16x9', 'N8_La-Nuit_16x9.mp4'), ('9x16', 'N8_La-Nuit_9x16.mp4')]


def run(cmd):
    return subprocess.run(cmd, check=True, capture_output=True, text=True)


def measure(wav):
    r = run(['ffmpeg', '-hide_banner', '-i', str(wav), '-af',
             f"loudnorm=I={TARGET['I']}:TP={TARGET['TP']}:LRA={TARGET['LRA']}:print_format=json", '-f', 'null', '-'])
    return json.loads(re.findall(r'\{[^{}]*\}', r.stderr)[-1])


def encode(src, wav, dst, m, tag):
    af = (f"loudnorm=I={TARGET['I']}:TP={TARGET['TP']}:LRA={TARGET['LRA']}"
          f":measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
          f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true,aresample=48000")
    v = ['-c:v', 'libx264', '-preset', 'slow', '-b:v', '10M', '-maxrate', '14M', '-bufsize', '20M',
         '-x264-params', 'aq-mode=3', '-pix_fmt', 'yuv420p', '-profile:v', 'high',
         '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709']
    log = str(BUILD / f'x264_{tag}')
    run(['ffmpeg', '-y', '-hide_banner', '-i', str(src), '-an', *v, '-pass', '1', '-passlogfile', log, '-f', 'mp4', '/dev/null'])
    run(['ffmpeg', '-y', '-hide_banner', '-i', str(src), '-i', str(wav), '-map', '0:v', '-map', '1:a', *v,
         '-pass', '2', '-passlogfile', log, '-af', af, '-c:a', 'aac', '-b:a', '256k', '-ar', '48000',
         '-movflags', '+faststart', '-shortest', str(dst)])


def main():
    OUT.mkdir(exist_ok=True)
    wav = BUILD / 'soundtrack.wav'
    m = measure(wav)
    print(f"Bande-son mesurée : {m['input_i']} LUFS, crête {m['input_tp']} dBTP → cible {TARGET['I']} LUFS")
    for tag, name in FILMS:
        src = BUILD / f'video_{tag}.mp4'
        encode(src, wav, OUT / name, m, tag)
        size = (OUT / name).stat().st_size / 1e6
        print(f'Film écrit : output/{name} ({size:.1f} Mo)')


if __name__ == '__main__':
    main()
