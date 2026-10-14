"""
Récupère les vidéos réelles du montage « Nuits » (images réelles) d'après footage/edl.json.

Sources (libres de droits, usage commercial et publicitaire autorisé, sans attribution obligatoire) :
  - choix à l'œil : champ "src" du plan — « p:<id> » Pexels (index build/reel/pexels, scripts/footage/pexels.py),
    « c:<id> » Coverr (scripts/footage/coverr_index.py), « m:<id> » Mixkit Free License (mixkit_index.py)
  - recherche automatique à défaut : Pexels (variable PEXELS_API_KEY) puis Mixkit

    python3 scripts/footage/fetch.py                 # tous les plans manquants
    python3 scripts/footage/fetch.py --only p04,r01  # certains plans
    python3 scripts/footage/fetch.py --redo p04      # remplace un plan (exclut la vidéo précédente)

Un fichier déposé dans footage/override/<id>.mp4 (vos propres images) est toujours prioritaire.
Les vidéos vont dans footage/clips/<id>.mp4 avec leur fiche <id>.json ; les crédits dans footage/CREDITS.md.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EDL = ROOT / 'footage' / 'edl.json'
CLIPS = ROOT / 'footage' / 'clips'
OVERRIDE = ROOT / 'footage' / 'override'
UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36'


def http(url, headers=None, timeout=60):
    req = urllib.request.Request(url, headers={'User-Agent': UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def download(url, dst):
    tmp = dst.with_suffix('.part')
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=300) as r, open(tmp, 'wb') as f:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
    tmp.rename(dst)


def probe(path):
    out = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                          'stream=width,height,r_frame_rate:format=duration', '-of', 'json', str(path)],
                         capture_output=True, text=True, check=True).stdout
    j = json.loads(out)
    s = j['streams'][0]
    num, den = s['r_frame_rate'].split('/')
    return {'width': s['width'], 'height': s['height'], 'fps': float(num) / float(den or 1), 'duration': float(j['format']['duration'])}


# ------------------------------------------------------------------ Pexels
def pexels_candidates(query, key, min_dur):
    url = 'https://api.pexels.com/videos/search?' + urllib.parse.urlencode({'query': query, 'per_page': 20, 'orientation': 'landscape'})
    data = json.loads(http(url, {'Authorization': key}))
    out = []
    for v in data.get('videos', []):
        if v.get('duration', 0) < min_dur:
            continue
        files = [f for f in v.get('video_files', []) if f.get('file_type') == 'video/mp4' and f.get('width')]
        if not files:
            continue
        # le plus grand fichier ≤ 4K (le 4K permet un recadrage vertical net)
        files.sort(key=lambda f: f['width'])
        best = [f for f in files if f['width'] <= 3840][-1]
        if best['width'] < 1280:
            continue
        out.append({
            'provider': 'pexels', 'uid': f"pexels:{v['id']}", 'link': best['link'], 'width': best['width'], 'height': best['height'],
            'duration': v['duration'], 'page': v.get('url'), 'author': (v.get('user') or {}).get('name'),
            'author_url': (v.get('user') or {}).get('url'), 'license': 'Pexels License (https://www.pexels.com/license/)',
            'score': min(best['width'], 3840) / 3840 + min(v['duration'], 20) / 40,
        })
    return out


# ------------------------------------------------------------------ Mixkit
MIX_RE = re.compile(r'https://assets\.mixkit\.co/videos/[^"\'\s<>]+?\.mp4')


def mixkit_candidates(query, min_dur):
    slug = re.sub(r'[^a-z0-9]+', '-', query.lower()).strip('-')
    pages = [f'https://mixkit.co/free-stock-video/discover/?q={urllib.parse.quote(query)}',
             f'https://mixkit.co/free-stock-video/{slug}/']
    urls = []
    for pg in pages:
        try:
            html = http(pg).decode('utf-8', 'ignore')
        except Exception:
            continue
        for u in MIX_RE.findall(html):
            if u not in urls:
                urls.append(u)
        if urls:
            break
    out = []
    for u in urls:
        m = re.search(r'/videos/(?:preview/)?(?:mixkit-[a-z0-9-]+-)?(\d+)', u)
        vid = m.group(1) if m else u
        hi = re.sub(r'-(360|720)\.mp4$', '-1080.mp4', u).replace('-small.mp4', '-large.mp4').replace('-medium.mp4', '-large.mp4')
        out.append({'provider': 'mixkit', 'uid': f'mixkit:{vid}', 'link': hi, 'fallback': u, 'width': None, 'height': None,
                    'duration': None, 'page': 'https://mixkit.co/', 'author': 'Mixkit',
                    'license': 'Mixkit Stock Video Free License (https://mixkit.co/license/#videoFree)', 'score': 0.5})
    return out


def mixkit_item(iid):
    idx = ROOT / 'build' / 'reel' / 'mixkit' / 'index.json'
    if idx.exists():
        d = json.loads(idx.read_text())
        if iid in d:
            return d[iid]
    html = http(f'https://mixkit.co/free-stock-video/discover/?q={iid}').decode('utf-8', 'ignore')
    m = re.search(r'href="/free-stock-video/([a-z0-9-]+)-' + iid + r'/"', html)
    if not m:
        return None
    page = f'https://mixkit.co/free-stock-video/{m.group(1)}-{iid}/'
    html = http(page).decode('utf-8', 'ignore')
    hi = [u for u in sorted(set(MIX_RE.findall(html))) if re.search(r'-720\.mp4$', u) or 'video-720' in u]
    lic = 'free' if 'data-license="videoFree"' in html else 'restricted'
    return {'id': iid, 'slug': m.group(1), 'license': lic, 'hi': hi[-1] if hi else None, 'page': page}


def chosen(src):
    """Fiche de téléchargement d'une vidéo choisie : « p:<id> » Pexels, « c:<id> » Coverr, « m:<id> » Mixkit."""
    kind, iid = src.split(':', 1)
    if kind == 'pp':  # photo Pexels (même licence) : transformée en plan fixe de 4 s, animé au montage
        return {'provider': 'pexels', 'uid': f'pexels-photo:{iid}', 'photo': True,
                'link': f'https://images.pexels.com/photos/{iid}/pexels-photo-{iid}.jpeg?w=3840',
                'page': f'https://www.pexels.com/photo/{iid}/', 'author': '—',
                'license': 'Pexels License (https://www.pexels.com/license/)', 'query': f'photo {iid}'}
    if kind == 'p':
        idx_path = ROOT / 'build' / 'reel' / 'pexels' / 'index.json'
        v = (json.loads(idx_path.read_text()) if idx_path.exists() else {}).get(iid)
        if not v:  # index absent (clone neuf) : on retrouve les fichiers directement
            sys.path.insert(0, str(Path(__file__).parent))
            from pexels import resolve
            r = resolve(iid)
            if not r:
                return None
            v = {'files': r['files'], 'page': f'https://www.pexels.com/video/{iid}/', 'slug': iid}
        # le plus grand fichier jusqu'au 4K (net en recadrage vertical)
        files = sorted(((int(k.split('x')[0]) * int(k.split('x')[1]), u) for k, u in v['files'].items()
                        if max(map(int, k.split('x'))) <= 4096))
        return {'provider': 'pexels', 'uid': f'pexels:{iid}', 'link': files[-1][1], 'page': v['page'], 'author': '—',
                'license': 'Pexels License (https://www.pexels.com/license/)', 'query': v['slug']}
    if kind == 'c':
        idx = json.loads((ROOT / 'build' / 'reel' / 'coverr' / 'index.json').read_text())
        v = idx.get(iid)
        if not v:
            return None
        return {'provider': 'coverr', 'uid': f'coverr:{iid}', 'link': v['mp4'], 'page': v['page'], 'author': '—',
                'license': 'Coverr License (https://coverr.co/license)', 'query': v['title']}
    v = mixkit_item(iid)
    if not v or v['license'] != 'free' or not v.get('hi'):
        return None
    return {'provider': 'mixkit', 'uid': f'mixkit:{iid}', 'link': v['hi'], 'page': v['page'], 'author': 'Mixkit',
            'license': 'Mixkit Stock Video Free License (https://mixkit.co/license/#videoFree)', 'query': v['slug']}


