/*
 * N+8 — « La nuit »
 * Court-métrage génératif rendu image par image (window.N8.renderAt(t)).
 * Palette : noir, gris, bleu nuit très foncé.
 */
(() => {
  'use strict';
  const RENDER = new URLSearchParams(location.search).has('render');
  const cv = document.getElementById('film');
  const ctx = cv.getContext('2d');
  let W = 0, H = 0, U = 1, LAND = true;

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
    expoIn: p => (p <= 0 ? 0 : Math.pow(2, 10 * p - 10)),
  };
  const prog = (t, s, d, e = E.lin) => e(clamp((t - s) / d));
  const bump = (t, s, d) => Math.sin(Math.PI * clamp((t - s) / d));
  const mixC = (a, b, p) => [lerp(a[0], b[0], p), lerp(a[1], b[1], p), lerp(a[2], b[2], p)];
  const rgb = (c, a = 1) => `rgba(${c[0] | 0},${c[1] | 0},${c[2] | 0},${clamp(a).toFixed(4)})`;
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
  // Caméra « à l'épaule » : léger tremblement continu
  const shake = (u, seed, amp) => [
    (vnoise(u * 0.7, seed) - 0.5) * 2 * amp + (vnoise(u * 2.1, seed + 3) - 0.5) * amp * 0.4,
    (vnoise(u * 0.6, seed + 5) - 0.5) * 2 * amp + (vnoise(u * 1.9, seed + 9) - 0.5) * amp * 0.4,
  ];
  // Allumage d'un néon : grésillement puis lumière stable
  function flickOn(u, t0, dur, seed) {
    if (t0 == null) return 1;
    if (u < t0) return 0;
    if (u >= t0 + dur) return 1;
    const k = (u - t0) / dur, step = Math.floor((u - t0) / 0.042);
    const r = hash1(step * 13 + seed * 101);
    if (r < k * 1.25 - 0.05) return 0.72 + 0.28 * hash1(step + seed * 7);
    return r > 0.93 ? 0.3 : 0;
  }
  function flickOff(u, t0, dur, seed) {
    if (t0 == null || u < t0) return 1;
    if (u >= t0 + dur) return 0;
    const k = (u - t0) / dur, step = Math.floor((u - t0) / 0.042);
    const r = hash1(step * 17 + seed * 103);
    if (r > k * 1.2) return 0.8;
    return r > 0.9 ? 0.3 : 0;
  }

  /* =========================================================
   * Palette
   * ======================================================= */
  const COL = {
    glowT: [22, 50, 128],     // halo serré (bleu nuit)
    glowW: [11, 28, 88],      // halo large
    litTop: [122, 134, 160],  // verre éclairé : gris bleuté
    litBot: [46, 58, 92],
    ghostTop: [20, 22, 27],   // verre éteint
    ghostBot: [10, 11, 14],
    rain: [150, 160, 178],
    spark: [196, 202, 214],
    window: [118, 128, 148],
    logoTop: [168, 176, 192],
    logoBot: [92, 104, 132],
  };
  const FONT = '"Bodoni Moda", "GFS Didot", serif';
  const REF = 40;

  /* =========================================================
   * Calques et textures
   * ======================================================= */
  const mk = (w, h) => {
    const c = document.createElement('canvas');
    c.width = Math.max(1, Math.round(w)); c.height = Math.max(1, Math.round(h));
    return c;
  };
  const L = {};
  function layer(name, w, h, read = false) {
    const c = mk(w, h);
    L[name] = { c, x: c.getContext('2d', read ? { willReadFrequently: true } : undefined), w: c.width, h: c.height };
  }
  const MAIN = { get c() { return cv; }, get x() { return ctx; } };
  function reset(x) {
    x.setTransform(1, 0, 0, 1, 0, 0);
    x.globalAlpha = 1; x.globalCompositeOperation = 'source-over'; x.filter = 'none';
  }

  const TEX = {};
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
  const gray = (px, v) => { const g = clamp(v) * 255; px[0] = g; px[1] = g; px[2] = g; px[3] = 255; };
  function buildTextures() {
    const S = 1024;
    const r = rng(5);
    // Béton banché
    {
      const b = fbm(S, 170, 6, 11), f = fbm(S, 8, 2, 12);
      TEX.concrete = texCanvas(S, (i, x, y, px) => {
        let v = 0.5 + (b[i] - 0.5) * 1.7 + (f[i] - 0.5) * 0.25 + (r() - 0.5) * 0.06;
        if (y % 256 < 3) v -= 0.18;
        const hx = (x % 256) - 128, hy = (y % 256) - 128;
        if (hx * hx + hy * hy < 64) v -= 0.3;
        gray(px, v);
      });
    }
    // Enduit
    {
      const b = fbm(S, 300, 5, 21), f = fbm(S, 12, 2, 22);
      TEX.plaster = texCanvas(S, (i, x, y, px) => gray(px, 0.55 + (b[i] - 0.5) * 1.3 + (f[i] - 0.5) * 0.35 + (r() - 0.5) * 0.05));
    }
    // Briques
    {
      const b = fbm(S, 64, 4, 31), tone = Array.from({ length: 400 }, () => 0.42 + r() * 0.24);
      TEX.brick = texCanvas(S, (i, x, y, px) => {
        const row = Math.floor(y / 64), xo = (x + (row % 2) * 64) % S, col = Math.floor(xo / 128);
        const mortar = y % 64 < 7 || xo % 128 < 7;
        gray(px, mortar ? 0.22 + (b[i] - 0.5) * 0.2 : tone[(row * 8 + col) % 400] + (b[i] - 0.5) * 0.45 + (r() - 0.5) * 0.05);
      });
    }
    // Pierre de taille
    {
      const b = fbm(S, 128, 5, 41), rows = [];
      let yy = 0;
      while (yy < S) {
        const h = 170 + Math.floor(r() * 2) * 86, cuts = [];
        let xx = Math.floor(r() * 200);
        while (xx < S + 400) { cuts.push(xx); xx += 180 + Math.floor(r() * 220); }
        rows.push({ y: yy, h: Math.min(h, S - yy), cuts, tones: cuts.map(() => 0.4 + r() * 0.2) });
        yy += h;
      }
      TEX.stone = texCanvas(S, (i, x, y, px) => {
        const R = rows.find(o => y >= o.y && y < o.y + o.h) || rows[rows.length - 1];
        let k = 0; while (k < R.cuts.length - 1 && R.cuts[k + 1] <= x) k++;
        const joint = y - R.y < 8 || Math.abs(x - R.cuts[k]) < 5;
        gray(px, joint ? 0.16 : R.tones[k] + (b[i] - 0.5) * 0.5 + (r() - 0.5) * 0.05);
      });
    }
    // Métal brossé
    {
      const rowv = Array.from({ length: S }, () => r());
      const b = fbm(S, 256, 3, 51);
      TEX.metal = texCanvas(S, (i, x, y, px) => gray(px, 0.45 + (rowv[y] - 0.5) * 0.18 + (b[i] - 0.5) * 0.35 + Math.sin(x * 0.004 + rowv[y] * 6) * 0.03));
    }
    // Asphalte mouillé
    {
      const b = fbm(512, 64, 4, 61);
      TEX.asphalt = texCanvas(512, (i, x, y, px) => gray(px, 0.35 + (b[i] - 0.5) * 0.8 + (r() < 0.02 ? 0.25 : 0)));
    }
    // Brouillard (RGBA)
    {
      const b = fbm(512, 160, 5, 71);
      TEX.fog = texCanvas(512, (i, x, y, px) => {
        px[0] = 120; px[1] = 130; px[2] = 150; px[3] = clamp((b[i] - 0.38) * 2.4) * 255;
      });
    }
    // Nuages (RGBA)
    {
      const b = fbm(S, 300, 6, 81);
      TEX.clouds = texCanvas(S, (i, x, y, px) => {
        const a = clamp((b[i] - 0.42) / 0.32);
        px[0] = 46; px[1] = 52; px[2] = 64; px[3] = a * a * (3 - 2 * a) * 235;
      });
    }
    // Grain
    TEX.grain = [0, 1, 2, 3].map(k => {
      const rr = rng(900 + k);
      return texCanvas(256, (i, x, y, px) => gray(px, 0.5 + (rr() - 0.5) * 0.9));
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
   * Caméra
   * ======================================================= */
  function camM(cam) {
    const s = cam.s * U, r = cam.r || 0, cs = Math.cos(r), sn = Math.sin(r);
    return [s * cs, s * sn, -s * sn, s * cs, W / 2 - s * (cs * cam.x - sn * cam.y), H / 2 - s * (sn * cam.x + cs * cam.y)];
  }
  function applyM(x, m, k = 1, mirrorY = null) {
    x.setTransform(m[0] * k, m[1] * k, m[2] * k, m[3] * k, m[4] * k, m[5] * k);
    if (mirrorY != null) x.transform(1, 0, 0, -1, 0, 2 * mirrorY);
  }
  const toScreen = (m, x, y) => [m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5]];
  const mScale = m => Math.hypot(m[0], m[1]);

  /* =========================================================
   * Lettres lumineuses
   * ======================================================= */
  const advCache = new Map();
  function adv(ch) {
    if (!advCache.has(ch)) { ctx.font = `500 ${REF}px ${FONT}`; advCache.set(ch, ctx.measureText(ch).width / REF); }
    return advCache.get(ch);
  }
  const PLUS_W = 0.4;
  function rowX(chars, track = 0.035) {
    const ws = chars.map(c => (c === '+' ? PLUS_W : adv(c)));
    const tot = ws.reduce((a, b) => a + b, 0) + track * (ws.length - 1);
    let x = -tot / 2;
    return ws.map(w => { const c = x + w / 2; x += w + track; return c; });
  }
  function makeSign(def, S, x0 = 0, y0 = 0) {
    const N = def.N || 'N', eight = [...def.eight], night = [...def.night];
    const sx = v => v * S + x0;
    return {
      def, S, x0, y0, N, eight, night,
      r0: rowX([N, '+', '8']).map(sx),
      r1: rowX([N, '+', ...eight]).map(sx),
      r2: rowX(night).map(sx),
    };
  }
  function pushGlyph(it, a, b, x, y, S, lit, sw, ghost) {
    if (a === b) { it.push({ kind: 'glyph', ch: a, x, y, S, lit, ghost }); return; }
    if (sw < 1) it.push({ kind: 'glyph', ch: a, x, y, S, lit: lit * (1 - sw), ghost: ghost * (1 - sw) });
    if (sw > 0) it.push({ kind: 'glyph', ch: b, x, y, S, lit: lit * sw, ghost: 0 });
  }
  // État de l'enseigne à l'instant u : « N + 8 » → « N + huit » → « nuit »
  function signItems(sg, u, sc, seed) {
    const { S, N, eight, night, def } = sg, y = sg.y0, it = [];
    const shim = k => 0.93 + 0.07 * vnoise(u * 7 + k * 1.7, seed + k);
    const pB = sc.b == null || sc.b < 0 ? 1 : prog(u, sc.b, sc.bd, E.inOut);
    const pS = prog(u, sc.s, sc.sd, E.inOut);
    const swapF = k => prog(u, sc.sw + k * 0.05, 0.3, E.inOut);
    const dip = 1 - 0.5 * bump(u, sc.sw - 0.05, 0.45);
    const ghost = sc.ghost || 0;
    const jN = def.map.indexOf(0);
    const litN = flickOn(u, sc.n0, sc.n0d ?? 0.55, seed + 1) * shim(1);
    const xN = lerp(lerp(sg.r0[0], sg.r1[0], pB), sg.r2[jN], pS);
    pushGlyph(it, N, night[jN], xN, y, S, litN * (N === night[jN] ? 1 : dip), swapF(0), ghost);
    const litP = flickOn(u, sc.p0, 0.35, seed + 2) * flickOff(u, sc.d, 0.45, seed + 3) * shim(2);
    it.push({ kind: 'plus', x: lerp(sg.r0[1], sg.r1[1], pB), y, S, lit: litP, ghost: u < sc.d ? ghost : 0 });
    if (sc.e8 !== undefined) {
      const lit8 = flickOn(u, sc.e8, 0.5, seed + 4) * flickOff(u, sc.o8, 0.5, seed + 5) * shim(3);
      it.push({ kind: 'glyph', ch: '8', x: sg.r0[2], y, S, lit: lit8, ghost: sc.o8 == null || u < sc.o8 ? ghost : 0 });
    }
    eight.forEach((ch, k) => {
      const j = def.map.indexOf(k + 1);
      let lit = flickOn(u, sc.w + k * sc.ws, sc.wd ?? 0.32, seed + 10 + k) * shim(4 + k);
      let x = sg.r1[k + 2];
      if (j >= 0) {
        x = lerp(x, sg.r2[j], prog(u, sc.s + k * 0.03, sc.sd, E.inOut));
        pushGlyph(it, ch, night[j], x, y, S, lit * (ch === night[j] ? 1 : dip), swapF(k + 1), 0);
      } else {
        lit *= flickOff(u, sc.d, 0.5, seed + 30 + k);
        it.push({ kind: 'glyph', ch, x, y: y + prog(u, sc.d + 0.3, 0.6, E.in) * 0.08 * S, S, lit, ghost: 0 });
      }
    });
    def.map.forEach((m, j) => {
      if (m !== -1) return;
      const lit = flickOn(u, (sc.nw ?? sc.s + sc.sd * 0.6) + j * 0.06, 0.35, seed + 50 + j) * shim(20 + j);
      it.push({ kind: 'glyph', ch: night[j], x: sg.r2[j], y, S, lit, ghost: 0 });
    });
    it.gain = 1 + (sc.surge != null ? 0.7 * bump(u, sc.surge, 1.1) : 0);
    return it;
  }
  // Enseigne « N+8 » seule
  function brandItems(x0, y0, S, litN, litP, lit8, ghost = 0) {
    const r = rowX(['N', '+', '8']).map(v => v * S + x0);
    const it = [
      { kind: 'glyph', ch: 'N', x: r[0], y: y0, S, lit: litN, ghost },
      { kind: 'plus', x: r[1], y: y0, S, lit: litP, ghost },
      { kind: 'glyph', ch: '8', x: r[2], y: y0, S, lit: lit8, ghost },
    ];
    it.gain = 1;
    return it;
  }

  // Logo officiel (calques extraits du fichier fourni)
  const LOGO = { meta: null, parts: {}, lit: {} };
  function drawShape(x, it, forFace) {
    if (it.kind === 'img') {
      const p = LOGO.meta.parts[it.part];
      x.save();
      if (it.clip) { x.beginPath(); it.clip(x); x.clip(); }
      x.drawImage(forFace ? LOGO.lit[it.part] : LOGO.parts[it.part], p.x, p.y);
      x.restore();
      return;
    }
    x.save();
    x.translate(it.x, it.y);
    const k = it.S / REF;
    x.scale(k, k);
    if (it.kind === 'plus') {
      const cy = -0.29 * REF, h = 0.15 * REF, lw = 0.016 * REF;
      x.fillRect(-h, cy - lw / 2, 2 * h, lw);
      x.fillRect(-lw / 2, cy - h, lw, 2 * h);
    } else {
      x.font = `500 ${REF}px ${FONT}`;
      x.textAlign = 'center'; x.textBaseline = 'alphabetic';
      x.fillText(it.ch, 0, 0);
    }
    x.restore();
  }
  function drawMask(x, items) {
    x.fillStyle = '#fff';
    for (const it of items) {
      const a = clamp(it.lit);
      if (a <= 0.003) continue;
      x.globalAlpha = a;
      drawShape(x, it, false);
    }
    x.globalAlpha = 1;
  }
  function drawFaces(x, items) {
    for (const it of items) {
      const lit = clamp(it.lit), g = it.ghost || 0;
      if (lit <= 0.003 && g <= 0.003) continue;
      if (it.kind === 'img') {
        x.globalAlpha = lit * (it.faceA ?? 1);
        drawShape(x, it, true);
        x.globalAlpha = 1;
        continue;
      }
      const a = Math.max(lit, g);
      const top = mixC(COL.ghostTop, COL.litTop, lit), bot = mixC(COL.ghostBot, COL.litBot, lit);
      const gr = x.createLinearGradient(0, it.y - 0.72 * it.S, 0, it.y + 0.05 * it.S);
      gr.addColorStop(0, rgb(top, a)); gr.addColorStop(1, rgb(bot, a));
      x.fillStyle = gr;
      drawShape(x, it, true);
    }
  }
  function tint(l, col) {
    l.x.globalCompositeOperation = 'source-in';
    l.x.fillStyle = rgb(col); l.x.fillRect(0, 0, l.w, l.h);
    l.x.globalCompositeOperation = 'source-over';
  }
  // Halo : masque des lettres → flou serré + flou large, teintés bleu nuit
  function buildGlow(items, m, mirrorY, emPx) {
    const a = L.g4, b = L.g4b, c = L.g8;
    reset(a.x); a.x.clearRect(0, 0, a.w, a.h);
    applyM(a.x, m, a.w / W, mirrorY); drawMask(a.x, items); reset(a.x);
    reset(b.x); b.x.clearRect(0, 0, b.w, b.h);
    b.x.filter = `blur(${Math.max(0.7, emPx * 0.06 * b.w / W).toFixed(2)}px)`;
    b.x.drawImage(a.c, 0, 0); b.x.filter = 'none'; tint(b, COL.glowT);
    reset(c.x); c.x.clearRect(0, 0, c.w, c.h);
    c.x.filter = `blur(${Math.max(1, emPx * 0.3 * c.w / W).toFixed(2)}px)`;
    c.x.drawImage(a.c, 0, 0, c.w, c.h); c.x.filter = 'none'; tint(c, COL.glowW);
  }
  // Le monde d'une scène : mur ambiant, mur éclairé par le halo, halo, lettres.
  function drawWorld(T, m, spec, mirrorY = null) {
    const x = T.x;
    reset(x); x.fillStyle = '#000'; x.fillRect(0, 0, W, H);
    if (spec.backdrop) { applyM(x, m, 1, mirrorY); spec.backdrop(x); reset(x); }
    buildGlow(spec.items, m, mirrorY, spec.emPx);
    const gain = spec.items.gain || 1;
    if (spec.texture) {
      const l = L.lm;
      reset(l.x); l.x.fillStyle = '#000'; l.x.fillRect(0, 0, l.w, l.h);
      l.x.globalCompositeOperation = 'lighter';
      l.x.globalAlpha = Math.min(1, gain);
      l.x.drawImage(L.g8.c, 0, 0, l.w, l.h); l.x.drawImage(L.g4b.c, 0, 0, l.w, l.h);
      l.x.globalAlpha = 1;
      if (spec.lights) { applyM(l.x, m, l.w / W, mirrorY); spec.lights(l.x); l.x.setTransform(1, 0, 0, 1, 0, 0); }
      l.x.globalCompositeOperation = 'multiply';
      applyM(l.x, m, l.w / W, mirrorY); spec.texture(l.x); reset(l.x);
      x.globalCompositeOperation = 'lighter'; x.globalAlpha = spec.wallGain ?? 1.6;
      x.drawImage(l.c, 0, 0, W, H);
      if (spec.wallGain > 1) { x.globalAlpha = spec.wallGain - 1; x.drawImage(l.c, 0, 0, W, H); }
    }
    x.globalCompositeOperation = 'lighter';
    const gg = (spec.glowGain ?? 0.5) * gain;
    x.globalAlpha = Math.min(1, gg); x.drawImage(L.g8.c, 0, 0, W, H);
    x.globalAlpha = Math.min(1, gg * 1.1); x.drawImage(L.g4b.c, 0, 0, W, H);
    if (gg > 1) { x.globalAlpha = gg - 1; x.drawImage(L.g8.c, 0, 0, W, H); }
    reset(x);
    applyM(x, m, 1, mirrorY);
    drawFaces(x, spec.items);
    if (spec.after) spec.after(x);
    reset(x);
  }
  // Sol mouillé / eau : reflet du monde avec ondulations
  function drawFloor(m, spec, floorY, opt, u) {
    const fy = toScreen(m, 0, floorY)[1];
    if (fy >= H) return;
    drawWorld(L.refl, m, spec, floorY);
    const t2 = L.tmp;
    reset(t2.x); t2.x.clearRect(0, 0, W, H);
    t2.x.filter = `blur(${((opt.soft ?? 0.12) * U).toFixed(2)}px)`; t2.x.drawImage(L.refl.c, 0, 0); t2.x.filter = 'none';
    const x = ctx;
    const top = Math.max(0, Math.floor(fy));
    reset(x);
    const g = x.createLinearGradient(0, top, 0, H);
    g.addColorStop(0, rgb(opt.base0 || [6, 7, 10])); g.addColorStop(1, rgb(opt.base1 || [1, 1, 2]));
    x.fillStyle = g; x.fillRect(0, top, W, H - top);
    if (opt.tex) {
      applyM(x, m); x.globalAlpha = opt.texAlpha;
      x.fillStyle = pattern(x, opt.tex, opt.texScale);
      x.fillRect(-400, floorY, 800, 400); reset(x);
    }
    x.globalCompositeOperation = 'lighter';
    const strip = 2, span = Math.max(1, H - fy);
    for (let y = top; y < H; y += strip) {
      const d = (y - fy) / span;
      const amp = opt.amp * U * (0.25 + d * 1.6);
      const dx = Math.sin(y * opt.freq + u * opt.speed) * amp + Math.sin(y * opt.freq * 2.7 - u * opt.speed * 1.4) * amp * 0.35;
      x.globalAlpha = opt.alpha * clamp(1 - d * (opt.fade ?? 0.8));
      x.drawImage(t2.c, 0, y, W, strip, dx, y, W, strip);
    }
    reset(x);
    if (opt.edge) {
      const e = x.createLinearGradient(0, fy - 2, 0, fy + 0.8 * U);
      e.addColorStop(0, 'rgba(0,0,0,0)'); e.addColorStop(0.5, rgb(opt.edge, 0.55)); e.addColorStop(1, 'rgba(0,0,0,0)');
      x.fillStyle = e; x.fillRect(0, fy - 2, W, 0.8 * U + 2);
    }
  }

  /* =========================================================
   * Atmosphère : pluie, neige, brouillard, étincelles, gouttes
   * ======================================================= */
  function drawRain(u, o) {
    const x = ctx, r = rng(o.seed);
    reset(x); x.lineCap = 'round';
    const k = U / 10.8;
    for (let i = 0; i < o.n; i++) {
      const z = r(), x0 = r(), ph = r();
      const sp = o.speed * (0.65 + 0.7 * z);
      const len = o.len * (0.45 + z) * H;
      const yf = ((ph + u * sp) % 1.3) - 0.2;
      const py = yf * H, px = (x0 * 1.3 - 0.15) * W + py * o.slant;
      let a = o.alpha * (0.2 + 0.8 * z);
      if (o.lights) {
        let boost = 0;
        for (const L0 of o.lights) {
          const dx = px - L0[0], dy = py - L0[1];
          boost += L0[3] * Math.exp(-(dx * dx + dy * dy) / (L0[2] * L0[2]));
        }
        a *= 1 + boost;
      }
      if (a < 0.01) continue;
      x.strokeStyle = rgb(COL.rain, Math.min(a, 0.55));
      x.lineWidth = (0.5 + 1.7 * z) * k;
      x.beginPath(); x.moveTo(px, py); x.lineTo(px + len * o.slant, py + len); x.stroke();
    }
  }
  function drawSplashes(m, u, floorY, o) {
    const x = ctx;
    reset(x);
    const fy = toScreen(m, 0, floorY)[1];
    if (fy > H) return;
    const slot = 0.05;
    for (let k = 0; k < 14; k++) {
      const base = Math.floor(u / slot) - k;
      for (let j = 0; j < o.per; j++) {
        const id = base * 31 + j;
        const age = u - base * slot - hash1(id * 3) * slot;
        if (age < 0 || age > 0.6) continue;
        const sx = hash1(id * 7 + 1) * W, d = hash1(id * 11 + 2);
        const sy = fy + d * d * (H - fy);
        const rr = (0.3 + age * 3.2) * U * (0.4 + d);
        x.strokeStyle = rgb([120, 132, 152], (1 - age / 0.6) * o.alpha * (0.4 + d));
        x.lineWidth = 0.8 * U / 10.8;
        x.beginPath(); x.ellipse(sx, sy, rr, rr * 0.22, 0, 0, Math.PI * 2); x.stroke();
      }
    }
  }
  function drawSnow(u, o) {
    const x = ctx, r = rng(o.seed);
    reset(x);
    for (let i = 0; i < o.n; i++) {
      const z = r(), x0 = r(), ph = r(), sw = r() * 6.28;
      const sp = 0.035 + 0.09 * z;
      const yf = ((ph + u * sp) % 1.1) - 0.05;
      const px = (x0 + Math.sin(u * 0.9 + sw) * 0.012 * (1 + z)) * W, py = yf * H;
      let a = 0.18 + 0.55 * z;
      if (o.light) { const dx = px - o.light[0], dy = py - o.light[1]; a *= 1 + o.light[3] * Math.exp(-(dx * dx + dy * dy) / (o.light[2] * o.light[2])); }
      x.fillStyle = rgb([190, 196, 208], Math.min(0.85, a));
      x.beginPath(); x.arc(px, py, (0.5 + 2.6 * z) * U / 10.8, 0, Math.PI * 2); x.fill();
    }
  }
  function drawFog(u, o) {
    const x = ctx;
    reset(x); x.globalCompositeOperation = 'screen';
    for (let i = 0; i < 2; i++) {
      const sc = (o.scale || 1) * (i ? 1.9 : 1.1) * U / 10.8;
      x.globalAlpha = o.alpha * (i ? 0.7 : 1);
      x.fillStyle = pattern(x, TEX.fog, sc * 1.6, -u * (o.speed || 1) * U * (i ? 0.6 : 1) + i * 211, i * 97, sc * 0.8);
      x.fillRect(0, 0, W, H);
    }
    reset(x);
  }
  function drawSparks(m, u, sp) {
    const a = u - sp.t0;
    if (a < 0 || a > 1.3) return;
    const x = ctx, r = rng(sp.seed);
    applyM(x, m); x.globalCompositeOperation = 'lighter';
    for (let i = 0; i < sp.n; i++) {
      const ang = -Math.PI / 2 + (r() - 0.5) * 2.6, v = 5 + r() * 12, life = 0.35 + r() * 0.75, delay = r() * 0.12, size = 0.12 + r() * 0.12;
      const tt = a - delay;
      if (tt < 0 || tt > life) continue;
      const px = sp.x + Math.cos(ang) * v * tt, py = sp.y + Math.sin(ang) * v * tt + 22 * tt * tt;
      x.fillStyle = rgb(COL.spark, (1 - tt / life) * 0.95);
      x.beginPath(); x.arc(px, py, size * sp.scale, 0, Math.PI * 2); x.fill();
    }
    reset(x);
  }
  // Vitre mouillée : gouttes (réfractent le halo), coulures, mise au point
  const DROPS = [], RUNNERS = [];
  function buildDrops() {
    const r = rng(77);
    for (let i = 0; i < 300; i++) DROPS.push({ x: r(), y: r(), r: 0.16 + Math.pow(r(), 2.4) * 1.05, e: 1 + r() * 0.35, ph: r() });
    for (let i = 0; i < 12; i++) RUNNERS.push({ x: r(), y0: r() * 0.4, t0: r() * 4, sp: 0.06 + r() * 0.12, r: 0.5 + r() * 0.5 });
  }
  function drawWindow(u, o) {
    const x = ctx;
    if (o.bgBlur > 0.3) {
      const t = L.tmp; reset(t.x); t.x.clearRect(0, 0, W, H); t.x.drawImage(cv, 0, 0);
      reset(x); x.fillStyle = '#000'; x.fillRect(0, 0, W, H);
      x.filter = `blur(${o.bgBlur.toFixed(2)}px)`; x.drawImage(t.c, 0, 0); x.filter = 'none';
    }
    const gw = L.g8.w, gh = L.g8.h, gd = L.g8.x.getImageData(0, 0, gw, gh).data;
    const sample = (px, py) => {
      const ix = clamp(Math.floor(px / W * gw), 0, gw - 1), iy = clamp(Math.floor(py / H * gh), 0, gh - 1);
      const i = (iy * gw + ix) * 4, a = gd[i + 3] / 255;
      return [gd[i] * a, gd[i + 1] * a, gd[i + 2] * a];
    };
    const l = L.drop;
    reset(l.x); l.x.clearRect(0, 0, W, H);
    const dx = l.x;
    // buée légère
    dx.fillStyle = 'rgba(16,19,26,0.22)'; dx.fillRect(0, 0, W, H);
    const drop = (px, py, rr, e) => {
      const c = sample(px, py - rr * 5);
      dx.fillStyle = 'rgba(2,3,6,0.55)';
      dx.beginPath(); dx.ellipse(px, py, rr, rr * e, 0, 0, Math.PI * 2); dx.fill();
      dx.fillStyle = rgb([c[0] * 3.2 + 26, c[1] * 3.2 + 30, c[2] * 3.2 + 40], 0.85);
      dx.beginPath(); dx.ellipse(px, py + rr * e * 0.42, rr * 0.62, rr * e * 0.3, 0, 0, Math.PI * 2); dx.fill();
      dx.fillStyle = 'rgba(176,184,198,0.45)';
      dx.beginPath(); dx.arc(px - rr * 0.35, py - rr * e * 0.42, rr * 0.16, 0, Math.PI * 2); dx.fill();
      dx.strokeStyle = 'rgba(0,0,0,0.35)'; dx.lineWidth = Math.max(0.6, rr * 0.12);
      dx.beginPath(); dx.ellipse(px, py, rr, rr * e, 0, 0, Math.PI * 2); dx.stroke();
    };
    for (const d of DROPS) drop(d.x * W, d.y * H, d.r * U, d.e);
    for (const rn of RUNNERS) {
      const cyc = 4.2, tt = ((u + rn.t0) % cyc);
      const yA = rn.y0 * H, yB = yA + tt * rn.sp * H;
      const px = rn.x * W + Math.sin(tt * 3 + rn.t0) * 0.15 * U;
      dx.strokeStyle = 'rgba(120,130,150,0.16)'; dx.lineWidth = rn.r * 0.5 * U;
      dx.beginPath(); dx.moveTo(rn.x * W, yA); dx.lineTo(px, yB); dx.stroke();
      drop(px, yB, rn.r * U * 1.15, 1.25);
    }
    reset(x);
    if (o.dropBlur > 0.3) x.filter = `blur(${o.dropBlur.toFixed(2)}px)`;
    x.drawImage(l.c, 0, 0); x.filter = 'none';
    if (o.mullion != null) {
      const mx = o.mullion * W, mw = 3.2 * U;
      const g = x.createLinearGradient(mx, 0, mx + mw, 0);
      g.addColorStop(0, '#050608'); g.addColorStop(0.15, '#1a1d23'); g.addColorStop(0.3, '#08090c'); g.addColorStop(1, '#030304');
      x.fillStyle = g; x.fillRect(mx, 0, mw, H);
    }
  }
  // Réverbère : flaque de lumière sur le mur + cône visible dans l'air
  function lampLight(x, lp, k = 1) {
    const g = x.createRadialGradient(lp.x + 4, lp.y + 20, 0, lp.x + 4, lp.y + 20, 46);
    g.addColorStop(0, rgb([62, 66, 74], k)); g.addColorStop(1, 'rgba(0,0,0,0)');
    x.fillStyle = g; x.fillRect(lp.x - 60, lp.y - 30, 130, 110);
  }
  function lampProps(x, lp, k = 1) {
    x.strokeStyle = '#08090b'; x.lineWidth = 0.7;
    x.beginPath(); x.moveTo(lp.x - 12, lp.y - 3); x.quadraticCurveTo(lp.x - 5, lp.y - 5, lp.x, lp.y - 1.4); x.stroke();
    x.fillStyle = '#0b0c0f';
    x.beginPath(); x.moveTo(lp.x - 2.4, lp.y - 1.6); x.lineTo(lp.x + 2.4, lp.y - 1.6); x.lineTo(lp.x + 1.6, lp.y); x.lineTo(lp.x - 1.6, lp.y); x.closePath(); x.fill();
    x.globalCompositeOperation = 'lighter';
    const cone = x.createLinearGradient(0, lp.y, 0, lp.y + 60);
    cone.addColorStop(0, rgb([92, 98, 110], 0.16 * k)); cone.addColorStop(1, 'rgba(0,0,0,0)');
    x.fillStyle = cone;
    x.beginPath(); x.moveTo(lp.x - 1.3, lp.y); x.lineTo(lp.x + 1.3, lp.y); x.lineTo(lp.x + 26, lp.y + 60); x.lineTo(lp.x - 22, lp.y + 60); x.closePath(); x.fill();
    const b = x.createRadialGradient(lp.x, lp.y + 0.2, 0, lp.x, lp.y + 0.2, 4.5);
    b.addColorStop(0, rgb([196, 200, 208], 0.9 * k)); b.addColorStop(0.15, rgb([120, 126, 138], 0.35 * k)); b.addColorStop(1, 'rgba(0,0,0,0)');
    x.fillStyle = b; x.fillRect(lp.x - 5, lp.y - 5, 10, 10);
    x.globalCompositeOperation = 'source-over';
  }
  function finish(t) {
    const x = ctx;
    reset(x);
    // vignette
    const v = x.createRadialGradient(W / 2, H / 2, Math.min(W, H) * 0.3, W / 2, H / 2, Math.hypot(W, H) * 0.55);
    v.addColorStop(0, 'rgba(0,0,0,0)'); v.addColorStop(1, 'rgba(0,0,0,0.7)');
    x.fillStyle = v; x.fillRect(0, 0, W, H);
    // grain argentique
    const f = Math.floor(t * 30 + 0.5), r = rng(1000 + f);
    const ox = -Math.floor(r() * 256), oy = -Math.floor(r() * 256);
    x.globalCompositeOperation = 'overlay'; x.globalAlpha = 0.1;
    x.fillStyle = pattern(x, TEX.grain[f % 4], 1, ox, oy); x.fillRect(0, 0, W, H);
    x.globalCompositeOperation = 'lighter'; x.globalAlpha = 0.018;
    x.fillRect(0, 0, W, H);
    reset(x);
    // format cinéma 2.39:1 en paysage
    if (LAND) {
      const bar = Math.round((H - W / 2.39) / 2);
      x.fillStyle = '#000'; x.fillRect(0, 0, W, bar); x.fillRect(0, H - bar, W, bar);
    }
    const veil = Math.max(1 - prog(t, 0, 1.6, E.out), prog(t, DURATION - 1.6, 1.6, E.inOut));
    if (veil > 0) { x.fillStyle = `rgba(0,0,0,${veil.toFixed(4)})`; x.fillRect(0, 0, W, H); }
  }

  /* =========================================================
   * Chronologie et événements sonores
   * ======================================================= */
  const EV = [];
  const ev = (type, t, extra = {}) => EV.push({ type, t: +t.toFixed(3), ...extra });
  const SCENES = [];
  let DURATION = 0;

  function signEvents(start, sc, sg, o = {}) {
    const pan = o.pan ?? 0, g = o.gain ?? 1;
    const on = t => t != null && t >= 0 && ev('flick', start + t, { pan, gain: g });
    on(sc.n0); on(sc.p0); if (sc.e8 != null) on(sc.e8);
    if (sc.o8 != null) ev('off', start + sc.o8, { pan, gain: g });
    sg.eight.forEach((_, k) => on(sc.w + k * sc.ws));
    if (sg.def.map.some(m => m === -1)) sg.def.map.forEach((m, j) => { if (m === -1) on((sc.nw ?? sc.s + sc.sd * 0.6) + j * 0.06); });
    const dying = sg.eight.some((_, k) => sg.def.map.indexOf(k + 1) < 0);
    ev(dying ? 'spark' : 'off', start + sc.d, { pan, gain: g * (dying ? 1 : 0.5) });
    ev('slide', start + sc.s, { dur: sc.sd, pan, gain: g });
    ev('snap', start + sc.sw, { pan, gain: g });
    if (sc.surge != null) ev('surge', start + sc.surge, { gain: g });
  }
  function sparksFor(sg, sc, seed) {
    const out = [];
    sg.eight.forEach((ch, k) => {
      if (sg.def.map.indexOf(k + 1) < 0) out.push({ t0: sc.d + 0.05, x: sg.r1[k + 2], y: sg.y0 - 0.32 * sg.S, seed: seed + k, n: 18, scale: sg.S / 19 });
    });
    return out;
  }

  /* ---------- 1. La nuit tombe sur la ville ---------- */
  function sceneSky(start, dur) {
    const HZ = LAND ? 12 : 20;
    const SX = LAND ? 27 : 13, SROOF = HZ - 17.5, SS = 2.1, SY = SROOF - 0.55;
    const r = rng(404), B = [], FAR = [], WIN = [], STARS = [];
    for (let x = -190; x < 190;) {
      const w = 3 + r() * 6.5, h = 2.5 + Math.pow(r(), 1.7) * 19;
      const tier = h > 9 && r() < 0.55 ? { w: w * (0.45 + r() * 0.3), h: 1.5 + r() * 4, o: r() } : null;
      B.push({ x, w, h, tier, ant: r() < 0.22 ? 1 + r() * 3.5 : 0, tank: r() < 0.18, blink: r() < 0.25 ? r() * 2 : -1 });
      x += w + r() * 0.9;
    }
    const sb = B.reduce((a, b) => (Math.abs(b.x + b.w / 2 - SX) < Math.abs(a.x + a.w / 2 - SX) ? b : a));
    sb.x = SX - 5; sb.w = 10; sb.h = 17.5; sb.ant = 0; sb.tier = null; sb.tank = false; sb.blink = -1;
    for (let x = -200; x < 200;) { const w = 4 + r() * 8; FAR.push({ x, w, h: 4 + Math.pow(r(), 1.3) * 16 }); x += w; }
    for (const b of B) {
      const cols = Math.floor((b.w - 0.9) / 1.15), rows = Math.floor((b.h - 1.2) / 1.35);
      for (let c = 0; c < cols; c++) for (let k = 0; k < rows; k++) {
        if (r() > 0.5) continue;
        WIN.push({ x: b.x + 0.7 + c * 1.15, y: HZ - 1.4 - k * 1.35, on: 1 + r() * 7.5, b: 0.3 + r() * 0.7, w: r() < 0.1 ? 1.6 : 0.5, seed: WIN.length });
      }
    }
    for (let i = 0; i < 170; i++) STARS.push({ x: (r() - 0.5) * 260, y: -70 + r() * (HZ - 4 + 70) * 0.75, s: 0.05 + r() * 0.14, ph: r() * 6.28 });
    const dusk = u => 1 - prog(u, 0.3, 8.2, E.sine);
    const sc = { n0: 5.0, p0: 5.7, e8: 6.05 };
    const cam = u => {
      const p1 = prog(u, 0, 7.6, E.sine), p2 = prog(u, 7.25, dur - 7.25, E.expoIn);
      const tx = SX, ty = SY - 0.75 * SS;
      const bx = lerp(0, tx * 0.3, p1), by = lerp(0, ty * 0.15, p1), bs = lerp(1, 1.1, p1);
      const pc = E.inOut(clamp(p2 * 2.2));
      return { x: lerp(bx, tx, pc), y: lerp(by, ty, pc), s: lerp(bs, 15, p2), r: 0 };
    };
    const items = u => brandItems(SX, SY, SS, flickOn(u, sc.n0, 0.6, 3), flickOn(u, sc.p0, 0.3, 4), flickOn(u, sc.e8, 0.5, 5));
    ev('flick', start + sc.n0, { pan: 0.3, gain: 0.35 }); ev('flick', start + sc.p0, { pan: 0.3, gain: 0.3 }); ev('flick', start + sc.e8, { pan: 0.3, gain: 0.35 });
    ev('whoosh', start + 7.25, { dur: dur - 7.25 });
    function backdrop(u) {
      const d = dusk(u);
      return x => {
        const top = mixC([2, 3, 6], [20, 25, 36], d), mid = mixC([5, 7, 12], [38, 44, 58], d), hz = mixC([12, 15, 22], [70, 76, 88], d);
        const g = x.createLinearGradient(0, -70, 0, HZ);
        g.addColorStop(0, rgb(top)); g.addColorStop(0.7, rgb(mid)); g.addColorStop(1, rgb(hz));
        x.fillStyle = g; x.fillRect(-400, -200, 800, HZ + 200);
        x.globalAlpha = 0.55 * d + 0.18;
        x.fillStyle = pattern(x, TEX.clouds, 0.16, -u * 1.6, -40, 0.055);
        x.fillRect(-400, -200, 800, HZ + 199.5);
        x.globalAlpha = 1;
        const sa = Math.pow(1 - d, 1.5);
        if (sa > 0.01) {
          for (const s of STARS) {
            x.fillStyle = rgb([170, 178, 194], sa * (0.35 + 0.35 * Math.sin(u * 1.3 + s.ph)));
            x.fillRect(s.x, s.y, s.s, s.s);
          }
        }
        const cg = x.createLinearGradient(0, HZ - 18, 0, HZ);
        cg.addColorStop(0, 'rgba(0,0,0,0)'); cg.addColorStop(1, rgb([34, 42, 60], 0.5 * (1 - d) + 0.1));
        x.fillStyle = cg; x.fillRect(-400, HZ - 18, 800, 18);
        x.fillStyle = rgb(mixC([10, 12, 17], [30, 35, 46], d));
        for (const b of FAR) x.fillRect(b.x * 1.05, HZ - b.h * 0.7, b.w, b.h * 0.7);
        x.fillStyle = '#040508';
        for (const b of B) {
          x.fillRect(b.x, HZ - b.h, b.w, b.h);
          let top = HZ - b.h;
          if (b.tier) { const tx = b.x + (b.w - b.tier.w) * b.tier.o; x.fillRect(tx, top - b.tier.h, b.tier.w, b.tier.h); top -= b.tier.h; }
          if (b.tank) { x.fillRect(b.x + b.w * 0.2, HZ - b.h - 1.3, 1.1, 1.3); x.fillRect(b.x + b.w * 0.2 + 0.2, HZ - b.h - 1.9, 0.7, 0.6); }
          if (b.ant) x.fillRect(b.x + b.w / 2 - 0.07, top - b.ant, 0.14, b.ant);
        }
        for (const b of B) {
          if (b.blink < 0 || !b.ant) continue;
          const on = ((u + b.blink) % 2.2) < 0.25 ? 1 : 0;
          if (!on) continue;
          const top = HZ - b.h - (b.tier ? b.tier.h : 0) - b.ant;
          x.fillStyle = rgb([150, 158, 175], 0.8 * (1 - d * 0.5));
          x.fillRect(b.x + b.w / 2 - 0.12, top - 0.12, 0.24, 0.24);
        }
        for (const w of WIN) {
          const on = flickOn(u, w.on, 0.25, w.seed);
          if (on <= 0) continue;
          x.fillStyle = rgb(COL.window, on * w.b * (0.45 + 0.55 * (1 - d)));
          x.fillRect(w.x, w.y, w.w, 0.62);
        }
      };
    }
    const S = {
      start, dur,
      items,
      humGain: 0.12,
      audio: u => ({ wind: 0.7 * (1 - prog(u, 7, 3)), city: 0.6, rain: prog(u, 7.0, 3.0, E.in) * 0.8 }),
      render(u) {
        const m = camM(cam(u)), it = items(u);
        const spec = { items: it, emPx: SS * mScale(m), glowGain: 0.9, backdrop: backdrop(u) };
        drawWorld(MAIN, m, spec);
        drawFloor(m, spec, HZ, { alpha: 0.3, amp: 0.3, freq: 0.5, speed: 1.6, fade: 0.7, soft: 0.25, base0: [4, 5, 8], base1: [1, 1, 2] }, u);
        const pr = prog(u, 7.0, 3.0, E.in);
        if (pr > 0) drawRain(u, { seed: 21, n: Math.round(420 * pr), speed: 1.7, len: 0.07, alpha: 0.2 * pr, slant: 0.1 });
        drawFog(u, { alpha: 0.05, speed: 0.6, scale: 1.4 });
        const p2 = prog(u, 7.25, dur - 7.25, E.expoIn);
        if (p2 > 0.02) {
          const [fx, fy] = toScreen(m, SX, SY - 0.75 * SS);
          const t = L.tmp; reset(t.x); t.x.clearRect(0, 0, W, H); t.x.drawImage(cv, 0, 0);
          ctx.globalAlpha = 0.16;
          for (let i = 1; i <= 6; i++) {
            const k = 1 + i * 0.018 * p2 * 3;
            ctx.setTransform(k, 0, 0, k, fx * (1 - k), fy * (1 - k));
            ctx.drawImage(t.c, 0, 0);
          }
          reset(ctx);
        }
      },
    };
    return S;
  }

  /* ---------- Scènes « enseigne » génériques ---------- */
  function signScene(o) {
    const sg = makeSign(o.def, o.S, o.sx || 0, o.sy);
    const items = u => signItems(sg, u, o.sc, o.seed);
    const sparks = sparksFor(sg, o.sc, o.seed + 500);
    signEvents(o.start, o.sc, sg, { pan: o.pan || 0, gain: o.evGain ?? 1 });
    if (o.cut) ev('cut', o.start, { gain: o.cut });
    return {
      start: o.start, dur: o.dur, items, humGain: o.humGain ?? 1,
      audio: o.audio,
      render(u) {
        const cam = o.cam(u), m = camM(cam), it = items(u);
        const tex = o.tex, ts = o.texScale || 0.075;
        const spec = {
          items: it, emPx: o.S * mScale(m), wallGain: o.wallGain ?? 1.8, glowGain: o.glowGain ?? 0.55,
          backdrop: x => {
            x.globalAlpha = o.amb ?? 0.1; x.fillStyle = pattern(x, tex, ts); x.fillRect(-500, -500, 1000, 1000); x.globalAlpha = 1;
            x.fillStyle = 'rgba(2,4,10,0.6)'; x.globalCompositeOperation = 'lighter'; x.fillRect(-500, -500, 1000, 1000); x.globalCompositeOperation = 'source-over';
            if (o.backdrop) o.backdrop(x, u);
          },
          texture: x => { x.fillStyle = pattern(x, tex, ts); x.fillRect(-500, -500, 1000, 1000); },
          lights: o.lights ? x => o.lights(x, u, it) : null,
          after: o.props ? x => o.props(x, u) : null,
        };
        drawWorld(MAIN, m, spec);
        if (o.floor) drawFloor(m, spec, o.floor.y, o.floor, u);
        const [lx, ly] = toScreen(m, sg.x0, sg.y0 - 0.35 * o.S);
        const lightR = o.S * mScale(m) * 2.2;
        if (o.window) drawWindow(u, o.window(u));
        if (o.rain) {
          const lights = [[lx, ly, lightR, 2.6]];
          if (o.rain.lamp) { const [px, py] = toScreen(m, o.rain.lamp.x + 2, o.rain.lamp.y + 22); lights.push([px, py, 30 * U, 2.2]); }
          drawRain(u, { seed: o.seed + 7, n: o.rain.n, speed: o.rain.speed || 1.8, len: o.rain.len || 0.075, alpha: o.rain.alpha, slant: o.rain.slant ?? 0.1, lights });
        }
        if (o.floor && o.floor.splash) drawSplashes(m, u, o.floor.y, { per: o.floor.splash, alpha: 0.45 });
        if (o.snow) drawSnow(u, { seed: o.seed + 9, n: o.snow, light: [lx, ly, lightR, 2.4] });
        for (const sp of sparks) drawSparks(m, u, sp);
        if (o.fog) drawFog(u, o.fog);
        if (o.post) o.post(u, m);
      },
    };
  }

  /* =========================================================
   * Construction du film
   * ======================================================= */
  function buildFilm() {
    SCENES.length = 0; EV.length = 0;
    let t = 0;
    const add = s => { SCENES.push(s); t = s.start + s.dur; return s; };

    // 1. Crépuscule → nuit
    add(sceneSky(0, 10));

    // 2. Français — « N + 8 » … « N + huit » … « nuit » (pluie, mur de béton, sol mouillé)
    {
      const D = 10.5, S = LAND ? 19 : 16, sy = LAND ? 3 : -2;
      const sc = { n0: -1, p0: -1, e8: -1, o8: 2.4, b: 2.7, bd: 0.8, w: 2.85, ws: 0.3, d: 5.4, s: 6.2, sd: 1.5, sw: 7.2, surge: 7.35 };
      ev('car', t + 8.0, { dur: 2.6 });
      add(signScene({
        start: t, dur: D, seed: 100, S, sy, sc, tex: TEX.concrete, def: { eight: 'huit', night: 'nuit', map: [0, 2, 3, 4] },
        cam: u => { const p = prog(u, 0, D, E.sine), [hx, hy] = shake(u, 11, 0.22); return { x: lerp(-2.5, 2, p) + hx, y: sy - 0.36 * S + lerp(1.5, -0.5, p) + hy, s: lerp(1.0, 1.12, p) }; },
        floor: { y: LAND ? 12 : 20, alpha: 0.5, amp: 0.14, freq: 0.35, speed: 2.4, fade: 0.55, soft: 0.18, tex: TEX.asphalt, texScale: 0.06, texAlpha: 0.05, splash: 3, edge: [40, 46, 60] },
        rain: { n: 620, alpha: 0.2, speed: 1.9 },
        fog: { alpha: 0.06, speed: 1.2 },
        lights: (x, u, it) => {
          const p = prog(u, 8.0, 2.6, E.inOut);
          if (p <= 0 || p >= 1) return;
          const k = Math.sin(Math.PI * p), hx = lerp(-150, 150, p);
          x.save(); x.translate(hx, -6); x.scale(2.1, 1);
          const g = x.createRadialGradient(0, 0, 0, 0, 0, 22);
          g.addColorStop(0, rgb([70, 72, 78], k)); g.addColorStop(1, 'rgba(0,0,0,0)');
          x.fillStyle = g; x.fillRect(-24, -24, 48, 48); x.restore();
          x.globalCompositeOperation = 'source-over';
          x.fillStyle = `rgba(0,0,0,${(0.85 * k).toFixed(3)})`;
          for (const g2 of it) { if (g2.lit < 0.05) continue; drawShape(x, { ...g2, x: g2.x + (g2.x - hx) * 0.1, y: g2.y + 1.2 }, false); }
          x.globalCompositeOperation = 'lighter';
        },
        audio: u => ({ rain: 1, city: 0.15 }),
      }));
    }

    // 3. Español — balcon, réverbère, contre-plongée
    {
      const D = 5.8, S = LAND ? 17 : 15, sy = LAND ? 6 : 2;
      const lamp = LAND ? { x: -52, y: -16 } : { x: -30, y: -30 };
      const sc = { n0: 0.3, p0: 0.62, e8: 0.8, o8: 1.65, b: 1.85, bd: 0.5, w: 1.9, ws: 0.17, d: 2.95, s: 3.25, sd: 0.85, sw: 3.85, surge: 4.0 };
      add(signScene({
        start: t, dur: D, seed: 200, S, sy, sc, tex: TEX.plaster, texScale: 0.06, cut: 0.6, pan: 0.1, def: { eight: 'ocho', night: 'noche', map: [0, 1, 2, 3, 4] },
        cam: u => { const p = prog(u, 0, D, E.sine), [hx, hy] = shake(u, 21, 0.2); return { x: lerp(3, 0, p) + hx, y: lerp(sy + 8, sy - 7, p) + hy, s: 1.06, r: lerp(-0.05, -0.015, p) }; },
        rain: { n: 380, alpha: 0.16, speed: 1.7, lamp },
        fog: { alpha: 0.08, speed: 0.9, scale: 1.3 },
        lights: x => lampLight(x, lamp),
        props: x => {
          const by = sy - 30;
          x.fillStyle = '#0a0b0e'; x.fillRect(-60, by, 120, 3.2);
          x.fillStyle = '#1c1f25'; x.fillRect(-60, by + 3.2, 120, 0.35);
          x.fillStyle = '#060709';
          for (let bx = -59; bx <= 59; bx += 2.2) x.fillRect(bx, by - 9, 0.28, 9);
          x.fillRect(-60, by - 9.4, 120, 0.6);
          lampProps(x, lamp);
        },
        audio: () => ({ rain: 0.55, city: 0.2 }),
      }));
    }

    // 4. English — derrière une vitre mouillée, mise au point
    {
      const D = 5.7, S = LAND ? 18 : 15, sy = LAND ? 4 : 0;
      const sc = { n0: -1, p0: -1, e8: -1, o8: 2.0, b: 2.25, bd: 0.5, w: 2.3, ws: 0.15, d: 3.2, s: 3.45, sd: 0.85, sw: 4.0, surge: 4.15 };
      ev('focus', t + 0.7, { dur: 1.3 });
      add(signScene({
        start: t, dur: D, seed: 300, S, sy, sc, tex: TEX.brick, texScale: 0.05, cut: 0.5, pan: -0.15, evGain: 0.7, humGain: 0.5,
        def: { eight: 'eight', night: 'night', map: [0, 2, 3, 4, 5] },
        cam: u => { const p = prog(u, 0, D, E.sine), [hx, hy] = shake(u, 31, 0.15); return { x: lerp(-1.5, 1.5, p) + hx, y: sy - 0.36 * S + hy, s: lerp(1.08, 1.0, p) }; },
        window: u => {
          const f = prog(u, 0.7, 1.3, E.inOut);
          return { bgBlur: lerp(1.6, 0, f) * U, dropBlur: lerp(0, 0.45, f) * U, mullion: LAND ? 0.8 : 0.86 };
        },
        fog: { alpha: 0.04, speed: 0.6 },
        audio: () => ({ rain: 0.9, muffle: 1, drops: 1 }),
      }));
    }

    // 5. Italiano — le reflet dans l'eau noire, puis la caméra se lève
    {
      const D = 5.6, S = LAND ? 17 : 15, sy = LAND ? -4 : -8, wy = LAND ? 6 : 4;
      const sc = { n0: 0.1, p0: 0.32, e8: 0.45, o8: 1.05, b: 1.25, bd: 0.45, w: 1.3, ws: 0.14, d: 1.95, s: 2.1, sd: 0.75, sw: 2.6, surge: 2.75 };
      ev('tilt', t + 3.1, { dur: 1.9 });
      add(signScene({
        start: t, dur: D, seed: 400, S, sy, sc, tex: TEX.stone, texScale: 0.07, cut: 0.6, pan: 0.05,
        def: { eight: 'otto', night: 'notte', map: [0, 1, 2, 3, 4] },
        cam: u => { const p = prog(u, 3.1, 1.9, E.inOut), [hx, hy] = shake(u, 41, 0.18); return { x: hx, y: lerp(wy + (LAND ? 30 : 40), sy - 0.36 * S, p) + hy, s: lerp(LAND ? 1.15 : 1.8, 1.0, p) }; },
        floor: { y: wy, alpha: 0.75, amp: 0.38, freq: 0.07, speed: 1.6, fade: 0.25, soft: 0.2, base0: [3, 4, 8], base1: [1, 2, 4], edge: [26, 30, 40] },
        props: x => {
          const px = LAND ? -46 : -34;
          x.fillStyle = '#07080a'; x.fillRect(px, -60, 2.6, 60 + wy);
          x.fillStyle = '#16191f'; x.fillRect(px + 2.1, -60, 0.4, 60 + wy);
          x.fillStyle = '#050608'; x.fillRect(-300, wy - 1.2, 600, 1.2);
        },
        fog: { alpha: 0.05, speed: 0.4, scale: 1.6 },
        audio: () => ({ water: 1, rain: 0.15 }),
      }));
    }

    // 6. Montage : Deutsch, Português, Nederlands, Svenska, Română, Ελληνικά
    {
      const shots = [
        { d: 1.45, def: { eight: 'acht', night: 'Nacht', map: [0, 1, 2, 3, 4] }, tex: TEX.metal, ts: 0.05, cam: [7, -1, 1.7, -0.09], fog: 0.05, audio: { rain: 0.35 } },
        { d: 1.35, def: { eight: 'oito', night: 'noite', map: [0, 1, 2, 3, 4] }, tex: TEX.plaster, ts: 0.06, cam: [0, 0, 1.0, 0.03], lamp: true, rain: 340, fog: 0.09, audio: { rain: 0.6 } },
        { d: 1.25, def: { eight: 'acht', night: 'nacht', map: [0, 1, 2, 3, 4] }, tex: TEX.brick, ts: 0.05, cam: [0, 34, 1.05, 0], water: true, audio: { water: 0.9 } },
        { d: 1.2, def: { eight: 'åtta', night: 'natt', map: [0, 1, 2, 3] }, tex: TEX.concrete, ts: 0.07, cam: [-3, 0, 1.15, 0.025], snow: 260, fog: 0.07, audio: { wind: 0.5 } },
        { d: 1.15, def: { eight: 'opt', night: 'noapte', map: [0, 1, -1, 2, 3, -1] }, tex: TEX.brick, ts: 0.05, cam: [0, 0, 1.05, 0], window: true, audio: { rain: 0.7, muffle: 1 } },
        { d: 1.4, def: { N: 'Ν', eight: 'οκτώ', night: 'νύχτα', map: [0, 1, 2, 3, 4] }, tex: TEX.stone, ts: 0.07, cam: [2, 4, 1.25, 0.05], fog: 0.06, audio: { wind: 0.35 } },
      ];
      shots.forEach((sh, i) => {
        const d = sh.d, S = LAND ? 18 : 15, sy = sh.water ? -9 : 4;
        const sc = { n0: 0, n0d: 0.16, p0: 0.03, b: -1, w: 0.02, ws: 0.025, wd: 0.16, d: 0.42 * d, s: 0.45 * d, sd: 0.2, sw: 0.5 * d, nw: 0.55 * d, surge: 0.55 * d };
        const lamp = LAND ? { x: -44, y: -22 } : { x: -28, y: -34 };
        ev('pulse', t, { gain: 1, i });
        add(signScene({
          start: t, dur: d, seed: 600 + i * 37, S, sy, sc, tex: sh.tex, texScale: sh.ts, cut: 0.9, evGain: 0.8, def: sh.def,
          cam: u => {
            const [hx, hy] = shake(u, 61 + i, 0.25), c = sh.cam;
            return { x: c[0] + hx + u * 0.8, y: (sh.water ? (LAND ? c[1] : 44) : sy - 0.36 * S + c[1]) + hy, s: (sh.water && !LAND ? 1.8 : c[2]) * (1 + u * 0.025), r: c[3] };
          },
          floor: sh.water ? { y: 2, alpha: 0.8, amp: 0.4, freq: 0.08, speed: 1.9, fade: 0.2, soft: 0.2, base0: [3, 4, 8], base1: [1, 2, 4] } : null,
          rain: sh.rain ? { n: sh.rain, alpha: 0.17, lamp: sh.lamp ? lamp : null } : null,
          snow: sh.snow || 0,
          lights: sh.lamp ? x => lampLight(x, lamp) : null,
          props: sh.lamp ? x => lampProps(x, lamp) : null,
          window: sh.window ? () => ({ bgBlur: 0, dropBlur: 0.25 * U, mullion: null }) : null,
          fog: sh.fog ? { alpha: sh.fog, speed: 1.4 } : null,
          audio: () => sh.audio,
        }));
      });
      ev('riser', t - 2.2, { dur: 2.2 });
    }

    // 7–8. Silence, puis le logo
    add(sceneFinale(t, 17.8));
    DURATION = t;
  }

  /* ---------- Finale : « la nuit s'écrit N+8 », l'arche, le logo ---------- */
  function logoM(z) {
    const s0 = LAND ? (W / 2.39) * 0.86 / 700 : W * 0.88 / 712;
    const s = s0 * z;
    return [s, 0, 0, s, W / 2 - s * 768, H / 2 - s * (LAND ? 500 : 520)];
  }
  function sceneFinale(start, dur) {
    const CX = 767.5, CY = 456, R = 300, SIDE = 246, ARC = Math.PI / 2 * R, HALF = SIDE + ARC;
    const archClip = p => x => {
      const d = p * HALF;
      const h = Math.min(d, SIDE + 4);
      x.rect(440, 712 - h, 60, h); x.rect(1036, 712 - h, 60, h);
      if (d > SIDE) {
        const a = Math.min(Math.PI / 2, (d - SIDE) / R);
        x.moveTo(CX, CY); x.arc(CX, CY, R + 40, Math.PI, Math.PI + a); x.closePath();
        x.moveTo(CX, CY); x.arc(CX, CY, R + 40, -a, 0); x.closePath();
      }
    };
    const tip = p => {
      const d = p * HALF;
      if (d <= SIDE) return [[CX - 300 - 0.5, 706 - d], [CX + 300, 706 - d]];
      const a = (d - SIDE) / R;
      return [[CX + R * Math.cos(Math.PI + a), CY + R * Math.sin(Math.PI + a)], [CX + R * Math.cos(-a), CY + R * Math.sin(-a)]];
    };
    const wipe = (part, p) => x => {
      const q = LOGO.meta.parts[part], cx = q.x + q.w / 2, hw = (q.w / 2 + 10) * p;
      x.rect(cx - hw, q.y - 5, 2 * hw, q.h + 10);
    };
    const T = { n: 0.9, p: 1.55, e: 1.85, txtIn: 2.6, txtOut: 5.7, arch: 6.2, archD: 2.5, l1: 8.5, l2: 9.1, swell: 9.6 };
    ev('silence', start, {});
    ev('flick', start + T.n, { gain: 0.9 }); ev('flick', start + T.p, { gain: 0.6 }); ev('flick', start + T.e, { gain: 0.9 });
    ev('arch', start + T.arch, { dur: T.archD });
    ev('logo', start + T.swell, {});
    const items = u => {
      const br = 0.95 + 0.05 * Math.sin(u * 1.4);
      const ap = prog(u, T.arch, T.archD, E.inOut);
      const it = [
        { kind: 'img', part: 'n', lit: flickOn(u, T.n, 0.6, 801) * br },
        { kind: 'img', part: 'plus', lit: flickOn(u, T.p, 0.3, 802) * br },
        { kind: 'img', part: 'eight', lit: flickOn(u, T.e, 0.5, 803) * br },
      ];
      if (ap > 0) it.push({ kind: 'img', part: 'arch', lit: br, clip: archClip(ap) });
      const p1 = prog(u, T.l1, 1.5, E.inOut), p2 = prog(u, T.l2, 1.5, E.inOut);
      if (p1 > 0) it.push({ kind: 'img', part: 'line1', lit: br * 0.95, clip: wipe('line1', p1) });
      if (p2 > 0) it.push({ kind: 'img', part: 'line2', lit: br * 0.95, clip: wipe('line2', p2) });
      it.gain = 1 + 0.8 * bump(u, T.swell, 2.6);
      return it;
    };
    return {
      start, dur, items, humGain: 0.5,
      audio: u => ({ rain: (0.12 + 0.1 * prog(u, 0.8, 1.5)) * (1 - prog(u, 3.5, 3.0)) }),
      render(u) {
        const z = 1 + 0.04 * prog(u, 1.0, dur - 1, E.sine);
        const m = logoM(z), it = items(u);
        drawWorld(MAIN, m, { items: it, emPx: 330 * mScale(m), glowGain: 0.7 });
        // étincelle qui trace l'arche
        const ap = prog(u, T.arch, T.archD, E.inOut);
        if (ap > 0 && ap < 1) {
          applyM(ctx, m); ctx.globalCompositeOperation = 'lighter';
          for (const [px, py] of tip(ap)) {
            const g = ctx.createRadialGradient(px, py, 0, px, py, 40);
            g.addColorStop(0, 'rgba(200,208,224,0.9)'); g.addColorStop(0.12, 'rgba(70,100,170,0.45)'); g.addColorStop(1, 'rgba(0,0,0,0)');
            ctx.fillStyle = g; ctx.fillRect(px - 40, py - 40, 80, 80);
          }
          reset(ctx);
        }
        const rp = 1 - prog(u, 3.5, 3.0);
        if (rp > 0) drawRain(u, { seed: 991, n: Math.round(260 * rp), speed: 1.6, len: 0.06, alpha: 0.1 * rp, slant: 0.08, lights: [[W / 2, H / 2, 25 * U, 1.5]] });
        drawFog(u, { alpha: 0.035, speed: 0.4, scale: 1.8 });
        // la phrase
        const a = prog(u, T.txtIn, 1.4, E.out) * (1 - prog(u, T.txtOut, 0.9, E.in));
        if (a > 0) {
          const [tx, ty] = toScreen(m, 768, LAND ? 790 : 800);
          reset(ctx);
          ctx.font = `italic 400 ${(LAND ? 3.7 : 4.6) * U}px "Bodoni Moda", serif`;
          ctx.textAlign = 'center'; ctx.textBaseline = 'alphabetic';
          ctx.filter = a < 1 ? `blur(${((1 - a) * 0.6 * U).toFixed(2)}px)` : 'none';
          ctx.fillStyle = rgb([150, 158, 175], a);
          if (LAND) ctx.fillText('Dans toutes les langues, la nuit s’écrit N+8.', tx, ty);
          else { ctx.fillText('Dans toutes les langues,', tx, ty); ctx.fillText('la nuit s’écrit N+8.', tx, ty + 6.4 * U); }
          reset(ctx);
        }
      },
    };
  }

  /* =========================================================
   * Rendu
   * ======================================================= */
  let last = null;
  function renderAt(t) {
    t = clamp(t, 0, DURATION - 1e-6);
    let s = SCENES[SCENES.length - 1];
    for (const sc of SCENES) if (t >= sc.start && t < sc.start + sc.dur) { s = sc; break; }
    s.render(t - s.start);
    finish(t);
    last = t;
  }
  function audioEnv(rate = 50) {
    const keys = ['rain', 'muffle', 'drops', 'water', 'wind', 'city'];
    const out = { rate, hum: [] };
    keys.forEach(k => (out[k] = []));
    for (let i = 0; i <= Math.ceil(DURATION * rate); i++) {
      const t = i / rate;
      let s = SCENES[SCENES.length - 1];
      for (const sc of SCENES) if (t >= sc.start && t < sc.start + sc.dur) { s = sc; break; }
      const u = t - s.start, a = s.audio ? s.audio(u) : {};
      keys.forEach(k => out[k].push(+(a[k] || 0).toFixed(3)));
      const it = s.items(u);
      const p = it.reduce((acc, g) => acc + clamp(g.lit), 0) * (it.gain || 1);
      out.hum.push(+(Math.min(3, p) / 3 * s.humGain).toFixed(3));
    }
    return out;
  }

  async function loadImage(src) {
    const img = new Image();
    img.src = src;
    await img.decode();
    return img;
  }
  async function init() {
    W = innerWidth; H = innerHeight; U = Math.min(W, H) / 100; LAND = W >= H;
    cv.width = W; cv.height = H;
    await Promise.all([
      document.fonts.load(`500 ${REF}px "Bodoni Moda"`, 'N+8 nuit noche'),
      document.fonts.load(`italic 400 40px "Bodoni Moda"`, 'Dans toutes les langues'),
      document.fonts.load(`400 ${REF}px "GFS Didot"`, 'Ννύχτα οκτώ'),
    ]);
    await document.fonts.ready;
    LOGO.meta = await (await fetch('logo/parts.json')).json().catch(() => null);
    if (!LOGO.meta) throw new Error('logo/parts.json introuvable');
    for (const name of Object.keys(LOGO.meta.parts)) {
      const img = await loadImage(`logo/${name}.png`);
      LOGO.parts[name] = img;
      const p = LOGO.meta.parts[name], c = mk(p.w, p.h), x = c.getContext('2d');
      x.drawImage(img, 0, 0);
      x.globalCompositeOperation = 'source-in';
      const g = x.createLinearGradient(0, 0, 0, p.h);
      g.addColorStop(0, rgb(COL.logoTop)); g.addColorStop(1, rgb(COL.logoBot));
      x.fillStyle = g; x.fillRect(0, 0, p.w, p.h);
      LOGO.lit[name] = c;
    }
    layer('g4', W / 4, H / 4); layer('g4b', W / 4, H / 4); layer('g8', W / 8, H / 8, true);
    layer('lm', W / 2, H / 2); layer('refl', W, H); layer('tmp', W, H); layer('drop', W, H);
    buildTextures(); buildDrops(); buildFilm();
    renderAt(0);
  }

  window.N8 = {
    renderAt,
    get duration() { return DURATION; },
    get events() { return EV; },
    audioEnv,
    get scenes() { return SCENES.map(s => ({ start: s.start, dur: s.dur })); },
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
