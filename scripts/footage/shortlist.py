"""
Présélection visuelle : pour chaque plan de footage/edl.json, retient les vidéos libres d'usage commercial
(Pexels trouvées pour ce plan, Coverr hors payantes / IA, Mixkit « Free License » dont le titre correspond),
privilégie les images sombres, et compose des planches (build/reel/review/<section>-<n>.png) pour choisir à l'œil.
Chaque vignette porte sa référence : « p:<id> » (Pexels), « c:<id> » (Coverr) ou « m:<id> » (Mixkit), à reporter
dans le champ "src" du plan.

    python3 scripts/footage/shortlist.py [--per 8] [--only p04,r01]
"""
import argparse
import concurrent.futures as cf
import json
import re
import subprocess
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageStat

ROOT = Path(__file__).resolve().parents[2]
MIX = ROOT / 'build' / 'reel' / 'mixkit' / 'index.json'
PEX = ROOT / 'build' / 'reel' / 'pexels' / 'index.json'
COV = ROOT / 'build' / 'reel' / 'coverr' / 'index.json'
THUMBS = ROOT / 'build' / 'reel' / 'thumbs'
REV = ROOT / 'build' / 'reel' / 'review'
UA = 'Mozilla/5.0 (X11; Linux x86_64) Chrome/140.0'
BAD = re.compile(r'\b(woman|women|girl|couple|kid|child|children|boy|dancing|yoga|boxing|soccer|fitness|gym|coffee|beer|tea|dj|'
                 r'phone|laptop|selfie|tourist|wedding|bride|halloween|pumpkin|marijuana|weed|cook|birthday|baby|dog|cat|bike|'
                 r'flag|3d|animation|loop|snow|beach|sunny|summer|happy|smil|laugh|office|business|meeting|christmas|valentine|'
                 r'vr|money|poker|crypto|bitcoin|cake|pasta|sandwich|food|zoo|eating|chewing|grazing|vape|vaping|cannabis|joint|'
                 r'hookah|shisha|family|friends|picnic|kids|teen|students?|hipster|skate|surf|tattoo|ai)\b')


def slugify(s):
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')


def pool():
    out = []
    if PEX.exists():
        for v in json.loads(PEX.read_text()).values():
            out.append({'ref': f"p:{v['id']}", 'text': v['slug'], 'label': v['slug'], 'dur': v.get('duration') or 99,
                        'thumb': v['thumb'], 'thumb_mp4': v['small'], 'w': v['w'], 'vertical': v['vertical'],
                        'shots': v.get('shots', [])})
    if MIX.exists():
        for v in json.loads(MIX.read_text()).values():
            if v['license'] == 'free' and v.get('preview') and v.get('hi'):
                out.append({'ref': f"m:{v['id']}", 'text': v['slug'], 'label': v['slug'], 'dur': v.get('duration') or 99,
                            'thumb_mp4': v['preview'], 'w': 1280, 'vertical': v.get('vertical', False)})
    if COV.exists():
        for v in json.loads(COV.read_text()).values():
            out.append({'ref': f"c:{v['id']}", 'text': slugify(v['title'] + ' ' + v['description']), 'label': slugify(v['title']),
                        'dur': v['duration'], 'thumb': v['thumb'], 'w': v.get('w') or 1920, 'vertical': v.get('vertical', False)})
    return out


def fetch(url, dst):
    if dst.exists():
        return True
    try:
        req = urllib.request.Request(url, headers={'User-Agent': UA})
        dst.write_bytes(urllib.request.urlopen(req, timeout=60).read())
        return True
    except Exception:
        return False


def thumb(c):
    """Vignette JPEG locale du candidat (image fournie par Coverr, ou image extraite de l'aperçu Mixkit)."""
    jpg = THUMBS / (c['ref'].replace(':', '_') + '.jpg')
    if jpg.exists():
        return jpg
    if c.get('thumb') and fetch(c['thumb'], jpg):
        return jpg
    if not c.get('thumb_mp4'):
        return None
    mp4 = THUMBS / (c['ref'].replace(':', '_') + '.mp4')
    if not fetch(c['thumb_mp4'], mp4):
        return None
    dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(mp4)],
                               capture_output=True, text=True).stdout or 4)
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-ss', f'{dur * 0.4:.2f}', '-i', str(mp4), '-frames:v', '1',
                    '-vf', 'scale=640:-2', str(jpg)])
    return jpg if jpg.exists() else None


