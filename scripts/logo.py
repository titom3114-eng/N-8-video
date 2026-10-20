"""
Logo N+8 retravaillé : propositions vectorielles (formes vectorisées, aucune police requise à l'usage).

Typographie : Bodoni Moda (le caractère du film), en taille optique « titrage » pour le N et le 8 ; Jost pour la
signature « MAISON DE PARFUMS / NOCTURNE ». Les deux sont sous licence SIL Open Font License : usage dans un logo
autorisé, y compris commercial. Le « + » devient une étoile à quatre branches : N, l'étoile, 8 — la nuit.

    python3 scripts/logo.py      → assets/logo-v2/*.svg, assets/logo-v2/png/*.png, assets/logo-v2/planche-*.png
"""
import json
import subprocess
from pathlib import Path

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / 'assets' / 'logo-v2'
FONTS = DIR / 'polices'

# palette
NUIT = '#0B0B0D'
IVOIRE = '#F3EEE4'
OR_PLAT = '#C8A45E'        # or d'impression (aplat) ; dorure à chaud : or mat, Pantone 871 C ou 7502 C
OR_DEGRADE = [(0, '#F4E4B4'), (0.45, '#D6B26D'), (1, '#9C7333')]
COLORWAYS = {'or': None, 'or-plat': OR_PLAT, 'ivoire': IVOIRE, 'noir': NUIT}


# ---------------------------------------------------------------- polices
def instance(fname, **axes):
    f = TTFont(FONTS / fname)
    return instantiateVariableFont(f, axes) if 'fvar' in f else f


# taille optique 22 : les déliés du N restent visibles en petit (étiquette, icône) sans perdre le contraste Didot
BODONI = instance('BodoniModa-normal.woff2', wght=570, opsz=22)
JOST = instance('Jost-normal.woff2', wght=380)


def glyph(font, ch):
    gs = font.getGlyphSet()
    return gs, font.getBestCmap()[ord(ch)]


def bounds(font, ch, scale=1.0):
    gs, g = glyph(font, ch)
    bp = BoundsPen(gs)
    gs[g].draw(bp)
    x0, y0, x1, y1 = bp.bounds
    return x0 * scale, y0 * scale, x1 * scale, y1 * scale, gs[g].width * scale


def outline(font, ch, x, base, scale=1.0):
    """Contour SVG du caractère, origine (x, ligne de base) ; y vers le bas."""
    gs, g = glyph(font, ch)
    pen = SVGPathPen(gs)
    gs[g].draw(TransformPen(pen, (scale, 0, 0, -scale, x, base)))
    return pen.getCommands()


# ---------------------------------------------------------------- éléments (unités : hauteur de capitale C = 1500)
C = 1500.0


def star(cx, cy, a, b, waist):
    """Étoile à quatre branches, côtés concaves : le « + » devenu étoile de nuit (branche verticale plus longue)."""
    k = waist
    return (f'M{cx:.1f},{cy - a:.1f} C{cx + k * 0.5:.1f},{cy - a * 0.35:.1f} {cx + b * 0.35:.1f},{cy - k * 0.5:.1f} {cx + b:.1f},{cy:.1f} '
            f'C{cx + b * 0.35:.1f},{cy + k * 0.5:.1f} {cx + k * 0.5:.1f},{cy + a * 0.35:.1f} {cx:.1f},{cy + a:.1f} '
            f'C{cx - k * 0.5:.1f},{cy + a * 0.35:.1f} {cx - b * 0.35:.1f},{cy + k * 0.5:.1f} {cx - b:.1f},{cy:.1f} '
            f'C{cx - b * 0.35:.1f},{cy - k * 0.5:.1f} {cx - k * 0.5:.1f},{cy - a * 0.35:.1f} {cx:.1f},{cy - a:.1f} Z')


