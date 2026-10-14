"""
Indexe les effets sonores Mixkit (licence « Mixkit Sound Effects Free License » : usage commercial,
publicité en ligne, télévision et radio autorisés, sans attribution) et télécharge ceux retenus.

    python3 scripts/footage/mixkit_sfx.py index           → build/reel/sfx/index.json
    python3 scripts/footage/mixkit_sfx.py get 1318 156    → footage/sfx/<id>.wav (fichiers d'origine)
"""
import concurrent.futures as cf
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'build' / 'reel' / 'sfx'
LIB = ROOT / 'footage' / 'sfx'
UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36'
TAGS = """fire match lighter smoke cigarette breath breathing exhale pour drink drinks glass ice bottle bar restaurant
crowd city traffic street rain thunder footsteps bell bells church chain candle water drop splash fountain wind desert
sand horse whoosh swoosh woosh swish swell impact cinematic boom hit transition rumble drone tension heartbeat
jazz piano saxophone leather creak metal coins jewelry chime chimes magic shimmer gong arabic night crickets insects
car motorcycle engine people party cheers toast wine whiskey liquid cork sizzle burn burning explosion""".split()
QUERIES = """match strike;lighter;zippo;lighting cigarette;cigar;cigarette;inhale;exhale;smoke;fire crackling;fireplace;
embers;burning;pour;pouring drink;pouring whiskey;liquid pour;ice cubes;ice in glass;glass clink;glass on table;toast;
bottle;cork;bar ambience;restaurant ambience;jazz club;crowd murmur;city night;night street;traffic distant;rain;
rain on street;rain city;thunder;footsteps;footsteps stone;church bell;bell toll;choir;chain;metal chain;candle;
water drop;drip;splash;fountain;lemon;fruit;squeeze;wind;desert wind;sand;camel;horse;whoosh;swoosh;swell;impact;
cinematic impact;deep boom;boom;sub;riser;reverse;transition;hit;bass hit;rumble;low rumble;drone;dark drone;tension;
heartbeat;saxophone;piano;double bass;leather;creak;coins;jewelry;chime;wind chimes;shimmer;sparkle;gong;oud;arabic;
mosque;crickets;night ambience;insects;car passing;motorcycle;scooter;sizzle;flame;torch;flicker;paper burn;
heavy breath;sigh;sniff;smell;dubai;city ambience;metro;bridge;river;sea night;boat;glass break;whisky""".replace('\n', '').split(';')


def get(url, tries=4):
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'text/html'})
            return urllib.request.urlopen(req, timeout=30).read().decode('utf-8', 'ignore')
        except Exception as e:
            if getattr(e, 'code', 0) == 404:
                return ''
            time.sleep(1 + 2 * k)
    return ''


def cards(html):
    out = []
    for c in html.split('class="item-grid__item"')[1:]:
        iid = re.search(r'data-audio-player-item-id-value="(\d+)"', c)
        if not iid:
            continue
        t = re.search(r'item-grid-card__title[^>]*>\s*([^<]+?)\s*<', c)
        d = re.search(r'data-test-id="duration">\s*(\d+):(\d\d)', c)
        tags = re.findall(r'href="/free-sound-effects/([a-z0-9-]+)/">', c)
        out.append({'id': iid.group(1), 'title': t.group(1) if t else '', 'duration': int(d.group(1)) * 60 + int(d.group(2)) if d else None,
                    'tags': tags})
    return out


def crawl(kind, q):
    found = []
    for page in (1, 2, 3, 4):
        if kind == 'tag':
            url = f'https://mixkit.co/free-sound-effects/{q}/' + (f'?page={page}' if page > 1 else '')
        else:
            url = f"https://mixkit.co/free-sound-effects/discover/{q.replace(' ', '-')}/" + (f'?page={page}' if page > 1 else '')
        items = cards(get(url))
        new = [i for i in items if i['id'] not in {f['id'] for f in found}]
        if not new:
            break
        found += new
    return q, found


def index():
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / 'index.json'
    idx = json.loads(path.read_text()) if path.exists() else {}
    jobs = [('tag', t) for t in TAGS] + [('q', q.strip()) for q in QUERIES if q.strip()]
    with cf.ThreadPoolExecutor(6) as ex:
        for q, items in ex.map(lambda j: crawl(*j), jobs):
            for it in items:
                e = idx.setdefault(it['id'], {**it, 'found': []})
                if q not in e['found']:
                    e['found'].append(q)
            print(f'{q:20s} {len(items)}', flush=True)
    path.write_text(json.dumps(idx, indent=0, ensure_ascii=False))
    print(f'Index : {len(idx)} effets sonores.')


def fetch(ids):
    LIB.mkdir(parents=True, exist_ok=True)
    for iid in ids:
        dst = LIB / f'{iid}.wav'
        if dst.exists():
            continue
        req = urllib.request.Request(f'https://assets.mixkit.co/active_storage/sfx/{iid}/{iid}.wav', headers={'User-Agent': UA})
        dst.write_bytes(urllib.request.urlopen(req, timeout=120).read())
        print(f'{iid} → {dst.relative_to(ROOT)}')


if __name__ == '__main__':
    if sys.argv[1:2] == ['index']:
        index()
    elif sys.argv[1:2] == ['get']:
        fetch(sys.argv[2:])
