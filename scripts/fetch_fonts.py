"""Télécharge les polices Google Fonts utilisées par la vidéo (latin, latin-ext, greek)
et génère src/fonts/fonts.css pointant vers les fichiers locaux."""
import re
import sys
import urllib.request
from pathlib import Path

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/140.0 Safari/537.36")
FAMILIES = [
    "Bodoni+Moda:ital,opsz,wght@0,6..96,400..700;1,6..96,400..700",
    "GFS+Didot",
    "Montserrat:wght@300..500",
    "Amiri:wght@400;700",
    "Cinzel:wght@400..900",
    "Noto+Serif+Display:wght@400..900",
]
KEEP = {"latin", "latin-ext", "greek", "arabic"}
OUT = Path(__file__).resolve().parent.parent / "src" / "fonts"


def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    css_out = []
    for fam in FAMILIES:
        css = get(f"https://fonts.googleapis.com/css2?family={fam}&display=block").decode()
        for subset, block in re.findall(r"/\* ([\w-]+) \*/\s*(@font-face\s*{[^}]*})", css):
            if subset not in KEEP:
                continue
            family = re.search(r"font-family:\s*'([^']+)'", block).group(1)
            style = re.search(r"font-style:\s*(\w+)", block).group(1)
            weight = re.search(r"font-weight:\s*(\d+)", block).group(1)
            url = re.search(r"url\((https://[^)]+)\)", block).group(1)
            name = f"{family.replace(' ', '')}-{style}-{weight}-{subset}.woff2"
            (OUT / name).write_bytes(get(url))
            css_out.append(re.sub(r"url\(https://[^)]+\)", f"url('{name}')", block))
            print("ok", name)
    (OUT / "fonts.css").write_text("\n".join(css_out) + "\n")


if __name__ == "__main__":
    sys.exit(main())
