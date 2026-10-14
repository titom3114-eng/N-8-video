"""
Assemble le montage « Nuits » en images réelles, d'après footage/edl.json :
découpe de chaque vidéo au temps près, ralenti éventuel, recadrage 16:9 ou 9:16, léger travelling,
étalonnage or / noir (ou noir et blanc chaud), grain, vignettage, format 2.39:1 en paysage,
puis calque des titres (rendu par src/reel.html) par-dessus.

    python3 scripts/footage/assemble.py --format 16x9
    python3 scripts/footage/assemble.py --format 9x16
    python3 scripts/footage/assemble.py --format 16x9 --placeholders   (essai de la chaîne sans vidéos)

Sortie : build/reel/video_<format>.mp4 (sans son ; le son est ajouté par scripts/mux.py --film reel).
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EDL = ROOT / 'footage' / 'edl.json'
CLIPS = ROOT / 'footage' / 'clips'
OVERRIDE = ROOT / 'footage' / 'override'
BUILD = ROOT / 'build' / 'reel'
FORMATS = {'16x9': (1920, 1080), '9x16': (1080, 1920)}
FPS = 30
GRADES = {
    # or et noir : noirs écrasés, hautes lumières dorées, couleurs retenues
    'gold': ("eq=contrast=1.12:saturation=0.36:gamma=0.94:brightness=-0.02,"
             "colorbalance=rs=0.05:bs=-0.07:rm=0.08:gm=0.02:bm=-0.09:rh=0.09:gh=0.04:bh=-0.07,"
             "curves=all='0/0 0.12/0.025 0.38/0.25 0.72/0.66 1/0.95'"),
    # noir et blanc à peine réchauffé
    'mono': ("hue=s=0,eq=contrast=1.16:gamma=0.94,"
             "colorbalance=rh=0.05:gh=0.03:bh=-0.03:rm=0.02:bm=-0.02,"
             "curves=all='0/0 0.12/0.02 0.4/0.29 0.8/0.77 1/0.95'"),
}


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(r.stderr[-3000:])
        raise SystemExit(f'Échec : {" ".join(cmd[:6])} …')
    return r


def probe(path):
    out = run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
               'stream=width,height:format=duration', '-of', 'json', str(path)]).stdout
    j = json.loads(out)
    return {'w': j['streams'][0]['width'], 'h': j['streams'][0]['height'], 'dur': float(j['format']['duration'])}


def even(v):
    return max(2, int(round(v / 2)) * 2)


def source_for(sh, placeholders):
    if (OVERRIDE / f"{sh['id']}.mp4").exists():
        return OVERRIDE / f"{sh['id']}.mp4"
    if placeholders:
        p = BUILD / 'placeholder' / f"{sh['id']}.mp4"
        if not p.exists():
            p.parent.mkdir(parents=True, exist_ok=True)
            run(['ffmpeg', '-y', '-v', 'error', '-f', 'lavfi', '-i', 'testsrc2=size=1920x1080:rate=30:duration=8',
                 '-vf', f"drawtext=text='{sh['id']}':fontsize=160:fontcolor=white:x=(w-tw)/2:y=(h-th)/2",
                 '-c:v', 'libx264', '-preset', 'ultrafast', '-pix_fmt', 'yuv420p', str(p)])
        return p
    p = CLIPS / f"{sh['id']}.mp4"
    if not p.exists():
        raise SystemExit(f"Vidéo manquante pour le plan {sh['id']} : lancez scripts/footage/fetch.py "
                         f"ou déposez vos images dans footage/override/{sh['id']}.mp4")
    return p


def shot_filter(sh, info, W, H, d, portrait):
    speed = sh.get('speed', 1.0)
    need = d * speed
    if info['dur'] < need + 0.05:
        speed = max(0.2, (info['dur'] - 0.1) / d)
        need = d * speed
    ss = sh.get('in', max(0.0, (info['dur'] - need) * 0.45))
    move = sh.get('move', 'push')
    fx, fy = sh.get('focus_v' if portrait else 'focus', [0.5, 0.5])
    k0 = max(W / info['w'], H / info['h'])
    D = f'{d:.4f}'
    if move in ('push', 'pull'):
        z0, z1 = (1.0, 1.08) if move == 'push' else (1.08, 1.0)
        sw = even(info['w'] * k0)
        scale = f"scale=w='trunc({sw}*({z0}+({z1 - z0})*min(t/{D},1))/2)*2':h=-2:eval=frame:flags=lanczos"
        crop = f"crop={W}:{H}:x='(iw-{W})*{fx}':y='(ih-{H})*{fy}'"
    elif move in ('left', 'right'):
        sgn = -1 if move == 'left' else 1
        sw = even(info['w'] * k0 * 1.12)
        scale = f"scale={sw}:-2:flags=lanczos"
        crop = f"crop={W}:{H}:x='(iw-{W})*({fx}+{sgn}*0.42*(min(t/{D},1)-0.5))':y='(ih-{H})*{fy}'"
    else:
        sw = even(info['w'] * k0)
        scale = f"scale={sw}:-2:flags=lanczos"
        crop = f"crop={W}:{H}:x='(iw-{W})*{fx}':y='(ih-{H})*{fy}'"
    grade = GRADES[sh.get('grade', 'gold')]
    extra = sh.get('vf', '')
    chain = [f"trim=start={ss:.3f}:duration={need + 0.2:.3f}", f"setpts=(PTS-STARTPTS)/{speed:.4f}", f"fps={FPS}",
             scale, crop, grade]
    if k0 > 1.2:  # source agrandie (720p) : léger renforcement de netteté
        chain.append('unsharp=5:5:0.55:5:5:0')
    if extra:
        chain.append(extra)
    chain += ["tpad=stop_mode=clone:stop_duration=1", "setsar=1", "format=yuv420p"]
    return ','.join(chain)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--format', default='16x9', choices=sorted(FORMATS))
    ap.add_argument('--placeholders', action='store_true')
    ap.add_argument('--skip-overlay', action='store_true')
    args = ap.parse_args()
    W, H = FORMATS[args.format]
    portrait = H > W
    edl = json.loads(EDL.read_text())
    beat = 60 / edl['bpm']
    seg_dir = BUILD / f'seg_{args.format}'
    seg_dir.mkdir(parents=True, exist_ok=True)
    listing = []
    shots = [sh for sec in edl['sections'] for sh in sec['shots']]
    for i, sh in enumerate(shots):
        d = sh['beats'] * beat
        frames = round(d * FPS)
        seg = seg_dir / f"{i:03d}_{sh['id']}.mp4"
        if sh.get('render'):
            run(['ffmpeg', '-y', '-v', 'error', '-f', 'lavfi', '-i', f'color=c=black:s={W}x{H}:r={FPS}',
                 '-frames:v', str(frames), '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '12', '-pix_fmt', 'yuv420p', str(seg)])
        else:
            src = source_for(sh, args.placeholders)
            info = probe(src)
            vf = shot_filter(sh, info, W, H, d, portrait)
            run(['ffmpeg', '-y', '-v', 'error', '-i', str(src), '-an', '-vf', vf, '-frames:v', str(frames), '-r', str(FPS),
                 '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '12', '-pix_fmt', 'yuv420p', str(seg)])
        listing.append(f"file '{seg.as_posix()}'")
        print(f"[{args.format}] {sh['id']} {d:.2f} s")
    lst = BUILD / f'concat_{args.format}.txt'
    lst.write_text('\n'.join(listing) + '\n')
    base = BUILD / f'base_{args.format}.mp4'
    run(['ffmpeg', '-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', str(lst), '-c', 'copy', str(base)])

    ov = BUILD / f'ov_{args.format}'
    if not args.skip_overlay and not (ov / '00000.png').exists():
        run(['node', str(ROOT / 'scripts' / 'render.cjs'), '--page', 'reel.html', '--format', args.format,
             '--alpha', '--frames-dir', str(ov)])
    bar = round((H - W / 2.39) / 2) if not portrait else 0
    post = "noise=alls=7:allf=t+u,vignette=angle=PI/4.6"
    cmd = ['ffmpeg', '-y', '-v', 'error', '-i', str(base)]
    if args.skip_overlay:
        fc = f"[0:v]{post}[v]"
    else:
        cmd += ['-framerate', str(FPS), '-i', str(ov / '%05d.png')]
        fc = f"[0:v]{post}[b];[b][1:v]overlay=format=auto:shortest=1[v]"
    if bar:
        fc = fc[:-3] + f"[o];[o]drawbox=x=0:y=0:w=iw:h={bar}:color=black:t=fill,drawbox=x=0:y=ih-{bar}:w=iw:h={bar}:color=black:t=fill[v]"
    out = BUILD / f'video_{args.format}.mp4'
    cmd += ['-filter_complex', fc, '-map', '[v]', '-c:v', 'libx264', '-preset', 'slow', '-crf', '15', '-tune', 'film',
            '-pix_fmt', 'yuv420p', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709',
            '-movflags', '+faststart', str(out)]
    run(cmd)
    print(f'Vidéo écrite : {out}')


if __name__ == '__main__':
    main()
