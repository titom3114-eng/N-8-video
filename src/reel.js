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
  // titrage : "font": "cinzel" dans le montage → capitales romaines gravées (Cinzel), plus marquantes ; grec en Noto Serif Display
  let DISPLAY = false, TW = 400;
  const caps = str => {
    if (!DISPLAY) return str;
    const up = str.toUpperCase();
    return /[\u0370-\u03ff]/.test(up) ? up.normalize('NFD').replace(/[\u0300-\u036f]/g, '').normalize('NFC') : up;   // grec : capitales sans accents
  };
  const titleFont = (size, w) => (DISPLAY ? `${w ?? TW} ${size}px ${F.title}` : `${w ?? 400} ${size}px ${F.serif}`);
  // or dégradé (clair en haut, profond en bas) pour les grands mots en mode titrage
  function goldFill(y0, y1) {
    const g = ctx.createLinearGradient(0, y0, 0, y1);
    g.addColorStop(0, '#FBEBC0'); g.addColorStop(0.5, '#E0BC72'); g.addColorStop(1, '#B4843A');
    return g;
  }
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
  // mode « lisible » (montage avec "text": "lisible") : textes plus grands, affichés plus longtemps, détachés de l'image
  let BIG = false;
  const big = (a, b) => (BIG ? b : a);
  // ombre portée sombre sous le texte : il se détache même sur une image claire (tour illuminée, lumières de la ville)
  function darkShadow(on = BIG) {
    if (!on) return;
    ctx.shadowColor = 'rgba(0,0,0,0.92)'; ctx.shadowBlur = 1.3 * U; ctx.shadowOffsetX = 0; ctx.shadowOffsetY = 0.18 * U;
  }
  function noShadow() { ctx.shadowColor = 'rgba(0,0,0,0)'; ctx.shadowBlur = 0; ctx.shadowOffsetY = 0; }
  const fitFont = (str, font, size, maxW) => { ctx.font = font(size); const w = ctx.measureText(str).width; return w > maxW ? size * maxW / w : size; };
  function shade(cx, cy, rx, ry, a) {
    if (a <= 0.003) return;
    ctx.save(); ctx.translate(cx, cy); ctx.scale(rx / ry, 1);
    const g = ctx.createRadialGradient(0, 0, 0, 0, 0, ry);
    g.addColorStop(0, `rgba(0,0,0,${(big(0.55, 0.7) * a).toFixed(3)})`); g.addColorStop(1, 'rgba(0,0,0,0)');
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
    if (!advCache.has(ch)) { ctx.font = titleFont(48, DISPLAY ? TW : 400); advCache.set(ch, ctx.measureText(ch).width / 48); }
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
    const ax = LAND ? SX(-VX * 0.5) : W / 2, ay = LAND ? SY(big(-3, -9)) : SY(VY * big(0.38, 0.2));
    const aName = prog(u, 0.05, big(0.4, 0.3), E.out) * out, aCo = prog(u, big(0.2, 0.15), 0.4, E.out) * out;
    const nS = big(2.3, LAND ? 3.4 : 4.4) * U, cS = big(1.35, LAND ? 1.9 : 2.4) * U, k = BIG ? nS / (2.3 * U) : 1;
    if (BIG) {
      const va = 0.5 * prog(u, 0, 0.35, E.out) * out;
      const g = LAND ? ctx.createLinearGradient(0, 0, 0.62 * W, 0) : ctx.createLinearGradient(0, ay - 18 * U, 0, ay + 44 * U);
      g.addColorStop(0, `rgba(0,0,0,${LAND ? va : 0})`);
      if (!LAND) { g.addColorStop(0.25, `rgba(0,0,0,${va})`); g.addColorStop(0.8, `rgba(0,0,0,${va})`); }
      g.addColorStop(1, 'rgba(0,0,0,0)');
      ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
    }
    shade(ax, ay + big(7, 11) * U, big(34, LAND ? 48 : 56) * U, big(20, 30) * U, aName * big(1.1, 1.35));
    darkShadow();
    tracked(ctx, o.name, ax, ay, nS, DISPLAY ? 0.42 : 0.62, DISPLAY ? `700 ${nS * 1.1}px ${F.title}` : `${big(300, 400)} ${nS}px ${F.sans}`, rgb(C.goldHi, aName));
    tracked(ctx, o.coords, ax, ay + 3.6 * U * k, cS, 0.35, `${big(300, 400)} ${cS}px ${F.sans}`, rgb(C.white, aCo * big(0.75, 0.9)));
    noShadow();
    ctx.fillStyle = rgb(C.gold, aCo * 0.7); ctx.fillRect(ax - 3 * U * k, ay + 5.6 * U * k, 6 * U * k, Math.max(1, 0.1 * U * k));
    const fy = ay + big(15, LAND ? 22 : 26) * U;
    let size = big(LAND ? 9 : 11, LAND ? 13.5 : 18) * U;
    if (o.arabic) {
      const a = prog(u, big(0.45, 0.3), 0.5, E.out) * out;
      ctx.font = `${DISPLAY ? 700 : 400} ${size * 1.25}px ${F.arabic}`; ctx.textAlign = 'center'; ctx.direction = 'rtl';
      if (BIG) { darkShadow(); ctx.fillStyle = rgb(C.gold, a); ctx.fillText(o.arabic, ax, fy + 1.5 * U); }
      ctx.shadowColor = rgb(C.gold, 0.5 * a); ctx.shadowBlur = 1.6 * U; ctx.shadowOffsetY = 0;
      ctx.fillStyle = rgb(C.gold, a); ctx.fillText(o.arabic, ax, fy + 1.5 * U);
      ctx.direction = 'ltr';
      reset(ctx);
      return;
    }
    const f = o.formula, N = 'N', eight = [...caps(f.eight)], night = [...caps(f.night)];
    const r1 = rowX([N, '+', ...eight]), r2 = rowX(night);
    if (BIG) {   // la formule tient toujours dans sa moitié d'écran (paysage) ou dans la largeur (vertical)
      const span = Math.max(r1[r1.length - 1] - r1[0], r2[r2.length - 1] - r2[0]) + 0.8;
      size = Math.min(size, (LAND ? 0.46 : 0.86) * W / span);
    }
    // N + huit, puis les lettres glissent : nuit (plus lent en mode lisible, pour que l'idée se lise)
    const T = BIG ? { a: 0.25, s: 1.5, sd: 0.7, w: 1.75, wd: 0.4, o: 1.35 } : { a: 0.35, s: 1.15, sd: 0.6, w: 1.4, wd: 0.35, o: 1.0 };
    const aIn = prog(u, T.a, 0.3, E.out) * out, pS = prog(u, T.s, T.sd, E.inOut), pSw = prog(u, T.w, T.wd, E.inOut);
    const pOff = prog(u, T.o, 0.3, E.out);
    ctx.font = titleFont(size, DISPLAY ? TW : big(400, 500)); ctx.textAlign = 'center'; ctx.textBaseline = 'alphabetic';
    const gf = DISPLAY ? goldFill(fy - 0.72 * size, fy) : null;
    let shadowPass = false;
    const letters = () => {
      const put = (ch, xEm, a, col = C.gold) => {
        if (a <= 0.003) return;
        if (gf && !shadowPass && (col === C.gold || col === C.goldHi)) { ctx.globalAlpha = a; ctx.fillStyle = gf; ctx.fillText(ch, ax + xEm * size, fy); ctx.globalAlpha = 1; return; }
        ctx.fillStyle = rgb(col, a); ctx.fillText(ch, ax + xEm * size, fy);
      };
      const jN = f.map.indexOf(0), xN = lerp(r1[0], r2[jN], pS);
      if (N === night[jN]) put(N, xN, aIn, C.goldHi);
      else { put(N, xN, aIn * (1 - pSw), C.goldHi); put(night[jN], xN, aIn * pSw, C.goldHi); }
      const pa = aIn * (1 - pOff);
      if (pa > 0) {   // en capitales grasses (Cinzel) : un « + » plus épais, centré sur la hauteur des capitales
        ctx.fillStyle = rgb(C.gold, pa);
        const px = ax + r1[1] * size, py = fy - (DISPLAY ? 0.34 : 0.27) * size, h = (DISPLAY ? 0.15 : 0.13) * size;
        const lw = Math.max(1, (DISPLAY ? 0.055 : big(0.02, 0.028)) * size);
        ctx.fillRect(px - h, py - lw / 2, 2 * h, lw); ctx.fillRect(px - lw / 2, py - h, lw, 2 * h);
      }
      eight.forEach((ch, kk) => {
        const j = f.map.indexOf(kk + 1);
        if (j < 0) { put(ch, r1[kk + 2], aIn * (1 - pOff), C.white); return; }
        const x = lerp(r1[kk + 2], r2[j], pS), col = mixC(C.white, C.gold, pS);
        if (ch === night[j]) put(ch, x, aIn, col);
        else { put(ch, x, aIn * (1 - pSw), col); put(night[j], x, aIn * pSw, col); }
      });
      f.map.forEach((m, j) => { if (m === -1) put(night[j], r2[j], aIn * pSw, C.gold); });
    };
    if (BIG) { darkShadow(); shadowPass = true; letters(); shadowPass = false; }
    ctx.shadowColor = rgb(C.gold, 0.45 * aIn); ctx.shadowBlur = 1.4 * U; ctx.shadowOffsetY = 0;
    letters();
    reset(ctx);
  }
  function phrase(u, d, str, fadeOut) {
    const a = prog(u, big(0.2, 0.1), big(0.5, 0.35), E.out) * (fadeOut ? 1 - prog(u, d - 0.35, 0.35, E.in) : 1);
    if (a <= 0) return;
    reset(ctx);
    str = caps(str);
    const font = sz => (DISPLAY ? `600 ${sz}px ${F.title}` : `italic ${big(400, 500)} ${sz}px ${F.serif}`);
    const size = BIG ? fitFont(str, font, (LAND ? (DISPLAY ? 5.6 : 6.4) : (DISPLAY ? 6.6 : 7.6)) * U, 0.9 * W) : (LAND ? 3.7 : 5.0) * U;
    const y = SY(LAND ? big(25, 24) : big(40, 30));
    shade(W / 2, y - size * 0.3, big(60, 80) * U, big(6, 9) * U, a);
    ctx.font = font(size); ctx.textAlign = 'center';
    darkShadow();
    ctx.fillStyle = DISPLAY ? rgb([246, 236, 214], a) : rgb(C.white, big(0.92, 0.97) * a);
    ctx.fillText(str, W / 2, y);
    reset(ctx);
  }
  function cityWord(u, d, city, word) {
    const a = prog(u, 0, 0.06);
    reset(ctx);
    word = caps(word);
    const font = sz => titleFont(sz, DISPLAY ? TW : big(400, 500));
    const size = BIG ? fitFont(word, font, (LAND ? 16 : 22) * U, (LAND ? 0.62 : 0.86) * W) : (LAND ? 11 : 15) * U;
    shade(W / 2, H / 2 - size * 0.1, size * big(3, 3.6), size * big(0.9, 1.15), a * big(1, 1.3));
    ctx.font = font(size); ctx.textAlign = 'left'; ctx.textBaseline = 'alphabetic';
    const first = [...word][0], rest = [...word].slice(1).join('');
    const w1 = ctx.measureText(first).width, w2 = ctx.measureText(rest).width;
    const x0 = W / 2 - (w1 + w2) / 2, y0 = H / 2 + size * 0.3;
    if (BIG) { darkShadow(); ctx.fillStyle = rgb(C.goldHi, a); ctx.fillText(first, x0, y0); ctx.fillStyle = rgb(C.white, a); ctx.fillText(rest, x0 + w1, y0); noShadow(); }
    ctx.shadowColor = rgb(C.gold, 0.6 * a); ctx.shadowBlur = 1.6 * U;
    if (DISPLAY) {   // le mot entier en or dégradé
      ctx.globalAlpha = a; ctx.fillStyle = goldFill(y0 - 0.72 * size, y0);
      ctx.fillText(first, x0, y0); ctx.shadowBlur = 0; ctx.fillText(rest, x0 + w1, y0); ctx.globalAlpha = 1;
    } else {
      ctx.fillStyle = rgb(C.goldHi, a); ctx.fillText(first, x0, y0);
      ctx.shadowBlur = 0;
      ctx.fillStyle = rgb(C.white, big(0.92, 1) * a); ctx.fillText(rest, x0 + w1, y0);
    }
    const cS = big(1.8, LAND ? 2.8 : 3.6) * U;
    darkShadow();
    tracked(ctx, city, W / 2, H / 2 - size * big(0.75, 0.8), cS, DISPLAY ? 0.45 : 0.6, DISPLAY ? `700 ${cS * 1.05}px ${F.title}` : `${big(300, 400)} ${cS}px ${F.sans}`, rgb(C.gold, big(0.9, 1) * a));
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
    const nights = NIGHTS.map(caps);
    const rows = LAND ? [nights] : [nights.slice(0, 4), nights.slice(4)];
    let size = big(LAND ? 4.4 : 5.2, LAND ? 5.8 : 7.2) * U;
    const rowFont = sz => (DISPLAY ? `600 ${sz}px ${F.title}` : `italic ${big(400, 500)} ${sz}px ${F.serif}`);
    if (BIG) size = fitFont(rows[0].join('   '), rowFont, size, 0.9 * W);
    ctx.font = rowFont(size); ctx.textBaseline = 'alphabetic'; ctx.textAlign = 'left';
    const [nx, ny] = toS(...pc('n'));
    const nTarget = [nx, ny + 0.36 * parts.n.h * M.s];
    rows.forEach((row, ri) => {
      const ws = row.map(wd => ctx.measureText(wd).width), gap = 2.4 * U;
      const tot = ws.reduce((a, b) => a + b, 0) + gap * (row.length - 1);
      let x0 = W / 2 - tot / 2;
      const y0 = (LAND ? H / 2 : H / 2 - big(4, 5.5) * U + ri * big(8, 11) * U) + size * 0.3;
      row.forEach((wd, k) => {
        const first = [...wd][0], rest = [...wd].slice(1).join('');
        const w1 = ctx.measureText(first).width;
        if (lineA * (1 - restOff) > 0.003) { ctx.fillStyle = rgb(C.white, big(0.78, 0.92) * lineA * (1 - restOff)); ctx.fillText(rest, x0 + w1, y0); }
        const fx = lerp(x0, nTarget[0] - w1 / 2, gather), fy = lerp(y0, nTarget[1], gather);
        const nA = lineA * (1 - prog(u, 2.15, 0.3)) * (gather > 0.98 && k + ri > 0 ? 0 : 1);
        if (nA > 0.003) { ctx.fillStyle = rgb(C.goldHi, nA); ctx.fillText(first, fx, fy); }
        x0 += ws[k] + gap;
      });
    });
    const pA = prog(u, 1.6, 0.5, E.out) * (1 - prog(u, 5.0, 0.5, E.in));
    if (pA > 0 && !BIG) {
      ctx.font = `italic 400 ${(LAND ? 3.0 : 3.8) * U}px ${F.serif}`; ctx.textAlign = 'center';
      ctx.fillStyle = rgb(C.white, 0.8 * pA);
      ctx.fillText('Dans toutes les langues, la nuit s’écrit N+8.', W / 2, toS(0, 905)[1]);
    }
    if (pA > 0 && BIG) {   // plus grande ; en vertical, sur deux lignes sous le logo
      const font = sz => (DISPLAY ? `600 ${sz}px ${F.title}` : `italic 500 ${sz}px ${F.serif}`);
      ctx.textAlign = 'center'; ctx.fillStyle = DISPLAY ? rgb([246, 236, 214], 0.95 * pA) : rgb(C.white, 0.95 * pA);
      const l1 = caps('Dans toutes les langues,'), l2 = caps('la nuit s’écrit N+8.');
      if (LAND) {
        const str = `${l1} ${l2}`;
        ctx.font = font(fitFont(str, font, (DISPLAY ? 4.0 : 4.5) * U, 0.88 * W)); ctx.fillText(str, W / 2, toS(0, 905)[1]);
      } else {
        const sz = fitFont(l1, font, (DISPLAY ? 5.2 : 5.6) * U, 0.86 * W), y = toS(0, 960)[1];
        ctx.font = font(sz); ctx.fillText(l1, W / 2, y); ctx.fillText(l2, W / 2, y + sz * 1.35);
      }
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
    // l'arche se trace des pieds vers le sommet ; les montants recouvrent le départ des arcs (aucune coupure),
    // puis, une fois tracée, elle est dessinée entière
    drawPart('arch', arch > 0 ? 1 : 0, arch >= 1 ? null : x => {
      const dd = arch * HALF, hh = dd > SIDE ? 712 - CY + 10 : dd;
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

  // ---- « Huit voix » : la nuit s'écrit au centre, puis le mot devient une fenêtre sur la ville
  const WORDS8 = ['nuit', 'notte', 'noche', 'night', 'noite', 'noapte', 'Nacht', 'nacht'];
  const fitSize = (chars, base, frac = 0.84) => {
    const em = chars.reduce((a, c) => a + (c === '+' ? 0.55 : adv(c)), 0) + 0.03 * (chars.length - 1);
    return Math.min(base, frac * W / em);
  };
  const winSize = word => fitSize([...word], (LAND ? 30 : 40) * U, LAND ? 0.6 : 0.84);
  const BASE_Y = () => H / 2 + (LAND ? 9 : 10) * U;        // ligne de base des mots, un peu sous le centre
  // point d'ancrage du zoom : au cœur du jambage le plus épais de la première lettre (le zoom « traverse » la lettre)
  const anchorCache = new Map();
  function zoomAnchor(word) {
    if (anchorCache.has(word)) return anchorCache.get(word);
    const S = 200, chars = [...word], xs = rowX(chars);
    const c = mk(S * 6, S * 1.6), x = c.getContext('2d');
    x.font = `400 ${S}px ${F.serif}`; x.textAlign = 'center'; x.textBaseline = 'alphabetic'; x.fillStyle = '#fff';
    const ox = S * 3, oy = S * 1.2;
    x.fillText(chars[0], ox + xs[0] * S, oy);
    const img = x.getImageData(0, 0, c.width, c.height).data, w = c.width, h = c.height;
    const on = (i, j) => img[(j * w + i) * 4 + 3] > 128;
    let best = [ox + xs[0] * S, oy - 0.3 * S], score = -1;
    for (let j = 0; j < h; j += 2) for (let i = 0; i < w; i += 2) {
      if (!on(i, j)) continue;
      let l = 0, r = 0, u2 = 0, d2 = 0;
      while (i - l > 0 && on(i - l, j)) l++;
      while (i + r < w - 1 && on(i + r, j)) r++;
      while (j - u2 > 0 && on(i, j - u2)) u2++;
      while (j + d2 < h - 1 && on(i, j + d2)) d2++;
      const sc = Math.min(Math.min(l, r), Math.min(u2, d2) * 0.8);
      if (sc > score) { score = sc; best = [i, j]; }
    }
    const a = [(best[0] - ox) / S, (best[1] - oy) / S];   // en em, relatif au centre du mot et à la ligne de base
    anchorCache.set(word, a);
    return a;
  }
  function drawChars(chars, xs, cx, cy, size, mode, col, a) {
    ctx.font = `400 ${size}px ${F.serif}`; ctx.textAlign = 'center'; ctx.textBaseline = 'alphabetic';
    chars.forEach((ch, k) => {
      if (mode === 'fill') { ctx.fillStyle = rgb(col, a); ctx.fillText(ch, cx + xs[k] * size, cy); }
      else { ctx.strokeText(ch, cx + xs[k] * size, cy); }
    });
  }
  function formulaCard(u, d, f) {
    reset(ctx);
    const veil = lerp(f.veil ?? 0.8, 1, prog(u, d - 0.3, 0.3, E.inOut));
    ctx.fillStyle = `rgba(2,2,2,${veil.toFixed(4)})`; ctx.fillRect(0, 0, W, H);
    const N = 'N', eight = [...f.eight], night = [...f.night];
    const r1 = rowX([N, '+', ...eight]), r2 = rowX(night);
    const sizeF = fitSize([N, '+', ...eight], (LAND ? 17 : 24) * U, LAND ? 0.6 : 0.8), sizeW = winSize(f.night);
    const pG = prog(u, d - 0.3, 0.3, E.inOut), size = lerp(sizeF, sizeW, pG);
    const cx = W / 2, fy = BASE_Y();
    const aN = prog(u, 0.02, Math.min(0.3, 0.15 * d), E.out), aE = prog(u, 0.12 * d, 0.15 * d, E.out);
    const pS = prog(u, 0.42 * d, 0.26 * d, E.inOut), pSw = prog(u, 0.5 * d, 0.18 * d, E.inOut), pOff = prog(u, 0.38 * d, 0.12 * d, E.out);
    shade(cx, fy - 0.3 * size, size * 2.6, size * 0.9, 0.6 * aN);
    ctx.font = `400 ${size}px ${F.serif}`; ctx.textAlign = 'center'; ctx.textBaseline = 'alphabetic';
    ctx.shadowColor = rgb(C.gold, 0.45 * aN); ctx.shadowBlur = 1.4 * U;
    const put = (ch, xEm, a, col = C.gold) => { if (a <= 0.003) return; ctx.fillStyle = rgb(col, a); ctx.fillText(ch, cx + xEm * size, fy); };
    const jN = f.map.indexOf(0), xN = lerp(r1[0], r2[jN], pS);
    if (N === night[jN]) put(N, xN, aN, C.goldHi);
    else { put(N, xN, aN * (1 - pSw), C.goldHi); put(night[jN], xN, aN * pSw, C.goldHi); }
    const pa = aE * (1 - pOff);
    if (pa > 0.003) {
      ctx.fillStyle = rgb(C.gold, pa);
      const px = cx + r1[1] * size, py = fy - 0.27 * size, hh = 0.13 * size, lw = Math.max(1, 0.02 * size);
      ctx.fillRect(px - hh, py - lw / 2, 2 * hh, lw); ctx.fillRect(px - lw / 2, py - hh, lw, 2 * hh);
    }
    eight.forEach((ch, k) => {
      const j = f.map.indexOf(k + 1);
      if (j < 0) { put(ch, r1[k + 2], aE * (1 - pOff), C.white); return; }
      const x = lerp(r1[k + 2], r2[j], pS), col = mixC(C.white, C.gold, pS);
      if (ch === night[j]) put(ch, x, aE, col);
      else { put(ch, x, aE * (1 - pSw), col); put(night[j], x, aE * pSw, col); }
    });
    f.map.forEach((m, j) => { if (m === -1) put(night[j], r2[j], aE * pSw, C.gold); });
    reset(ctx);
  }
  function windowWord(u, d, w) {
    reset(ctx);
    const chars = [...w.word], xs = rowX(chars), size0 = winSize(w.word);
    const cx = W / 2, fy = BASE_Y();
    // zoom à travers la première lettre : exponentiel (vitesse perçue constante), accéléré
    const zd = w.fast ? 0 : Math.min(0.42, 0.62 * d);
    const p = w.fast ? 0 : prog(u, d - zd - 0.05, zd);      // la lettre a tout recouvert juste avant la coupe
    const S = w.fast ? 1 + 0.07 * (u / d) : Math.pow(240, p * p);
    const [axE, ayE] = zoomAnchor(w.word);
    const a0x = cx + axE * size0, a0y = fy + ayE * size0;
    const k = E.inOut(clamp(p * 1.15));
    const px = lerp(a0x, W / 2, k), py = lerp(a0y, H / 2, k);
    // noir partout, sauf dans les lettres : la ville apparaît à travers le mot
    ctx.fillStyle = '#020202'; ctx.fillRect(0, 0, W, H);
    ctx.setTransform(S, 0, 0, S, px - S * a0x, py - S * a0y);
    ctx.globalCompositeOperation = 'destination-out';
    drawChars(chars, xs, cx, fy, size0, 'fill', [0, 0, 0], 1);
    ctx.globalCompositeOperation = 'source-over';
    // voile d'or très léger dans les lettres : le mot reste lisible même sur une image très sombre
    const tint = (w.fast ? 0.2 : 0.16) * (1 - prog(p, 0, 0.35));
    if (tint > 0.003) drawChars(chars, xs, cx, fy, size0, 'fill', C.gold, tint);
    // liseré doré sur le bord des lettres, puis l'or qui se dissout en image au début du plan
    const rimA = (w.fast ? 0.8 : 0.85) * (1 - prog(p, 0, 0.25));
    if (rimA > 0.003) {
      ctx.strokeStyle = rgb(C.goldHi, rimA); ctx.lineWidth = Math.max(1.2, 0.014 * size0);
      drawChars(chars, xs, cx, fy, size0, 'stroke');
    }
    const goldA = w.fast ? 0 : 1 - prog(u, 0, Math.min(0.32, 0.4 * d), E.inOut);
    if (goldA > 0.003) {
      ctx.shadowColor = rgb(C.gold, 0.45 * goldA); ctx.shadowBlur = 1.4 * U;
      drawChars([chars[0]], [xs[0]], cx, fy, size0, 'fill', C.goldHi, goldA);
      drawChars(chars.slice(1), xs.slice(1), cx, fy, size0, 'fill', C.gold, goldA);
    }
    reset(ctx);
    if (w.city) {
      const la = prog(u, 0.08, 0.25, E.out) * (1 - prog(u, d - zd - 0.05, 0.15));
      if (la > 0.003) {
        const top = fy - 0.86 * size0, cs = (LAND ? 2.2 : 2.7) * U, ks = (LAND ? 1.35 : 1.75) * U;
        shade(cx, top - 3 * U, 22 * U, 5 * U, 0.8 * la);
        tracked(ctx, w.city, cx, top - 2.6 * U, cs, 0.62, `300 ${cs}px ${F.sans}`, rgb(C.goldHi, la));
        tracked(ctx, w.coords, cx, fy + (LAND ? 6.5 : 8) * U, ks, 0.35, `300 ${ks}px ${F.sans}`, rgb(C.white, 0.75 * la));
      }
    }
  }
  function gather(u, d) {
    reset(ctx);
    ctx.fillStyle = '#020202'; ctx.fillRect(0, 0, W, H);
    const M = logoM(), parts = LOGO.meta.parts;
    const toS = (x, y) => [M.ox + x * M.s, M.oy + y * M.s];
    const [nx, ny] = toS(parts.n.x + parts.n.w / 2, parts.n.y + parts.n.h / 2);
    const nT = [nx, ny + 0.5 * parts.n.h * M.s];             // ligne de base du N du logo
    const sizeN = parts.n.h * M.s / 0.68;                     // hauteur de capitale de Bodoni ≈ 0,68 em
    const lineA = prog(u, 0, 0.14, E.out), restOff = prog(u, 0.28 * d, 0.25 * d, E.inOut), g = prog(u, 0.38 * d, 0.42 * d, E.inOut);
    const size = (LAND ? 4.4 : 5.6) * U;
    ctx.font = `italic 400 ${size}px ${F.serif}`; ctx.textBaseline = 'alphabetic'; ctx.textAlign = 'left';
    const rows = LAND ? [WORDS8] : [WORDS8.slice(0, 4), WORDS8.slice(4)];
    const logoN = prog(u, 0.78 * d, 0.2 * d, E.inOut);
    rows.forEach((row, ri) => {
      const ws = row.map(wd => ctx.measureText(wd).width), gap = 2.2 * U;
      const tot = ws.reduce((a, b) => a + b, 0) + gap * (row.length - 1);
      let x0 = W / 2 - tot / 2;
      const y0 = (LAND ? H / 2 : H / 2 - 4 * U + ri * 8 * U) + size * 0.3;
      row.forEach((wd, k) => {
        const first = [...wd][0], rest = [...wd].slice(1).join(''), w1 = ctx.measureText(first).width;
        if (lineA * (1 - restOff) > 0.003) { ctx.fillStyle = rgb(C.white, 0.8 * lineA * (1 - restOff)); ctx.fillText(rest, x0 + w1, y0); }
        const sz = lerp(size, sizeN, E.inOut(g)), cap = prog(g, 0.15, 0.5);
        const fx = lerp(x0 + w1 / 2, nT[0], g), fy = lerp(y0, nT[1], g);
        const nA = lineA * (1 - logoN) * (g > 0.98 && k + ri > 0 ? 0 : 1);
        ctx.font = `${g > 0.02 ? '' : 'italic '}400 ${sz}px ${F.serif}`; ctx.textAlign = 'center';
        if (nA * (1 - cap) > 0.003 && first !== 'N') { ctx.fillStyle = rgb(C.goldHi, nA * (1 - cap)); ctx.fillText(first, fx, fy); }
        if (nA * (first === 'N' ? 1 : cap) > 0.003) { ctx.fillStyle = rgb(C.goldHi, nA * (first === 'N' ? 1 : cap)); ctx.fillText('N', fx, fy); }
        ctx.font = `italic 400 ${size}px ${F.serif}`; ctx.textAlign = 'left';
        x0 += ws[k] + gap;
      });
    });
    if (logoN > 0.003) {
      ctx.setTransform(M.s, 0, 0, M.s, M.ox, M.oy);
      ctx.globalAlpha = logoN; ctx.shadowColor = rgb(C.gold, 0.55); ctx.shadowBlur = 1.6 * U;
      ctx.drawImage(LOGO.gold.n, parts.n.x, parts.n.y);
    }
    reset(ctx);
  }
  // logo sur la voix : « … la nuit s'écrit N plus huit » — le +, puis le 8, puis l'arche ; « Maison de parfums nocturne »
  function logoVoice(u, d, vo) {
    reset(ctx);
    ctx.fillStyle = '#020202'; ctx.fillRect(0, 0, W, H);
    const M = logoM(), parts = LOGO.meta.parts;
    const toS = (x, y) => [M.ox + x * M.s, M.oy + y * M.s];
    const hit = Math.sin(Math.PI * clamp((u - vo.huit) / 0.9)) * (u > vo.huit ? 1 : 0);
    if (hit > 0.003) {   // éclat doré derrière le logo au moment où il se forme
      const [cx, cy] = toS(767, 520);
      const g = ctx.createRadialGradient(cx, cy, 0, cx, cy, 60 * U);
      g.addColorStop(0, rgb([255, 214, 150], 0.13 * hit)); g.addColorStop(1, rgb([255, 214, 150], 0));
      ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
    }
    const sub = prog(u, vo.at + 0.15, 0.5, E.out) * (1 - prog(u, vo.huit + 0.9, 0.5, E.in));
    if (sub > 0.003) {
      ctx.font = `italic 400 ${(LAND ? 3.0 : 3.8) * U}px ${F.serif}`; ctx.textAlign = 'center'; ctx.textBaseline = 'alphabetic';
      ctx.fillStyle = rgb(C.white, 0.8 * sub);
      ctx.fillText('Dans toutes les langues, la nuit s’écrit N+8.', W / 2, toS(0, 905)[1]);
    }
    const nGlow = 1 + 1.6 * Math.sin(Math.PI * clamp((u - vo.n + 0.05) / 0.5)) * (u > vo.n - 0.05 ? 1 : 0);
    const arch = prog(u, vo.huit + 0.12, 1.3, E.inOut);
    const l1 = prog(u, vo.tag - 0.05, 0.7, E.inOut), l2 = prog(u, vo.tag + 0.85, 0.6, E.inOut);
    ctx.setTransform(M.s, 0, 0, M.s, M.ox, M.oy);
    const drawPart = (name, a, clipFn, glow = 1) => {
      if (a <= 0.003) return;
      const p = parts[name];
      ctx.save();
      if (clipFn) { ctx.beginPath(); clipFn(ctx, p); ctx.clip(); }
      ctx.globalAlpha = a; ctx.shadowColor = rgb(C.gold, Math.min(1, 0.55 * glow)); ctx.shadowBlur = 1.6 * U * glow;
      ctx.drawImage(LOGO.gold[name], p.x, p.y);
      ctx.restore();
    };
    drawPart('n', 1, null, nGlow);
    drawPart('plus', prog(u, vo.plus - 0.04, 0.3, E.out));
    drawPart('eight', prog(u, vo.huit - 0.04, 0.32, E.out), null, 1 + 1.2 * hit);
    const CX = 767.5, CY = 456, R = 310, SIDE = 246, HALF = SIDE + Math.PI / 2 * R;
    drawPart('arch', arch > 0 ? 1 : 0, arch >= 1 ? null : x => {
      const dd = arch * HALF, hh = dd > SIDE ? 712 - CY + 10 : dd;
      x.rect(440, 712 - hh, 60, hh); x.rect(1036, 712 - hh, 60, hh);
      if (dd > SIDE) { const a = Math.min(Math.PI / 2, (dd - SIDE) / R); x.moveTo(CX, CY); x.arc(CX, CY, R + 40, Math.PI, Math.PI + a); x.closePath(); x.moveTo(CX, CY); x.arc(CX, CY, R + 40, -a, 0); x.closePath(); }
    });
    const wipe = p => (x, q) => { const cx = q.x + q.w / 2, hw = (q.w / 2 + 10) * p; x.rect(cx - hw, q.y - 5, 2 * hw, q.h + 10); };
    drawPart('line1', l1 > 0 ? 1 : 0, wipe(l1));
    drawPart('line2', l2 > 0 ? 1 : 0, wipe(l2));
    reset(ctx);
    const fade = prog(u, d - 1.2, 1.2, E.inOut);
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
          // bruitage : nom seul, ou { n, at (s depuis le début du plan), db, end (aligné sur la fin du plan) }
          const o = typeof fx === 'string' ? { n: fx } : fx;
          const { n, at, ...rest } = o;   // autres champs (voix : fichier, panoramique, coupure…) transmis tels quels
          EV.push({ ...rest, type: n, t: +(t + (o.end ? d : (at ?? 0.04))).toFixed(3), dur: +d.toFixed(3), db: o.db || 0,
                    end: !!o.end, shot: sh.id, section: sec.name });
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
    if (s.render === 'finale') { const k = s.speed || 1; finale(u * k, s.dur * k); return; }
    if (s.render === 'gather') { gather(u, s.dur); return; }
    if (s.render === 'logo') { logoVoice(u, s.dur, s.vo); return; }
    if (s.formula) { formulaCard(u, s.dur, s.formula); return; }
    if (s.window) { windowWord(u, s.dur, s.window); return; }
    if (s.render) return;  // plan noir
    if (s.phrase) {
      // la phrase court sur plusieurs plans consécutifs
      const first = SHOTS.find(sh => sh.phrase === s.phrase);
      const lastIdx = SHOTS.map(sh => sh.phrase).lastIndexOf(s.phrase);
      const span = SHOTS[lastIdx].start + SHOTS[lastIdx].dur - first.start;
      phrase(t - first.start, span, s.phrase, true);
    }
    // la carte de ville peut courir sur plusieurs plans (card.beats)
    const cs = SHOTS.filter(sh => sh.card && t >= sh.start && t < sh.start + (sh.card.beats ? sh.card.beats * BEAT : sh.dur)).pop();
    if (cs) cityCard(t - cs.start, { ...cs.card, end: cs.card.beats ? cs.card.beats * BEAT : cs.dur });
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
    // montage : footage/edl.json (film) ou footage/<edl>.json (ex. ?edl=edl_teaser)
    const EDL_NAME = new URLSearchParams(location.search).get('edl') || 'edl';
    EDL = await (await fetch(`../footage/${EDL_NAME}.json`)).json();
    BIG = EDL.text === 'lisible';
    if (EDL.font === 'cinzel') {
      DISPLAY = true; TW = 700; F.title = '"Cinzel", "Noto Serif Display", serif';
      await Promise.all([document.fonts.load(`700 48px "Cinzel"`, 'NUIT HUIT PARIS'), document.fonts.load(`600 48px "Cinzel"`, 'CHAQUE'),
                         document.fonts.load(`700 48px "Noto Serif Display"`, 'ΝΥΧΤΑ'), document.fonts.load(`700 60px "Amiri"`, 'ليل')]);
      advCache.clear();
    }
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
