// Convierte tesis.md → tesis.pdf renderizando bloques ```mermaid``` con mermaid.js
// Uso: node scripts/md2pdf.js [input.md] [output.pdf]
const fs = require('fs');
const path = require('path');

async function main() {
  const input = path.resolve(process.argv[2] || 'tesis.md');
  const output = path.resolve(process.argv[3] || input.replace(/\.md$/i, '.pdf'));

  const md = fs.readFileSync(input, 'utf8');

  // Resolver dependencias desde la caché de npx (md-to-pdf ya las descargó)
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
  if (!basedir) {
    console.error('No encontré puppeteer/marked en la caché de npx. Ejecuta primero `npx md-to-pdf` o instala las deps localmente.');
    process.exit(1);
  }
  const require_ = (id) => require(path.join(basedir, id));
  const { marked } = require_('marked');
  const puppeteer = require_('puppeteer');

  // Convertir bloques ```mermaid``` a <div class="mermaid"> antes de marked
  // (marked normalmente los volvería <pre><code class="language-mermaid">)
  const renderer = new marked.Renderer();
  const origCode = renderer.code.bind(renderer);
  renderer.code = (code, lang) => {
    if (lang === 'mermaid') {
      return `<div class="mermaid">${code}</div>`;
    }
    return origCode(code, lang);
  };
  marked.setOptions({ renderer, gfm: true, breaks: false });

  const bodyHtml = marked.parse(md);

  const html = `<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8" />
<title>${path.basename(input, '.md')}</title>
<style>
  body { font-family: 'Segoe UI', Arial, sans-serif; max-width: 800px; margin: 2em auto; padding: 0 1em; line-height: 1.55; color: #222; }
  h1, h2, h3, h4 { color: #1a1a1a; line-height: 1.25; page-break-after: avoid; }
  h1 { border-bottom: 2px solid #444; padding-bottom: .3em; }
  h2 { border-bottom: 1px solid #999; padding-bottom: .2em; margin-top: 1.6em; }
  pre { background: #f4f4f4; padding: .8em; border-radius: 4px; overflow-x: auto; font-size: .85em; }
  code { font-family: 'Consolas', 'Courier New', monospace; }
  :not(pre) > code { background: #f4f4f4; padding: 0 .3em; border-radius: 3px; }
  table { border-collapse: collapse; margin: 1em 0; }
  th, td { border: 1px solid #bbb; padding: .35em .6em; }
  th { background: #eee; }
  blockquote { border-left: 4px solid #888; margin: 1em 0; padding: .2em 1em; color: #555; background: #fafafa; }
  img { max-width: 100%; height: auto; display: block; margin: 1em auto; border: 1px solid #ddd; border-radius: 4px; page-break-inside: avoid; }
  .mermaid { text-align: center; margin: 1.2em 0; page-break-inside: avoid; }
  .mermaid svg { max-width: 100%; height: auto; }
  a { color: #0645ad; text-decoration: none; }
</style>
</head>
<body>
${bodyHtml}
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<script>
  mermaid.initialize({ startOnLoad: false, theme: 'default', securityLevel: 'loose', flowchart: { useMaxWidth: true } });
  window.__mermaidDone = mermaid.run().then(() => true).catch(e => { console.error(e); return false; });
</script>
</body>
</html>`;

  const tmpHtml = path.join(path.dirname(output), '.md2pdf.tmp.html');
  fs.writeFileSync(tmpHtml, html, 'utf8');

  console.log('Lanzando navegador…');
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  await page.goto('file:///' + tmpHtml.replace(/\\/g, '/'), { waitUntil: 'networkidle0' });
  console.log('Renderizando diagramas mermaid…');
  await page.waitForFunction('window.__mermaidDone !== undefined', { timeout: 60000 });
  await page.evaluate(() => window.__mermaidDone);

  console.log('Generando PDF…');
  await page.pdf({
    path: output,
    format: 'A4',
    printBackground: true,
    margin: { top: '20mm', right: '15mm', bottom: '20mm', left: '15mm' },
  });

  await browser.close();
  fs.unlinkSync(tmpHtml);
  console.log('Listo:', output);
}

main().catch(err => { console.error(err); process.exit(1); });
