"""
Assemble les films finaux : vidéo master + bande-son normalisée (−14 LUFS, −1,5 dBTP),
encodage H.264 deux passes (~10 Mb/s) prêt pour la diffusion, plus un aperçu 720p (< 30 Mo).

    python3 scripts/mux.py                     # film « La nuit »  (build/ → output/N8_La-Nuit_*)
    python3 scripts/mux.py --film nuits        # film « Nuits »    (build/nuits/ → output/N8_Nuits_*)
"""
import argparse
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'output'
TARGET = dict(I=-14, TP=-1.5, LRA=11)
FILMS = {
    'la-nuit': (ROOT / 'build', 'N8_La-Nuit'),
    'nuits': (ROOT / 'build' / 'nuits', 'N8_Nuits'),
}
BUILD = FILMS['la-nuit'][0]


def run(cmd):
    return subprocess.run(cmd, check=True, capture_output=True, text=True)


def measure(wav):
    r = run(['ffmpeg', '-hide_banner', '-i', str(wav), '-af',
             f"loudnorm=I={TARGET['I']}:TP={TARGET['TP']}:LRA={TARGET['LRA']}:print_format=json", '-f', 'null', '-'])
    return json.loads(re.findall(r'\{[^{}]*\}', r.stderr)[-1])


def loudnorm(m):
    return (f"loudnorm=I={TARGET['I']}:TP={TARGET['TP']}:LRA={TARGET['LRA']}"
            f":measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
            f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true,aresample=48000")


def encode(src, wav, dst, m, tag, build=BUILD, scale=None, vbr='10M', maxrate='14M', bufsize='20M', abr='256k'):
    v = ['-c:v', 'libx264', '-preset', 'slow', '-b:v', vbr, '-maxrate', maxrate, '-bufsize', bufsize,
         '-x264-params', 'aq-mode=3', '-pix_fmt', 'yuv420p', '-profile:v', 'high',
         '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709']
    if scale:
        v = ['-vf', f'scale={scale}:flags=lanczos'] + v
    log = str(build / f'x264_{tag}')
    run(['ffmpeg', '-y', '-hide_banner', '-i', str(src), '-an', *v, '-pass', '1', '-passlogfile', log, '-f', 'mp4', '/dev/null'])
    run(['ffmpeg', '-y', '-hide_banner', '-i', str(src), '-i', str(wav), '-map', '0:v', '-map', '1:a', *v,
         '-pass', '2', '-passlogfile', log, '-af', loudnorm(m), '-c:a', 'aac', '-b:a', abr, '-ar', '48000',
         '-movflags', '+faststart', '-shortest', str(dst)])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--film', default='la-nuit', choices=sorted(FILMS))
    ap.add_argument('--formats', default='16x9,9x16')
    args = ap.parse_args()
    build, name = FILMS[args.film]
    OUT.mkdir(exist_ok=True)
    (OUT / 'apercu').mkdir(exist_ok=True)
    wav = build / 'soundtrack.wav'
    m = measure(wav)
    print(f"Bande-son mesurée : {m['input_i']} LUFS, crête {m['input_tp']} dBTP → cible {TARGET['I']} LUFS")
    for tag in args.formats.split(','):
        src = build / f'video_{tag}.mp4'
        dst = OUT / f'{name}_{tag}.mp4'
        encode(src, wav, dst, m, tag, build)
        print(f'Film écrit : output/{dst.name} ({dst.stat().st_size / 1e6:.1f} Mo)')
        prev = OUT / 'apercu' / f'{name}_{tag}_apercu-720p.mp4'
        encode(src, wav, prev, m, f'prev_{tag}', build, scale='1280:720' if tag == '16x9' else '720:1280',
               vbr='3400k', maxrate='4500k', bufsize='7000k', abr='160k')
        print(f'Aperçu écrit : output/apercu/{prev.name} ({prev.stat().st_size / 1e6:.1f} Mo)')


if __name__ == '__main__':
    main()