def luma(jpg):
    try:
        return ImageStat.Stat(Image.open(jpg).convert('L').resize((64, 36))).mean[0] / 255
    except Exception:
        return 1.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--per', type=int, default=10)
    ap.add_argument('--rows', type=int, default=5)
    ap.add_argument('--only', default='')
    args = ap.parse_args()
    only = set(filter(None, args.only.split(',')))
    edl = json.loads((ROOT / 'footage' / 'edl.json').read_text())
    cands_all = pool()
    THUMBS.mkdir(parents=True, exist_ok=True)
    REV.mkdir(parents=True, exist_ok=True)
    picks = {}
    for sec in edl['sections']:
        rows = []
        extra = {'paris': 'px', 'oman': 'ox', 'roma': 'rx'}.get(sec['name'])
        shots = sec['shots'] + ([{'id': extra, 'beats': 1, 'q': ['autres'], 'mk': '^$'}] if extra else [])
        for sh in shots:
            if sh.get('render') or (only and sh['id'] not in only):
                continue
            rx = re.compile(r'\b(?:' + sh.get('mk', '^$') + ')')
            need = sh['beats'] * 60 / edl['bpm'] / sh.get('speed', 1.0)
            words = set(re.findall(r'[a-z]+', ' '.join(sh['q']))) - {'night', 'dark', 'slow', 'motion', 'close', 'up'}
            pex = [c for c in cands_all if sh['id'] in c.get('shots', []) and c['dur'] >= need]
            cands = [c for c in cands_all if c['ref'][0] != 'p' and rx.search(c['text']) and not BAD.search(c['text'].replace('-', ' '))
                     and c['dur'] >= need and not c['vertical']]
            cands.sort(key=lambda c: (-len(words & set(c['text'].split('-'))), c['ref'][0] != 'c'))
            cands = pex + cands[:max(0, args.per * 2 - len(pex))]
            with cf.ThreadPoolExecutor(8) as ex:
                jpgs = list(ex.map(thumb, cands))
            scored = []
            for c, j in zip(cands, jpgs):
                if j:
                    c['jpg'] = j
                    c['luma'] = luma(j)
                    # pertinence du titre, puis noirceur (la nuit), puis définition
                    scored.append((len(words & set(c['text'].split('-'))) * 0.35 + (1 - c['luma']) + (c['w'] >= 1920) * 0.15
                                   + (c['ref'][0] == 'p') * 2 - c['vertical'] * 0.8, c))
            scored.sort(key=lambda t: -t[0])
            best = [c for _, c in scored[:args.per]]
            picks[sh['id']] = [c['ref'] for c in best]
            rows.append((sh, best))
        tw, th, lab = 256, 144, 120
        for part in range(0, len(rows), args.rows):
            chunk = rows[part:part + args.rows]
            sheet = Image.new('RGB', (lab + tw * args.per, th * len(chunk)), (24, 24, 24))
            d = ImageDraw.Draw(sheet)
            for r, (sh, cands) in enumerate(chunk):
                d.text((6, r * th + 6), f"{sh['id']}\n{sh['q'][0][:18]}\n{sh['q'][1][:18] if len(sh['q']) > 1 else ''}",
                       fill=(230, 210, 160))
                for k, c in enumerate(cands):
                    try:
                        im = Image.open(c['jpg']).convert('RGB').resize((tw - 2, th - 2))
                    except Exception:
                        continue
                    sheet.paste(im, (lab + k * tw, r * th))
                    d.rectangle([lab + k * tw, r * th + th - 15, lab + k * tw + tw - 2, r * th + th - 2], fill=(0, 0, 0))
                    d.text((lab + k * tw + 3, r * th + th - 14), f"{k} {c['ref']}{' V' if c['vertical'] else ''} {c['label'][:24]}", fill=(255, 255, 255))
            name = f"{sec['name']}-{part // args.rows + 1}.png"
            sheet.save(REV / name)
            print(f'planche : build/reel/review/{name} ({len(chunk)} plans)')
    (REV / 'picks.json').write_text(json.dumps(picks, indent=1))


if __name__ == '__main__':
    main()