def arch(cx, base, ro, leg, t_leg, t_top):
    """Arche (porte, niche, fenêtre de nuit) : trait épais aux montants, délié au sommet — le contraste du Bodoni."""
    ri_x, ri_y = ro - t_leg, ro - t_top
    top = base - leg
    return (f'M{cx - ro:.1f},{base:.1f} L{cx - ro:.1f},{top:.1f} A{ro:.1f},{ro:.1f} 0 0 1 {cx + ro:.1f},{top:.1f} '
            f'L{cx + ro:.1f},{base:.1f} L{cx + ri_x:.1f},{base:.1f} L{cx + ri_x:.1f},{top:.1f} '
            f'A{ri_x:.1f},{ri_y:.1f} 0 0 0 {cx - ri_x:.1f},{top:.1f} L{cx - ri_x:.1f},{base:.1f} Z')


def ring_moon(cx, cy, r, t, crescent):
    """Lune : un anneau fin, et un croissant plus épais qui s'y appuie à droite (deux arcs)."""
    ring = (f'M{cx - r:.1f},{cy:.1f} A{r:.1f},{r:.1f} 0 1 1 {cx + r:.1f},{cy:.1f} A{r:.1f},{r:.1f} 0 1 1 {cx - r:.1f},{cy:.1f} Z '
            f'M{cx - r + t:.1f},{cy:.1f} A{r - t:.1f},{r - t:.1f} 0 1 0 {cx + r - t:.1f},{cy:.1f} A{r - t:.1f},{r - t:.1f} 0 1 0 {cx - r + t:.1f},{cy:.1f} Z')
    # croissant : entre le bord intérieur de l'anneau (à droite) et un arc plus plat ; épaisseur maximale « crescent »
    rr, off = r - t, crescent
    a = (rr * rr + (rr - off) ** 2) / (2 * (rr - off))
    moon = (f'M{cx:.1f},{cy - rr:.1f} A{rr:.1f},{rr:.1f} 0 0 1 {cx:.1f},{cy + rr:.1f} '
            f'A{a:.1f},{a:.1f} 0 0 0 {cx:.1f},{cy - rr:.1f} Z')
    return ring + ' ' + moon


def plus(cx, cy, arm, t):
    """« + » classique, au délié du Bodoni (variante sans étoile)."""
    return (f'M{cx - arm:.1f},{cy - t / 2:.1f} L{cx - t / 2:.1f},{cy - t / 2:.1f} L{cx - t / 2:.1f},{cy - arm:.1f} '
            f'L{cx + t / 2:.1f},{cy - arm:.1f} L{cx + t / 2:.1f},{cy - t / 2:.1f} L{cx + arm:.1f},{cy - t / 2:.1f} '
            f'L{cx + arm:.1f},{cy + t / 2:.1f} L{cx + t / 2:.1f},{cy + t / 2:.1f} L{cx + t / 2:.1f},{cy + arm:.1f} '
            f'L{cx - t / 2:.1f},{cy + arm:.1f} L{cx - t / 2:.1f},{cy + t / 2:.1f} L{cx - arm:.1f},{cy + t / 2:.1f} Z')


def wordmark(x0, base, gap=0.075 * C, star_a=0.33 * C, star_b=0.25 * C, waist=0.07 * C, etoile=True):
    """N ✦ 8 : renvoie (chemins, largeur). Espaces optiques égaux de part et d'autre de l'étoile (ou du +)."""
    nx0, _, nx1, _, _ = bounds(BODONI, 'N')
    ex0, _, ex1, _, _ = bounds(BODONI, '8')
    paths = [outline(BODONI, 'N', x0 - nx0, base)]
    half = star_b if etoile else 0.21 * C
    x = x0 + (nx1 - nx0) + gap + half
    paths.append(star(x, base - 0.5 * C, star_a, star_b, waist) if etoile else plus(x, base - 0.5 * C, 0.21 * C, 0.05 * C))
    x += half + gap
    paths.append(outline(BODONI, '8', x - ex0, base))
    return paths, x + (ex1 - ex0) - x0