# ------------------------------------------------------------------ sélection
def shots(edl):
    for sec in edl['sections']:
        for sh in sec['shots']:
            if sh.get('render') or sh.get('use'):
                continue
            yield sec['name'], sh


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only', default='')
    ap.add_argument('--redo', default='')
    ap.add_argument('--provider', default='auto', choices=['auto', 'pexels', 'mixkit'])
    args = ap.parse_args()
    edl = json.loads(EDL.read_text())
    bpm = edl['bpm']
    CLIPS.mkdir(parents=True, exist_ok=True)
    OVERRIDE.mkdir(parents=True, exist_ok=True)
    key = os.environ.get('PEXELS_API_KEY', '').strip()
    providers = ['pexels', 'mixkit'] if args.provider == 'auto' else [args.provider]
    if 'pexels' in providers and not key:
        providers = [p for p in providers if p != 'pexels']
        print('PEXELS_API_KEY absente : Pexels ignoré.')
    only = set(filter(None, args.only.split(','))) | set(filter(None, args.redo.split(',')))
    redo = set(filter(None, args.redo.split(',')))
    used = set()
    for j in CLIPS.glob('*.json'):
        meta = json.loads(j.read_text())
        if j.stem not in redo:
            used.add(meta.get('uid'))
    excluded = {}
    for j in CLIPS.glob('*.json'):
        meta = json.loads(j.read_text())
        excluded.setdefault(j.stem, set()).update(meta.get('rejected', []) + ([meta.get('uid')] if j.stem in redo else []))

    failures = []
    for sec, sh in shots(edl):
        sid = sh['id']
        if only and sid not in only:
            continue
        dst = CLIPS / f'{sid}.mp4'
        if (OVERRIDE / f'{sid}.mp4').exists():
            print(f'{sid}: vos images (footage/override) seront utilisées')
            continue
        if dst.exists() and sid not in redo:
            continue
        need = sh['beats'] * 60 / bpm / sh.get('speed', 1.0) + 0.6
        got = None
        src = sh.get('src') or (f"m:{sh['mixkit']}" if sh.get('mixkit') else '')
        if src:
            # vidéo choisie à l'œil sur les planches (licence vérifiée)
            meta = chosen(src)
            if meta and meta.pop('photo', False):
                jpg = dst.with_suffix('.jpg')
                download(meta['link'], jpg)
                subprocess.run(['ffmpeg', '-y', '-v', 'error', '-loop', '1', '-framerate', '30', '-i', str(jpg), '-t', '4',
                                '-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2', '-c:v', 'libx264', '-crf', '10', '-pix_fmt', 'yuv420p',
                                str(dst)], check=True)
                jpg.unlink()
            elif meta:
                download(meta['link'], dst)
            if meta:
                meta.update(probe(dst), shot=sid, section=sec)
                (CLIPS / f'{sid}.json').write_text(json.dumps(meta, indent=1, ensure_ascii=False))
                used.add(meta['uid'])
                print(f"{sid}: {meta['provider']} {meta['width']}x{meta['height']} {meta['duration']:.1f}s « {meta['query']} »")
                continue
            print(f"{sid}: la vidéo {src} n'est pas en licence libre ou introuvable — recherche automatique")
        for q in sh['q']:
            for prov in providers:
                try:
                    cands = pexels_candidates(q, key, need) if prov == 'pexels' else mixkit_candidates(q, need)
                except Exception as e:
                    print(f'{sid}: {prov} « {q} » indisponible ({e})')
                    continue
                cands = [c for c in cands if c['uid'] not in used and c['uid'] not in excluded.get(sid, set())]
                cands.sort(key=lambda c: -c['score'])
                for c in cands[:4]:
                    try:
                        try:
                            download(c['link'], dst)
                        except Exception:
                            if not c.get('fallback'):
                                raise
                            download(c['fallback'], dst)
                        info = probe(dst)
                        if info['duration'] < need * 0.6:
                            dst.unlink()
                            continue
                        meta = {**c, **info, 'shot': sid, 'section': sec, 'query': q,
                                'rejected': sorted(excluded.get(sid, set()))}
                        (CLIPS / f'{sid}.json').write_text(json.dumps(meta, indent=1, ensure_ascii=False))
                        used.add(c['uid'])
                        got = meta
                        break
                    except Exception as e:
                        print(f'{sid}: échec téléchargement {c["link"]} ({e})')
                        if dst.exists():
                            dst.unlink()
                if got:
                    break
            if got:
                break
            time.sleep(0.3)
        if got:
            print(f"{sid}: {got['provider']} {got['width']}x{got['height']} {got['duration']:.1f}s « {got['query']} »")
        else:
            failures.append(sid)
            print(f'{sid}: AUCUNE vidéo trouvée')
    write_credits(edl)
    if failures:
        print('Plans sans vidéo :', ', '.join(failures))
        sys.exit(1)


def write_credits(edl):
    lines = ['# Crédits des images', '', 'Vidéos libres de droits utilisées dans « Nuits » (images réelles).', '',
             '| Plan | Source | Auteur | Licence | Lien |', '|---|---|---|---|---|']
    for _, sh in shots(edl):
        j = CLIPS / f"{sh['id']}.json"
        if (OVERRIDE / f"{sh['id']}.mp4").exists():
            lines.append(f"| {sh['id']} | images fournies par N+8 | — | — | — |")
        elif j.exists():
            m = json.loads(j.read_text())
            lines.append(f"| {sh['id']} | {m['provider']} | {m.get('author') or '—'} | {m['license']} | {m.get('page') or m['link']} |")
    (ROOT / 'footage' / 'CREDITS.md').write_text('\n'.join(lines) + '\n')


if __name__ == '__main__':
    main()
