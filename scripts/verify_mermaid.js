// Verifica que todos los bloques ```mermaid``` de un .md se rendericen a SVG.
// Uso: node scripts/verify_mermaid.js [input.md]
const fs = require('fs');
const path = require('path');

async function main() {
  const input = path.resolve(process.argv[2] || 'tesis.md');
  const md = fs.readFileSync(input, 'utf8');

  const npxCache = path.join(process.env.LOCALAPPDATA || '', 'npm-cache', '_npx');
  const fallback = path.join(process.env.APPDATA || '', 'npm-cache', '_npx');
  let basedir = null;
  for (const root of [npxCache, fallback]) {
    if (!fs.existsSync(root)) continue;
    for (const dir of fs.readdirSync(root)) {
      const nm = path.join(root, dir, 'node_modules');
      if (fs.existsSync(path.join(nm, 'puppeteer')) && fs.existsSync(path.join(nm, 'marked'))) {
        basedir = nm;
        break;
      }
    }
    if (basedir) break;
  }
  if (!basedir) { console.error('No encontré puppeteer/marked en caché npx.'); process.exit(1); }

  const markedPkg = JSON.parse(fs.readFileSync(path.join(basedir, 'marked', 'package.json'), 'utf8'));
  console.log('marked version:', markedPkg.version);

  const require_ = (id) => require(path.join(basedir, id));
  const { marked } = require_('marked');
  const puppeteer = require_('puppeteer');

  const renderer = new marked.Renderer();
  const origCode = renderer.code.bind(renderer);
  renderer.code = (code, lang) => {
    // Soporta firma vieja (code, lang) y nueva ({text, lang})
    let c = code, l = lang;
    if (typeof code === 'object' && code !== null) { c = code.text; l = code.lang; }
    if (l === 'mermaid') return `<div class="mermaid">${c}</div>`;
    return origCode(code, lang);
  };
  marked.setOptions({ renderer, gfm: true, breaks: false });

  const bodyHtml = marked.parse(md);
  const divCount = (bodyHtml.match(/<div class="mermaid">/g) || []).length;
  console.log('Bloques convertidos a <div class="mermaid">:', divCount);

  const html = `<!DOCTYPE html><html><head><meta charset="utf-8"></head><body>
${bodyHtml}
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<script>
  window.__errors = [];
  mermaid.initialize({ startOnLoad: false, theme: 'default', securityLevel: 'loose', flowchart: { useMaxWidth: true } });
  window.__mermaidDone = mermaid.run({ suppressErrors: true }).then(() => true).catch(e => { window.__errors.push(String(e)); return false; });
</script>
</body></html>`;

  const tmp = path.join(path.dirname(input), '.verify_mermaid.tmp.html');
  fs.writeFileSync(tmp, html, 'utf8');

  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  const consoleErrors = [];
  page.on('console', m => { if (m.type() === 'error') consoleErrors.push(m.text()); });
  page.on('pageerror', e => consoleErrors.push('PAGEERROR: ' + e.message));
  page.on('requestfailed', r => consoleErrors.push('REQFAILED: ' + r.url() + ' ' + (r.failure() && r.failure().errorText)));
  await page.goto('file:///' + tmp.replace(/\\/g, '/'), { waitUntil: 'networkidle0' });
  console.log('typeof mermaid:', await page.evaluate(() => typeof window.mermaid));
  console.log('mermaid.version:', await page.evaluate(() => (window.mermaid && window.mermaid.version) ? window.mermaid.version : 'N/A'));
  await page.waitForFunction('window.__mermaidDone !== undefined', { timeout: 60000 });
  await page.evaluate(() => window.__mermaidDone);
  const firstErr = await page.evaluate(() => (window.__errors && window.__errors[0]) || null);
  if (firstErr) console.log('Primer error mermaid.run:', firstErr.slice(0, 200));

  const stats = await page.evaluate(() => {
    const divs = Array.from(document.querySelectorAll('div.mermaid'));
    const withSvg = divs.filter(d => d.querySelector('svg')).length;
    const errorDivs = divs.filter(d => d.querySelector('svg') === null);
    return {
      totalDivs: divs.length,
      withSvg,
      withoutSvg: errorDivs.length,
      offending: errorDivs.map(d => (d.textContent || '').trim().slice(0, 60)),
    };
  });

  console.log('Diagramas con SVG renderizado:', stats.withSvg, '/', stats.totalDivs);
  if (stats.withoutSvg > 0) {
    console.log('SIN renderizar:', stats.withoutSvg);
    stats.offending.forEach(o => console.log('   -', o.replace(/\n/g, ' ')));
  }
  if (consoleErrors.length) {
    console.log('Errores de consola:');
    consoleErrors.slice(0, 10).forEach(e => console.log('   !', e.replace(/\n/g, ' ').slice(0, 120)));
  }

  await browser.close();
  fs.unlinkSync(tmp);
  process.exit(stats.withSvg === stats.totalDivs && stats.totalDivs > 0 ? 0 : 2);
}

main().catch(e => { console.error(e); process.exit(1); });
