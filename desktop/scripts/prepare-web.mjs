// 把网页版的 相角.html 变成电脑版用的 app/：
// Google 字体、Three.js、Shaders 原来都从网上加载，这里下载或打包到本地，装好以后不联网也能用。
// 字体按 Google 的分片原样保存（每片只含一部分汉字，用到才读），下载过的放在 .cache/fonts 里不重复下。
import { build } from 'esbuild';
import { copyFile, mkdir, readFile, readdir, rm, stat, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const desktop = path.resolve(here, '..');
const repo = path.resolve(desktop, '..');
const out = path.join(desktop, 'app');
const fontCache = path.join(desktop, '.cache', 'fonts');
const modules = path.join(desktop, 'node_modules');
// 拿到 woff2 和 unicode-range 分片版本的样式表
const CHROME_UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36';

let html = await readFile(path.join(repo, '相角.html'), 'utf8');
function swap(from, to) {
  const count = html.split(from).length - 1;
  if (count !== 1) throw new Error(`页面里应该正好有一处「${from}」，实际有 ${count} 处，网页版可能改过加载方式`);
  html = html.replace(from, () => to);
}

await rm(out, { recursive: true, force: true });
await mkdir(path.join(out, 'vendor'), { recursive: true });
await mkdir(path.join(out, 'fonts'), { recursive: true });
await mkdir(fontCache, { recursive: true });

// Three.js：3D 拆解用，0.160.0 的模块版本身就是单个文件
await copyFile(path.join(modules, 'three', 'build', 'three.module.js'), path.join(out, 'vendor', 'three.module.js'));
swap("import('https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js')", "import('./vendor/three.module.js')");

// Shaders：纸面光影用，原来 jsDelivr 会把依赖拆成很多个请求，这里打成一个文件
await build({
  entryPoints: [path.join(modules, 'shaders', 'dist', 'js', 'index.js')],
  bundle: true, format: 'esm', minify: true, target: 'chrome130', logLevel: 'warning',
  outfile: path.join(out, 'vendor', 'shaders.js'),
});
swap("'https://cdn.jsdelivr.net/npm/shaders@4.0.4/dist/js/index.js/+esm'", "'./vendor/shaders.js'");

// 字体
const link = html.match(/href="(https:\/\/fonts\.googleapis\.com\/css2\?[^"]+)"/);
if (!link) throw new Error('页面里没找到 Google 字体的链接');
const cssResponse = await fetch(link[1], { headers: { 'user-agent': CHROME_UA } });
if (!cssResponse.ok) throw new Error(`字体样式表下载失败：${cssResponse.status}`);
let css = await cssResponse.text();
const urls = [...new Set([...css.matchAll(/url\((https:\/\/fonts\.gstatic\.com\/[^)]+)\)/g)].map(m => m[1]))];
const localName = url => new URL(url).pathname.replace(/^\/s\//, '').replace(/[^a-zA-Z0-9._-]+/g, '_');
let downloaded = 0, bytes = 0;
async function fetchFont(url) {
  const name = localName(url), cached = path.join(fontCache, name);
  try { await stat(cached) } catch {
    for (let attempt = 1; ; attempt++) {
      try {
        const res = await fetch(url);
        if (!res.ok) throw new Error(String(res.status));
        await writeFile(cached, Buffer.from(await res.arrayBuffer()));
        downloaded++;
        break;
      } catch (e) {
        if (attempt === 3) throw new Error(`字体文件下载失败：${url}（${e.message}）`);
      }
    }
  }
  await copyFile(cached, path.join(out, 'fonts', name));
  bytes += (await stat(cached)).size;
}
for (let i = 0; i < urls.length; i += 16) await Promise.all(urls.slice(i, i + 16).map(fetchFont));
css = css.replace(/url\((https:\/\/fonts\.gstatic\.com\/[^)]+)\)/g, (_, url) => `url(./${localName(url)})`);
await writeFile(path.join(out, 'fonts', 'fonts.css'), css);
swap(link[0], 'href="./fonts/fonts.css"');

await writeFile(path.join(out, 'index.html'), html);
// 离线分发时把完整的版权及许可文本一起带上，不能只写库名和链接。
const notices = path.join(out, 'vendor', 'licenses');
await mkdir(notices, { recursive: true });
for (const pkg of ['three', 'shaders']) {
  await copyFile(path.join(modules, pkg, 'LICENSE'), path.join(notices, `${pkg}-MIT.txt`));
}
for (const name of await readdir(path.join(desktop, 'licenses', 'fonts'))) {
  if (name.endsWith('.txt')) await copyFile(path.join(desktop, 'licenses', 'fonts', name), path.join(notices, name));
}
const readme = await readFile(path.join(repo, 'README.md'), 'utf8');
const credits = readme.split('## 图片署名 / Image credits')[1]?.split('## 商标 / Trademarks')[0];
if (!credits) throw new Error('README 里缺少示例照片的署名和许可');
await writeFile(path.join(out, 'vendor', 'IMAGE-CREDITS.md'), '# Image credits / 图片署名\n' + credits);
await writeFile(path.join(out, 'vendor', 'LICENSES.txt'), [
  'Full copyright and license texts: ./licenses/',
  'Bundled photo credits, source links and licenses: ./IMAGE-CREDITS.md',
  '',
  'three.js 0.160.0 — MIT License — https://github.com/mrdoob/three.js',
  'shaders 4.0.4 — MIT License — https://shaders.com/',
  'Fonts from Google Fonts (Noto Serif SC, Noto Sans SC, Zen Maru Gothic, Long Cang, Ma Shan Zheng, Zhi Mang Xing,',
  'Liu Jian Mao Cao, ZCOOL KuaiLe, ZCOOL QingKe HuangYou, ZCOOL XiaoWei, Caveat) — SIL Open Font License 1.1',
  'Special Elite — Apache License 2.0',
  'Font license sources: https://github.com/google/fonts (ofl/<family>/OFL.txt; apache/specialelite/LICENSE.txt)',
  '',
].join('\n'));
console.log(`app/ 准备好了：${urls.length} 个字体分片（新下载 ${downloaded} 个，共 ${(bytes / 1048576).toFixed(1)} MB），Three.js 和 Shaders 已放到本地`);
