/*
 * N+8 — « Nuits » (images réelles) : calque des titres, rendu image par image en transparence.
 * Noms des villes, la nuit qui s'écrit (N + huit → nuit), notes olfactives, mots des villes,
 * puis la finale opaque : toutes les nuits → N+8 → logo doré.
 * La chronologie est lue dans footage/edl.json (tempo et plans).
 */
(() => {
  'use strict';
  const RENDER = new URLSearchParams(location.search).has('render');
  const cv = document.getElementById('film');
  const ctx = cv.getContext('2d');
  let W = 0, H = 0, U = 1, LAND = true, VX = 88.9, VY = 37.2;

  const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
  const lerp = (a, b, p) => a + (b - a) * p;
  const E = {
    out: p => 1 - Math.pow(1 - p, 3),
    in: p => p * p * p,
    inOut: p => (p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2),
  };
  const prog = (t, s, d, e = p => p) => e(clamp((t - s) / d));
  const mixC = (a, b, p) => [lerp(a[0], b[0], p), lerp(a[1], b[1], p), lerp(a[2], b[2], p)];
  const rgb = (c, a = 1) => `rgba(${c[0] | 0},${c[1] | 0},${c[2] | 0},${clamp(a).toFixed(4)})`;
  const C = { gold: [214, 174, 104], goldHi: [250, 230, 186], white: [240, 238, 232], gray: [150, 150, 154] };
  const F = { serif: '"Bodoni Moda", "GFS Didot", serif', sans: '"Montserrat", sans-serif', arabic: '"Amiri", serif' };
  const mk = (w, h) => { const c = document.createElement('canvas'); c.width = Math.max(1, Math.round(w)); c.height = Math.max(1, Math.round(h)); return c; };
  function reset(x) {
    x.setTransform(1, 0, 0, 1, 0, 0);
    x.globalAlpha = 1; x.globalCompositeOperation = 'source-over'; x.filter = 'none';
    x.shadowBlur = 0; x.shadowColor = 'rgba(0,0,0,0)';
  }
  const SX = v => W / 2 + v * U, SY = v => H / 2 + v * U;

  function tracked(x, str, cx, cy, sizePx, track, font, fill) {
    x.font = font; x.textAlign = 'left'; x.textBaseline = 'alphabetic'; x.fillStyle = fill;
    const chars = [...str], ws = chars.map(ch => x.measureText(ch).width);
    const tot = ws.reduce((a, b) => a + b, 0) + track * sizePx * (chars.length - 1);
    let px = cx - tot / 2;
    chars.forEach((ch, i) => { x.fillText(ch, px, cy); px += ws[i] + track * sizePx; });
  }
  // ombre portée douce sous le texte, pour rester lisible sur l'image
  function shade(cx, cy, rx, ry, a) {
    if (a <= 0.003) return;
    ctx.save(); ctx.translate(cx, cy); ctx.scale(rx / ry, 1);
    const g = ctx.createRadialGradient(0, 0, 0, 0, 0, ry);
    g.addColorStop(0, `rgba(0,0,0,${(0.55 * a).toFixed(3)})`); g.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.fillStyle = g; ctx.fillRect(-ry, -ry, 2 * ry, 2 * ry);
    ctx.restore();
  }
  function caption(u, d, str) {
    const a = prog(u, 0.08, 0.2, E.out) * (1 - prog(u, d - 0.12, 0.12));
    if (a <= 0) return;
    reset(ctx);
    const size = (LAND ? 2.5 : 3.4) * U;
    const px = LAND ? SX(-VX + 10) : W / 2, py = LAND ? SY(VY - 7) : SY(VY - 18);
    ctx.font = `italic 400 ${size}px ${F.serif}`;
    const tw = ctx.measureText(str).width, dash = 3.2 * U;
    const x0 = LAND ? px : px - (tw + dash + 1.2 * U) / 2;
    shade(x0 + (tw + dash) / 2, py - size * 0.3, tw + 8 * U, 5 * U, a);
    ctx.fillStyle = rgb(C.gold, 0.9 * a); ctx.fillRect(x0, py - size * 0.32, dash, Math.max(1, 0.12 * U));
    ctx.fillStyle = rgb(C.white, 0.9 * a); ctx.textAlign = 'left';
    ctx.fillText(str, x0 + dash + 1.2 * U, py);
    reset(ctx);
  }
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
  function cityCard(u, o) {
    const out = 1 - prog(u, o.end - 0.3, 0.3, E.in);
    if (out <= 0) return;
    reset(ctx);
    const ax = LAND ? SX(-VX * 0.5) : W / 2, ay = LAND ? SY(-3) : SY(VY * 0.38);
    const aName = prog(u, 0.05, 0.4, E.out) * out, aCo = prog(u, 0.2, 0.4, E.out) * out;
    shade(ax, ay + 7 * U, 34 * U, 20 * U, aName * 1.1);
    tracked(ctx, o.name, ax, ay, 2.3 * U, 0.62, `300 ${2.3 * U}px ${F.sans}`, rgb(C.goldHi, aName));
    tracked(ctx, o.coords, ax, ay + 3.6 * U, 1.35 * U, 0.35, `300 ${1.35 * U}px ${F.sans}`, rgb(C.white, aCo * 0.75));
    ctx.fillStyle = rgb(C.gold, aCo * 0.7); ctx.fillRect(ax - 3 * U, ay + 5.6 * U, 6 * U, Math.max(1, 0.1 * U));
    const fy = ay + 14 * U, size = (LAND ? 7.5 : 9) * U;
    if (o.arabic) {
      const a = prog(u, 0.45, 0.5, E.out) * out;
      ctx.font = `400 ${size * 1.25}px ${F.arabic}`; ctx.textAlign = 'center'; ctx.direction = 'rtl';
      ctx.shadowColor = rgb(C.gold, 0.5 * a); ctx.shadowBlur = 1.6 * U;
      ctx.fillStyle = rgb(C.gold, a); ctx.fillText(o.arabic, ax, fy + 1.5 * U);
      ctx.direction = 'ltr';
      reset(ctx);
      return;
    }
    const f = o.formula, N = 'N', eight = [...f.eight], night = [...f.night];
    const r1 = rowX([N, '+', ...eight]), r2 = rowX(night);
    const aIn = prog(u, 0.4, 0.3, E.out) * out, pS = prog(u, 0.95, 0.45, E.inOut), pSw = prog(u, 1.15, 0.25, E.inOut);
    const pOff = prog(u, 0.85, 0.25, E.out);
    ctx.font = `400 ${size}px ${F.serif}`; ctx.textAlign = 'center'; ctx.textBaseline = 'alphabetic';
    ctx.shadowColor = rgb(C.gold, 0.45 * aIn); ctx.shadowBlur = 1.4 * U;
    const put = (ch, xEm, a, col = C.gold) => { if (a <= 0.003) return; ctx.fillStyle = rgb(col, a); ctx.fillText(ch, ax + xEm * size, fy); };
    const jN = f.map.indexOf(0), xN = lerp(r1[0], r2[jN], pS);
    if (N === night[jN]) put(N, xN, aIn, C.goldHi);
    else { put(N, xN, aIn * (1 - pSw), C.goldHi); put(night[jN], xN, aIn * pSw, C.goldHi); }
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
  function phrase(u, d, str, fadeOut) {
    const a = prog(u, 0.2, 0.5, E.out) * (fadeOut ? 1 - prog(u, d - 0.35, 0.35, E.in) : 1);
    if (a <= 0) return;
    reset(ctx);
    const size = (LAND ? 3.2 : 4.4) * U, y = SY(LAND ? 25 : 40);
    shade(W / 2, y - size * 0.3, 60 * U, 6 * U, a);
    ctx.font = `italic 400 ${size}px ${F.serif}`; ctx.textAlign = 'center';
    ctx.fillStyle = rgb(C.white, 0.92 * a);
    ctx.fillText(str, W / 2, y);
    reset(ctx);
  }
  function cityWord(u, d, city, word) {
    const a = prog(u, 0, 0.06);
    reset(ctx);
    const size = (LAND ? 11 : 15) * U;
    shade(W / 2, H / 2 - size * 0.1, size * 3, size * 0.9, a);
    ctx.font = `400 ${size}px ${F.serif}`; ctx.textAlign = 'left'; ctx.textBaseline = 'alphabetic';
    const first = [...word][0], rest = [...word].slice(1).join('');
    const w1 = ctx.measureText(first).width, w2 = ctx.measureText(rest).width;
    const x0 = W / 2 - (w1 + w2) / 2, y0 = H / 2 + size * 0.3;
    ctx.shadowColor = rgb(C.gold, 0.6 * a); ctx.shadowBlur = 1.6 * U;
    ctx.fillStyle = rgb(C.goldHi, a); ctx.fillText(first, x0, y0);
    ctx.shadowBlur = 0;
    ctx.fillStyle = rgb(C.white, 0.92 * a); ctx.fillText(rest, x0 + w1, y0);
    tracked(ctx, city, W / 2, H / 2 - size * 0.75, 1.8 * U, 0.6, `300 ${1.8 * U}px ${F.sans}`, rgb(C.gold, 0.9 * a));
    reset(ctx);
  }

  // ---- finale opaque : toutes les nuits → N → N+8 → logo doré
  const LOGO = { meta: null, gold: {} };
  const NIGHTS = ['nuit', 'notte', 'night', 'noche', 'Nacht', 'noite', 'natt', 'νύχτα'];
  function logoM() {
    const s = LAND ? (W / 2.39) * 0.82 / 703 : W * 0.86 / 712;
    return { s, ox: W / 2 - s * 768, oy: H / 2 - s * (LAND ? 497 : 520) };
  }
  function finale(u, d) {
    reset(ctx);
    ctx.fillStyle = '#020202'; ctx.fillRect(0, 0, W, H);
    const M = logoM(), parts = LOGO.meta.parts;
    const toS = (x, y) => [M.ox + x * M.s, M.oy + y * M.s];
    const pc = n => [parts[n].x + parts[n].w / 2, parts[n].y + parts[n].h / 2];
    const lineA = prog(u, 0.3, 0.45, E.out), restOff = prog(u, 1.15, 0.5, E.inOut), gather = prog(u, 1.35, 0.8, E.inOut);
    const size = (LAND ? 4.4 : 5.2) * U;
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
        if (lineA * (1 - restOff) > 0.003) { ctx.fillStyle = rgb(C.white, 0.78 * lineA * (1 - restOff)); ctx.fillText(rest, x0 + w1, y0); }
        const fx = lerp(x0, nTarget[0] - w1 / 2, gather), fy = lerp(y0, nTarget[1], gather);
        const nA = lineA * (1 - prog(u, 2.15, 0.3)) * (gather > 0.98 && k + ri > 0 ? 0 : 1);
        if (nA > 0.003) { ctx.fillStyle = rgb(C.goldHi, nA); ctx.fillText(first, fx, fy); }
        x0 += ws[k] + gap;
      });
    });
    const pA = prog(u, 1.6, 0.5, E.out) * (1 - prog(u, 3.5, 0.5, E.in));
    if (pA > 0) {
      ctx.font = `italic 400 ${(LAND ? 2.6 : 3.4) * U}px ${F.serif}`; ctx.textAlign = 'center';
      ctx.fillStyle = rgb(C.gray, pA);
      ctx.fillText('Dans toutes les langues, la nuit s’écrit N+8.', W / 2, toS(0, 905)[1]);
    }
    const logoA = prog(u, 2.1, 0.45, E.out), arch = prog(u, 2.45, 1.2, E.inOut);
    const l1 = prog(u, 3.4, 0.8, E.inOut), l2 = prog(u, 3.7, 0.8, E.inOut);
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
    drawPart('n', logoA); drawPart('plus', prog(u, 2.25, 0.35, E.out)); drawPart('eight', prog(u, 2.35, 0.4, E.out));
    const CX = 767.5, CY = 456, R = 310, SIDE = 246, HALF = SIDE + Math.PI / 2 * R;
    drawPart('arch', arch > 0 ? 1 : 0, x => {
      const dd = arch * HALF, hh = Math.min(dd, SIDE + 4);
      x.rect(440, 712 - hh, 60, hh); x.rect(1036, 712 - hh, 60, hh);
      if (dd > SIDE) { const a = Math.min(Math.PI / 2, (dd - SIDE) / R); x.moveTo(CX, CY); x.arc(CX, CY, R + 40, Math.PI, Math.PI + a); x.closePath(); x.moveTo(CX, CY); x.arc(CX, CY, R + 40, -a, 0); x.closePath(); }
    });
    const wipe = p => (x, q) => { const cx = q.x + q.w / 2, hw = (q.w / 2 + 10) * p; x.rect(cx - hw, q.y - 5, 2 * hw, q.h + 10); };
    drawPart('line1', l1 > 0 ? 1 : 0, wipe(l1));
    drawPart('line2', l2 > 0 ? 1 : 0, wipe(l2));
    reset(ctx);
    const fade = prog(u, d - 1.3, 1.3, E.inOut);
    if (fade > 0) { ctx.fillStyle = `rgba(0,0,0,${fade.toFixed(4)})`; ctx.fillRect(0, 0, W, H); }
  }

  // ---- chronologie (depuis footage/edl.json)
  let EDL = null, SHOTS = [], SECTIONS = [], EV = [], DURATION = 0, BEAT = 0.5;
  function build() {
    BEAT = 60 / EDL.bpm;
    let t = 0;
    SHOTS = []; SECTIONS = []; EV = [];
    for (const sec of EDL.sections) {
      const s0 = t;
      for (const sh of sec.shots) {
        const d = sh.beats * BEAT;
        SHOTS.push({ ...sh, section: sec.name, start: t, dur: d });
        for (const fx of sh.sfx || []) {
          const add = (dt, extra = {}) => EV.push({ type: fx, t: +(t + dt).toFixed(3), shot: sh.id, ...extra });
          if (fx === 'pour' || fx === 'coals') add(0, { dur: d });
          else if (fx === 'ice') add(d * 0.35);
          else if (fx === 'drop') add(d * 0.45);
          else if (fx === 'steps') for (let k = 0; k < 4; k++) EV.push({ type: 'step', t: +(t + 0.08 + k * d / 4).toFixed(3) });
          else if (fx === 'chain') { add(0.2); add(0.85); }
          else if (fx === 'reveal') add(1.35);
          else if (fx === 'logo') add(2.1);
          else if (fx === 'strike') add(0.15);
          else if (fx === 'puff' || fx === 'clink') add(0.3);
          else add(0.04);
        }
        t += d;
      }
      SECTIONS.push({ name: sec.name, start: s0, end: t });
    }
    DURATION = t;
  }
  function renderAt(t) {
    t = clamp(t, 0, DURATION - 1e-6);
    reset(ctx); ctx.clearRect(0, 0, W, H);
    const s = SHOTS.find(sh => t >= sh.start && t < sh.start + sh.dur) || SHOTS[SHOTS.length - 1];
    const u = t - s.start;
    if (s.render === 'finale') { finale(u, s.dur); return; }
    if (s.phrase) {
      // la phrase court sur plusieurs plans consécutifs
      const first = SHOTS.find(sh => sh.phrase === s.phrase);
      const lastIdx = SHOTS.map(sh => sh.phrase).lastIndexOf(s.phrase);
      const span = SHOTS[lastIdx].start + SHOTS[lastIdx].dur - first.start;
      phrase(t - first.start, span, s.phrase, true);
    }
    if (s.card) cityCard(u, { ...s.card, end: s.dur });
    if (s.caption) caption(u, s.dur, s.caption);
    if (s.word) cityWord(u, s.dur, s.city, s.word);
    // ouverture au noir et éclat doré à l'entrée de chaque ville
    reset(ctx);
    if (s.card && u < 0.45) {
      const k = Math.sin(Math.PI * clamp(u / 0.45));
      const g = ctx.createRadialGradient(W * (0.2 + u), H * 0.3, 0, W * (0.2 + u), H * 0.3, W * 0.7);
      g.addColorStop(0, rgb([255, 214, 150], 0.18 * k)); g.addColorStop(1, rgb([255, 214, 150], 0));
      ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
    }
    const veil = 1 - prog(t, 0, 0.6, E.out);
    if (veil > 0) { ctx.fillStyle = `rgba(0,0,0,${veil.toFixed(4)})`; ctx.fillRect(0, 0, W, H); }
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
    EDL = await (await fetch('../footage/edl.json')).json();
    LOGO.meta = await (await fetch('logo/parts.json')).json();
    for (const name of Object.keys(LOGO.meta.parts)) {
      const img = await loadImage(`logo/${name}.png`);
      const p = LOGO.meta.parts[name], c = mk(p.w, p.h), x = c.getContext('2d');
      x.drawImage(img, 0, 0);
      x.globalCompositeOperation = 'source-in';
      const g = x.createLinearGradient(0, 0, 0, p.h);
      g.addColorStop(0, rgb([246, 222, 160])); g.addColorStop(0.5, rgb([212, 170, 96])); g.addColorStop(1, rgb([160, 116, 52]));
      x.fillStyle = g; x.fillRect(0, 0, p.w, p.h);
      LOGO.gold[name] = c;
    }
    build();
    renderAt(0);
  }

  window.N8 = {
    renderAt,
    get duration() { return DURATION; },
    get events() { return EV; },
    get scenes() { return SHOTS.map(s => ({ id: s.id, section: s.section, start: +s.start.toFixed(3), dur: +s.dur.toFixed(3) })); },
    get music() { return { bpm: EDL.bpm, sections: SECTIONS.map(s => ({ ...s })) }; },
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
