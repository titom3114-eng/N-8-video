"""
Indexe les vidéos Mixkit utiles au montage : parcourt les pages par thème, puis lit la fiche de chaque
vidéo (licence, durée, fichier 720p). Seules les vidéos sous « Mixkit Stock Video Free License »
(usage commercial et publicitaire autorisé) sont retenues pour le film.

    python3 scripts/footage/mixkit_index.py            → build/reel/mixkit/index.json
"""
import concurrent.futures as cf
import json
import re
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'build' / 'reel' / 'mixkit'
UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36'
TAGS = """match fire flame lighter cigar smoke tobacco ash ember eiffel-tower paris night-city city-night street-night rain
bar bottles bottle whiskey alcohol drinks cocktail glass ice toast cheers jazz saxophone piano trumpet leather suit
silhouette man rome colosseum italy fountain incense candle candles church vatican lemon citrus statue marble ruins
desert dunes sand camel night stars moon mosque dubai abu-dhabi arab arabic lantern lamp rose rose-petals petals
gold golden honey oil drop jewelry necklace horse london big-ben madrid berlin lisbon amsterdam stockholm athens
acropolis perfume slow-motion dark black-background""".split()


def get(url, tries=4):
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'text/html'})
            return urllib.request.urlopen(req, timeout=12).read().decode('utf-8', 'ignore')
        except Exception:
            time.sleep(0.5 + k)
    return ''


def tag_items(tag):
    found = {}
    for page in (1, 2, 3):
        html = get(f'https://mixkit.co/free-stock-video/{tag}/' + (f'?page={page}' if page > 1 else ''))
        items = re.findall(r'href="/free-stock-video/([a-z0-9-]+)-(\d+)/"', html)
        if not items:
            break
        before = len(found)
        for slug, iid in items:
            found[iid] = slug
        if len(found) == before:
            break
    return tag, found


def item_info(iid, slug):
    html = get(f'https://mixkit.co/free-stock-video/{slug}-{iid}/')
    if not html:
        return None
    lic = 'free' if 'data-license="videoFree"' in html else ('restricted' if 'data-license="videoRestricted"' in html else 'unknown')
    mp4 = sorted(set(re.findall(r'https://assets\.mixkit\.co/[^"\'\s<>]+\.mp4', html)))
    hi = [u for u in mp4 if re.search(r'-(720|1080|2160)\.mp4$', u) or 'video-720' in u or 'video-1080' in u]
    lo = [u for u in mp4 if re.search(r'-360\.mp4$', u) or 'video-360' in u]
    dm = re.search(r'"duration":"PT(\d+)M(\d+)S"', html)
    dur = int(dm.group(1)) * 60 + int(dm.group(2)) if dm else None
    vertical = 'vertical' in slug
    return {'id': iid, 'slug': slug, 'license': lic, 'duration': dur, 'hi': hi[-1] if hi else None,
            'preview': lo[0] if lo else None, 'page': f'https://mixkit.co/free-stock-video/{slug}-{iid}/', 'vertical': vertical}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    idx_path = OUT / 'index.json'
    index = json.loads(idx_path.read_text()) if idx_path.exists() else {}
    tags = {}
    with cf.ThreadPoolExecutor(8) as ex:
        for tag, found in ex.map(tag_items, TAGS):
            tags[tag] = found
            print(f'{tag:14s} {len(found)}')
    todo = {iid: slug for found in tags.values() for iid, slug in found.items() if iid not in index}
    print(f'{len(todo)} fiches à lire…', flush=True)
    done = 0
    with cf.ThreadPoolExecutor(6) as ex:
        futs = [ex.submit(item_info, iid, slug) for iid, slug in todo.items()]
        for fu in cf.as_completed(futs):
            info = fu.result()
            done += 1
            if info:
                index[info['id']] = info
            if done % 100 == 0:
                idx_path.write_text(json.dumps(index, indent=0))
                print(f'{done}/{len(todo)} lues, index {len(index)}', flush=True)
    (OUT / 'tags_full.json').write_text(json.dumps(tags))
    idx_path.write_text(json.dumps(index, indent=0))
    free = sum(1 for v in index.values() if v['license'] == 'free')
    print(f'Index : {len(index)} vidéos, dont {free} en licence libre (usage commercial).')


if __name__ == '__main__':
    main()
