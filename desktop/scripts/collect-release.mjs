// 把安装包、免安装 zip 和单文件网页版收进 release/<版本>/，附上 SHA-256 校验值和安装说明。
import { createHash } from 'node:crypto';
import { createReadStream } from 'node:fs';
import { copyFile, mkdir, readFile, rm, stat, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const desktop = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const { version } = JSON.parse(await readFile(path.join(desktop, 'package.json'), 'utf8'));
if (!/^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$/.test(version)) throw new Error('Invalid release version');
const files = [`XiangJiao-Setup-${version}.exe`, `XiangJiao-${version}-win-x64-portable.zip`, `XiangJiao-${version}-web.html`];
const out = path.join(desktop, 'release', version);

const sha256 = file => new Promise((resolve, reject) => {
  const hash = createHash('sha256');
  createReadStream(file).on('data', d => hash.update(d)).on('end', () => resolve(hash.digest('hex'))).on('error', reject);
});

await rm(out, { recursive: true, force: true });
await mkdir(out, { recursive: true });
const sums = [], sizes = [];
for (const name of files) {
  const from = name.endsWith('.html') ? path.join(desktop, '..', '相角.html') : path.join(desktop, 'dist', name);
  await copyFile(from, path.join(out, name));
  sums.push(`${await sha256(from)}  ${name}`);
  sizes.push(`${name}（${((await stat(from)).size / 1048576).toFixed(0)} MB）`);
}
await writeFile(path.join(out, 'SHA256SUMS.txt'), sums.join('\n') + '\n');
await writeFile(path.join(out, 'INSTALL.txt'), [
  `相角 ${version} · Windows 10 / 11（64 位）`,
  '',
  `安装版：${sizes[0]}`,
  '  双击运行，选择安装位置，装好后从开始菜单或桌面打开「相角」。卸载在「设置 → 应用」里。',
  '',
  `免安装版：${sizes[1]}`,
  '  解压到任意文件夹，双击里面的 XiangJiao.exe。适合放在 U 盘里或者不想安装的时候用。',
  '',
  '两个 Windows 版本的照片和草稿都存在这台电脑的 %APPDATA%\\相角 里，卸载或删掉程序文件夹不会删照片。',
  '换电脑前，在应用首页底部「备份与恢复」里保存一份完整备份。',
  '',
  `网页版：${sizes[2]}`,
  '  用浏览器打开即可。字体、3D 和纸面光影需要联网；收藏只保存在当前浏览器中。',
  '',
  '安装包还没有代码签名，第一次打开时 Windows 可能提示「Windows 已保护你的电脑」：',
  '点「更多信息」，再点「仍要运行」。可以用 SHA256SUMS.txt 核对下载的文件有没有被改动：',
  '  在 PowerShell 里运行  Get-FileHash .\\文件名  ，结果应该和清单里的一致。',
  '',
].join('\r\n'));
console.log(`下载包在 ${out}：\n  ${sizes.join('\n  ')}`);
