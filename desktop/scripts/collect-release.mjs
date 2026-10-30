// 把安装包、免安装 zip 和单文件网页版收进 release/<版本>/，附上 SHA-256 校验值和安装说明。
// Mac 版要在 Mac 上打包（GitHub Actions 的「Mac 版」，或者 Mac 上的 npm run dist:mac）：两个 dmg 放进 dist/ 就一起收进来。
import { createHash } from 'node:crypto';
import { createReadStream } from 'node:fs';
import { copyFile, mkdir, readFile, rm, stat, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const desktop = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const { version } = JSON.parse(await readFile(path.join(desktop, 'package.json'), 'utf8'));
if (!/^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$/.test(version)) throw new Error('Invalid release version');
const SETUP = `XiangJiao-Setup-${version}.exe`, PORTABLE = `XiangJiao-${version}-win-x64-portable.zip`, WEB = `XiangJiao-${version}-web.html`;
const ARM = `XiangJiao-${version}-mac-arm64.dmg`, INTEL = `XiangJiao-${version}-mac-x64.dmg`;
const files = [SETUP, PORTABLE];
const exists = name => stat(path.join(desktop, 'dist', name)).then(() => true, () => false);
const macFound = [await exists(ARM), await exists(INTEL)];
if (macFound[0] !== macFound[1]) throw new Error(`dist/ 里只有一个 Mac 版 dmg：${ARM} 和 ${INTEL} 要一起放进去`);
const withMac = macFound[0];
if (withMac) files.push(ARM, INTEL);
else console.log(`dist/ 里没有 ${version} 的 Mac 版 dmg，这次只收 Windows 版和网页版`);
files.push(WEB);
const out = path.join(desktop, 'release', version);

const sha256 = file => new Promise((resolve, reject) => {
  const hash = createHash('sha256');
  createReadStream(file).on('data', d => hash.update(d)).on('end', () => resolve(hash.digest('hex'))).on('error', reject);
});

await rm(out, { recursive: true, force: true });
await mkdir(out, { recursive: true });
const sums = [], sizes = new Map();
for (const name of files) {
  const from = name.endsWith('.html') ? path.join(desktop, '..', '相角.html') : path.join(desktop, 'dist', name);
  await copyFile(from, path.join(out, name));
  sums.push(`${await sha256(from)}  ${name}`);
  sizes.set(name, `${name}（${((await stat(from)).size / 1048576).toFixed(0)} MB）`);
}
await writeFile(path.join(out, 'SHA256SUMS.txt'), sums.join('\n') + '\n');
await writeFile(path.join(out, 'INSTALL.txt'), [
  `相角 ${version}`,
  '',
  '■ Windows 10 / 11（64 位）',
  '',
  `安装版：${sizes.get(SETUP)}`,
  '  双击运行，选择安装位置，装好后从开始菜单或桌面打开「相角」。卸载在「设置 → 应用」里。',
  '',
  `免安装版：${sizes.get(PORTABLE)}`,
  '  解压到任意文件夹，双击里面的 XiangJiao.exe。适合放在 U 盘里或者不想安装的时候用。',
  '',
  '两个 Windows 版本的照片和草稿都存在这台电脑的 %APPDATA%\\相角 里，卸载或删掉程序文件夹不会删照片。',
  '换电脑前，在应用首页底部「备份与恢复」里保存一份完整备份。',
  '',
  '安装包还没有代码签名，第一次打开时 Windows 可能提示「Windows 已保护你的电脑」：',
  '点「更多信息」，再点「仍要运行」。',
  '',
  ...(withMac ? [
    '■ Mac（macOS 13 或更新版本）',
    '',
    `Apple 芯片（M1、M2、M3、M4 等）：${sizes.get(ARM)}`,
    `Intel 芯片：${sizes.get(INTEL)}`,
    '  不确定是哪种：点屏幕左上角的苹果菜单 →「关于本机」，看「芯片」或「处理器」那一行。',
    '  打开 dmg，把「相角」拖进「应用程序」文件夹，再从「应用程序」或启动台打开。',
    '',
    '照片和草稿存在 ~/Library/Application Support/相角 里，删掉应用不会删照片。',
    '',
    '还没有 Apple 的开发者签名和公证，第一次打开时 macOS 会提示无法验证开发者：',
    '点「完成」，到「系统设置 → 隐私与安全性」页面底部点「仍要打开」，再确认一次',
    '如果提示「已损坏，无法打开」，在「终端」里运行下面这行，再打开：',
    '  xattr -dr com.apple.quarantine /Applications/相角.app',
    '',
  ] : []),
  '■ 网页版',
  '',
  `${sizes.get(WEB)}`,
  '  用浏览器打开即可。字体、3D 和纸面光影需要联网；收藏只保存在当前浏览器中。',
  '',
  '可以用 SHA256SUMS.txt 核对下载的文件有没有被改动，结果应该和清单里的一致：',
  '  Windows：在 PowerShell 里运行  Get-FileHash .\\文件名',
  ...(withMac ? ['  Mac：在「终端」里运行  shasum -a 256 文件名'] : []),
  '',
].join('\r\n'));
console.log(`下载包在 ${out}：\n  ${[...sizes.values()].join('\n  ')}`);
