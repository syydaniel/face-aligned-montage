// usage: node capture.js frames OUTDIR START END WORKERS   |  node capture.js times OUTDIR t1,t2,...
const { chromium } = require('playwright-core'); const fs = require('fs');
(async () => {
  const [mode, out, a, b, wk] = process.argv.slice(2); fs.mkdirSync(out, {recursive: true});
  const browser = await chromium.launch({channel: 'chrome', headless: true, args: ['--use-angle=metal', '--ignore-gpu-blocklist', '--disable-background-timer-throttling']});
  const mk = async () => { const p = await browser.newPage({viewport: {width: 540, height: 960}}); p.on('console', m => { if (m.type() === 'error') console.error('PAGE', m.text()); }); p.on('pageerror', e => console.error('PAGEERR', e.message)); await p.goto(`http://127.0.0.1:8777/web/${process.env.PAGE || 'index.html'}?capture=1`); await p.waitForFunction('window.READY === true', null, {timeout: 120000}); return p; };
  if (mode === 'times') {
    const p = await mk(); const ts = a.split(',').map(Number);
    for (const t of ts) { const b64 = await p.evaluate(async t => { await window.renderAt(t); return document.getElementById('c').toDataURL('image/jpeg', 0.9).split(',')[1]; }, t); fs.writeFileSync(`${out}/t_${t.toFixed(2)}.jpg`, Buffer.from(b64, 'base64')); }
  } else {
    const s = +a, e = +b, n = +(wk || 4), t0 = Date.now(); let done = 0;
    await Promise.all(Array.from({length: n}, async (_, w) => { const p = await mk(); for (let i = s + w; i < e; i += n) { const f = `${out}/${String(i).padStart(5, '0')}.jpg`; if (fs.existsSync(f)) { done++; continue; } const b64 = await p.evaluate(i => window.renderFrame(i), i); fs.writeFileSync(f, Buffer.from(b64, 'base64')); done++; if (done % 150 === 0) console.log(`${done}/${e - s} ${((Date.now() - t0) / 1000).toFixed(0)}s`); } }));
  }
  await browser.close(); console.log('DONE');
})().catch(e => { console.error(e); process.exit(1); });
