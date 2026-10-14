/*
 * N+8 — « Nuits »
 * La nuit et son parfum, à travers les villes : Paris, Rome, Oman… puis le logo.
 * Court-métrage génératif rendu image par image (window.N8.renderAt(t)).
 * Palette : or, noir, gris, blanc. Tempo : 96 BPM, coupes sur le temps.
 */
(() => {
  'use strict';
  const RENDER = new URLSearchParams(location.search).has('render');
  const cv = document.getElementById('film');
  const ctx = cv.getContext('2d');
  let W = 0, H = 0, U = 1, LAND = true, VX = 88.9, VY = 37.2;

  /* =========================================================
   * Outils
   * ======================================================= */
  const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
  const lerp = (a, b, p) => a + (b - a) * p;
  const E = {
    lin: p => p,
    out: p => 1 - Math.pow(1 - p, 3),
    in: p => p * p * p,
    inOut: p => (p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2),
    sine: p => -(Math.cos(Math.PI * p) - 1) / 2,
    quadIn: p => p * p,
  };
  const prog = (t, s, d, e = E.lin) => e(clamp((t - s) / d));
  const bump = (t, s, d) => Math.sin(Math.PI * clamp((t - s) / d));
  const mixC = (a, b, p) => [lerp(a[0], b[0], p), lerp(a[1], b[1], p), lerp(a[2], b[2], p)];
  const rgb = (c, a = 1) => `rgba(${c[0] | 0},${c[1] | 0},${c[2] | 0},${clamp(a).toFixed(4)})`;
  const mul = (c, k) => [c[0] * k, c[1] * k, c[2] * k];
  function hash1(n) {
    n = (n | 0) ^ 0x9e3779b9;
    n = Math.imul(n ^ (n >>> 16), 0x85ebca6b);
    n = Math.imul(n ^ (n >>> 13), 0xc2b2ae35);
    n ^= n >>> 16;
    return (n >>> 0) / 4294967296;
  }
  function rng(seed) {
    let s = seed | 0;
    return () => {
      s = (s + 0x6D2B79F5) | 0;
      let t = Math.imul(s ^ (s >>> 15), 1 | s);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  const vnoise = (x, seed = 0) => {
    const i = Math.floor(x), f = x - i, s = f * f * (3 - 2 * f);
    return lerp(hash1(i + seed * 7919), hash1(i + 1 + seed * 7919), s);
  };
  const shake = (u, seed, amp) => [
    (vnoise(u * 0.8, seed) - 0.5) * 2 * amp + (vnoise(u * 2.3, seed + 3) - 0.5) * amp * 0.4,
    (vnoise(u * 0.7, seed + 5) - 0.5) * 2 * amp + (vnoise(u * 2.1, seed + 9) - 0.5) * amp * 0.4,
  ];

  /* =========================================================
   * Palette : or, noir, gris, blanc
   * ======================================================= */
  const C = {
    gold: [214, 174, 104], goldHi: [250, 230, 186], goldDeep: [140, 98, 44], amber: [196, 128, 48],
    white: [240, 238, 232], gray: [132, 132, 136], dark: [14, 13, 12], ink: [4, 4, 5],
  };
  const F = { serif: '"Bodoni Moda", "GFS Didot", serif', sans: '"Montserrat", sans-serif', arabic: '"Amiri", serif' };

  /* =========================================================
   * Calques et textures
   * ======================================================= */
  const mk = (w, h) => {
    const c = document.createElement('canvas');
    c.width = Math.max(1, Math.round(w)); c.height = Math.max(1, Math.round(h));
    return c;
  };
  const L = {};
  function layer(name, w, h) { const c = mk(w, h); L[name] = { c, x: c.getContext('2d'), w: c.width, h: c.height }; }
  function reset(x) {
    x.setTransform(1, 0, 0, 1, 0, 0);
    x.globalAlpha = 1; x.globalCompositeOperation = 'source-over'; x.filter = 'none';
    x.shadowBlur = 0; x.shadowColor = 'rgba(0,0,0,0)';
  }
  function fbm(size, cell, oct, seed, gain = 0.5) {
    const out = new Float32Array(size * size);
    let amp = 1, tot = 0;
    for (let o = 0; o < oct; o++) {
      const per = Math.max(2, Math.round(size / cell) << o);
      const lat = new Float32Array(per * per), r = rng(seed * 31 + o * 7);
      for (let i = 0; i < lat.length; i++) lat[i] = r();
      const st = size / per;
      for (let y = 0; y < size; y++) {
        const gy = y / st, iy = Math.floor(gy), fy = gy - iy, sy = fy * fy * (3 - 2 * fy);
        const y0 = (iy % per) * per, y1 = ((iy + 1) % per) * per;
        for (let x = 0; x < size; x++) {
          const gx = x / st, ix = Math.floor(gx), fx = gx - ix, sx = fx * fx * (3 - 2 * fx);
          const x0 = ix % per, x1 = (ix + 1) % per;
          const a = lat[y0 + x0] + (lat[y0 + x1] - lat[y0 + x0]) * sx;
          const b = lat[y1 + x0] + (lat[y1 + x1] - lat[y1 + x0]) * sx;
          out[y * size + x] += amp * (a + (b - a) * sy);
        }
      }
      tot += amp; amp *= gain;
    }
    for (let i = 0; i < out.length; i++) out[i] /= tot;
    return out;
  }
  function texCanvas(size, fn) {
    const c = mk(size, size), x = c.getContext('2d'), img = x.createImageData(size, size), d = img.data;
    const px = [0, 0, 0, 255];
    for (let y = 0; y < size; y++) {
      for (let xx = 0; xx < size; xx++) {
        const i = y * size + xx;
        fn(i, xx, y, px);
        d[i * 4] = px[0]; d[i * 4 + 1] = px[1]; d[i * 4 + 2] = px[2]; d[i * 4 + 3] = px[3];
      }
    }
    x.putImageData(img, 0, 0);
    return c;
  }
  const TEX = {};
  function buildTextures() {
    // Fumée : 4 volutes, blanc-gris et or
    TEX.smoke = []; TEX.smokeGold = [];
    for (let k = 0; k < 4; k++) {
      const n = fbm(256, 46, 5, 300 + k), n2 = fbm(256, 18, 3, 340 + k);
      const mkSmoke = col => texCanvas(256, (i, x, y, px) => {
        const dx = (x - 128) / 128, dy = (y - 128) / 128, r2 = dx * dx + dy * dy;
        const fall = Math.pow(clamp(1 - r2), 2);
        const v = clamp((n[i] * 0.75 + n2[i] * 0.25 - 0.36) * 2.4) * fall;
        px[0] = col[0]; px[1] = col[1]; px[2] = col[2]; px[3] = v * 255;
      });
      TEX.smoke.push(mkSmoke([214, 214, 218]));
      TEX.smokeGold.push(mkSmoke([226, 184, 112]));
    }
    // Bokeh : disque doux à liseré
    const mkBokeh = col => texCanvas(128, (i, x, y, px) => {
      const r = Math.hypot(x - 64, y - 64) / 60;
      const edge = clamp((1 - r) / 0.08), rim = Math.exp(-Math.pow((r - 0.9) / 0.08, 2)) * 0.5;
      px[0] = col[0]; px[1] = col[1]; px[2] = col[2]; px[3] = clamp(edge * (0.55 + 0.25 * r + rim)) * 255;
    });
    TEX.bokehGold = mkBokeh([232, 186, 112]);
    TEX.bokehWhite = mkBokeh([236, 232, 222]);
    // Pierre (travertin), nuages, sable, grain
    {
      const b = fbm(512, 64, 5, 11), f = fbm(512, 8, 2, 12);
      TEX.stone = texCanvas(512, (i, x, y, px) => { const v = clamp(0.55 + (b[i] - 0.5) * 1.2 + (f[i] - 0.5) * 0.4) * 255; px[0] = v; px[1] = v; px[2] = v; px[3] = 255; });
    }
    {
      const b = fbm(1024, 300, 6, 81);
      TEX.clouds = texCanvas(1024, (i, x, y, px) => {
        const a = clamp((b[i] - 0.44) / 0.3);
        px[0] = 40; px[1] = 38; px[2] = 36; px[3] = a * a * (3 - 2 * a) * 220;
      });
    }
    TEX.grain = [0, 1, 2, 3].map(k => {
      const rr = rng(900 + k);
      return texCanvas(256, (i, x, y, px) => { const v = (0.5 + (rr() - 0.5) * 0.9) * 255; px[0] = v; px[1] = v; px[2] = v; px[3] = 255; });
    });
  }
  const patCache = new Map();
  function pattern(x, tex, sx, ox = 0, oy = 0, sy = null) {
    let m = patCache.get(tex);
    if (!m) { m = new Map(); patCache.set(tex, m); }
    let p = m.get(x);
    if (!p) { p = x.createPattern(tex, 'repeat'); m.set(x, p); }
    p.setTransform(new DOMMatrix([sx, 0, 0, sy ?? sx, ox, oy]));
    return p;
  }

  /* =========================================================
   * Caméra, sprites, fumée, bokeh, flammes
   * ======================================================= */
  // Espace d'un plan : origine au centre de l'image, unité = 1 % du petit côté.
  function camSet(x, c = {}, k = 1) {
    const s = (c.s || 1) * U * k, r = c.r || 0, cs = Math.cos(r), sn = Math.sin(r), cx = c.x || 0, cy = c.y || 0;
    x.setTransform(s * cs, s * sn, -s * sn, s * cs, (W / 2) * k - s * (cs * cx - sn * cy), (H / 2) * k - s * (sn * cx + cs * cy));
  }
  function sprite(x, img, cx, cy, size, a, rot = 0) {
    if (a <= 0.003 || size <= 0) return;
    x.globalAlpha = clamp(a);
    if (rot) {
      x.save(); x.translate(cx, cy); x.rotate(rot);
      x.drawImage(img, -size / 2, -size / 2, size, size);
      x.restore();
    } else x.drawImage(img, cx - size / 2, cy - size / 2, size, size);
  }
  // Émetteur de fumée déterministe (chaque volute dépend de son instant de naissance)
  function smoke(x, u, e) {
    const imgs = e.gold ? TEX.smokeGold : TEX.smoke;
    const i0 = Math.ceil((u - e.life) * e.rate), i1 = Math.floor(u * e.rate);
    x.globalCompositeOperation = e.comp || 'screen';
    for (let i = i0; i <= i1; i++) {
      const t0 = i / e.rate;
      if (e.start != null && t0 < e.start) continue;
      if (e.stop != null && t0 > e.stop) continue;
      const age = u - t0, k = age / e.life;
      const h1 = hash1(i * 7 + e.seed), h2 = hash1(i * 13 + e.seed * 3 + 1), h3 = hash1(i * 29 + e.seed * 5 + 2), h4 = hash1(i * 41 + e.seed * 7 + 3);
      const [sx, sy] = e.src ? e.src(t0) : [e.x, e.y];
      const px = sx + (h1 - 0.5) * e.spread + Math.sin(age * (e.curlF || 1.3) + h2 * 6.28) * (e.curl || 0) * Math.min(1, k * 2) + (e.wind || 0) * age;
      const py = sy - e.rise * (0.7 + 0.6 * h3) * age;
      const size = lerp(e.s0, e.s1, Math.pow(k, 0.6)) * (0.75 + 0.5 * h4);
      let a = e.a * Math.min(1, age / (e.fadeIn || 0.25)) * Math.pow(1 - k, 1.4);
      if (e.mask) a *= e.mask(px, py);
      sprite(x, imgs[(h2 * imgs.length) | 0], px, py, size, a, h1 * 6.28 + age * (h3 - 0.5) * 0.7);
    }
    x.globalAlpha = 1; x.globalCompositeOperation = 'source-over';
  }
  function makeBokeh(seed, n, x0, x1, y0, y1, rmin, rmax, gold = 0.8, amin = 0.08, amax = 0.3) {
    const r = rng(seed);
    return Array.from({ length: n }, () => ({
      x: lerp(x0, x1, r()), y: lerp(y0, y1, r()), r: lerp(rmin, rmax, Math.pow(r(), 1.6)),
      gold: r() < gold, a: lerp(amin, amax, r()), ph: r() * 6.28, f: 0.6 + r() * 2,
    }));
  }
  function bokeh(x, u, list, drift = 0) {
    x.globalCompositeOperation = 'lighter';
    for (const b of list) sprite(x, b.gold ? TEX.bokehGold : TEX.bokehWhite, b.x + drift * u, b.y, b.r * 2, b.a * (0.8 + 0.2 * Math.sin(u * b.f + b.ph)));
    x.globalAlpha = 1; x.globalCompositeOperation = 'source-over';
  }
  function glow(x, cx, cy, r, col, a) {
    if (a <= 0.003) return;
    const g = x.createRadialGradient(cx, cy, 0, cx, cy, r);
    g.addColorStop(0, rgb(col, a)); g.addColorStop(0.35, rgb(col, a * 0.35)); g.addColorStop(1, rgb(col, 0));
    x.globalCompositeOperation = 'lighter'; x.fillStyle = g; x.fillRect(cx - r, cy - r, 2 * r, 2 * r);
    x.globalCompositeOperation = 'source-over';
  }
  function flame(x, cx, cy, h, w, u, seed, k = 1) {
    if (k <= 0.01) return;
    const fl = 0.85 + 0.25 * vnoise(u * 9, seed) - 0.1 * vnoise(u * 23, seed + 1);
    const sway = (vnoise(u * 3.3, seed + 2) - 0.5) * w * 1.2;
    const hh = h * fl * k, ww = w * (0.85 + 0.15 * k);
    glow(x, cx, cy - hh * 0.4, h * 3.2, C.gold, 0.22 * k);
    x.beginPath();
    x.moveTo(cx, cy + ww * 0.55);
    x.bezierCurveTo(cx + ww, cy + ww * 0.4, cx + ww * 0.8, cy - hh * 0.45, cx + sway, cy - hh);
    x.bezierCurveTo(cx - ww * 0.8, cy - hh * 0.45, cx - ww, cy + ww * 0.4, cx, cy + ww * 0.55);
    const g = x.createLinearGradient(cx, cy + ww * 0.5, cx + sway, cy - hh);
    g.addColorStop(0, rgb([150, 110, 60], 0.35 * k)); g.addColorStop(0.22, rgb([255, 248, 230], 0.95 * k));
    g.addColorStop(0.55, rgb([244, 196, 116], 0.9 * k)); g.addColorStop(1, rgb([210, 140, 60], 0));
    x.globalCompositeOperation = 'lighter'; x.fillStyle = g; x.fill();
    x.globalCompositeOperation = 'source-over';
  }
  // Silhouette + liseré de lumière du seul côté de la source (lx, ly = direction de la lumière)
  function rimFill(x, path, fill, rimCol, w, lx, ly, blurPx = 0) {
    x.fillStyle = fill; x.fill(path);
    x.save(); x.clip(path);
    x.fillStyle = rimCol; x.fill(path);
    x.translate(-lx * w, -ly * w);
    if (blurPx) x.filter = `blur(${blurPx.toFixed(2)}px)`;
    x.fillStyle = fill; x.fill(path);
    x.restore();
  }
  function rainStreaks(x, u, o) {
    const r = rng(o.seed);
    reset(x); x.lineCap = 'round';
    for (let i = 0; i < o.n; i++) {
      const z = r(), x0 = r(), ph = r();
      const yf = ((ph + u * o.speed * (0.6 + 0.8 * z)) % 1.3) - 0.2;
      const py = yf * H, px = (x0 * 1.3 - 0.15) * W + py * (o.slant || 0.08);
      const len = (0.025 + 0.05 * z) * H;
      let a = o.a * (0.25 + 0.75 * z);
      if (o.light) { const dx = px - o.light[0], dy = py - o.light[1]; a *= 1 + o.light[3] * Math.exp(-(dx * dx + dy * dy) / (o.light[2] * o.light[2])); }
      x.strokeStyle = rgb(o.col || [200, 196, 186], Math.min(0.5, a));
      x.lineWidth = (0.5 + 1.4 * z) * U / 10.8;
      x.beginPath(); x.moveTo(px, py); x.lineTo(px + len * (o.slant || 0.08), py + len); x.stroke();
    }
  }
  // Calque flou (profondeur de champ) : dessin à demi-résolution puis flou
  function blurred(cam, b, fn) {
    const l = L.half;
    reset(l.x); l.x.clearRect(0, 0, l.w, l.h);
    camSet(l.x, cam, 0.5); fn(l.x);
    reset(l.x); reset(ctx);
    ctx.filter = b > 0.05 ? `blur(${(b * U * 0.5).toFixed(2)}px)` : 'none';
    ctx.drawImage(l.c, 0, 0, W, H);
    ctx.filter = 'none';
  }
  function bg(c0, c1) {
    reset(ctx);
    const g = ctx.createLinearGradient(0, 0, 0, H);
    g.addColorStop(0, rgb(c0)); g.addColorStop(1, rgb(c1));
    ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
  }

  /* =========================================================
   * Typographie
   * ======================================================= */
  const SX = v => W / 2 + v * U, SY = v => H / 2 + v * U;
  function tracked(x, str, cx, cy, sizePx, track, font, fill) {
    x.font = font; x.textAlign = 'left'; x.textBaseline = 'alphabetic'; x.fillStyle = fill;
    const chars = [...str], ws = chars.map(ch => x.measureText(ch).width);
    const tot = ws.reduce((a, b) => a + b, 0) + track * sizePx * (chars.length - 1);
    let px = cx - tot / 2;
    chars.forEach((ch, i) => { x.fillText(ch, px, cy); px += ws[i] + track * sizePx; });
  }
  // Note olfactive : « — tabac »
  function caption(u, d, str) {
    const a = prog(u, 0.12, 0.3, E.out) * (1 - prog(u, d - 0.18, 0.18));
    if (a <= 0) return;
    reset(ctx);
    const size = (LAND ? 2.5 : 3.4) * U;
    const px = LAND ? SX(-VX + 10) : W / 2, py = LAND ? SY(VY - 7) : SY(VY - 16);
    ctx.font = `italic 400 ${size}px ${F.serif}`;
    ctx.textBaseline = 'alphabetic';
    const tw = ctx.measureText(str).width, dash = 3.2 * U;
    const x0 = LAND ? px : px - (tw + dash + 1.2 * U) / 2;
    ctx.filter = a < 1 ? `blur(${((1 - a) * 0.5 * U).toFixed(2)}px)` : 'none';
    ctx.fillStyle = rgb(C.gold, 0.85 * a); ctx.fillRect(x0, py - size * 0.32, dash, Math.max(1, 0.12 * U));
    ctx.fillStyle = rgb(C.white, 0.82 * a); ctx.textAlign = 'left';
    ctx.fillText(str, x0 + dash + 1.2 * U, py);
    reset(ctx);
  }
  // Mesure des lettres pour les formules « N + huit → nuit »
  const advCache = new Map();
  function adv(ch) {
    if (!advCache.has(ch)) { ctx.font = `400 48px ${F.serif}`; advCache.set(ch, ctx.measureText(ch).width / 48); }
    return advCache.get(ch);
  }
  function rowX(chars, track = 0.03) {
    const ws = chars.map(c => (c === '+' ? 0.55 : adv(c)));
    const tot = ws.reduce((a, b) => a + b, 0) + track * (ws.length - 1);
    let x = -tot / 2;
    return ws.map(w => { const c = x + w / 2; x += w + track; return c; });
  }
  // Carte de ville : nom, coordonnées, et la nuit dans la langue du lieu
  function cityCard(u, o) {
    const out = 1 - prog(u, o.end - 0.45, 0.45, E.in);
    if (out <= 0) return;
    reset(ctx);
    const ax = LAND ? SX(-VX * 0.5) : W / 2, ay = LAND ? SY(-3) : SY(VY * 0.42);
    const aName = prog(u, 0.15, 0.7, E.out) * out, aCo = prog(u, 0.45, 0.7, E.out) * out;
    const veil = ctx.createRadialGradient(ax, ay + 7 * U, 0, ax, ay + 7 * U, 30 * U);
    veil.addColorStop(0, `rgba(0,0,0,${(0.62 * aName).toFixed(3)})`); veil.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.fillStyle = veil; ctx.fillRect(ax - 30 * U, ay - 23 * U, 60 * U, 60 * U);
    ctx.filter = aName < 1 ? `blur(${((1 - aName) * 0.6 * U).toFixed(2)}px)` : 'none';
    tracked(ctx, o.name, ax, ay, 2.3 * U, 0.62, `300 ${2.3 * U}px ${F.sans}`, rgb(C.goldHi, aName));
    ctx.filter = 'none';
    tracked(ctx, o.coords, ax, ay + 3.6 * U, 1.35 * U, 0.35, `300 ${1.35 * U}px ${F.sans}`, rgb(C.gray, aCo * 0.9));
    ctx.fillStyle = rgb(C.gold, aCo * 0.7); ctx.fillRect(ax - 3 * U, ay + 5.6 * U, 6 * U, Math.max(1, 0.1 * U));
    const fy = ay + 14 * U, size = (LAND ? 7.5 : 9) * U;
    if (o.arabic) {
      const a = prog(u, 0.9, 0.8, E.out) * out;
      ctx.font = `400 ${size * 1.25}px ${F.arabic}`; ctx.textAlign = 'center'; ctx.direction = 'rtl';
      ctx.shadowColor = rgb(C.gold, 0.5 * a); ctx.shadowBlur = 1.6 * U;
      ctx.fillStyle = rgb(C.gold, a); ctx.fillText(o.arabic, ax, fy + 1.5 * U);
      ctx.direction = 'ltr';
      reset(ctx);
      return;
    }
    const f = o.formula, N = 'N', eight = [...f.eight], night = [...f.night];
    const r1 = rowX([N, '+', ...eight]), r2 = rowX(night);
    const aIn = prog(u, 0.85, 0.5, E.out) * out, pS = prog(u, 1.75, 0.65, E.inOut), pSw = prog(u, 2.05, 0.35, E.inOut);
    const pOff = prog(u, 1.55, 0.35, E.out);
    ctx.font = `400 ${size}px ${F.serif}`; ctx.textAlign = 'center'; ctx.textBaseline = 'alphabetic';
    ctx.shadowColor = rgb(C.gold, 0.45 * aIn); ctx.shadowBlur = 1.4 * U;
    const put = (ch, xEm, a, col = C.gold) => { if (a <= 0.003) return; ctx.fillStyle = rgb(col, a); ctx.fillText(ch, ax + xEm * size, fy); };
    const jN = f.map.indexOf(0);
    const xN = lerp(r1[0], r2[jN], pS);
    if (N === night[jN]) put(N, xN, aIn, C.goldHi);
    else { put(N, xN, aIn * (1 - pSw), C.goldHi); put(night[jN], xN, aIn * pSw, C.goldHi); }
    // « + »
    const pa = aIn * (1 - pOff);
    if (pa > 0) { ctx.fillStyle = rgb(C.gold, pa); const px = ax + r1[1] * size, py = fy - 0.27 * size, h = 0.13 * size, lw = Math.max(1, 0.02 * size); ctx.fillRect(px - h, py - lw / 2, 2 * h, lw); ctx.fillRect(px - lw / 2, py - h, lw, 2 * h); }
    eight.forEach((ch, k) => {
      const j = f.map.indexOf(k + 1);
      if (j < 0) { put(ch, r1[k + 2], aIn * (1 - pOff), C.white); return; }
      const x = lerp(r1[k + 2], r2[j], pS), col = mixC(C.white, C.gold, pS);
      if (ch === night[j]) put(ch, x, aIn, col);
      else { put(ch, x, aIn * (1 - pSw), col); put(night[j], x, aIn * pSw, col); }
    });
    f.map.forEach((m, j) => { if (m === -1) put(night[j], r2[j], aIn * pSw, C.gold); });
    reset(ctx);
  }

  /* =========================================================
   * Silhouettes (tracés dans une boîte 0–100)
   * ======================================================= */
  const P = {};
  function buildPaths() {
    P.man = new Path2D('M30 22 C31 12 40 8 52 8 C62 8 70 11 70 18 L71 24 C78 24 84 25 86 27 C84 28.5 76 29 70 29 L68 30 C69 33 69 35 70 37 C71 39 73 41 74 43.5 C74 45 72 45.5 71 46 C71.5 47 72 47.5 71.5 48.5 C72 49.5 71.5 50.5 70.8 51 C71 53 70.5 55 68.5 56.5 C66 57.5 62 57.5 60 58 L60 62 C64 63 68 65 70 68 C76 72 80 85 82 120 L0 120 L0 96 C6 80 18 70 34 66 C40 64 44 62 45 58 C42 52 40 46 40 40 C40 34 36 31 28 30 C22 29.5 18 28.5 18 27.5 C22 26 27 25 30 25 Z');
    P.hand = new Path2D('M73.5 50.5 C77 47.6 84 47.8 87.5 50.6 C89.6 53.6 88 58.4 84 59.8 C80 61 75.6 59.2 74.2 56 Z M79.5 58.5 L93 86 L85.5 89 L73.8 59.6 Z');
    P.bust = new Path2D('M40 34 C39 21 49 12 61 12 C71 12 77 20 77 30 C77 33 78 35 79 38 C81 41 82 43 81 44.5 C80 45.5 79 46 78.5 47 C79 48.5 79 50 78 51 C78.5 53 77.5 56 74.5 57 C71 58 68 58.5 66 60 L65 68 C71 70 81 74 87 82 C91 88 93 100 93 112 L18 112 C18 98 23 88 33 81 C39 77 43 74 45 70 C41 63 39 52 40 42 Z');
    P.petal = new Path2D('M0 6 C-3.5 4.5 -5.5 0.5 -4.5 -2.5 C-3.6 -5 -1.4 -5.8 0 -4.4 C1.4 -5.8 3.6 -5 4.5 -2.5 C5.5 0.5 3.5 4.5 0 6 Z');
    P.leaf = new Path2D('M0 0 C3 -2.6 9 -2.8 14 0 C9 2.8 3 2.6 0 0 Z');
  }

  /* =========================================================
   * Éléments de décor
   * ======================================================= */
  function cigar(x, tipX, y, len, dia, ember, flameLight = 0, u = 0) {
    const y0 = y - dia / 2;
    const g = x.createLinearGradient(0, y0, 0, y0 + dia);
    g.addColorStop(0, '#2a2018'); g.addColorStop(0.35, '#1a130e'); g.addColorStop(1, '#070505');
    x.fillStyle = g;
    x.beginPath(); x.roundRect(tipX - len, y0, len, dia, dia * 0.35); x.fill();
    x.strokeStyle = 'rgba(0,0,0,0.35)'; x.lineWidth = dia * 0.03;
    for (let i = 0; i < len / dia * 2; i++) {
      const px = tipX - len + i * dia * 0.55;
      x.beginPath(); x.moveTo(px, y0); x.lineTo(px + dia * 0.45, y0 + dia); x.stroke();
    }
    // bague dorée
    const bx = tipX - len * 0.72, bw = dia * 0.95;
    const bg2 = x.createLinearGradient(0, y0, 0, y0 + dia);
    bg2.addColorStop(0, rgb(C.goldHi, 0.95)); bg2.addColorStop(0.4, rgb(C.gold)); bg2.addColorStop(1, rgb(C.goldDeep));
    x.fillStyle = bg2; x.fillRect(bx, y0 - dia * 0.02, bw, dia * 1.04);
    x.fillStyle = 'rgba(20,14,6,0.6)';
    for (let i = 0; i < 6; i++) x.fillRect(bx + bw * (0.12 + i * 0.14), y0 + dia * 0.42, bw * 0.06, dia * 0.16);
    // reflet supérieur
    x.fillStyle = rgb(C.gold, 0.12 + 0.35 * flameLight);
    x.fillRect(tipX - len, y0 + dia * 0.08, len, dia * 0.06);
    // cendre et braise
    const ashW = dia * 0.35;
    x.fillStyle = '#3a3836'; x.fillRect(tipX - ashW, y0, ashW, dia);
    x.fillStyle = 'rgba(90,88,84,0.6)';
    for (let i = 0; i < 4; i++) x.fillRect(tipX - ashW + i * ashW * 0.25, y0, ashW * 0.06, dia);
    if (ember > 0.01) {
      const eg = x.createLinearGradient(tipX - ashW * 1.6, 0, tipX, 0);
      eg.addColorStop(0, 'rgba(0,0,0,0)'); eg.addColorStop(0.55, rgb([230, 140, 50], 0.85 * ember)); eg.addColorStop(1, rgb([255, 214, 140], ember));
      x.globalCompositeOperation = 'lighter'; x.fillStyle = eg; x.fillRect(tipX - ashW * 1.6, y0 + dia * 0.05, ashW * 1.6, dia * 0.9);
      x.globalCompositeOperation = 'source-over';
      glow(x, tipX, y, dia * 2.6, [236, 150, 60], 0.35 * ember);
      glow(x, tipX, y, dia * 0.9, [255, 220, 160], 0.4 * ember);
    }
  }
  function glass(x, cx, by, w, h, level, o = {}) {
    const top = by - h, inset = w * 0.06, baseT = h * 0.13, bw = w * 0.9;
    const pathOuter = new Path2D();
    pathOuter.moveTo(cx - w / 2, top); pathOuter.lineTo(cx + w / 2, top); pathOuter.lineTo(cx + bw / 2, by); pathOuter.lineTo(cx - bw / 2, by); pathOuter.closePath();
    const inner = new Path2D();
    inner.moveTo(cx - w / 2 + inset, top); inner.lineTo(cx + w / 2 - inset, top); inner.lineTo(cx + bw / 2 - inset, by - baseT); inner.lineTo(cx - bw / 2 + inset, by - baseT); inner.closePath();
    x.fillStyle = 'rgba(255,255,255,0.025)'; x.fill(pathOuter);
    const ly = by - baseT - (h - baseT) * level;
    x.save(); x.clip(inner);
    const lg = x.createLinearGradient(0, ly, 0, by - baseT);
    lg.addColorStop(0, rgb([226, 168, 84], 0.92)); lg.addColorStop(0.5, rgb([168, 98, 34], 0.92)); lg.addColorStop(1, rgb([82, 42, 14], 0.95));
    x.fillStyle = lg; x.fillRect(cx - w, ly, 2 * w, h);
    const sg = x.createLinearGradient(cx - w / 2, 0, cx + w / 2, 0);
    sg.addColorStop(0, 'rgba(0,0,0,0.55)'); sg.addColorStop(0.3, 'rgba(0,0,0,0)'); sg.addColorStop(0.75, 'rgba(0,0,0,0.1)'); sg.addColorStop(1, 'rgba(0,0,0,0.6)');
    x.fillStyle = sg; x.fillRect(cx - w, ly, 2 * w, h);
    glow(x, cx + w * 0.1, (ly + by) / 2, w * 0.45, [255, 200, 120], 0.3);
    if (o.bubbles) {
      x.fillStyle = 'rgba(255,236,200,0.5)';
      for (let i = 0; i < 26; i++) {
        const bx = cx + (hash1(i * 3 + 1) - 0.5) * w * 0.8, sp = 3 + hash1(i * 5) * 7;
        const byy = by - baseT - (((o.u || 0) * sp + hash1(i * 7) * 30) % Math.max(1, by - baseT - ly));
        x.beginPath(); x.arc(bx, byy, 0.12 + hash1(i * 11) * 0.22, 0, Math.PI * 2); x.fill();
      }
    }
    if (o.ice) for (const ic of o.ice) {
      x.save(); x.translate(ic.x, ic.y); x.rotate(ic.r);
      x.fillStyle = 'rgba(255,248,236,0.10)'; x.strokeStyle = 'rgba(255,246,230,0.45)'; x.lineWidth = 0.25;
      x.beginPath(); x.roundRect(-ic.s / 2, -ic.s / 2, ic.s, ic.s, ic.s * 0.18); x.fill(); x.stroke();
      x.strokeStyle = 'rgba(255,246,230,0.2)'; x.beginPath(); x.moveTo(-ic.s * 0.3, -ic.s * 0.1); x.lineTo(ic.s * 0.2, ic.s * 0.3); x.stroke();
      x.restore();
    }
    x.restore();
    // ménisque
    x.strokeStyle = rgb(C.goldHi, 0.6); x.lineWidth = 0.3;
    x.beginPath(); x.ellipse(cx, ly, w / 2 - inset - (w - bw) * (1 - level) * 0.25, w * 0.05, 0, 0, Math.PI * 2); x.stroke();
    // arêtes du verre
    const eg = x.createLinearGradient(0, top, 0, by);
    eg.addColorStop(0, 'rgba(255,250,240,0.6)'); eg.addColorStop(1, 'rgba(255,250,240,0.15)');
    x.strokeStyle = eg; x.lineWidth = 0.45;
    x.beginPath(); x.moveTo(cx - w / 2, top); x.lineTo(cx - bw / 2, by); x.moveTo(cx + w / 2, top); x.lineTo(cx + bw / 2, by); x.stroke();
    x.strokeStyle = 'rgba(255,250,240,0.25)'; x.lineWidth = 0.9;
    x.beginPath(); x.moveTo(cx - w / 2 + inset * 0.6, top + h * 0.05); x.lineTo(cx - bw / 2 + inset * 0.6, by - baseT * 1.2); x.stroke();
    x.strokeStyle = 'rgba(255,250,240,0.45)'; x.lineWidth = 0.3;
    x.beginPath(); x.ellipse(cx, top, w / 2, w * 0.06, 0, 0, Math.PI * 2); x.stroke();
    x.fillStyle = rgb(C.gold, 0.35);
    x.beginPath(); x.ellipse(cx, by - baseT * 0.5, bw / 2 - inset, baseT * 0.35, 0, 0, Math.PI * 2); x.fill();
    return ly;
  }
  function eiffel(x, cx, by, h, u, sparkle) {
    const hw = t => h * (0.006 + 0.205 * Math.pow(t, 2.35));
    const pts = [];
    for (let i = 0; i <= 40; i++) { const t = 0.02 + 0.98 * i / 40; pts.push([cx + hw(t), by - h * (1 - t)]); }
    const path = new Path2D();
    path.moveTo(cx, by - h * 1.06);
    path.lineTo(cx + h * 0.004, by - h);
    pts.forEach(p => path.lineTo(p[0], p[1]));
    const fr = hw(1);
    path.lineTo(cx + fr * 0.55, by);
    path.lineTo(cx + hw(0.9) * 0.5, by - h * 0.1);
    path.quadraticCurveTo(cx + hw(0.85) * 0.35, by - h * 0.165, cx, by - h * 0.17);
    path.quadraticCurveTo(cx - hw(0.85) * 0.35, by - h * 0.165, cx - hw(0.9) * 0.5, by - h * 0.1);
    path.lineTo(cx - fr * 0.55, by);
    for (let i = pts.length - 1; i >= 0; i--) path.lineTo(2 * cx - pts[i][0], pts[i][1]);
    path.lineTo(cx - h * 0.004, by - h);
    path.closePath();
    x.save();
    x.shadowColor = rgb(C.gold, 0.55); x.shadowBlur = 3.5 * U;
    const g = x.createLinearGradient(0, by - h, 0, by);
    g.addColorStop(0, rgb([170, 118, 52])); g.addColorStop(0.6, rgb([206, 146, 64])); g.addColorStop(1, rgb([226, 168, 82]));
    x.fillStyle = g; x.fill(path);
    x.restore();
    x.save(); x.clip(path);
    x.strokeStyle = 'rgba(30,18,6,0.55)'; x.lineWidth = h * 0.0045;
    for (const rot of [0.85, -0.85]) {
      x.save(); x.translate(cx, by - h / 2); x.rotate(rot);
      for (let k = -h; k < h; k += h * 0.022) { x.beginPath(); x.moveTo(k, -h); x.lineTo(k, h); x.stroke(); }
      x.restore();
    }
    const cg = x.createLinearGradient(cx - fr, 0, cx + fr, 0);
    cg.addColorStop(0, 'rgba(0,0,0,0.35)'); cg.addColorStop(0.5, 'rgba(0,0,0,0)'); cg.addColorStop(1, 'rgba(0,0,0,0.45)');
    x.fillStyle = cg; x.fillRect(cx - fr, by - h * 1.1, 2 * fr, h * 1.1);
    x.restore();
    x.fillStyle = rgb([236, 186, 104]);
    for (const [t, th] of [[0.81, 0.016], [0.62, 0.013], [0.17, 0.01]]) x.fillRect(cx - hw(t) * 1.12, by - h * (1 - t), hw(t) * 2.24, h * th);
    if (sparkle) {
      x.globalCompositeOperation = 'lighter';
      const slot = Math.floor(u * 14);
      for (let i = 0; i < 160; i++) {
        if (hash1(i * 31 + slot * 977) < 0.8) continue;
        const t = 0.05 + 0.93 * hash1(i * 17 + 3), s = (hash1(i * 13 + 5) * 2 - 1) * hw(t) * 0.92;
        const px = cx + s, py = by - h * (1 - t), r = h * (0.004 + 0.004 * hash1(i * 7 + slot));
        const sg = x.createRadialGradient(px, py, 0, px, py, r * 4);
        sg.addColorStop(0, 'rgba(255,255,252,1)'); sg.addColorStop(0.3, 'rgba(255,250,236,0.5)'); sg.addColorStop(1, 'rgba(255,250,236,0)');
        x.fillStyle = sg; x.fillRect(px - r * 4, py - r * 4, r * 8, r * 8);
      }
      x.globalCompositeOperation = 'source-over';
    }
  }
  function parisRoofs(x, y0, seed, x0, x1, k = 1) {
    const r = rng(seed);
    for (let bx = x0; bx < x1;) {
      const w = (12 + r() * 12) * k, top = y0 + (r() - 0.5) * 3 * k, mh = (4.5 + r() * 2.5) * k, inset = mh * 0.55;
      x.fillStyle = '#060606';
      x.beginPath(); x.moveTo(bx, top + mh); x.lineTo(bx + inset, top); x.lineTo(bx + w - inset, top); x.lineTo(bx + w, top + mh); x.lineTo(bx + w, 400); x.lineTo(bx, 400); x.closePath(); x.fill();
      x.strokeStyle = rgb(C.gold, 0.16); x.lineWidth = 0.18 * k;
      x.beginPath(); x.moveTo(bx, top + mh); x.lineTo(bx + inset, top); x.lineTo(bx + w - inset, top); x.lineTo(bx + w, top + mh); x.stroke();
      const nCh = 1 + Math.floor(r() * 2);
      for (let c = 0; c < nCh; c++) {
        const cx = bx + inset + r() * (w - 2 * inset - 4 * k), ch = (3 + r() * 2) * k, cw = (2.5 + r() * 2.5) * k;
        x.fillStyle = '#060606'; x.fillRect(cx, top - ch, cw, ch + 0.5);
        for (let p = 0; p < Math.floor(cw / (0.9 * k)); p++) x.fillRect(cx + 0.25 * k + p * 0.9 * k, top - ch - 1.1 * k, 0.5 * k, 1.1 * k);
      }
      const nD = Math.floor((w - 2 * inset) / (4 * k));
      for (let d = 0; d < nD; d++) {
        const dx = bx + inset + 1 * k + d * 4 * k, lit = r() < 0.3;
        x.fillStyle = '#080808';
        x.beginPath(); x.moveTo(dx, top + mh * 0.75); x.lineTo(dx, top + mh * 0.25); x.lineTo(dx + 1 * k, top - 0.4 * k); x.lineTo(dx + 2 * k, top + mh * 0.25); x.lineTo(dx + 2 * k, top + mh * 0.75); x.closePath(); x.fill();
        if (lit) { x.fillStyle = rgb([226, 170, 92], 0.55 + r() * 0.3); x.fillRect(dx + 0.45 * k, top + mh * 0.32, 1.1 * k, mh * 0.38); }
      }
      for (let wy = top + mh + 2.5 * k; wy < y0 + 40; wy += 4 * k) {
        for (let wx = bx + 1.5 * k; wx < bx + w - 2 * k; wx += 3.2 * k) {
          if (r() < 0.12) { x.fillStyle = rgb([220, 164, 88], 0.25 + r() * 0.4); x.fillRect(wx, wy, 1.4 * k, 2.2 * k); }
        }
      }
      bx += w;
    }
  }
  function colosseum(x, cx, by, w, h, u, o = {}) {
    const N = 26, TH = 1.12, lv = [0.27, 0.25, 0.24, 0.24];
    const xs = th => cx + (w / 2) * Math.sin(th) / Math.sin(TH);
    const ruin = th => (th < 0.5 ? 4 : th < 0.72 ? 3 : th < 0.95 ? 2 : 1.4 + 0.6 * Math.cos((th - 0.95) * 9));
    let y = by;
    const tex = pattern(x, TEX.stone, 0.06);
    for (let l = 0; l < 4; l++) {
      const lh = h * lv[l], yt = y - lh;
      x.beginPath();
      x.moveTo(xs(-TH), y);
      const steps = 60;
      for (let i = 0; i <= steps; i++) {
        const th = -TH + 2 * TH * i / steps, levels = ruin(th);
        const top = l < Math.floor(levels) ? yt : (l < levels ? lerp(y, yt, levels - Math.floor(levels)) : y);
        x.lineTo(xs(th), top);
      }
      x.lineTo(xs(TH), y); x.closePath();
      const g = x.createLinearGradient(0, by, 0, by - h);
      g.addColorStop(0, rgb([226, 170, 96])); g.addColorStop(0.5, rgb([178, 128, 66])); g.addColorStop(1, rgb([110, 78, 40]));
      x.fillStyle = g; x.fill();
      x.save(); x.clip(); x.globalCompositeOperation = 'multiply'; x.globalAlpha = 0.5; x.fillStyle = tex; x.fillRect(cx - w, by - h * 1.2, 2 * w, h * 1.3); x.restore();
      for (let i = 0; i < N; i++) {
        const th = -TH + 2 * TH * (i + 0.5) / N;
        if (l >= ruin(th) - 0.05) continue;
        const ax = xs(th), aw = (w / N) * 0.62 * Math.cos(th) * 1.15;
        const isAttic = l === 3;
        const ah = isAttic ? lh * 0.28 : lh * 0.68, ay = y - lh * 0.12;
        const ig = x.createLinearGradient(0, ay, 0, ay - ah);
        ig.addColorStop(0, rgb([150, 96, 40], isAttic ? 0.6 : 1)); ig.addColorStop(1, rgb([30, 18, 8]));
        x.fillStyle = ig;
        x.beginPath();
        if (isAttic) x.rect(ax - aw * 0.22, ay - lh * 0.45, aw * 0.44, ah);
        else { x.moveTo(ax - aw / 2, ay); x.lineTo(ax - aw / 2, ay - ah + aw / 2); x.arc(ax, ay - ah + aw / 2, aw / 2, Math.PI, 0); x.lineTo(ax + aw / 2, ay); x.closePath(); }
        x.fill();
        if (!isAttic) { x.strokeStyle = rgb([255, 214, 150], 0.22); x.lineWidth = aw * 0.05; x.beginPath(); x.arc(ax, ay - ah + aw / 2, aw / 2, Math.PI, 0); x.stroke(); }
      }
      x.fillStyle = rgb([240, 196, 126], 0.35);
      x.fillRect(xs(-TH), yt - h * 0.006, xs(TH) - xs(-TH), h * 0.012);
      y = yt;
    }
  }
  function dunes(x, u, o) {
    const r = rng(o.seed);
    const layers = Array.from({ length: 5 }, (_, i) => ({ base: o.y0 + i * o.dy, A: 4 + r() * 5 + i * 1.5, f: 0.03 + r() * 0.03, p: r() * 6, f2: 0.09 + r() * 0.05, p2: r() * 6 }));
    const yAt = (L0, X) => { const ph = X * L0.f + L0.p, sk = Math.sin(ph + 0.6 * Math.sin(ph)); return L0.base - L0.A * Math.pow(0.5 + 0.5 * sk, 2.4) - L0.A * 0.22 * Math.sin(X * L0.f2 + L0.p2); };
    layers.forEach((L0, i) => {
      const k = i / (layers.length - 1);
      x.beginPath(); x.moveTo(-200, 300);
      for (let X = -200; X <= 200; X += 2) x.lineTo(X, yAt(L0, X + o.pan * (0.4 + k)));
      x.lineTo(200, 300); x.closePath();
      const dg = x.createLinearGradient(0, L0.base - L0.A * 1.2, 0, L0.base + 14);
      dg.addColorStop(0, rgb(mixC([58, 48, 36], [40, 33, 25], k))); dg.addColorStop(0.35, rgb(mixC([20, 17, 14], [12, 10, 8], k))); dg.addColorStop(1, rgb([3, 3, 3]));
      x.fillStyle = dg; x.fill();
      x.beginPath();
      for (let X = -200; X <= 200; X += 2) { const yy = yAt(L0, X + o.pan * (0.4 + k)); X === -200 ? x.moveTo(X, yy) : x.lineTo(X, yy); }
      x.strokeStyle = rgb(mixC(C.gold, C.goldHi, 0.3), 0.25 + 0.4 * k); x.lineWidth = 0.18 + 0.25 * k;
      x.shadowColor = rgb(C.gold, 0.6); x.shadowBlur = 0.8 * U; x.stroke(); x.shadowBlur = 0;
      if (i === layers.length - 1 && o.sand) {
        x.globalCompositeOperation = 'lighter';
        for (let p = 0; p < 260; p++) {
          const sx0 = -120 + hash1(p * 7) * 240, ph = hash1(p * 11), life = 1.2 + hash1(p * 13) * 1.5;
          const age = ((u + ph * life) % life), kk = age / life;
          const px = sx0 + age * o.sand * (1 + hash1(p * 3)), crest = yAt(L0, sx0 + o.pan * 1.4);
          const py = crest - age * 1.5 - Math.sin(age * 4 + p) * 0.4;
          x.fillStyle = rgb(C.goldHi, 0.5 * (1 - kk) * Math.min(1, kk * 6));
          x.fillRect(px, py, 0.18, 0.18);
        }
        x.globalCompositeOperation = 'source-over';
      }
    });
  }
  function stars(x, seed, n, x0, x1, y0, y1, u, a = 1) {
    const r = rng(seed);
    for (let i = 0; i < n; i++) {
      const sx = lerp(x0, x1, r()), sy = lerp(y0, y1, r()), s = 0.06 + r() * 0.16, ph = r() * 6.28;
      x.fillStyle = rgb(C.white, a * (0.35 + 0.35 * Math.sin(u * 1.5 + ph)));
      x.fillRect(sx, sy, s, s);
    }
  }
  function crescent(x, cx, cy, r) {
    glow(x, cx, cy, r * 9, C.goldHi, 0.12);
    x.save();
    x.beginPath(); x.arc(cx, cy, r, 0, Math.PI * 2); x.arc(cx + r * 0.42, cy - r * 0.2, r * 0.86, 0, Math.PI * 2, true);
    x.fillStyle = rgb([246, 236, 212]); x.shadowColor = rgb(C.goldHi, 0.9); x.shadowBlur = 2 * U; x.fill('evenodd');
    x.restore();
  }
  function mosque(x, cx, by, s) {
    const domeP = new Path2D();
    const dw = 22 * s, dh = 24 * s, dy = by - 22 * s;
    domeP.moveTo(cx - dw / 2, dy);
    domeP.bezierCurveTo(cx - dw * 0.62, dy - dh * 0.55, cx - dw * 0.22, dy - dh * 0.8, cx, dy - dh);
    domeP.bezierCurveTo(cx + dw * 0.22, dy - dh * 0.8, cx + dw * 0.62, dy - dh * 0.55, cx + dw / 2, dy);
    domeP.closePath();
    const lit = (y0, y1) => { const g = x.createLinearGradient(0, y0, 0, y1); g.addColorStop(0, rgb([230, 176, 98])); g.addColorStop(1, rgb([96, 66, 30])); return g; };
    x.save(); x.shadowColor = rgb(C.gold, 0.5); x.shadowBlur = 2.5 * U;
    x.fillStyle = lit(by, by - 30 * s); x.fillRect(cx - 40 * s, by - 14 * s, 80 * s, 14 * s);
    x.fillStyle = lit(by - 14 * s, by - 24 * s); x.fillRect(cx - 14 * s, by - 23 * s, 28 * s, 10 * s);
    x.fillStyle = lit(dy, dy - dh); x.fill(domeP);
    for (const m of [-1, 1]) {
      const mx = cx + m * 34 * s, mt = by - 62 * s;
      x.fillStyle = lit(by, mt); x.fillRect(mx - 1.8 * s, mt, 3.6 * s, 62 * s);
      x.fillRect(mx - 3 * s, by - 40 * s, 6 * s, 1.4 * s); x.fillRect(mx - 2.6 * s, by - 52 * s, 5.2 * s, 1.2 * s);
      x.beginPath(); x.moveTo(mx - 1.8 * s, mt); x.lineTo(mx, mt - 7 * s); x.lineTo(mx + 1.8 * s, mt); x.closePath(); x.fill();
      x.fillRect(mx - 0.15 * s, mt - 9.5 * s, 0.3 * s, 2.5 * s);
    }
    for (const m of [-1, 1]) {
      const sx = cx + m * 22 * s, sdy = by - 14 * s, sw = 9 * s;
      x.beginPath(); x.moveTo(sx - sw / 2, sdy); x.quadraticCurveTo(sx - sw * 0.5, sdy - sw * 0.9, sx, sdy - sw); x.quadraticCurveTo(sx + sw * 0.5, sdy - sw * 0.9, sx + sw / 2, sdy); x.fill();
    }
    x.restore();
    x.fillStyle = rgb([255, 226, 160], 0.75);
    for (let i = -6; i <= 6; i++) { const ax = cx + i * 5.6 * s; x.beginPath(); x.moveTo(ax - 1.4 * s, by); x.lineTo(ax - 1.4 * s, by - 6 * s); x.arc(ax, by - 6 * s, 1.4 * s, Math.PI, 0); x.lineTo(ax + 1.4 * s, by); x.fill(); }
    x.strokeStyle = rgb(C.goldHi, 0.9); x.lineWidth = 0.35 * s; x.fillStyle = rgb(C.goldHi);
    x.fillRect(cx - 0.2 * s, dy - dh - 4 * s, 0.4 * s, 4 * s);
    x.beginPath(); x.arc(cx, dy - dh - 5.2 * s, 1.1 * s, 0.4, Math.PI * 2 - 0.4); x.stroke();
    const sh = x.createLinearGradient(cx - dw / 2, 0, cx + dw / 2, 0);
    sh.addColorStop(0, 'rgba(0,0,0,0.5)'); sh.addColorStop(0.6, 'rgba(0,0,0,0)'); sh.addColorStop(1, 'rgba(255,230,180,0.15)');
    x.fillStyle = sh; x.fill(domeP);
  }
  function palm(x, bx, by, h, lean, u, seed) {
    x.strokeStyle = '#050505'; x.lineWidth = h * 0.035; x.lineCap = 'round'; x.shadowColor = rgb(C.gold, 0.5); x.shadowBlur = 0.6 * U;
    const tx = bx + lean * h, ty = by - h;
    x.beginPath(); x.moveTo(bx, by); x.quadraticCurveTo(bx + lean * h * 0.2, by - h * 0.6, tx, ty); x.stroke();
    x.lineWidth = h * 0.012;
    for (let i = 0; i < 11; i++) {
      const a = -Math.PI / 2 + (i / 10 - 0.5) * 3.4 + Math.sin(u * 1.4 + i + seed) * 0.04;
      const L0 = h * (0.32 + 0.12 * hash1(i + seed));
      const ex = tx + Math.cos(a) * L0, ey = ty + Math.sin(a) * L0 * 0.75 + L0 * 0.35 * Math.abs(Math.cos(a));
      x.beginPath(); x.moveTo(tx, ty); x.quadraticCurveTo(tx + Math.cos(a) * L0 * 0.6, ty + Math.sin(a) * L0 * 0.75 - L0 * 0.1, ex, ey); x.stroke();
      for (let f = 1; f < 8; f++) {
        const q = f / 8, fx = lerp(tx, ex, q), fy = lerp(ty, ey, q) - Math.sin(q * Math.PI) * L0 * 0.12;
        x.beginPath(); x.moveTo(fx, fy); x.lineTo(fx + Math.cos(a + 1.2) * L0 * 0.14, fy + L0 * 0.16); x.moveTo(fx, fy); x.lineTo(fx + Math.cos(a - 1.2) * L0 * 0.14, fy + L0 * 0.16); x.stroke();
      }
    }
    x.shadowBlur = 0;
  }

  /* =========================================================
   * Plans
   * ======================================================= */
  const BPM = 96, BEAT = 60 / BPM;
  const EV = [];
  const ev = (type, t, extra = {}) => EV.push({ type, t: +t.toFixed(3), ...extra });
  const SHOTS = [];
  const ENV = []; // ambiances par plan

  // --- Ouverture : l'allumette, le cigare
  function shotIntro(u, d) {
    bg([3, 3, 3], [1, 1, 1]);
    const s = LAND ? 1 : 1.25;
    const cam = { x: 2, y: 0, s: s * lerp(1, 1.07, prog(u, 0, d, E.sine)) };
    const strike = 0.95, fl = prog(u, strike, 0.12) * (1 - prog(u, 2.55, 0.35, E.in));
    const ember = prog(u, 1.4, 1.0, E.out) * (0.75 + 0.25 * Math.sin(u * 2.4)) + 0.4 * bump(u, 3.2, 1.0);
    camSet(ctx, cam);
    glow(ctx, 6, 2, 60, C.gold, 0.1 * fl + 0.04 * ember);
    // fumée
    smoke(ctx, u, { x: 8, y: 0, rate: 9, life: 4, rise: 5, spread: 1.2, curl: 2.4, wind: 1.4, s0: 2, s1: 18, a: 0.2 * prog(u, 1.6, 1), seed: 11, gold: 0, start: 1.6 });
    camSet(ctx, cam);
    cigar(ctx, 8, 0, 90, 6, ember, fl, u);
    // allumette et doigts
    const mx = lerp(19, 13, prog(u, 0.2, 0.8, E.out)) + prog(u, 2.5, 0.6, E.in) * 18, my = lerp(9, 4.5, prog(u, 0.2, 0.8, E.out)) + prog(u, 2.5, 0.6, E.in) * 10;
    ctx.save();
    ctx.lineCap = 'round';
    ctx.strokeStyle = '#1a1612'; ctx.lineWidth = 0.6;
    ctx.beginPath(); ctx.moveTo(mx, my); ctx.lineTo(mx + 40, my + 22); ctx.stroke();
    ctx.strokeStyle = rgb(C.gold, 0.45 * fl); ctx.lineWidth = 0.18;
    ctx.beginPath(); ctx.moveTo(mx + 0.6, my - 0.3); ctx.lineTo(mx + 14, my + 7.4); ctx.stroke();
    ctx.restore();
    ctx.fillStyle = rgb([60, 30, 16]); ctx.beginPath(); ctx.ellipse(mx, my, 0.8, 0.55, 0.5, 0, Math.PI * 2); ctx.fill();
    flame(ctx, mx - 0.2, my - 0.5, 5.2, 1.6, u, 3, fl);
    // étincelles de l'allumette
    if (u > strike && u < strike + 0.45) {
      ctx.globalCompositeOperation = 'lighter';
      for (let i = 0; i < 26; i++) {
        const a = hash1(i * 3) * 6.28, v = 6 + hash1(i * 5) * 16, tt = u - strike;
        const px = mx + Math.cos(a) * v * tt, py = my + Math.sin(a) * v * tt + 20 * tt * tt;
        ctx.fillStyle = rgb(C.goldHi, (1 - tt / 0.45) * 0.9); ctx.fillRect(px, py, 0.22, 0.22);
      }
      ctx.globalCompositeOperation = 'source-over';
      glow(ctx, mx, my, 30, C.goldHi, 0.35 * (1 - (u - strike) / 0.45));
    }
    if (u > 2.6) smoke(ctx, u, { x: mx, y: my - 2, rate: 14, life: 1.6, rise: 6, spread: 0.3, curl: 0.8, s0: 0.6, s1: 5, a: 0.3, seed: 12, start: 2.6, stop: 3.2 });
    reset(ctx);
    // la phrase
    const a = prog(u, 2.6, 0.9, E.out) * (1 - prog(u, d - 0.5, 0.45, E.in));
    if (a > 0) {
      ctx.font = `italic 400 ${(LAND ? 3.1 : 4.2) * U}px ${F.serif}`; ctx.textAlign = 'center';
      ctx.filter = a < 1 ? `blur(${((1 - a) * 0.6 * U).toFixed(2)}px)` : 'none';
      ctx.fillStyle = rgb(C.white, 0.86 * a);
      ctx.fillText('Chaque nuit a son parfum.', W / 2, SY(LAND ? 26 : 40));
      reset(ctx);
    }
  }

  // --- PARIS
  const PARIS_BOKEH = makeBokeh(31, 70, -110, 110, -60, 60, 1.2, 6, 0.85, 0.06, 0.28);
  function shotParis1(u, d) {
    bg([4, 4, 4], [20, 17, 12]);
    const tx = LAND ? 30 : 10, ty = LAND ? 26 : 38, th = LAND ? 62 : 96;
    const cam = { x: tx * 0.3, y: -4, s: lerp(1, 1.07, prog(u, 0, d, E.sine)) };
    camSet(ctx, cam);
    ctx.globalAlpha = 0.5; ctx.fillStyle = pattern(ctx, TEX.clouds, 0.14, -u * 2, -50, 0.06); ctx.fillRect(-200, -150, 400, 170); ctx.globalAlpha = 1;
    // faisceau du phare
    const ang = -Math.PI / 2 + Math.sin(u * 0.9 + 1) * 1.1;
    const bxp = tx, byp = ty - th * 1.04;
    ctx.globalCompositeOperation = 'lighter';
    const bgd = ctx.createLinearGradient(bxp, byp, bxp + Math.cos(ang) * 160, byp + Math.sin(ang) * 160);
    bgd.addColorStop(0, rgb(C.goldHi, 0.22)); bgd.addColorStop(1, rgb(C.goldHi, 0));
    ctx.fillStyle = bgd;
    ctx.beginPath(); ctx.moveTo(bxp, byp);
    ctx.lineTo(bxp + Math.cos(ang - 0.04) * 160, byp + Math.sin(ang - 0.04) * 160); ctx.lineTo(bxp + Math.cos(ang + 0.04) * 160, byp + Math.sin(ang + 0.04) * 160); ctx.fill();
    ctx.globalCompositeOperation = 'source-over';
    eiffel(ctx, tx, ty, th, u, true);
    parisRoofs(ctx, LAND ? 18 : 30, 7, -140, 140, LAND ? 1 : 1.2);
    reset(ctx);
  }
  function shotParisBottles(u, d) {
    bg([3, 3, 3], [5, 4, 3]);
    const cam = { x: lerp(-5, 5, prog(u, 0, d)), y: 0, s: 1.05 };
    const focus = lerp(1.3, 0.12, prog(u, 0.1, d * 0.6, E.inOut));
    const shelves = LAND ? [-20, 2, 24] : [-55, -26, 3, 32, 61];
    blurred(cam, focus, x => {
      shelves.forEach((sy, si) => {
        const g = x.createLinearGradient(0, sy - 20, 0, sy + 2);
        g.addColorStop(0, 'rgba(0,0,0,0)'); g.addColorStop(0.75, rgb([206, 146, 64], 0.3)); g.addColorStop(1, rgb([250, 214, 150], 0.45));
        x.fillStyle = g; x.fillRect(-140, sy - 20, 280, 22);
        const r = rng(50 + si);
        for (let bx = -130; bx < 130;) {
          const type = Math.floor(r() * 3), bw = 5 + r() * 3.5, bh = 13 + r() * 6;
          const b = new Path2D();
          if (type === 0) { b.roundRect(bx, sy - bh * 0.7, bw, bh * 0.7, 1); b.rect(bx + bw * 0.38, sy - bh, bw * 0.24, bh * 0.32); }
          else if (type === 1) { b.ellipse(bx + bw / 2, sy - bh * 0.32, bw / 2, bh * 0.32, 0, 0, Math.PI * 2); b.rect(bx + bw * 0.4, sy - bh, bw * 0.2, bh * 0.45); }
          else { b.roundRect(bx + bw * 0.1, sy - bh * 0.75, bw * 0.8, bh * 0.75, 2); b.rect(bx + bw * 0.38, sy - bh * 1.05, bw * 0.24, bh * 0.35); }
          x.fillStyle = '#0a0806'; x.fill(b);
          x.save(); x.clip(b);
          const lg = x.createLinearGradient(bx, 0, bx + bw, 0);
          const lit = 0.35 + r() * 0.6;
          lg.addColorStop(0, rgb([40, 20, 8], 0.95)); lg.addColorStop(0.5, rgb(mul([224, 152, 66], lit), 0.85)); lg.addColorStop(1, rgb([40, 20, 8], 0.95));
          x.fillStyle = lg; x.fillRect(bx, sy - bh * (0.25 + r() * 0.4), bw, bh);
          x.fillStyle = rgb(C.white, 0.35); x.fillRect(bx + bw * 0.18, sy - bh * 0.8, bw * 0.06, bh * 0.7);
          x.restore();
          bx += bw + 1.2 + r() * 2.5;
        }
        x.fillStyle = '#0d0b08'; x.fillRect(-140, sy, 280, 1.2);
        x.fillStyle = rgb(C.goldHi, 0.35); x.fillRect(-140, sy, 280, 0.15);
      });
    });
  }
  function shotParisPour(u, d) {
    bg([3, 3, 3], [8, 6, 4]);
    const cam = { x: 0, y: 0, s: lerp(1.05, 1.12, prog(u, 0, d, E.sine)) };
    blurred(cam, 1.0, x => bokeh(x, u, PARIS_BOKEH, 1));
    camSet(ctx, cam);
    const by = LAND ? 24 : 26, w = LAND ? 30 : 34, h = LAND ? 38 : 44;
    ctx.fillStyle = 'rgba(0,0,0,0.85)'; ctx.fillRect(-200, by, 400, 200);
    ctx.fillStyle = rgb(C.gold, 0.25); ctx.fillRect(-200, by, 400, 0.2);
    const level = lerp(0.15, 0.6, prog(u, 0, d * 0.95));
    const ly = glass(ctx, 0, by, w, h, level, { bubbles: true, u, ice: [{ x: -3, y: by - h * 0.13 - 6 - level * 12, s: 9, r: 0.3 }] });
    // filet de cognac
    const sx = 2.5, top = -VY - 6;
    ctx.globalCompositeOperation = 'lighter';
    const sg = ctx.createLinearGradient(sx - 1, 0, sx + 1, 0);
    sg.addColorStop(0, rgb([200, 120, 40], 0.3)); sg.addColorStop(0.5, rgb([255, 214, 140], 0.95)); sg.addColorStop(1, rgb([200, 120, 40], 0.3));
    ctx.fillStyle = sg;
    ctx.beginPath(); ctx.moveTo(sx - 0.9, top);
    for (let yy = top; yy <= ly; yy += 1) ctx.lineTo(sx - 0.55 + Math.sin(yy * 0.6 + u * 18) * 0.12, yy);
    for (let yy = ly; yy >= top; yy -= 1) ctx.lineTo(sx + 0.55 + Math.sin(yy * 0.6 + u * 18 + 1) * 0.12, yy);
    ctx.closePath(); ctx.fill();
    ctx.globalCompositeOperation = 'source-over';
    for (let k = 0; k < 3; k++) {
      const rr = ((u * 6 + k * 1.3) % 4);
      ctx.strokeStyle = rgb(C.goldHi, 0.5 * (1 - rr / 4)); ctx.lineWidth = 0.2;
      ctx.beginPath(); ctx.ellipse(sx, ly, rr * 1.8 + 1, (rr * 1.8 + 1) * 0.18, 0, 0, Math.PI * 2); ctx.stroke();
    }
    glow(ctx, sx, ly, 10, C.goldHi, 0.3);
    reset(ctx);
  }
  function manAt(x, x0, y0, k, mirror, rimCol, lx, ly, cigarOn, ember, u) {
    x.save(); x.translate(x0, y0); x.scale(mirror ? -k : k, k);
    const llx = mirror ? -lx : lx, bp = 0.5 * k * U;
    rimFill(x, P.man, '#040404', rimCol, 1.3, llx, ly, bp);
    if (cigarOn) {
      x.save(); x.translate(71, 49.4); x.rotate(-0.07);
      x.fillStyle = '#0a0807'; x.fillRect(0, -0.8, 17, 1.6);
      x.fillStyle = rimCol; x.globalAlpha = 0.5; x.fillRect(0, -0.8, 17, 0.25); x.globalAlpha = 1;
      x.restore();
    }
    x.restore();
    if (cigarOn) {
      const s = mirror ? -k : k;
      const ex = x0 + 88 * s, ey = y0 + 48.2 * k;
      glow(x, ex, ey, 3 * k * 4, [236, 150, 60], 0.45 * ember);
      glow(x, ex, ey, 1.2 * k * 4, [255, 226, 170], 0.55 * ember);
      return [ex, ey];
    }
    return null;
  }
  function shotParisCigar(u, d) {
    bg([3, 3, 3], [4, 3, 2]);
    const k = LAND ? 0.95 : 1.0, x0 = LAND ? -62 : -62, y0 = LAND ? -40 : -62;
    const cam = { x: 0, y: LAND ? 0 : -6, s: lerp(1, 1.06, prog(u, 0, d, E.sine)) };
    camSet(ctx, cam);
    glow(ctx, LAND ? 30 : 22, -12, 70, C.gold, 0.28);
    smoke(ctx, u, { x: 20, y: 10, rate: 3, life: 6, rise: 1.5, spread: 70, curl: 4, wind: 2, s0: 18, s1: 40, a: 0.1, seed: 21, gold: 1 });
    const fl = 1 - prog(u, 0.9, 0.3, E.in);
    const ember = prog(u, 0.5, 0.6, E.out) * (0.7 + 0.3 * bump(u, 1.2, 0.6));
    const tip = manAt(ctx, x0, y0, k, false, rgb(C.goldHi, 0.8), 1, -0.15, true, ember, u);
    if (fl > 0) { flame(ctx, tip[0] + 0.5, tip[1] + 4.5, 5, 1.5, u, 7, fl); glow(ctx, tip[0] - 8, tip[1], 26, C.gold, 0.25 * fl); }
    smoke(ctx, u, { x: tip[0], y: tip[1] - 1, rate: 10, life: 3.5, rise: 5, spread: 0.6, curl: 2.5, wind: 1.6, s0: 1.5, s1: 16, a: 0.3, seed: 22, gold: 1, start: 0.5 });
    const mxp = x0 + 72 * k, myp = y0 + 49.5 * k;
    smoke(ctx, u, { x: mxp + 2, y: myp, rate: 20, life: 2.6, rise: 1.5, spread: 1, curl: 1.5, wind: 9, s0: 3, s1: 22, a: 0.32, seed: 23, start: 1.25, stop: 1.7 });
    reset(ctx);
  }
  function shotParisBlinds(u, d) {
    bg([2, 2, 2], [3, 3, 3]);
    const cam = { x: lerp(-3, 3, prog(u, 0, d)), y: 0, s: 1.05, r: -0.02 };
    camSet(ctx, cam);
    const stripes = new Path2D();
    for (let i = 0; i < 9; i++) {
      const o = -40 + i * 9;
      stripes.moveTo(-120 + o, -80); stripes.lineTo(-120 + o + 4.2, -80); stripes.lineTo(100 + o + 4.2 + 40, 120); stripes.lineTo(100 + o + 40, 120); stripes.closePath();
    }
    smoke(ctx, u, { x: -10, y: 40, rate: 9, life: 5, rise: 10, spread: 110, curl: 6, wind: 3, s0: 12, s1: 40, a: 0.2, seed: 31 });
    ctx.save(); ctx.clip(stripes);
    const g = ctx.createLinearGradient(-100, -80, 100, 100);
    g.addColorStop(0, rgb(C.goldHi, 0.22)); g.addColorStop(1, rgb(C.gold, 0.02));
    ctx.globalCompositeOperation = 'lighter'; ctx.fillStyle = g; ctx.fillRect(-200, -120, 400, 260);
    ctx.globalCompositeOperation = 'source-over';
    smoke(ctx, u, { x: -10, y: 40, rate: 9, life: 5, rise: 10, spread: 110, curl: 6, wind: 3, s0: 12, s1: 40, a: 1, seed: 31, gold: 1, comp: 'lighter' });
    ctx.globalCompositeOperation = 'lighter';
    for (let i = 0; i < 120; i++) {
      const px = -90 + hash1(i * 3) * 180 + Math.sin(u * 0.6 + i) * 2, py = -40 + ((hash1(i * 5) * 80 + u * (1 + hash1(i) * 2)) % 80);
      ctx.fillStyle = rgb(C.goldHi, 0.5 * hash1(i * 7)); ctx.fillRect(px, py, 0.2, 0.2);
    }
    ctx.restore();
    reset(ctx);
  }
  function shotParisBar(u, d) {
    bg([3, 3, 3], [2, 2, 2]);
    const cam = { x: lerp(3, -3, prog(u, 0, d)), y: LAND ? 0 : 4, s: LAND ? 1.04 : 1.35 };
    blurred(cam, 1.1, x => bokeh(x, u, PARIS_BOKEH, -1));
    camSet(ctx, cam);
    const cy = LAND ? 16 : 22;
    // cône de la suspension
    ctx.globalCompositeOperation = 'lighter';
    const cg = ctx.createLinearGradient(0, -VY, 0, cy);
    cg.addColorStop(0, rgb(C.goldHi, 0.12)); cg.addColorStop(1, rgb(C.gold, 0.02));
    ctx.filter = `blur(${(1.2 * U).toFixed(1)}px)`;
    ctx.fillStyle = cg; ctx.beginPath(); ctx.moveTo(-4, -VY + 4); ctx.lineTo(4, -VY + 4); ctx.lineTo(34, cy); ctx.lineTo(-34, cy); ctx.fill();
    ctx.filter = 'none';
    ctx.globalCompositeOperation = 'source-over';
    ctx.fillStyle = '#080706'; ctx.beginPath(); ctx.moveTo(-6, -VY + 4.5); ctx.lineTo(6, -VY + 4.5); ctx.lineTo(3, -VY); ctx.lineTo(-3, -VY); ctx.fill();
    ctx.fillRect(-0.2, -VY - 30, 0.4, 30);
    glow(ctx, 0, -VY + 4.5, 8, C.goldHi, 0.6);
    const k = LAND ? 0.72 : 0.5;
    const tip = manAt(ctx, LAND ? -80 : -57, LAND ? -21 : -8, k, false, rgb(C.goldHi, 0.7), 0.7, -0.7, true, 0.7 + 0.3 * Math.sin(u * 2), u);
    manAt(ctx, LAND ? 80 : 57, LAND ? -20 : -7, k * 1.02, true, rgb(C.goldHi, 0.7), -0.7, -0.7, false, 0, u);
    smoke(ctx, u, { x: tip[0], y: tip[1], rate: 10, life: 4, rise: 6, spread: 1, curl: 3, wind: 2.5, s0: 1.5, s1: 18, a: 0.32, seed: 41, gold: 1 });
    ctx.fillStyle = '#0b0907'; ctx.fillRect(-200, cy, 400, 200);
    ctx.fillStyle = rgb(C.goldHi, 0.5); ctx.fillRect(-200, cy, 400, 0.25);
    glass(ctx, LAND ? -20 : -14, cy, 5.5, 7, 0.4, {});
    glass(ctx, LAND ? 26 : 18, cy, 5.5, 7, 0.3, {});
    reset(ctx);
  }
  function shotParisIce(u, d) {
    bg([3, 3, 3], [8, 6, 4]);
    const cam = { x: 0, y: 0, s: 1.12 };
    blurred(cam, 1.1, x => bokeh(x, u, PARIS_BOKEH, 0.6));
    camSet(ctx, cam);
    const by = LAND ? 24 : 26, w = LAND ? 30 : 34, h = LAND ? 38 : 44;
    ctx.fillStyle = 'rgba(0,0,0,0.85)'; ctx.fillRect(-200, by, 400, 200);
    const ti = d * 0.3, fall = prog(u, 0, ti, E.quadIn);
    const surf = by - h * 0.13 - (h * 0.87) * 0.55;
    const iy = u < ti ? lerp(-VY - 12, surf, fall) : surf + 3 + Math.sin((u - ti) * 6) * 0.8 * Math.exp(-(u - ti) * 2);
    const ly = glass(ctx, 0, by, w, h, 0.55, { ice: [{ x: 1, y: iy, s: 10, r: 0.25 + u * 0.3 }] });
    if (u > ti) {
      const tt = u - ti;
      ctx.globalCompositeOperation = 'lighter';
      for (let i = 0; i < 16; i++) {
        const a = -Math.PI / 2 + (hash1(i * 3) - 0.5) * 2.2, v = 12 + hash1(i * 5) * 16;
        const px = Math.cos(a) * v * tt * 0.6, py = ly + Math.sin(a) * v * tt * 0.6 + 26 * tt * tt;
        if (py > ly + 1) continue;
        ctx.fillStyle = rgb(C.goldHi, 0.85); ctx.beginPath(); ctx.arc(px, py, 0.35 + hash1(i) * 0.3, 0, Math.PI * 2); ctx.fill();
      }
      for (let k2 = 0; k2 < 3; k2++) {
        const rr = tt * 9 - k2 * 2;
        if (rr <= 0) continue;
        ctx.strokeStyle = rgb(C.goldHi, Math.max(0, 0.6 - tt * 0.5)); ctx.lineWidth = 0.25;
        ctx.beginPath(); ctx.ellipse(0, ly, Math.min(rr, w * 0.42), Math.min(rr, w * 0.42) * 0.16, 0, 0, Math.PI * 2); ctx.stroke();
      }
      ctx.globalCompositeOperation = 'source-over';
    }
    reset(ctx);
  }
  function shotParisEmber(u, d) {
    bg([2, 2, 2], [3, 3, 3]);
    const cam = { x: 6, y: 0, s: lerp(1.0, 1.1, prog(u, 0, d, E.sine)), r: 0.04 };
    camSet(ctx, cam);
    const ember = 0.65 + 0.35 * Math.max(bump(u, 0.2, 0.9), bump(u, 1.45, 0.9));
    smoke(ctx, u, { x: 20, y: -6, rate: 12, life: 4.5, rise: 7, spread: 1.5, curl: 3.5, wind: 1.2, s0: 3, s1: 34, a: 0.35, seed: 51, gold: 1 });
    camSet(ctx, cam);
    cigar(ctx, 22, 0, 140, 16, ember, 0, u);
    const fill = prog(u, d - 0.9, 0.9, E.in);
    smoke(ctx, u, { x: -20, y: 10, rate: 30, life: 2.2, rise: 3, spread: 30, curl: 2, wind: 22, s0: 10, s1: 60, a: 0.45 * fill, seed: 52, start: d - 1.0 });
    reset(ctx);
  }

  // --- ROMA
  function shotRoma1(u, d) {
    bg([3, 3, 3], [14, 11, 8]);
    const cam = { x: 0, y: -2, s: lerp(1, 1.06, prog(u, 0, d, E.sine)) };
    camSet(ctx, cam);
    ctx.globalAlpha = 0.6; ctx.fillStyle = pattern(ctx, TEX.clouds, 0.14, -u * 1.5, -40, 0.06); ctx.fillRect(-200, -150, 400, 160); ctx.globalAlpha = 1;
    const by = LAND ? 22 : 30, w = LAND ? 170 : 160, h = LAND ? 54 : 58;
    glow(ctx, 0, by - h * 0.4, 110, C.gold, 0.12);
    colosseum(ctx, 4, by, w, h, u);
    const g = ctx.createLinearGradient(0, by, 0, by + 30);
    g.addColorStop(0, rgb([30, 22, 12])); g.addColorStop(1, rgb([4, 4, 4]));
    ctx.fillStyle = g; ctx.fillRect(-200, by, 400, 200);
    ctx.save(); ctx.translate(0, 2 * by); ctx.scale(1, -1); ctx.globalAlpha = 0.18; colosseum(ctx, 4, by, w, h, u); ctx.restore();
    reset(ctx);
    rainStreaks(ctx, u, { seed: 61, n: 260, speed: 1.4, a: 0.16, col: [214, 190, 150], light: [W / 2, H * 0.55, W * 0.5, 1] });
  }
  function shotRomaStones(u, d) {
    bg([2, 2, 2], [6, 5, 4]);
    const cam = { x: 0, y: 0, s: 1.02 };
    camSet(ctx, cam);
    const hz = LAND ? -VY - 4 : -VY * 0.6, F0 = 30, lampX = 6;
    for (let j = 0; j < 46; j++) {
      const z0 = 1 + j * 0.28, z1 = z0 + 0.28;
      const y0 = hz + F0 * 7 / z1, y1 = hz + F0 * 7 / z0;
      if (y0 > 140) continue;
      const sw = 26 / z0, off = (j % 2) * sw * 0.5;
      for (let sx = -160 - off; sx < 160; sx += sw) {
        const id = j * 97 + Math.floor((sx + 400) / Math.max(0.1, sw));
        const v = 14 + hash1(id) * 14;
        ctx.fillStyle = rgb([v, v * 0.95, v * 0.9]);
        ctx.fillRect(sx + sw * 0.05, y0 + (y1 - y0) * 0.06, sw * 0.9, (y1 - y0) * 0.88);
        const near = Math.exp(-Math.pow((sx + sw / 2 - lampX * (0.2 + 0.8 * (1 / z0))) / (6 + 20 / z0), 2));
        const wet = hash1(id * 3 + 1);
        if (near * wet > 0.05) { ctx.fillStyle = rgb(C.goldHi, near * wet * 0.55); ctx.fillRect(sx + sw * 0.1, y0 + (y1 - y0) * 0.2, sw * 0.8, (y1 - y0) * 0.5); }
      }
    }
    glow(ctx, lampX * 0.2, hz - 2, 22, C.goldHi, 0.5);
    // passant pressé (jambes, manteau)
    const px = lerp(-VX - 30, VX + 30, prog(u, 0.1, d * 0.85)), fy = LAND ? 30 : 50, ph = u * 7;
    ctx.fillStyle = '#030303';
    for (const sgn of [1, -1]) {
      const a = Math.sin(ph) * 0.42 * sgn;
      ctx.save(); ctx.translate(px, fy - 30); ctx.rotate(a);
      ctx.beginPath(); ctx.moveTo(-2.6, 0); ctx.lineTo(2.6, 0); ctx.lineTo(1.8, 29); ctx.lineTo(-1.8, 29); ctx.fill();
      ctx.beginPath(); ctx.ellipse(2, 29.5, 4.2, 1.5, 0, 0, Math.PI * 2); ctx.fill();
      ctx.restore();
    }
    const hs = Math.sin(ph) * 2.2;
    const coat = new Path2D();
    coat.moveTo(px - 6, fy - 70); coat.lineTo(px + 6, fy - 70);
    coat.quadraticCurveTo(px + 8.5, fy - 46, px + 11 + hs, fy - 25);
    coat.quadraticCurveTo(px + 1 + hs * 0.5, fy - 22.5, px - 9 + hs, fy - 24.5);
    coat.quadraticCurveTo(px - 8, fy - 46, px - 6, fy - 70); coat.closePath();
    rimFill(ctx, coat, '#030303', rgb(C.goldHi, 0.35), 0.7, -0.3, -1, 0.2 * U);
    reset(ctx);
    rainStreaks(ctx, u, { seed: 62, n: 180, speed: 1.6, a: 0.12, col: [214, 190, 150] });
  }
  function shotRomaCenser(u, d) {
    bg([2, 2, 2], [5, 4, 3]);
    const cam = { x: 0, y: 0, s: 1.05 };
    blurred(cam, 1.3, x => {
      for (let i = 0; i < 26; i++) { const cx = -100 + hash1(i * 3) * 200, cy = 10 + hash1(i * 5) * 30; flame(x, cx, cy, 1.4, 0.5, u, i, 1); glow(x, cx, cy, 6, C.gold, 0.3); }
      x.fillStyle = 'rgba(30,24,16,0.5)'; for (let c = -3; c <= 3; c++) x.fillRect(c * 32 - 3, -80, 6, 160);
    });
    camSet(ctx, cam);
    const pivotY = -VY - 22, Lc = LAND ? 64 : 92, T = 1.7;
    const angAt = t => 0.36 * Math.sin(2 * Math.PI * t / T);
    const pos = t => [Math.sin(angAt(t)) * Lc, pivotY + Math.cos(angAt(t)) * Lc];
    // rayon de lumière
    ctx.globalCompositeOperation = 'lighter';
    const bgd = ctx.createLinearGradient(-60, -80, 40, 60);
    bgd.addColorStop(0, rgb(C.goldHi, 0.18)); bgd.addColorStop(1, rgb(C.gold, 0));
    ctx.fillStyle = bgd; ctx.beginPath(); ctx.moveTo(-90, -80); ctx.lineTo(-60, -80); ctx.lineTo(60, 90); ctx.lineTo(10, 90); ctx.fill();
    ctx.globalCompositeOperation = 'source-over';
    smoke(ctx, u, { src: t => { const p = pos(t); return [p[0], p[1] - 3]; }, rate: 26, life: 3.2, rise: 5, spread: 0.6, curl: 2, wind: 1, s0: 1.5, s1: 18, a: 0.32, seed: 71, gold: 1 });
    const [cx, cy] = pos(u), a = angAt(u);
    ctx.strokeStyle = rgb(C.gold, 0.6); ctx.lineWidth = 0.22;
    for (const o of [-2.6, 0, 2.6]) { ctx.beginPath(); ctx.moveTo(0, pivotY); ctx.lineTo(cx + o * Math.cos(a), cy - 6); ctx.stroke(); }
    ctx.save(); ctx.translate(cx, cy); ctx.rotate(-a);
    const body = new Path2D();
    body.moveTo(-4, -6); body.quadraticCurveTo(-4.6, -11, 0, -12.5); body.quadraticCurveTo(4.6, -11, 4, -6); body.closePath();
    body.moveTo(-5, -6); body.lineTo(5, -6); body.quadraticCurveTo(5, 1, 0, 1.6); body.quadraticCurveTo(-5, 1, -5, -6);
    body.rect(-2.2, 1.4, 4.4, 1.6);
    const bgr = ctx.createLinearGradient(-5, 0, 5, 0);
    bgr.addColorStop(0, '#1a1208'); bgr.addColorStop(0.6, rgb(C.goldDeep)); bgr.addColorStop(0.8, rgb(C.goldHi)); bgr.addColorStop(1, '#2a1c0c');
    ctx.fillStyle = bgr; ctx.fill(body);
    ctx.globalCompositeOperation = 'lighter';
    for (let i = 0; i < 9; i++) { const hx = -3.2 + (i % 5) * 1.6, hy = -9 + Math.floor(i / 5) * 2; ctx.fillStyle = rgb([255, 200, 120], 0.6 + 0.4 * Math.sin(u * 9 + i)); ctx.beginPath(); ctx.arc(hx, hy, 0.32, 0, Math.PI * 2); ctx.fill(); }
    ctx.globalCompositeOperation = 'source-over';
    ctx.restore();
    glow(ctx, cx, cy - 6, 12, C.gold, 0.25);
    reset(ctx);
  }
  function shotRomaCitrus(u, d) {
    bg([4, 3, 2], [8, 6, 4]);
    const cam = { x: 0, y: 0, s: lerp(1.04, 1.1, prog(u, 0, d)) };
    blurred(cam, 1.4, x => bokeh(x, u, PARIS_BOKEH, 0.4));
    camSet(ctx, cam);
    glow(ctx, 30, -20, 70, C.gold, 0.16);
    const sw = Math.sin(u * 1.3) * 0.7;
    const p0 = [VX + 8, LAND ? -VY - 6 : -46], p1 = [30, -12 + sw], p2 = [-5, 2 + sw], p3 = [LAND ? -52 : -42, (LAND ? 4 : 10) + sw * 1.3];
    const cub = (a, b, c2, d2, t) => a * (1 - t) ** 3 + 3 * b * t * (1 - t) ** 2 + 3 * c2 * t * t * (1 - t) + d2 * t ** 3;
    const at = t => [cub(p0[0], p1[0], p2[0], p3[0], t), cub(p0[1], p1[1], p2[1], p3[1], t)];
    ctx.strokeStyle = '#0c0a07'; ctx.lineWidth = 2; ctx.lineCap = 'round';
    ctx.beginPath(); ctx.moveTo(...p0); ctx.bezierCurveTo(...p1, ...p2, ...p3); ctx.stroke();
    const r = rng(81);
    for (let i = 0; i < 30; i++) {
      const t = 0.06 + i / 30 * 0.92, [bx, by] = at(t), [nx, ny] = at(Math.min(1, t + 0.01));
      const tan = Math.atan2(ny - by, nx - bx), side = i % 2 ? 1 : -1;
      ctx.save(); ctx.translate(bx, by); ctx.rotate(tan + side * (0.6 + r() * 0.7)); const sc = 1.0 + r() * 0.6; ctx.scale(sc, sc);
      rimFill(ctx, P.leaf, '#070705', rgb(C.gold, 0.6), 0.7, 0.6, -0.8, 0.12 * U);
      ctx.strokeStyle = 'rgba(214,174,104,0.18)'; ctx.lineWidth = 0.12; ctx.beginPath(); ctx.moveTo(0.5, 0); ctx.lineTo(13, 0); ctx.stroke();
      ctx.restore();
    }
    for (const [t, rr, drop] of [[0.32, 6.4, 6], [0.57, 5.4, 4], [0.8, 6.8, 5]]) {
      const [bx, by] = at(t), fx = bx + 1, fy = by + drop + rr;
      ctx.strokeStyle = '#0c0a07'; ctx.lineWidth = 0.5; ctx.beginPath(); ctx.moveTo(bx, by); ctx.lineTo(fx, fy - rr); ctx.stroke();
      const g = ctx.createRadialGradient(fx + rr * 0.35, fy - rr * 0.4, rr * 0.1, fx, fy, rr);
      g.addColorStop(0, rgb([255, 236, 172])); g.addColorStop(0.35, rgb([214, 168, 72])); g.addColorStop(1, rgb([30, 22, 8]));
      ctx.fillStyle = g; ctx.beginPath(); ctx.arc(fx, fy, rr, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = 'rgba(255,255,250,0.75)';
      for (let k = 0; k < 5; k++) { ctx.beginPath(); ctx.arc(fx + (hash1(k + t * 100) - 0.3) * rr, fy + (hash1(k * 3 + t * 100) - 0.6) * rr, 0.22, 0, Math.PI * 2); ctx.fill(); }
    }
    reset(ctx);
    rainStreaks(ctx, u, { seed: 63, n: 120, speed: 1.4, a: 0.12, col: [214, 190, 150] });
  }
  function shotRomaBust(u, d) {
    bg([2, 2, 2], [3, 3, 3]);
    const cam = { x: 0, y: 0, s: lerp(1.02, 1.08, prog(u, 0, d, E.sine)) };
    camSet(ctx, cam);
    glow(ctx, 30, -14, 60, C.gold, 0.25);
    const k = LAND ? 0.82 : 0.7, x0 = LAND ? -48 : -38, y0 = LAND ? -46 : -48;
    smoke(ctx, u, { x: -30, y: 20, rate: 6, life: 5, rise: 4, spread: 40, curl: 4, wind: 5, s0: 10, s1: 34, a: 0.18, seed: 91, gold: 1 });
    ctx.save(); ctx.translate(x0, y0); ctx.scale(k, k);
    const hair = new Path2D(P.bust);
    for (const [hx, hy, hr] of [[44, 20, 6], [52, 14, 6.2], [61, 12.5, 5.6], [69, 15, 5.2], [40, 30, 6], [41, 40, 5.6], [47, 48, 5]]) { hair.moveTo(hx + hr, hy); hair.arc(hx, hy, hr, 0, Math.PI * 2); }
    rimFill(ctx, hair, '#050505', rgb([250, 238, 210], 0.85), 1.8, 1, -0.25, 0.5 * k * U);
    ctx.restore();
    smoke(ctx, u, { x: 10, y: 26, rate: 9, life: 4, rise: 6, spread: 30, curl: 3, wind: 4, s0: 6, s1: 26, a: 0.22, seed: 92, gold: 1 });
    reset(ctx);
  }
  function shotRomaFountain(u, d) {
    bg([2, 2, 2], [5, 4, 3]);
    const cam = { x: 0, y: 0, s: lerp(1.04, 1.1, prog(u, 0, d, E.sine)) };
    blurred(cam, 1.2, x => {
      x.fillStyle = rgb([60, 44, 24], 0.55);
      for (let i = -3; i <= 3; i++) { const ax = i * 26; x.beginPath(); x.moveTo(ax - 8, 20); x.lineTo(ax - 8, -16); x.arc(ax, -16, 8, Math.PI, 0); x.lineTo(ax + 8, 20); x.fill(); }
      bokeh(x, u, PARIS_BOKEH, 0.3);
    });
    camSet(ctx, cam);
    const poolY = LAND ? 18 : 30, g = 46;
    const jets = [{ x: -34, y: -12, vx: 20, vy: -6, n: 150 }, { x: 34, y: -12, vx: -20, vy: -6, n: 150 }, { x: 0, y: -2, vx: 0, vy: -30, n: 220, spread: 5 }];
    ctx.lineCap = 'round';
    ctx.globalCompositeOperation = 'lighter';
    jets.forEach((j, ji) => {
      for (let i = 0; i < j.n; i++) {
        const vx = j.vx + (j.spread ? (hash1(i * 7 + ji) - 0.5) * 2 * j.spread : (hash1(i * 7 + ji) - 0.5) * 1.5), vy = j.vy * (0.93 + 0.14 * hash1(i * 3 + ji));
        const T = (-vy + Math.sqrt(vy * vy + 2 * g * (poolY - j.y))) / g;
        const a = ((u * 0.9 + hash1(i * 13 + ji * 5)) % 1) * T, a0 = Math.max(0, a - 0.03);
        const px = j.x + vx * a, py = j.y + vy * a + 0.5 * g * a * a;
        const qx = j.x + vx * a0, qy = j.y + vy * a0 + 0.5 * g * a0 * a0;
        ctx.strokeStyle = rgb(hash1(i * 17) < 0.35 ? C.goldHi : C.white, 0.18 + 0.4 * hash1(i * 19)); ctx.lineWidth = 0.18 + 0.2 * hash1(i);
        ctx.beginPath(); ctx.moveTo(qx, qy); ctx.lineTo(px, py); ctx.stroke();
      }
      const T0 = (-j.vy + Math.sqrt(j.vy * j.vy + 2 * g * (poolY - j.y))) / g, ix = j.x + j.vx * T0;
      for (let k = 0; k < 24; k++) {
        const age = (u * 1.6 + hash1(k * 5 + ji)) % 1, an = -Math.PI / 2 + (hash1(k * 3 + ji) - 0.5) * 2.4, v = 6 + hash1(k * 7 + ji) * 8;
        ctx.fillStyle = rgb(C.white, 0.45 * (1 - age)); ctx.fillRect(ix + Math.cos(an) * v * age, poolY + Math.sin(an) * v * age + 14 * age * age, 0.25, 0.25);
      }
    });
    for (const sx of [-34, 34]) { glow(ctx, sx, -12, 6, C.gold, 0.3); ctx.globalCompositeOperation = 'source-over'; ctx.fillStyle = '#0a0806'; ctx.beginPath(); ctx.arc(sx, -12, 2.2, 0, Math.PI * 2); ctx.fill(); ctx.globalCompositeOperation = 'lighter'; }
    ctx.globalCompositeOperation = 'source-over';
    const rim = new Path2D(); rim.ellipse(0, poolY + 2, 80, 9, 0, 0, Math.PI * 2);
    ctx.fillStyle = '#060504'; ctx.fillRect(-200, poolY + 2, 400, 200);
    ctx.save(); ctx.clip(rim); ctx.fillStyle = '#0b0805'; ctx.fillRect(-90, poolY - 8, 180, 20);
    ctx.globalCompositeOperation = 'lighter';
    for (let i = 0; i < 90; i++) { const gx = -70 + hash1(i * 3 + 7) * 140, gy = poolY - 6 + hash1(i * 5 + 7) * 14, on = 0.5 + 0.5 * Math.sin(u * (6 + hash1(i) * 8) + i); ctx.fillStyle = rgb(C.goldHi, 0.5 * on); ctx.fillRect(gx, gy, 1.2 + hash1(i) * 2.5, 0.16); }
    ctx.restore();
    ctx.strokeStyle = rgb(C.gold, 0.55); ctx.lineWidth = 0.35; ctx.beginPath(); ctx.ellipse(0, poolY + 2, 80, 9, 0, Math.PI, 0); ctx.stroke();
    reset(ctx);
  }
  function shotRomaCandles(u, d) {
    bg([2, 2, 2], [4, 3, 2]);
    const cam = { x: lerp(-4, 4, prog(u, 0, d)), y: 0, s: 1.08 };
    blurred(cam, 1.5, x => { for (let i = 0; i < 14; i++) { const cx = -90 + i * 14, cy = 4 + hash1(i) * 10; flame(x, cx, cy, 3, 1, u, i + 20, 1); } });
    camSet(ctx, cam);
    const cands = LAND ? [[-34, 30, 8, 26], [-12, 34, 9, 34], [12, 28, 7.5, 22], [36, 32, 8.5, 30]] : [[-22, 40, 8, 30], [0, 46, 9, 40], [22, 38, 7.5, 26]];
    cands.forEach(([cx, by, cw, ch], i) => {
      const top = by - ch;
      const g = ctx.createLinearGradient(0, top, 0, by);
      g.addColorStop(0, rgb([236, 226, 206])); g.addColorStop(0.25, rgb([150, 140, 124])); g.addColorStop(1, rgb([20, 18, 16]));
      ctx.fillStyle = g; ctx.beginPath(); ctx.roundRect(cx - cw / 2, top, cw, ch + 40, 1.2); ctx.fill();
      ctx.fillStyle = rgb([240, 230, 210], 0.6);
      for (let k = 0; k < 3; k++) { const dx = cx - cw / 2 + hash1(i * 9 + k) * cw; ctx.beginPath(); ctx.roundRect(dx, top, 0.8, 2 + hash1(i * 5 + k) * 6, 0.4); ctx.fill(); }
      ctx.strokeStyle = '#111'; ctx.lineWidth = 0.25; ctx.beginPath(); ctx.moveTo(cx, top); ctx.lineTo(cx, top - 1.4); ctx.stroke();
      flame(ctx, cx, top - 1.2, 7.5, 1.7, u, 30 + i, 1);
    });
    smoke(ctx, u, { x: LAND ? 12 : 22, y: LAND ? -1 : 8, rate: 12, life: 3, rise: 7, spread: 0.2, curl: 1.4, curlF: 2, s0: 0.5, s1: 5, a: 0.3, seed: 101 });
    reset(ctx);
  }
  function shotRomaArches(u, d) {
    bg([3, 3, 3], [10, 8, 6]);
    const cam = { x: 0, y: lerp(16, -6, prog(u, 0, d, E.inOut)), s: 1 };
    camSet(ctx, cam);
    colosseum(ctx, 0, 70, 420, 130, u);
    reset(ctx);
    camSet(ctx, cam);
    smoke(ctx, u, { x: 0, y: 40, rate: 6, life: 6, rise: 5, spread: 160, curl: 5, wind: 4, s0: 20, s1: 50, a: 0.16, seed: 111, gold: 1 });
    reset(ctx);
    rainStreaks(ctx, u, { seed: 64, n: 300, speed: 1.5, a: 0.18, col: [214, 190, 150] });
  }

  // --- OMAN
  function shotOman1(u, d, o = {}) {
    bg([2, 2, 3], [10, 8, 6]);
    const cam = { x: 0, y: 0, s: lerp(1, 1.05, prog(u, 0, d, E.sine)) };
    camSet(ctx, cam);
    stars(ctx, 121, 260, -110, 110, -100, 10, u, 0.9);
    crescent(ctx, LAND ? -48 : -22, LAND ? -24 : -50, LAND ? 4.2 : 5.5);
    dunes(ctx, u, { seed: o.seed || 131, y0: LAND ? 4 : 10, dy: LAND ? 6 : 12, pan: u * (o.pan || 3), sand: o.sand || 6 });
    reset(ctx);
  }
  function shotOmanMosque(u, d) {
    bg([2, 2, 3], [8, 7, 6]);
    const cam = { x: 0, y: 0, s: lerp(1.0, 1.06, prog(u, 0, d, E.sine)) };
    camSet(ctx, cam);
    stars(ctx, 141, 160, -110, 110, -100, 0, u, 0.7);
    glow(ctx, 0, 0, 90, C.gold, 0.12);
    const mb = LAND ? 18 : 30, ms = LAND ? 0.72 : 0.95;
    mosque(ctx, 0, mb, ms);
    ctx.fillStyle = '#030303'; ctx.fillRect(-200, mb, 400, 200);
    ctx.save(); ctx.translate(0, 2 * mb + 1.5); ctx.scale(1, -1); ctx.globalAlpha = 0.22; mosque(ctx, 0, mb, ms); ctx.restore();
    const wg = ctx.createLinearGradient(0, mb, 0, mb + 40);
    wg.addColorStop(0, 'rgba(3,3,3,0.2)'); wg.addColorStop(1, 'rgba(3,3,3,1)');
    ctx.fillStyle = wg; ctx.fillRect(-200, mb, 400, 60);
    ctx.globalCompositeOperation = 'lighter';
    for (let i = 0; i < 60; i++) { const gx = -60 + hash1(i * 3) * 120, gy = mb + 2 + hash1(i * 5) * 20, on = 0.5 + 0.5 * Math.sin(u * 5 + i); ctx.fillStyle = rgb(C.goldHi, 0.25 * on); ctx.fillRect(gx, gy, 2 + hash1(i) * 4, 0.15); }
    ctx.globalCompositeOperation = 'source-over';
    reset(ctx);
  }
  function shotOmanBurner(u, d) {
    bg([2, 2, 2], [4, 3, 2]);
    const cam = { x: 0, y: lerp(4, -6, prog(u, 0, d, E.inOut)), s: 1.04 };
    camSet(ctx, cam);
    const by = LAND ? 34 : 50, k = LAND ? 0.42 : 0.5;
    smoke(ctx, u, { x: 0, y: by - 42 * k * 1.0, rate: 22, life: 4, rise: 9, spread: 3, curl: 4, wind: 0.8, s0: 3, s1: 34, a: 0.42, seed: 151 });
    smoke(ctx, u, { x: 0, y: by - 42 * k * 1.0, rate: 22, life: 1.6, rise: 8, spread: 3, curl: 2, s0: 3, s1: 14, a: 0.5, seed: 152, gold: 1, comp: 'lighter' });
    ctx.save(); ctx.translate(-50 * k, by - 100 * k); ctx.scale(k, k);
    const mb = new Path2D('M28 100 L72 100 L68 93 L32 93 Z M36 93 L64 93 L59 72 L41 72 Z M24 72 L76 72 L67 58 L33 58 Z');
    const g = ctx.createLinearGradient(20, 0, 80, 0);
    g.addColorStop(0, '#0c0907'); g.addColorStop(0.65, '#2a1e12'); g.addColorStop(1, '#0a0806');
    ctx.fillStyle = g; ctx.fill(mb);
    ctx.fillStyle = rgb(C.gold, 0.9);
    for (const yy of [99, 93.5, 72.5, 58.5]) ctx.fillRect(26, yy - 0.5, 48, 0.9);
    for (let i = 0; i < 6; i++) { ctx.fillStyle = rgb(C.goldHi, 0.5 + 0.5 * hash1(i)); ctx.fillRect(40 + i * 3.6, 80, 1.4, 1.4); ctx.fillRect(38 + i * 4.6, 63, 1.6, 1.6); }
    ctx.restore();
    const cx = 0, cy = by - 42 * k * 1.0;
    const coal = ctx.createRadialGradient(cx, cy, 0, cx, cy, 12 * k * 2);
    coal.addColorStop(0, rgb([255, 214, 140], 0.95)); coal.addColorStop(0.4, rgb([214, 120, 40], 0.7)); coal.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.globalCompositeOperation = 'lighter'; ctx.fillStyle = coal;
    ctx.beginPath(); ctx.ellipse(cx, cy, 20 * k, 4 * k, 0, 0, Math.PI * 2); ctx.fill();
    ctx.globalCompositeOperation = 'source-over';
    glow(ctx, cx, cy, 30, [236, 150, 60], 0.3 + 0.1 * Math.sin(u * 7));
    ctx.fillStyle = '#060504'; ctx.fillRect(-200, by, 400, 100);
    ctx.fillStyle = rgb(C.gold, 0.25); ctx.fillRect(-200, by, 400, 0.2);
    reset(ctx);
  }
  function shotOmanPetals(u, d) {
    bg([2, 2, 2], [6, 4, 3]);
    const cam = { x: 0, y: 0, s: 1 };
    camSet(ctx, cam);
    glow(ctx, 10, -10, 90, C.gold, 0.1);
    const petals = Array.from({ length: 30 }, (_, i) => ({ z: hash1(i * 3), x0: (hash1(i * 5) - 0.5) * VX * 2.2, ph: hash1(i * 7) * 6.28, y0: hash1(i * 11) }));
    const draw = (x, far) => {
      for (const p of petals) {
        if ((p.z < 0.45) !== far) continue;
        const s = 0.45 + p.z * 1.1, sp = 6 + 10 * p.z;
        const y = ((p.y0 * (2 * VY + 30) + u * sp) % (2 * VY + 30)) - VY - 15;
        const xx = p.x0 + Math.sin(u * 1.2 + p.ph) * 4;
        const flip = Math.cos(u * 2 + p.ph), lum = 0.45 + 0.55 * Math.abs(flip);
        x.save(); x.translate(xx, y); x.rotate(u * 0.8 + p.ph); x.scale(s * (0.25 + 0.75 * Math.abs(flip)), s);
        const pg = x.createLinearGradient(0, -5, 0, 6);
        pg.addColorStop(0, rgb(mul([236, 232, 224], lum))); pg.addColorStop(1, rgb(mul([118, 112, 104], lum)));
        rimFill(x, P.petal, pg, rgb(C.goldHi, 0.55), 0.7, 0.6, -0.8, 0.15 * U);
        x.strokeStyle = rgb([90, 84, 78], 0.4); x.lineWidth = 0.15; x.beginPath(); x.moveTo(0, 5); x.quadraticCurveTo(0.6, 0, 0, -3.5); x.stroke();
        x.restore();
      }
    };
    blurred(cam, 0.8, x => draw(x, true));
    camSet(ctx, cam); draw(ctx, false);
    reset(ctx);
  }
  function shotOmanLantern(u, d) {
    bg([3, 3, 3], [5, 4, 3]);
    const cam = { x: 0, y: 0, s: lerp(1.05, 1.12, prog(u, 0, d, E.sine)), r: lerp(-0.03, 0.03, prog(u, 0, d)) };
    camSet(ctx, cam);
    const sw = Math.sin(u * 1.8) * 0.12, lx = Math.sin(sw) * 30, ly = -4;
    ctx.globalCompositeOperation = 'lighter';
    for (let ring = 1; ring <= 6; ring++) {
      const n = ring * 9;
      for (let i = 0; i < n; i++) {
        const a = i / n * 6.28 + ring * 0.3, rr = ring * (LAND ? 11 : 13);
        const px = lx * (1 + ring * 0.4) + Math.cos(a) * rr * 1.25, py = ly + Math.sin(a) * rr;
        const s = 0.5 + ring * 0.25, al = 0.42 * (1 - ring / 7.5);
        ctx.fillStyle = rgb(C.goldHi, al);
        ctx.save(); ctx.translate(px, py); ctx.rotate(a);
        ctx.beginPath(); for (let q = 0; q < 8; q++) { const aa = q / 8 * 6.28, r2 = q % 2 ? s * 0.45 : s; ctx.lineTo(Math.cos(aa) * r2, Math.sin(aa) * r2); } ctx.closePath(); ctx.fill();
        ctx.restore();
      }
    }
    ctx.globalCompositeOperation = 'source-over';
    ctx.strokeStyle = rgb(C.gold, 0.5); ctx.lineWidth = 0.25;
    ctx.beginPath(); ctx.moveTo(0, -VY - 40); ctx.lineTo(lx, ly - 13); ctx.stroke();
    ctx.save(); ctx.translate(lx, ly); ctx.rotate(-sw * 0.6);
    const body = new Path2D('M-5 -12 L5 -12 L7 -6 L7 6 L4 11 L-4 11 L-7 6 L-7 -6 Z');
    ctx.fillStyle = '#120d07'; ctx.fill(body);
    ctx.save(); ctx.clip(body);
    ctx.globalCompositeOperation = 'lighter';
    for (let yy = -10; yy < 10; yy += 2.2) for (let xx = -6; xx < 6; xx += 2.2) { ctx.fillStyle = rgb([255, 222, 160], 0.75 + 0.25 * Math.sin(u * 8 + xx + yy)); ctx.beginPath(); ctx.arc(xx + (Math.round(yy) % 2 ? 1.1 : 0), yy, 0.45, 0, Math.PI * 2); ctx.fill(); }
    ctx.restore();
    ctx.strokeStyle = rgb(C.gold, 0.9); ctx.lineWidth = 0.4; ctx.stroke(body);
    ctx.fillStyle = rgb(C.goldDeep); ctx.beginPath(); ctx.moveTo(-5, -12); ctx.quadraticCurveTo(0, -18, 5, -12); ctx.fill();
    ctx.restore();
    glow(ctx, lx, ly, 30, C.gold, 0.4);
    reset(ctx);
  }
  function shotOmanDrop(u, d) {
    bg([2, 2, 2], [3, 3, 3]);
    const cam = { x: 0, y: LAND ? 6 : 8, s: 2.1 };
    camSet(ctx, cam);
    const sy = LAND ? 12 : 16;
    const sg = ctx.createLinearGradient(0, sy, 0, sy + 40);
    sg.addColorStop(0, '#0c0905'); sg.addColorStop(1, '#020202');
    ctx.fillStyle = sg; ctx.fillRect(-200, sy, 400, 200);
    ctx.globalCompositeOperation = 'lighter';
    const hl = ctx.createLinearGradient(-60, 0, 60, 0);
    hl.addColorStop(0, rgb(C.gold, 0)); hl.addColorStop(0.5, rgb(C.goldHi, 0.25)); hl.addColorStop(1, rgb(C.gold, 0));
    ctx.fillStyle = hl; ctx.fillRect(-60, sy + 4, 120, 0.4);
    ctx.globalCompositeOperation = 'source-over';
    const ti = d * 0.42;
    if (u < ti) {
      const y = lerp(-VY - 8, sy - 2, prog(u, 0, ti, E.quadIn));
      const g = ctx.createRadialGradient(-0.6, y - 0.6, 0.2, 0, y, 2.6);
      g.addColorStop(0, rgb([255, 244, 214])); g.addColorStop(0.4, rgb([226, 168, 78])); g.addColorStop(1, rgb([110, 64, 20]));
      ctx.fillStyle = g; ctx.beginPath(); ctx.moveTo(0, y - 6); ctx.bezierCurveTo(1.5, y - 3, 2.6, y - 1, 2.6, y + 0.6); ctx.arc(0, y + 0.6, 2.6, 0, Math.PI); ctx.bezierCurveTo(-2.6, y - 1, -1.5, y - 3, 0, y - 6); ctx.fill();
      glow(ctx, 0, y, 10, C.gold, 0.3);
    } else {
      const tt = u - ti;
      const jet = Math.max(0, Math.sin(Math.min(1, tt / 0.9) * Math.PI)) * 9;
      const jg = ctx.createLinearGradient(0, sy - jet, 0, sy);
      jg.addColorStop(0, rgb([255, 236, 190])); jg.addColorStop(1, rgb([160, 100, 34]));
      ctx.fillStyle = jg;
      if (jet > 0.3) { ctx.beginPath(); ctx.moveTo(-1.6, sy); ctx.bezierCurveTo(-0.7, sy - jet * 0.3, -0.45, sy - jet * 0.8, 0, sy - jet); ctx.bezierCurveTo(0.45, sy - jet * 0.8, 0.7, sy - jet * 0.3, 1.6, sy); ctx.closePath(); ctx.fill(); }
      if (tt > 0.35 && tt < 1.3) { const dy2 = sy - 9 - (tt - 0.35) * 4 + 12 * Math.pow(Math.max(0, tt - 0.6), 2); ctx.beginPath(); ctx.arc(0, dy2, 0.75, 0, Math.PI * 2); ctx.fill(); }
      ctx.globalCompositeOperation = 'lighter';
      for (let i = 0; i < 14; i++) {
        const a = Math.PI + (i / 13) * Math.PI, v = 10 + hash1(i) * 6;
        const px = Math.cos(a) * v * tt * 0.8, py = sy + Math.sin(a) * v * tt * 0.8 + 18 * tt * tt;
        if (py > sy + 0.5) continue;
        ctx.fillStyle = rgb(C.goldHi, 0.85); ctx.beginPath(); ctx.arc(px, py, 0.3, 0, Math.PI * 2); ctx.fill();
      }
      for (let k = 0; k < 4; k++) {
        const rr = tt * 14 - k * 3;
        if (rr <= 0) continue;
        ctx.strokeStyle = rgb(C.goldHi, Math.max(0, 0.55 - tt * 0.35)); ctx.lineWidth = 0.22;
        ctx.beginPath(); ctx.ellipse(0, sy, rr, rr * 0.14, 0, 0, Math.PI * 2); ctx.stroke();
      }
      ctx.globalCompositeOperation = 'source-over';
      glow(ctx, 0, sy, 18, C.gold, 0.25 * Math.max(0, 1 - tt));
    }
    reset(ctx);
  }
  function shotOmanDust(u, d) {
    bg([2, 2, 2], [3, 3, 3]);
    const cam = { x: 0, y: 0, s: 1, r: u * 0.05 };
    camSet(ctx, cam);
    smoke(ctx, u, { x: 0, y: 10, rate: 8, life: 4, rise: 3, spread: 60, curl: 6, wind: 2, s0: 12, s1: 40, a: 0.16, seed: 161, gold: 1 });
    ctx.globalCompositeOperation = 'lighter';
    for (let i = 0; i < 420; i++) {
      const r0 = 4 + Math.pow(hash1(i * 3), 0.7) * 70, a0 = hash1(i * 5) * 6.28, w = 0.9 / (0.3 + r0 / 30);
      const a = a0 + u * w, z = hash1(i * 7);
      const px = Math.cos(a) * r0 * 1.3, py = Math.sin(a) * r0 * 0.55 - z * 6;
      const s = 0.12 + z * 0.4, al = 0.3 + 0.6 * z;
      ctx.fillStyle = rgb(z > 0.85 ? C.white : C.goldHi, al * (0.6 + 0.4 * Math.sin(u * 5 + i)));
      ctx.beginPath(); ctx.arc(px, py, s, 0, Math.PI * 2); ctx.fill();
    }
    ctx.globalCompositeOperation = 'source-over';
    glow(ctx, 0, 0, 40, C.gold, 0.15);
    reset(ctx);
  }

  // --- Les autres villes : la nuit s'écrit N + 8
  const CITIES = [
    ['LONDON', 'night'], ['MADRID', 'noche'], ['BERLIN', 'Nacht'], ['LISBOA', 'noite'],
    ['AMSTERDAM', 'nacht'], ['STOCKHOLM', 'natt'], ['BUCUREȘTI', 'noapte'], ['ΑΘΗΝΑ', 'νύχτα'],
  ];
  function shotCity(i) {
    const [city, word] = CITIES[i];
    const bk = makeBokeh(400 + i * 17, 60, -110, 110, -60, 60, 0.6, 5, 0.75, 0.08, 0.4);
    return (u, d) => {
      bg([2, 2, 2], [4, 3, 3]);
      const cam = { x: 0, y: 0, s: lerp(1.0, 1.12, prog(u, 0, d)) };
      blurred(cam, 0.9, x => {
        bokeh(x, u, bk, (i % 2 ? 1 : -1) * 6);
        x.globalCompositeOperation = 'lighter';
        for (let k = 0; k < 6; k++) { const yy = -10 + hash1(i * 9 + k) * 40, xx = ((u * 80 * (k % 2 ? 1 : -1) + hash1(k + i) * 200) % 240) - 120; x.fillStyle = rgb(k % 3 ? C.goldHi : C.white, 0.35); x.fillRect(xx, yy, 18, 0.5); }
        x.globalCompositeOperation = 'source-over';
      });
      reset(ctx);
      const a = prog(u, 0, 0.08);
      const size = (LAND ? 11 : 15) * U;
      ctx.font = `400 ${size}px ${F.serif}`; ctx.textAlign = 'left'; ctx.textBaseline = 'alphabetic';
      const first = [...word][0], rest = [...word].slice(1).join('');
      const w1 = ctx.measureText(first).width, w2 = ctx.measureText(rest).width;
      const x0 = W / 2 - (w1 + w2) / 2, y0 = H / 2 + size * 0.3;
      ctx.shadowColor = rgb(C.gold, 0.6 * a); ctx.shadowBlur = 1.6 * U;
      ctx.fillStyle = rgb(C.goldHi, a); ctx.fillText(first, x0, y0);
      ctx.shadowBlur = 0;
      ctx.fillStyle = rgb(C.white, 0.88 * a); ctx.fillText(rest, x0 + w1, y0);
      tracked(ctx, city, W / 2, H / 2 - size * 0.75, 1.8 * U, 0.6, `300 ${1.8 * U}px ${F.sans}`, rgb(C.gold, 0.85 * a));
      reset(ctx);
    };
  }

  // --- Finale : toutes les nuits → N+8 → logo
  const LOGO = { meta: null, parts: {}, gold: {} };
  const NIGHTS = ['nuit', 'notte', 'night', 'noche', 'Nacht', 'noite', 'natt', 'νύχτα'];
  function logoM() {
    const s = LAND ? (W / 2.39) * 0.82 / 703 : W * 0.86 / 712;
    return { s, ox: W / 2 - s * 768, oy: H / 2 - s * (LAND ? 497 : 520) };
  }
  function shotFinale(u, d) {
    bg([1, 1, 1], [2, 2, 2]);
    const M = logoM();
    const toS = (x, y) => [M.ox + x * M.s, M.oy + y * M.s];
    const parts = LOGO.meta.parts;
    const pc = n => [parts[n].x + parts[n].w / 2, parts[n].y + parts[n].h / 2];
    // 1. la ligne des nuits
    const lineA = prog(u, 0.35, 0.5, E.out);
    const restOff = prog(u, 1.25, 0.6, E.inOut), gather = prog(u, 1.45, 0.9, E.inOut);
    const size = (LAND ? 4.4 : 5.2) * U;
    reset(ctx);
    ctx.font = `italic 400 ${size}px ${F.serif}`; ctx.textBaseline = 'alphabetic'; ctx.textAlign = 'left';
    const rows = LAND ? [NIGHTS] : [NIGHTS.slice(0, 4), NIGHTS.slice(4)];
    const [nx, ny] = toS(...pc('n'));
    const nTarget = [nx, ny + 0.36 * parts.n.h * M.s];
    rows.forEach((row, ri) => {
      const ws = row.map(wd => ctx.measureText(wd).width), gap = 2.4 * U;
      const tot = ws.reduce((a, b) => a + b, 0) + gap * (row.length - 1);
      let x0 = W / 2 - tot / 2;
      const y0 = (LAND ? H / 2 : H / 2 - 4 * U + ri * 8 * U) + size * 0.3;
      row.forEach((wd, k) => {
        const first = [...wd][0], rest = [...wd].slice(1).join('');
        const w1 = ctx.measureText(first).width;
        if (lineA * (1 - restOff) > 0.003) { ctx.fillStyle = rgb(C.white, 0.75 * lineA * (1 - restOff)); ctx.fillText(rest, x0 + w1, y0); }
        const fx = lerp(x0, nTarget[0] - w1 / 2, gather), fy = lerp(y0, nTarget[1], gather);
        const nA = lineA * (1 - prog(u, 2.3, 0.3)) * (gather > 0.98 && k + ri > 0 ? 0 : 1);
        if (nA > 0.003) { ctx.fillStyle = rgb(C.goldHi, nA); ctx.fillText(first, fx, fy); }
        x0 += ws[k] + gap;
      });
    });
    // 2. la phrase
    const pA = prog(u, 1.7, 0.6, E.out) * (1 - prog(u, 3.6, 0.5, E.in));
    if (pA > 0) {
      ctx.font = `italic 400 ${(LAND ? 2.6 : 3.4) * U}px ${F.serif}`; ctx.textAlign = 'center';
      ctx.fillStyle = rgb(C.gray, pA * 0.95);
      ctx.fillText('Dans toutes les langues, la nuit s’écrit N+8.', W / 2, toS(0, 905)[1]);
    }
    // 3. le logo doré
    const logoA = prog(u, 2.25, 0.5, E.out);
    const arch = prog(u, 2.6, 1.3, E.inOut);
    const l1 = prog(u, 3.6, 0.9, E.inOut), l2 = prog(u, 3.95, 0.9, E.inOut);
    reset(ctx);
    ctx.setTransform(M.s, 0, 0, M.s, M.ox, M.oy);
    const drawPart = (name, a, clipFn) => {
      if (a <= 0.003) return;
      const p = parts[name];
      ctx.save();
      if (clipFn) { ctx.beginPath(); clipFn(ctx, p); ctx.clip(); }
      ctx.globalAlpha = a; ctx.shadowColor = rgb(C.gold, 0.55); ctx.shadowBlur = 1.6 * U;
      ctx.drawImage(LOGO.gold[name], p.x, p.y);
      ctx.restore();
    };
    drawPart('n', logoA); drawPart('plus', prog(u, 2.4, 0.4, E.out)); drawPart('eight', prog(u, 2.5, 0.45, E.out));
    const CX = 767.5, CY = 456, R = 310, SIDE = 246, HALF = SIDE + Math.PI / 2 * R;
    drawPart('arch', arch > 0 ? 1 : 0, (x, p) => {
      const dd = arch * HALF, hh = Math.min(dd, SIDE + 4);
      x.rect(440, 712 - hh, 60, hh); x.rect(1036, 712 - hh, 60, hh);
      if (dd > SIDE) { const a = Math.min(Math.PI / 2, (dd - SIDE) / R); x.moveTo(CX, CY); x.arc(CX, CY, R + 40, Math.PI, Math.PI + a); x.closePath(); x.moveTo(CX, CY); x.arc(CX, CY, R + 40, -a, 0); x.closePath(); }
    });
    const wipe = p => (x, q) => { const cx = q.x + q.w / 2, hw = (q.w / 2 + 10) * p; x.rect(cx - hw, q.y - 5, 2 * hw, q.h + 10); };
    drawPart('line1', l1 > 0 ? 1 : 0, wipe(l1));
    drawPart('line2', l2 > 0 ? 1 : 0, wipe(l2));
    reset(ctx);
    const sw = prog(u, 4.6, 1.4, E.inOut);
    if (sw > 0 && sw < 1) {
      const [ax, ay] = toS(400 + sw * 800, 500);
      ctx.globalCompositeOperation = 'lighter';
      const g = ctx.createLinearGradient(ax - 12 * U, 0, ax + 12 * U, 0);
      g.addColorStop(0, 'rgba(255,240,200,0)'); g.addColorStop(0.5, 'rgba(255,240,200,0.10)'); g.addColorStop(1, 'rgba(255,240,200,0)');
      ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
      reset(ctx);
    }
  }

  /* =========================================================
   * Montage
   * ======================================================= */
  const SECTIONS = [];
  function buildFilm() {
    SHOTS.length = 0; EV.length = 0; SECTIONS.length = 0;
    let t = 0;
    const add = (name, beats, draw, o = {}) => {
      const s = { name, start: t, dur: beats * BEAT, draw, caption: o.caption, card: o.card, amb: o.amb || {}, leak: o.leak };
      SHOTS.push(s);
      if (o.ev) o.ev(t, s.dur);
      t += s.dur;
      return s;
    };
    const section = (name, fn) => { const s0 = t; fn(); SECTIONS.push({ name, start: s0, end: t }); };

    section('intro', () => add('intro', 8, shotIntro, { amb: { room: 0.15 }, ev: s => { ev('strike', s + 0.95); ev('flame', s + 1.0, { dur: 1.6 }); ev('puff', s + 3.2); } }));

    section('paris', () => {
      add('paris', 6, shotParis1, { leak: true, card: { name: 'PARIS', coords: '48°51′ N  ·  2°21′ E', formula: { eight: 'huit', night: 'nuit', map: [0, 2, 3, 4] } }, amb: { city: 0.6, room: 0.1 } });
      add('bouteilles', 2, shotParisBottles, { amb: { room: 0.6 }, ev: s => ev('clink', s + 0.6) });
      add('cognac', 2, shotParisPour, { caption: 'cognac', amb: { room: 0.55 }, ev: (s, d) => ev('pour', s, { dur: d }) });
      add('cigare', 3, shotParisCigar, { caption: 'tabac', amb: { room: 0.5 }, ev: s => { ev('lighter', s + 0.05); ev('exhale', s + 1.25); } });
      add('fumee', 2, shotParisBlinds, { amb: { room: 0.45 } });
      add('bar', 3, shotParisBar, { caption: 'cuir', amb: { room: 0.75 }, ev: s => ev('clink', s + 1.2) });
      add('glacon', 2, shotParisIce, { amb: { room: 0.5 }, ev: (s, d) => ev('ice', s + d * 0.3) });
      add('braise', 4, shotParisEmber, { caption: 'bois fumé', amb: { room: 0.35 }, ev: s => { ev('ember', s + 0.2); ev('ember', s + 1.45); ev('exhale', s + 1.6); } });
    });

    section('roma', () => {
      add('roma', 6, shotRoma1, { leak: true, card: { name: 'ROMA', coords: '41°54′ N  ·  12°30′ E', formula: { eight: 'otto', night: 'notte', map: [0, 1, 2, 3, 4] } }, amb: { rain: 0.6, city: 0.3 }, ev: s => ev('bell', s + 0.3) });
      add('pavés', 2, shotRomaStones, { caption: 'pierre mouillée', amb: { rain: 0.8 }, ev: (s, d) => { for (let k = 0; k < 6; k++) ev('step', s + 0.18 + k * (d * 0.85 / 6)); } });
      add('encensoir', 3, shotRomaCenser, { caption: 'encens', amb: { rain: 0.2, church: 0.8 }, ev: (s, d) => { for (let k = 0; k < 4; k++) ev('chain', s + 0.42 + k * 0.85); } });
      add('agrumes', 2, shotRomaCitrus, { caption: 'bergamote', amb: { rain: 0.5 } });
      add('buste', 3, shotRomaBust, { caption: 'fumée', amb: { rain: 0.25, church: 0.4 } });
      add('fontaine', 2, shotRomaFountain, { amb: { water: 1 } });
      add('cierges', 2, shotRomaCandles, { amb: { church: 0.9 } });
      add('arches', 4, shotRomaArches, { amb: { rain: 0.9, city: 0.2 }, ev: s => ev('bell', s + 0.5) });
    });

    section('oman', () => {
      add('oman', 6, (u, d) => shotOman1(u, d), { leak: true, card: { name: 'OMAN', coords: 'MASCATE  ·  23°35′ N  ·  58°23′ E', arabic: 'ليل' }, amb: { wind: 0.8 } });
      add('mosquee', 2, shotOmanMosque, { amb: { wind: 0.5 } });
      add('oud', 3, shotOmanBurner, { caption: 'oud', amb: { wind: 0.2, fire: 1 }, ev: s => ev('coals', s) });
      add('rose', 2, shotOmanPetals, { caption: 'rose', amb: { wind: 0.3 } });
      add('lanterne', 3, shotOmanLantern, { amb: { wind: 0.25 } });
      add('ambre', 2, shotOmanDrop, { caption: 'ambre', amb: { wind: 0.1 }, ev: (s, d) => ev('drop', s + d * 0.42) });
      add('or', 2, shotOmanDust, { amb: { wind: 0.4 } });
      add('desert', 4, (u, d) => shotOman1(u, d, { seed: 177, pan: 9, sand: 14 }), { amb: { wind: 1 } });
    });

    section('villes', () => { CITIES.forEach((_, i) => add('ville', 1, shotCity(i), { ev: s => ev('flash', s, { i }) })); });

    section('finale', () => add('finale', 8 / BEAT, shotFinale, { ev: s => { ev('silence', s); ev('reveal', s + 1.45); ev('logo', s + 2.3); } }));
    DURATION = t;
  }
  let DURATION = 0;

  /* =========================================================
   * Rendu
   * ======================================================= */
  function finish(t, shot, u) {
    const x = ctx;
    reset(x);
    // fuite de lumière dorée à l'ouverture de chaque ville
    if (shot.leak && u < 0.9) {
      const k = Math.sin(Math.PI * clamp(u / 0.9));
      const g = x.createRadialGradient(W * (0.15 + u * 0.6), H * 0.3, 0, W * (0.15 + u * 0.6), H * 0.3, W * 0.7);
      g.addColorStop(0, rgb([255, 214, 150], 0.22 * k)); g.addColorStop(1, rgb([255, 214, 150], 0));
      x.globalCompositeOperation = 'screen'; x.fillStyle = g; x.fillRect(0, 0, W, H); reset(x);
    }
    const v = x.createRadialGradient(W / 2, H / 2, Math.min(W, H) * 0.3, W / 2, H / 2, Math.hypot(W, H) * 0.55);
    v.addColorStop(0, 'rgba(0,0,0,0)'); v.addColorStop(1, 'rgba(0,0,0,0.72)');
    x.fillStyle = v; x.fillRect(0, 0, W, H);
    const f = Math.floor(t * 30 + 0.5), r = rng(1000 + f);
    x.globalCompositeOperation = 'overlay'; x.globalAlpha = 0.11;
    x.fillStyle = pattern(x, TEX.grain[f % 4], 1, -Math.floor(r() * 256), -Math.floor(r() * 256)); x.fillRect(0, 0, W, H);
    x.globalCompositeOperation = 'lighter'; x.globalAlpha = 0.016; x.fillRect(0, 0, W, H);
    reset(x);
    if (LAND) {
      const bar = Math.round((H - W / 2.39) / 2);
      x.fillStyle = '#000'; x.fillRect(0, 0, W, bar); x.fillRect(0, H - bar, W, bar);
    }
    const veil = Math.max(1 - prog(t, 0, 0.8, E.out), prog(t, DURATION - 1.4, 1.4, E.inOut));
    if (veil > 0) { x.fillStyle = `rgba(0,0,0,${veil.toFixed(4)})`; x.fillRect(0, 0, W, H); }
  }
  function renderAt(t) {
    t = clamp(t, 0, DURATION - 1e-6);
    let s = SHOTS[SHOTS.length - 1];
    for (const sh of SHOTS) if (t >= sh.start && t < sh.start + sh.dur) { s = sh; break; }
    const u = t - s.start;
    reset(ctx); ctx.fillStyle = '#000'; ctx.fillRect(0, 0, W, H);
    s.draw(u, s.dur);
    reset(ctx);
    if (s.card) cityCard(u, { ...s.card, end: s.dur });
    if (s.caption) caption(u, s.dur, s.caption);
    finish(t, s, u);
  }
  function audioEnv(rate = 100) {
    const keys = ['room', 'city', 'rain', 'church', 'water', 'wind', 'fire'];
    const out = { rate };
    keys.forEach(k => (out[k] = []));
    for (let i = 0; i <= Math.ceil(DURATION * rate); i++) {
      const t = i / rate;
      let s = SHOTS[SHOTS.length - 1];
      for (const sh of SHOTS) if (t >= sh.start && t < sh.start + sh.dur) { s = sh; break; }
      keys.forEach(k => out[k].push(+(s.amb[k] || 0).toFixed(3)));
    }
    return out;
  }

  async function loadImage(src) { const img = new Image(); img.src = src; await img.decode(); return img; }
  async function init() {
    W = innerWidth; H = innerHeight; U = Math.min(W, H) / 100; LAND = W >= H;
    VX = W / U / 2; VY = LAND ? (W / 2.39) / U / 2 : H / U / 2;
    cv.width = W; cv.height = H;
    await Promise.all([
      document.fonts.load(`400 48px "Bodoni Moda"`, 'N+8 nuit noche'),
      document.fonts.load(`italic 400 40px "Bodoni Moda"`, 'tabac cognac'),
      document.fonts.load(`400 48px "GFS Didot"`, 'νύχτα ΑΘΗΝΑ'),
      document.fonts.load(`300 30px "Montserrat"`, 'PARIS ROMA OMAN BUCUREȘTI'),
      document.fonts.load(`400 60px "Amiri"`, 'ليل'),
    ]);
    await document.fonts.ready;
    LOGO.meta = await (await fetch('logo/parts.json')).json();
    for (const name of Object.keys(LOGO.meta.parts)) {
      const img = await loadImage(`logo/${name}.png`);
      LOGO.parts[name] = img;
      const p = LOGO.meta.parts[name], c = mk(p.w, p.h), x = c.getContext('2d');
      x.drawImage(img, 0, 0);
      x.globalCompositeOperation = 'source-in';
      const g = x.createLinearGradient(0, 0, 0, p.h);
      g.addColorStop(0, rgb([246, 222, 160])); g.addColorStop(0.5, rgb([212, 170, 96])); g.addColorStop(1, rgb([160, 116, 52]));
      x.fillStyle = g; x.fillRect(0, 0, p.w, p.h);
      LOGO.gold[name] = c;
    }
    layer('half', W / 2, H / 2);
    buildTextures(); buildPaths(); buildFilm();
    renderAt(0);
  }

  window.N8 = {
    renderAt,
    get duration() { return DURATION; },
    get events() { return EV; },
    get scenes() { return SHOTS.map(s => ({ name: s.name, start: +s.start.toFixed(3), dur: +s.dur.toFixed(3) })); },
    get music() { return { bpm: BPM, sections: SECTIONS.map(s => ({ ...s })) }; },
    audioEnv,
  };
  window.N8.ready = init().then(() => true);

  if (!RENDER) {
    window.N8.ready.then(() => {
      const t0 = performance.now();
      const loop = now => { renderAt(((now - t0) / 1000) % DURATION); requestAnimationFrame(loop); };
      requestAnimationFrame(loop);
    });
  }
})();
