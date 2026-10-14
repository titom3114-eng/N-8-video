#!/usr/bin/env node
/*
 * Rendu image par image d'un film (src/index.html par défaut, ou --page nuits.html) vers une vidéo H.264 (sans son).
 *
 *   node scripts/render.cjs --format 16x9 --out output/video_16x9.mp4
 *   node scripts/render.cjs --format 9x16 --out output/video_9x16.mp4
 *   node scripts/render.cjs --format 16x9 --snap 2,15,40 --out output/snaps   (captures PNG)
 *   node scripts/render.cjs --cues build/cues.json                           (exporte la chronologie sonore)
 */
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');

let chromium;
try {
  ({ chromium } = require('playwright'));
} catch (e) {
  ({ chromium } = require(path.join(process.execPath, '..', '..', 'lib', 'node_modules', 'playwright')));
}

const args = Object.fromEntries(
  process.argv.slice(2).reduce((acc, a, i, arr) => {
    if (a.startsWith('--')) acc.push([a.slice(2), arr[i + 1] && !arr[i + 1].startsWith('--') ? arr[i + 1] : true]);
    return acc;
  }, [])
);

const FORMATS = { '16x9': [1920, 1080], '9x16': [1080, 1920], '1x1': [1080, 1080] };
const [width, height] = FORMATS[args.format || '16x9'];
const fps = Number(args.fps || 30);
const root = path.resolve(__dirname, '..');
const http = require('http');
const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.png': 'image/png', '.woff2': 'font/woff2' };

// Mini-serveur statique (évite les restrictions file:// de Chromium sur fetch et canvas)
function serve() {
  return new Promise(resolve => {
    const srv = http.createServer((req, res) => {
      const rel = decodeURIComponent(req.url.split('?')[0]);
      const file = path.join(root, rel);
      if (!file.startsWith(root) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) { res.writeHead(404); res.end(); return; }
      res.writeHead(200, { 'Content-Type': MIME[path.extname(file)] || 'application/octet-stream' });
      fs.createReadStream(file).pipe(res);
    });
    srv.listen(0, '127.0.0.1', () => resolve(srv));
  });
}

function launch() {
  const opts = { headless: true, args: ['--force-color-profile=srgb', '--disable-lcd-text', '--font-render-hinting=none'] };
  if (fs.existsSync('/opt/pw-browsers/chromium')) {
    const p = '/opt/pw-browsers/chromium';
    if (fs.statSync(p).isFile()) opts.executablePath = p;
  }
  return chromium.launch(opts);
}

(async () => {
  const srv = await serve();
  const pageUrl = `http://127.0.0.1:${srv.address().port}/src/${args.page || 'index.html'}?render=1`;
  const browser = await launch();
  const page = await browser.newPage({ viewport: { width, height }, deviceScaleFactor: 1 });
  page.on('console', m => { if (m.type() === 'error') console.error('[page]', m.text()); });
  page.on('pageerror', e => console.error('[page error]', e.message));
  await page.goto(pageUrl, { waitUntil: 'load' });
  await page.evaluate(() => window.N8.ready);
  const info = await page.evaluate(() => ({ duration: window.N8.duration, scenes: window.N8.scenes, events: window.N8.events, env: window.N8.audioEnv ? window.N8.audioEnv(100) : null, music: window.N8.music || null }));

  if (args.cues) {
    fs.mkdirSync(path.dirname(path.resolve(args.cues)), { recursive: true });
    fs.writeFileSync(path.resolve(args.cues), JSON.stringify(info, null, 2));
    console.log(`Chronologie exportée : ${args.cues} (durée ${info.duration.toFixed(2)} s)`);
    await browser.close(); srv.close();
    return;
  }

  const cdp = await page.context().newCDPSession(page);
  const shot = async () => {
    const { data } = await cdp.send('Page.captureScreenshot', { format: 'png', optimizeForSpeed: true, captureBeyondViewport: false });
    return Buffer.from(data, 'base64');
  };

  if (args.snap) {
    const dir = path.resolve(args.out || 'snaps');
    fs.mkdirSync(dir, { recursive: true });
    for (const s of String(args.snap).split(',')) {
      const t = Number(s);
      await page.evaluate(t => window.N8.renderAt(t), t);
      const file = path.join(dir, `${args.format || '16x9'}_${t.toFixed(2).padStart(6, '0')}.png`);
      fs.writeFileSync(file, await shot());
      console.log('snap', file);
    }
    await browser.close(); srv.close();
    return;
  }

  const out = path.resolve(args.out || `output/video_${args.format || '16x9'}.mp4`);
  fs.mkdirSync(path.dirname(out), { recursive: true });
  const start = Number(args.start || 0);
  const end = Math.min(Number(args.end || info.duration), info.duration);
  const total = Math.round((end - start) * fps);
  const ff = spawn('ffmpeg', [
    '-y', '-loglevel', 'error',
    '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'png', '-i', '-',
    '-c:v', 'libx264', '-preset', 'slow', '-crf', '15', '-tune', 'film',
    '-x264-params', 'aq-mode=3',
    '-pix_fmt', 'yuv420p', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709',
    '-movflags', '+faststart', out,
  ], { stdio: ['pipe', 'inherit', 'inherit'] });
  const ffDone = new Promise((res, rej) => ff.on('close', c => (c === 0 ? res() : rej(new Error('ffmpeg code ' + c)))));
  const write = buf => new Promise(res => (ff.stdin.write(buf) ? res() : ff.stdin.once('drain', res)));

  const t0 = Date.now();
  for (let f = 0; f < total; f++) {
    const t = start + f / fps;
    await page.evaluate(t => window.N8.renderAt(t), t);
    await write(await shot());
    if (f % (fps * 5) === 0) {
      const el = (Date.now() - t0) / 1000;
      process.stdout.write(`[${args.format || '16x9'}] ${f}/${total} images — ${el.toFixed(0)} s écoulées\n`);
    }
  }
  ff.stdin.end();
  await ffDone;
  await browser.close(); srv.close();
  console.log(`Vidéo écrite : ${out} (${total} images, ${((Date.now() - t0) / 1000).toFixed(0)} s)`);
})().catch(e => { console.error(e); process.exit(1); });
