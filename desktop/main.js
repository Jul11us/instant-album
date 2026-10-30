// 相角电脑版（Windows 和 Mac）：一个窗口装着网页版的全部界面。
// 页面从 app:// 读本地文件（字体、Three.js、Shaders 都在 app/ 里，不联网也能用）；
// 草稿存在这台电脑的应用数据里，不会跟着浏览器一起被清掉；导出和备份用系统的「另存为」。
const { app, BrowserWindow, Menu, dialog, ipcMain, protocol, session, shell } = require('electron');
const fs = require('node:fs/promises');
const path = require('node:path');
const { randomUUID } = require('node:crypto');

const ROOT = path.join(__dirname, 'app');
const HOME_URL = 'app://bundle/index.html';
const MIME = {
  '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.mjs': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8', '.woff2': 'font/woff2', '.json': 'application/json', '.png': 'image/png',
  '.jpg': 'image/jpeg', '.svg': 'image/svg+xml', '.txt': 'text/plain; charset=utf-8',
};
// 只给自动化检查用：单独的数据文件夹、存到指定文件夹不弹窗、窗口不显示、拦掉所有外网请求来证明离线可用
const TEST = {
  saveDir: process.env.XIANGJIAO_SAVE_DIR || '',
  hidden: process.env.XIANGJIAO_HIDDEN === '1',
  offline: process.env.XIANGJIAO_OFFLINE === '1',
};
if (process.env.XIANGJIAO_USER_DATA) app.setPath('userData', process.env.XIANGJIAO_USER_DATA);

protocol.registerSchemesAsPrivileged([{
  scheme: 'app',
  privileges: { standard: true, secure: true, supportFetchAPI: true, stream: true, codeCache: true },
}]);

if (!app.requestSingleInstanceLock()) app.quit();

const isMac = process.platform === 'darwin';
let win = null, ready = false;
const settingsFile = () => path.join(app.getPath('userData'), 'settings.json');
let settings = {};
async function loadSettings() {
  try { settings = JSON.parse(await fs.readFile(settingsFile(), 'utf8')) } catch { settings = {} }
}
async function saveSettings() {
  try { await fs.writeFile(settingsFile(), JSON.stringify(settings)) } catch { /* 记不住窗口大小不影响使用 */ }
}

async function serveApp(request) {
  const { host, pathname } = new URL(request.url);
  const file = path.normalize(path.join(ROOT, decodeURIComponent(pathname)));
  if (host !== 'bundle' || !file.startsWith(ROOT + path.sep)) return new Response('Not found', { status: 404 });
  try {
    const body = await fs.readFile(file);
    return new Response(body, { headers: { 'content-type': MIME[path.extname(file).toLowerCase()] || 'application/octet-stream' } });
  } catch {
    return new Response('Not found', { status: 404 });
  }
}

const isExternal = url => /^https?:\/\//i.test(url);

function defaultSaveDir() {
  if (settings.lastSaveDir) return settings.lastSaveDir;
  return path.join(app.getPath('pictures'), '相角');
}

function filtersFor(name) {
  const ext = path.extname(name).slice(1).toLowerCase();
  return {
    jpg: [{ name: 'JPEG 图片', extensions: ['jpg', 'jpeg'] }],
    png: [{ name: 'PNG 图片', extensions: ['png'] }],
    zip: [{ name: '压缩包', extensions: ['zip'] }],
    json: [{ name: '相角完整备份', extensions: ['json'] }],
  }[ext] || [];
}

