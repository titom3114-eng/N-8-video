"""
Pexels sans clé d'API : à partir d'identifiants de vidéos Pexels (trouvés par recherche web), retrouve les
fichiers sur videos.pexels.com (nommage « <id>-<uhd|hd>_<largeur>_<hauteur>_<i/s>fps.mp4 »), la vignette
et la durée, et les range dans build/reel/pexels/index.json.

Licence Pexels (https://www.pexels.com/license/) : usage commercial et publicitaire autorisé, sans attribution.

    python3 scripts/footage/pexels.py footage/pexels_candidates.json
      (fichier JSON : [{"shot": "p01", "id": "8827066", "slug": "a-time-lapse-of-the-eiffel-tower-at-night"}, …])
"""
import concurrent.futures as cf
import json
import struct
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'build' / 'reel' / 'pexels'
UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36'
LICENSE = 'Pexels License (https://www.pexels.com/license/)'
SIZES = [(3840, 2160), (4096, 2160), (2560, 1440), (1920, 1080), (1280, 720), (3840, 1620), (3840, 1600), (4096, 1716),
         (2732, 1440), (1920, 1012), (2160, 3840), (1440, 2560), (1080, 1920), (720, 1280)]
FPS = [24, 25, 30, 50, 60, 23, 29, 48, 120]


def head(url):
    try:
        req = urllib.request.Request(url, method='HEAD', headers={'User-Agent': UA})
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status == 200 and int(r.headers.get('Content-Length') or 0) > 10000
    except Exception:
        return False


def resolve(vid):
    """Fichiers disponibles {(l, h): url} : on cherche d'abord la cadence avec le format HD, puis toutes les tailles."""
    base = f'https://videos.pexels.com/video-files/{vid}/{vid}-'
    fps = None
    probes = [(w, h, f) for f in FPS for (w, h) in [(1920, 1080), (1280, 720), (1080, 1920), (3840, 2160), (2560, 1440)]]
    with cf.ThreadPoolExecutor(12) as ex:
        hits = [p for p, ok in zip(probes, ex.map(
            lambda p: head(f"{base}{'uhd' if max(p[:2]) > 1920 else 'hd'}_{p[0]}_{p[1]}_{p[2]}fps.mp4"), probes)) if ok]
    if not hits:  # tailles moins courantes
        probes = [(w, h, f) for f in FPS for (w, h) in SIZES]
        with cf.ThreadPoolExecutor(16) as ex:
            hits = [p for p, ok in zip(probes, ex.map(
                lambda p: head(f"{base}{'uhd' if max(p[:2]) > 1920 else 'hd'}_{p[0]}_{p[1]}_{p[2]}fps.mp4"), probes)) if ok]
    if not hits:
        return None
    fps = hits[0][2]
    with cf.ThreadPoolExecutor(12) as ex:
        urls = {(w, h): f"{base}{'uhd' if max(w, h) > 1920 else 'hd'}_{w}_{h}_{fps}fps.mp4" for (w, h) in SIZES}
        ok = dict(zip(urls, ex.map(head, urls.values())))
    files = {f'{w}x{h}': urls[(w, h)] for (w, h), good in ok.items() if good}
    return {'fps': fps, 'files': files}


def fetch_range(url, rng):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Range': f'bytes={rng}'})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def duration(url):
    """Durée lue dans l'en-tête MP4 (atome mvhd), au début ou à la fin du fichier."""
    for rng in ('0-262143', '-2097152'):
        try:
            d = fetch_range(url, rng)
        except Exception:
            continue
        i = d.find(b'mvhd')
        if i > 0:
            if d[i + 4] == 0:
                ts, dur = struct.unpack('>II', d[i + 16:i + 24])
            else:
                ts, dur = struct.unpack('>IQ', d[i + 24:i + 36])
            return round(dur / ts, 2) if ts else None
    return None


def entry(c):
    vid = str(c['id'])
    r = resolve(vid)
    if not r:
        return vid, None
    sizes = sorted(((int(k.split('x')[0]), int(k.split('x')[1]), u) for k, u in r['files'].items()), key=lambda t: -t[0] * t[1])
    w, h, best = sizes[0]
    small = sorted(sizes, key=lambda t: t[0] * t[1])[0][2]
    return vid, {'id': vid, 'slug': c.get('slug', ''), 'w': w, 'h': h, 'vertical': h > w, 'fps': r['fps'], 'files': r['files'],
                 'best': best, 'small': small, 'duration': duration(small),
                 'thumb': f'https://images.pexels.com/videos/{vid}/pexels-photo-{vid}.jpeg?auto=compress&w=640',
                 'page': f"https://www.pexels.com/video/{c.get('slug', 'video')}-{vid}/", 'license': LICENSE}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    idx_path = OUT / 'index.json'
    index = json.loads(idx_path.read_text()) if idx_path.exists() else {}
    cands = []
    for f in sys.argv[1:]:
        cands += json.loads(Path(f).read_text())
    shots = {}
    for c in cands:
        shots.setdefault(str(c['id']), set()).add(c['shot'])
    todo = {str(c['id']): c for c in cands if str(c['id']) not in index}
    print(f'{len(todo)} vidéos Pexels à résoudre…', flush=True)
    with cf.ThreadPoolExecutor(4) as ex:
        for vid, e in ex.map(entry, todo.values()):
            if e:
                index[vid] = e
                print(f"  {vid} {e['w']}x{e['h']} {e['fps']} i/s {e['duration'] or 0:.1f} s  {e['slug'][:50]}", flush=True)
            else:
                print(f'  {vid} introuvable', flush=True)
    for vid, s in shots.items():
        if vid in index:
            index[vid]['shots'] = sorted(set(index[vid].get('shots', [])) | s)
    idx_path.write_text(json.dumps(index, indent=0))
    print(f'Index Pexels : {len(index)} vidéos.')


if __name__ == '__main__':
    main()