def text_line(font, s, x_center, base, cap, track):
    """Ligne de capitales espacées, centrée : `cap` = hauteur de capitale voulue, `track` en fraction de corps."""
    upm_cap = font['OS/2'].sCapHeight
    sc = cap / upm_cap
    size = font['head'].unitsPerEm * sc
    adv = []
    for ch in s:
        if ch == ' ':
            adv.append(font['hmtx'][font.getBestCmap()[32]][0] * sc + track * size)
        else:
            adv.append(font['hmtx'][glyph(font, ch)[1]][0] * sc + track * size)
    width = sum(adv) - track * size
    x = x_center - width / 2
    paths = []
    for ch, a in zip(s, adv):
        if ch != ' ':
            paths.append(outline(font, ch, x, base, sc))
        x += a
    return paths, width


def text_left(font, s, x0, base, cap, track):
    paths, width = text_line(font, s, 0, base, cap, track)
    return text_line(font, s, x0 + width / 2, base, cap, track)


# ---------------------------------------------------------------- compositions
def lockup_principal(etoile=True):
    wm, w = wordmark(0, 0, etoile=etoile)
    wm, w = wordmark(-w / 2, 0, etoile=etoile)
    ro = w / 2 + 0.30 * C
    p = [arch(0, 0, ro, 0.62 * C, 0.05 * C, 0.022 * C)] + wm
    cap = 0.105 * C
    l1, w1 = text_line(JOST, 'MAISON DE PARFUMS', 0, 0.36 * C, cap, 0.42)
    l2, w2 = text_line(JOST, 'NOCTURNE', 0, 0.36 * C + 2.2 * cap, cap, 0.42)
    return p + l1 + l2


def lockup_embleme():
    wm, w = wordmark(0, 0)
    wm, w = wordmark(-w / 2, 0)
    ro = w / 2 + 0.30 * C
    return [arch(0, 0, ro, 0.62 * C, 0.05 * C, 0.022 * C)] + wm


def lockup_icone():
    """Arche et étoile seules : pastille de réseau social, bouchon, cachet de cire."""
    ro = 0.62 * C
    return [arch(0, 0, ro, 0.55 * C, 0.07 * C, 0.032 * C), star(0, -0.62 * C, 0.42 * C, 0.31 * C, 0.085 * C)]


def lockup_horizontal():
    wm, w = wordmark(0, 0)
    gap = 0.34 * C
    rule = f'M{w + gap:.1f},{-1.02 * C:.1f} L{w + gap + 0.012 * C:.1f},{-1.02 * C:.1f} L{w + gap + 0.012 * C:.1f},{0.02 * C:.1f} L{w + gap:.1f},{0.02 * C:.1f} Z'
    cap = 0.13 * C
    x0 = w + 2 * gap
    l1, _ = text_left(JOST, 'MAISON DE PARFUMS', x0, -0.56 * C, cap, 0.38)
    l2, _ = text_left(JOST, 'NOCTURNE', x0, -0.56 * C + 2.6 * cap, cap, 0.38)
    return wm + [rule] + l1 + l2


def lockup_lune():
    wm, w = wordmark(0, 0)
    wm, w = wordmark(-w / 2, 0)
    r = w / 2 + 0.42 * C
    cy = -0.5 * C
    p = [ring_moon(0, cy, r, 0.02 * C, 0.16 * C)] + wm
    cap = 0.105 * C
    l1, _ = text_line(JOST, 'MAISON DE PARFUMS', 0, cy + r + 0.42 * C, cap, 0.42)
    l2, _ = text_line(JOST, 'NOCTURNE', 0, cy + r + 0.42 * C + 2.2 * cap, cap, 0.42)
    return p + l1 + l2