// 导出图片、打包 zip、完整备份都走这里：弹「另存为」，默认放在「图片\相角」，记住上次选的文件夹
const savedPaths = new Set();
ipcMain.handle('desktop:save-file', async (event, name, bytes) => {
  if (typeof name !== 'string' || !(bytes instanceof Uint8Array)) throw new Error('Bad save request');
  const safeName = path.basename(name).replace(/[<>:"/\\|?*\u0000-\u001f]/g, '_') || 'xiangjiao';
  let target;
  if (TEST.saveDir) {
    target = path.join(TEST.saveDir, safeName);
  } else {
    const dir = defaultSaveDir(safeName);
    await fs.mkdir(dir, { recursive: true }).catch(() => {});
    const result = await dialog.showSaveDialog(BrowserWindow.fromWebContents(event.sender), {
      title: '保存到这台电脑', defaultPath: path.join(dir, safeName), filters: filtersFor(safeName),
    });
    if (result.canceled || !result.filePath) return null;
    target = result.filePath;
  }
  // 先写同目录的临时文件，成功后才替换，写入失败时保留用户已有的备份或成品。
  const temporary = path.join(path.dirname(target), `.${path.basename(target)}.${randomUUID()}.tmp`);
  try {
    await fs.writeFile(temporary, bytes, { flag: 'wx', flush: true });
    await fs.rename(temporary, target);
  } catch (error) {
    await fs.rm(temporary, { force: true }).catch(() => {});
    throw error;
  }
  savedPaths.add(target);
  settings.lastSaveDir = path.dirname(target);
  saveSettings();
  return { path: target };
});
// 只允许打开刚存过的文件所在文件夹
ipcMain.handle('desktop:reveal', (_event, file) => {
  if (savedPaths.has(file)) shell.showItemInFolder(file);
});

function createWindow() {
  const bounds = settings.bounds || {};
  const w = win = new BrowserWindow({
    width: bounds.width || 1280, height: bounds.height || 860, x: bounds.x, y: bounds.y,
    minWidth: 380, minHeight: 560,
    title: '相角', backgroundColor: '#F2EFE8', show: false,
    icon: path.join(__dirname, 'build', 'icon.ico'),
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true, sandbox: true, nodeIntegration: false, spellcheck: false,
      backgroundThrottling: !TEST.hidden,
    },
  });
  if (settings.maximized) w.maximize();
  w.once('ready-to-show', () => { if (!TEST.hidden) w.show() });
  const remember = () => {
    if (w.isDestroyed()) return;
    settings.maximized = w.isMaximized();
    if (!settings.maximized && !w.isMinimized()) settings.bounds = w.getBounds();
    saveSettings();
  };
  w.on('resize', remember); w.on('move', remember); w.on('close', remember);
  w.on('closed', () => { if (win === w) win = null });

  // 机型说明、教程这些外链交给系统浏览器；窗口本身永远停在相角里
  w.webContents.setWindowOpenHandler(({ url }) => {
    if (isExternal(url)) shell.openExternal(url);
    return { action: 'deny' };
  });
  w.webContents.on('will-navigate', (e, url) => {
    if (url.startsWith('app://bundle/')) return;
    e.preventDefault();
    if (isExternal(url)) shell.openExternal(url);
  });
  w.loadURL(HOME_URL);
}

// Windows 上不要菜单栏。Mac 的菜单栏是系统的一部分，没有它 ⌘Q、⌘W、⌘H 和输入框里的 ⌘C / ⌘V 都不起作用
function macMenu() {
  const name = app.name;
  return Menu.buildFromTemplate([
    { label: name, submenu: [
      { role: 'about', label: `关于${name}` },
      { type: 'separator' },
      { role: 'services', label: '服务' },
      { type: 'separator' },
      { role: 'hide', label: `隐藏${name}` },
      { role: 'hideOthers', label: '隐藏其他' },
      { role: 'unhide', label: '全部显示' },
      { type: 'separator' },
      { role: 'quit', label: `退出${name}` },
    ] },
    // 编辑照片时的 ⌘Z 由页面自己处理（撤销上一步调整），这里的撤销只管输入框里的文字
    { label: '编辑', submenu: [
      { role: 'undo', label: '撤销' },
      { role: 'redo', label: '重做' },
      { type: 'separator' },
      { role: 'cut', label: '剪切' },
      { role: 'copy', label: '拷贝' },
      { role: 'paste', label: '粘贴' },
      { role: 'selectAll', label: '全选' },
    ] },
    { label: '显示', submenu: [{ role: 'togglefullscreen', label: '进入 / 退出全屏幕' }] },
    { label: '窗口', role: 'window', submenu: [
      { role: 'minimize', label: '最小化' },
      { role: 'zoom', label: '缩放' },
      { role: 'close', label: '关闭窗口' },
      { type: 'separator' },
      { role: 'front', label: '前置全部窗口' },
    ] },
  ]);
}

// 再次打开相角（Windows 上又双击了图标，Mac 上点了程序坞）：把窗口拿到前面；Mac 上窗口关掉了就重新开一个
function bringBack() {
  if (!ready) return;
  if (!win) { createWindow(); return }
  if (win.isMinimized()) win.restore();
  win.focus();
}
app.on('second-instance', bringBack);
app.on('activate', bringBack);

app.whenReady().then(async () => {
  await loadSettings();
  Menu.setApplicationMenu(isMac ? macMenu() : null);
  protocol.handle('app', serveApp);
  const ses = session.defaultSession;
  // 这个应用用不到摄像头、定位、通知这些权限
  ses.setPermissionRequestHandler((_wc, _permission, callback) => callback(false));
  // 大图页里的「下载文件」链接也默认存进「图片\相角」
  ses.on('will-download', (_e, item) => {
    item.setSaveDialogOptions({ title: '保存到这台电脑', defaultPath: path.join(defaultSaveDir(item.getFilename()), item.getFilename()) });
  });
  if (TEST.offline) {
    ses.webRequest.onBeforeRequest((details, callback) => callback({ cancel: isExternal(details.url) }));
  }
  createWindow();
  ready = true;
});

// Mac 的习惯：关掉窗口应用还留在程序坞里，⌘Q 才退出
app.on('window-all-closed', () => { if (!isMac) app.quit() });
