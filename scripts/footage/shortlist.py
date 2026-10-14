"""
Présélection visuelle : pour chaque plan de footage/edl.json, retient les vidéos Mixkit en licence libre
dont le titre correspond au plan, télécharge leur aperçu 360p et compose une planche par section
(build/reel/review/<section>.png) pour choisir à l'œil.

    python3 scripts/footage/shortlist.py [--per 6] [--only p04,r01]
"""
import argparse
import concurrent.futures as cf
import json
import re
import subprocess
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
IDX = ROOT / 'build' / 'reel' / 'mixkit' / 'index.json'
PRE = ROOT / 'build' / 'reel' / 'mixkit' / 'previews'
REV = ROOT / 'build' / 'reel' / 'review'
UA = 'Mozilla/5.0 (X11; Linux x86_64) Chrome/140.0'
BAD = re.compile(r'(woman|girl|couple|kid|child|boy|dancing|yoga|boxing|soccer|fitness|gym|coffee|beer|tea|dj|phone|laptop|selfie|'
                 r'tourist|wedding|bride|halloween|pumpkin|marijuana|weed|cook|birthday|baby|dog|cat|bike|traffic|flag|3d|animation|'
                 r'loop|snow|beach|sunny|summer|happy|smil|laugh|office|business|meeting|christmas|valentine|vr|money|poker|'
                 r'crypto|bitcoin|cake|pasta|sandwich|food|zoo|eating|chewing|grazing|baby)')


def fetch(url, dst):
    if dst.exists():
        return True
    try:
        req = urllib.request.Request(url, headers={'User-Agent': UA})
        dst.write_bytes(urllib.request.urlopen(req, timeout=60).read())
        return True
    except Exception:
        return False


def frame(mp4, at=0.4):
    jpg = mp4.with_suffix('.jpg')
    if not jpg.exists():
        dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(mp4)],
                                   capture_output=True, text=True).stdout or 4)
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-ss', f'{dur * at:.2f}', '-i', str(mp4), '-frames:v', '1', '-vf', 'scale=320:-2', str(jpg)])
    return jpg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--per', type=int, default=6)
    ap.add_argument('--only', default='')
    args = ap.parse_args()
    only = set(filter(None, args.only.split(',')))
    edl = json.loads((ROOT / 'footage' / 'edl.json').read_text())
    index = json.loads(IDX.read_text())
    free = [v for v in index.values() if v['license'] == 'free' and v.get('preview') and v.get('hi')]
    PRE.mkdir(parents=True, exist_ok=True)
    REV.mkdir(parents=True, exist_ok=True)
    picks = {}
    for sec in edl['sections']:
        rows = []
        for sh in sec['shots']:
            if sh.get('render') or (only and sh['id'] not in only):
                continue
            rx = re.compile(r'\b(?:' + sh.get('mk', '^$') + ')')
            need = sh['beats'] * 60 / edl['bpm'] / sh.get('speed', 1.0)
            cands = [v for v in free if rx.search(v['slug']) and not BAD.search(v['slug']) and (v['duration'] or 99) >= need]
            words = set(re.findall(r'[a-z]+', ' '.join(sh['q'])))
            cands.sort(key=lambda v: -len(words & set(v['slug'].split('-'))))
            cands = cands[:args.per]
            picks[sh['id']] = [c['id'] for c in cands]
            rows.append((sh, cands))
        if not rows:
            continue
        with cf.ThreadPoolExecutor(8) as ex:
            list(ex.map(lambda c: fetch(c['preview'], PRE / f"{c['id']}.mp4"), [c for _, cs in rows for c in cs]))
        tw, th, lab = 320, 180, 150
        sheet = Image.new('RGB', (lab + tw * args.per, th * len(rows)), (20, 20, 20))
        d = ImageDraw.Draw(sheet)
        for r, (sh, cands) in enumerate(rows):
            d.text((6, r * th + 6), f"{sh['id']}\n{sh['q'][0][:22]}", fill=(230, 210, 160))
            for k, c in enumerate(cands):
                mp4 = PRE / f"{c['id']}.mp4"
                if not mp4.exists():
                    continue
                try:
                    im = Image.open(frame(mp4)).convert('RGB').resize((tw, th))
                except Exception:
                    continue
                sheet.paste(im, (lab + k * tw, r * th))
                d.rectangle([lab + k * tw, r * th + th - 16, lab + k * tw + tw, r * th + th], fill=(0, 0, 0))
                d.text((lab + k * tw + 4, r * th + th - 14), f"{c['id']} {c['slug'][:40]}", fill=(255, 255, 255))
        sheet.save(REV / f"{sec['name']}.png")
        print(f"planche : build/reel/review/{sec['name']}.png ({len(rows)} plans)")
    (REV / 'picks.json').write_text(json.dumps(picks, indent=1))


if __name__ == '__main__':
    main()
