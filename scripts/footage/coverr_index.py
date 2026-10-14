"""
Indexe les vidéos Coverr utiles au montage (pages de recherche de coverr.co, données intégrées à la page).

Licence Coverr (https://coverr.co/license) : usage commercial et publicitaire autorisé, sans attribution.
Sont exclues : les vidéos payantes (isPremium), générées par IA (isAiGenerated, « user-ai-generation-* »,
« coverr-temp-* ») et tout ce qui ne vient pas du catalogue Coverr lui-même (Shutterstock, etc.).

    python3 scripts/footage/coverr_index.py                  → build/reel/coverr/index.json
    python3 scripts/footage/coverr_index.py "rome night" bar  (requêtes supplémentaires)
"""
import concurrent.futures as cf
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'build' / 'reel' / 'coverr'
UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36'
STATE = re.compile(r'<script id="ng-state" type="application/json">(.*?)</script>', re.S)
QUERIES = """match;matches;lighting a match;lighter;zippo;flame;fire dark;cigar;cigars;smoking cigar;man smoking;smoking;
smoke;smoke dark;smoke black background;incense;ash;ember;embers;tobacco;
paris;paris night;eiffel tower;eiffel tower night;paris street;paris rain;paris rooftops;paris cafe;seine;montmartre;
bar;bar night;cocktail bar;bartender;whiskey;whisky;cognac;brandy;pouring whiskey;pouring drink;bottles;liquor;
ice cubes;ice;glass;toast;cheers;champagne;jazz;saxophone;piano;trumpet;leather;armchair;suit;man in suit;tuxedo;hat;
silhouette;silhouette night;gentleman;elegant man;night club;lounge;
rome;rome night;italy;italy night;colosseum;roman;trevi;fountain;fountain night;cobblestone;cobblestones;wet street;
rain night;rain street;puddle;church;cathedral;candles;candle;candle flame;lemon;lemons;citrus;orange tree;bergamot;
statue;statues;marble;sculpture;ruins;vespa;scooter;vatican;dome;basilica;florence;venice;venice night;naples;
desert;dunes;desert night;sand dunes;sand;sand wind;moon;full moon;stars;night sky;milky way;mosque;minaret;oman;muscat;
dubai;dubai night;abu dhabi;arab;arabic;middle east;incense burner;oud;rose;roses;rose petals;petals;lantern;lanterns;
lamp;moroccan;morocco;marrakech;honey;gold;golden;oil drop;drop;liquid gold;jewelry;necklace;camel;camels;horse;
horses;black horse;gold particles;dust particles;perfume;perfume bottle;
london;london night;big ben;madrid;spain night;berlin;berlin night;lisbon;lisbon night;tram;amsterdam;amsterdam night;
canal night;stockholm;bucharest;athens;acropolis;greece night;city night;city lights;night drive;night traffic;
skyline night;street lights;neon;night""".replace('\n', '').split(';')


def get(url, tries=4):
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'text/html'})
            return urllib.request.urlopen(req, timeout=60).read().decode('utf-8', 'ignore')
        except Exception:
            time.sleep(1 + 2 * k)
    return ''


def acceptable(v):
    base = v.get('baseFilename') or ''
    return (not v.get('isPremium') and not v.get('isAiGenerated') and v.get('state') == 'published'
            and base.startswith('coverr-') and not base.startswith(('coverr-premium', 'coverr-temp'))
            and (v.get('urls') or {}).get('mp4'))


def search(q):
    html = get('https://coverr.co/s?' + urllib.parse.urlencode({'q': q}))
    m = STATE.search(html)
    if not m:
        return q, [], 0
    out, rejected = [], 0
    for blk in json.loads(m.group(1)).values():
        if not (isinstance(blk, dict) and str(blk.get('u', '')).startswith('https://public-api.coverr.co/videos')):
            continue
        for v in (blk.get('b') or {}).get('hits', []):
            if not acceptable(v):
                rejected += 1
                continue
            base = v['baseFilename']
            out.append({
                'id': v['id'], 'base': base, 'title': (v.get('title') or '').strip(),
                'description': (v.get('description') or '').strip(), 'keywords': v.get('searchKeywords') or [],
                'duration': float(v.get('duration') or 0), 'w': v.get('maxWidth'), 'h': v.get('maxHeight'),
                'vertical': bool(v.get('isVertical')), 'fps': v.get('fps'),
                'mp4': v['urls']['mp4'].split('?')[0], 'preview': v['urls'].get('mp4Preview'),
                'thumb': f'https://cdn.coverr.co/videos/{base}/thumbnail?width=640',
                'page': f"https://coverr.co/videos/{v.get('slug')}", 'queries': [q]})
    return q, out, rejected


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    idx_path = OUT / 'index.json'
    index = json.loads(idx_path.read_text()) if idx_path.exists() else {}
    queries = [q.strip() for q in QUERIES + sys.argv[1:] if q.strip()]
    with cf.ThreadPoolExecutor(4) as ex:
        for q, items, rej in ex.map(search, queries):
            new = 0
            for it in items:
                if it['id'] in index:
                    if q not in index[it['id']]['queries']:
                        index[it['id']]['queries'].append(q)
                else:
                    index[it['id']] = it
                    new += 1
            print(f'{q:22s} {len(items):3d} retenues ({new} nouvelles), {rej} exclues (payantes / IA)', flush=True)
    idx_path.write_text(json.dumps(index, indent=0, ensure_ascii=False))
    print(f'Index Coverr : {len(index)} vidéos libres (usage commercial).')


if __name__ == '__main__':
    main()