def lockup_epure():
    """Sans arche : le mot seul, la signature sur une ligne entre deux filets."""
    wm, w = wordmark(0, 0)
    wm, w = wordmark(-w / 2, 0)
    cap, y = 0.085 * C, 0.42 * C
    l1, w1 = text_line(JOST, 'MAISON DE PARFUMS NOCTURNE', 0, y, cap, 0.45)
    rules, t, ym = [], 0.008 * C, y - 0.5 * cap
    for sgn in (-1, 1):
        xa, xb = sgn * (w1 / 2 + 0.1 * C), sgn * (w1 / 2 + 0.1 * C + 0.38 * C)
        x1, x2 = min(xa, xb), max(xa, xb)
        rules.append(f'M{x1:.1f},{ym - t:.1f} L{x2:.1f},{ym - t:.1f} L{x2:.1f},{ym + t:.1f} L{x1:.1f},{ym + t:.1f} Z')
    return wm + l1 + rules


LOCKUPS = {
    'n8-principal': lockup_principal,
    'n8-principal-plus': lambda: lockup_principal(etoile=False),
    'n8-embleme': lockup_embleme,
    'n8-horizontal': lockup_horizontal,
    'n8-icone': lockup_icone,
    'n8-lune': lockup_lune,
    'n8-epure': lockup_epure,
}


# ---------------------------------------------------------------- SVG
def extent(paths):
    """Boîte englobante exacte (courbes et arcs compris)."""
    from fontTools.svgLib.path import parse_path
    bp = BoundsPen(None)
    for d in paths:
        parse_path(d, bp)
    return bp.bounds


def svg(paths, color, pad=0.12, bg=None):
    x0, y0, x1, y1 = extent(paths)
    w, h = x1 - x0, y1 - y0
    m = pad * max(w, h)
    vb = (x0 - m, y0 - m, w + 2 * m, h + 2 * m)
    fill = color or 'url(#or)'
    defs = ''
    if color is None:
        stops = ''.join(f'<stop offset="{o}" stop-color="{c}"/>' for o, c in OR_DEGRADE)
        defs = (f'<defs><linearGradient id="or" gradientUnits="userSpaceOnUse" x1="0" y1="{y0:.1f}" x2="0" y2="{y1:.1f}">'
                f'{stops}</linearGradient></defs>')
    rect = f'<rect x="{vb[0]:.1f}" y="{vb[1]:.1f}" width="{vb[2]:.1f}" height="{vb[3]:.1f}" fill="{bg}"/>' if bg else ''
    body = ''.join(f'<path d="{d}"/>' for d in paths)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb[0]:.1f} {vb[1]:.1f} {vb[2]:.1f} {vb[3]:.1f}">'
            f'{defs}{rect}<g fill="{fill}">{body}</g></svg>')


def render_png(svg_path, png_path, width):
    """Rendu PNG par Chromium (Playwright), fond transparent."""
    page = png_path.with_suffix('.html')
    vb = [float(v) for v in svg_path.read_text().split('viewBox="')[1].split('"')[0].split()]
    height = round(width * vb[3] / vb[2])
    page.write_text(f'<html><body style="margin:0;background:transparent"><img src="{svg_path.resolve().as_uri()}" '
                    f'style="width:{width}px;height:{height}px;display:block"></body></html>')
    subprocess.run(['node', str(ROOT / 'scripts' / 'shot.cjs'), str(page), str(png_path), str(width), str(height)],
                   check=True, env={**__import__('os').environ, 'ALPHA': '1'})
    page.unlink()


def main():
    DIR.mkdir(parents=True, exist_ok=True)
    (DIR / 'png').mkdir(exist_ok=True)
    made = {}
    for name, fn in LOCKUPS.items():
        paths = fn()
        for cw, color in COLORWAYS.items():
            p = DIR / f'{name}-{cw}.svg'
            p.write_text(svg(paths, color))
            made[p.name] = True
        for cw in ('or', 'noir'):
            render_png(DIR / f'{name}-{cw}.svg', DIR / 'png' / f'{name}-{cw}.png', 2400)
    (DIR / 'fichiers.json').write_text(json.dumps(sorted(made), indent=1))
    print(f'{len(made)} fichiers SVG, rendus PNG dans {DIR / "png"}')


if __name__ == '__main__':
    main()
