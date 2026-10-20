// Capture PNG d'une page locale (Playwright / Chromium) : node scripts/shot.cjs page.html sortie.png largeur hauteur  (ALPHA=1 : fond transparent)
const path = require('path');
let chromium;
try { ({ chromium } = require('playwright')); } catch (e) { ({ chromium } = require(path.join(process.execPath, '..', '..', 'lib', 'node_modules', 'playwright'))); }
(async () => {
  const [, , page, out, w, h] = process.argv;
  const fs = require('fs');
  const opts = { headless: true, args: ['--force-color-profile=srgb', '--allow-file-access-from-files'] };
  if (fs.existsSync('/opt/pw-browsers/chromium') && fs.statSync('/opt/pw-browsers/chromium').isFile()) opts.executablePath = '/opt/pw-browsers/chromium';
  const b = await chromium.launch(opts);
  const p = await b.newPage({ viewport: { width: +w, height: +h }, deviceScaleFactor: 1 });
  await p.goto('file://' + path.resolve(page));
  await p.evaluate(() => document.fonts.ready);
  await p.waitForTimeout(300);
  await p.screenshot({ path: out, omitBackground: process.env.ALPHA === '1' });
  await b.close();
})();
