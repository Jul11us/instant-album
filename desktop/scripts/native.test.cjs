const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const desktop = path.resolve(__dirname, '..');

async function harness(t, choose, shouldFail = () => false) {
  const prefix = path.join(os.tmpdir(), 'xiangjiao-native-');
  const root = await fs.mkdtemp(prefix);
  t.after(async () => {
    assert.ok(path.resolve(root).startsWith(path.resolve(prefix)));
    await fs.rm(root, { recursive: true, force: true });
  });
  const handlers = new Map(), dialogs = [], revealed = [];
  const electron = {
    app: { getPath: name => path.join(root, name), requestSingleInstanceLock: () => true,
      whenReady: () => ({ then() {} }), on() {}, quit() {} },
    BrowserWindow: { fromWebContents: () => null },
    protocol: { registerSchemesAsPrivileged() {} },
    ipcMain: { handle: (name, handler) => handlers.set(name, handler) },
    dialog: { showSaveDialog: async (_win, options) => { dialogs.push(options); return choose(options) } },
    shell: { showItemInFolder: file => revealed.push(file) },
  };
  const fileSystem = { ...fs, writeFile: async (file, data, options) => {
    if (path.basename(file) === 'settings.json') return;
    if (shouldFail() && path.extname(file) === '.tmp') {
      await fs.writeFile(file, data.subarray(0, 3));
      throw Object.assign(new Error('Disk full'), { code: 'ENOSPC' });
    }
    return fs.writeFile(file, data, options);
  } };
  vm.runInNewContext(await fs.readFile(path.join(desktop, 'main.js'), 'utf8'), {
    require: name => name === 'electron' ? electron : name === 'node:fs/promises' ? fileSystem : require(name),
    __dirname: desktop, process: { env: {} }, Uint8Array, URL, Response,
  }, { filename: 'desktop/main.js' });
  const event = { sender: {} };
  return { root, dialogs, revealed,
    save: (name, bytes) => handlers.get('desktop:save-file')(event, name, bytes),
    reveal: file => handlers.get('desktop:reveal')(event, file) };
}

test('cancelled image and backup dialogs default to Pictures/相角 and write no files', async t => {
  const h = await harness(t, () => ({ canceled: true }));
  for (const name of ['photo.jpg', 'collection.instant-album.json']) {
    assert.equal(await h.save(name, new Uint8Array([1, 2, 3])), null);
    assert.equal(h.dialogs.at(-1).defaultPath, path.join(h.root, 'pictures', '相角', name));
  }
  assert.deepEqual(await fs.readdir(path.join(h.root, 'pictures', '相角')), []);
});

test('successful replacement is complete; a partial failed write preserves the previous backup', async t => {
  let fail = false;
  const h = await harness(t, options => ({ filePath: options.defaultPath }), () => fail);
  const original = new TextEncoder().encode('previous valid complete backup');
  const saved = await h.save('collection.json', original);
  assert.deepEqual(await fs.readFile(saved.path), Buffer.from(original));
  fail = true;
  await assert.rejects(h.save('collection.json', new TextEncoder().encode('new backup data')), /Disk full/);
  assert.deepEqual(await fs.readFile(saved.path), Buffer.from(original));
  assert.deepEqual(await fs.readdir(path.dirname(saved.path)), ['collection.json']);
  fail = false;
  const replacement = new Uint8Array([4, 5, 6, 7]);
  await h.save('collection.json', replacement);
  assert.deepEqual(await fs.readFile(saved.path), Buffer.from(replacement));
  h.reveal(saved.path);
  h.reveal(path.join(h.root, 'not-saved.json'));
  assert.deepEqual(h.revealed, [saved.path]);
});

// 窗口和菜单：照着 Electron 的事件顺序跑一遍 main.js（启动、关窗口、点程序坞）
async function lifecycle(t, platform) {
  const prefix = path.join(os.tmpdir(), 'xiangjiao-native-');
  const root = await fs.mkdtemp(prefix);
  t.after(async () => {
    assert.ok(path.resolve(root).startsWith(path.resolve(prefix)));
    await fs.rm(root, { recursive: true, force: true });
  });
  const events = new Map(), windows = [], menus = [];
  let quits = 0, appReady;
  class FakeWindow {
    constructor() {
      this.handlers = new Map(); this.destroyed = false; this.focused = false; windows.push(this);
      this.webContents = { setWindowOpenHandler() {}, on() {} };
    }
    on(name, fn) { this.handlers.set(name, fn) }
    once(name, fn) { this.handlers.set(name, fn) }
    maximize() {} restore() {} loadURL() {}
    focus() { this.focused = true }
    isDestroyed() { return this.destroyed }
    isMaximized() { return false }
    isMinimized() { return false }
    getBounds() { return { x: 0, y: 0, width: 1280, height: 860 } }
    close() { this.handlers.get('close')(); this.destroyed = true; this.handlers.get('closed')() }
  }
  const electron = {
    app: { name: '相角', getPath: name => path.join(root, name), requestSingleInstanceLock: () => true,
      whenReady: () => new Promise(resolve => { appReady = resolve }), on: (name, fn) => events.set(name, fn), quit: () => quits++ },
    BrowserWindow: FakeWindow,
    Menu: { buildFromTemplate: template => ({ template }), setApplicationMenu: menu => menus.push(menu) },
    protocol: { registerSchemesAsPrivileged() {}, handle() {} },
    session: { defaultSession: { setPermissionRequestHandler() {}, on() {}, webRequest: { onBeforeRequest() {} } } },
    ipcMain: { handle() {} }, dialog: {}, shell: {},
  };
  vm.runInNewContext(await fs.readFile(path.join(desktop, 'main.js'), 'utf8'), {
    require: name => name === 'electron' ? electron : require(name),
    __dirname: desktop, process: { env: {}, platform }, Uint8Array, URL, Response,
  }, { filename: 'desktop/main.js' });
  events.get('activate')?.();   // macOS 启动时可能先发 activate：这时还不能开窗口
  assert.equal(windows.length, 0);
  appReady();
  for (let i = 0; i < 200 && !windows.length; i++) await new Promise(r => setTimeout(r, 5));
  assert.equal(windows.length, 1);
  return { events, windows, menus, quits: () => quits };
}

test('Mac: native menu bar; closing the window keeps the app running and the Dock icon reopens it', async t => {
  const h = await lifecycle(t, 'darwin');
  const [menu] = h.menus;
  assert.deepEqual(Array.from(menu.template, m => m.label), ['相角', '编辑', '显示', '窗口']);   // 数组来自 main.js 的上下文，先拷过来再比
  const roles = menu.template.flatMap(m => m.submenu.map(i => i.role).filter(Boolean));
  for (const role of ['about', 'hide', 'quit', 'undo', 'cut', 'copy', 'paste', 'selectAll', 'togglefullscreen', 'minimize', 'close'])
    assert.ok(roles.includes(role), role);
  assert.equal(menu.template[0].submenu.find(i => i.role === 'quit').label, '退出相角');
  h.windows[0].close();
  h.events.get('window-all-closed')();
  assert.equal(h.quits(), 0);
  h.events.get('activate')();
  assert.equal(h.windows.length, 2);
  h.events.get('activate')();
  assert.equal(h.windows.length, 2);
  assert.ok(h.windows[1].focused);
});

test('Windows: no menu bar; closing the window quits; a second launch focuses the window', async t => {
  const h = await lifecycle(t, 'win32');
  assert.deepEqual(h.menus, [null]);
  h.events.get('second-instance')();
  assert.ok(h.windows[0].focused);
  h.windows[0].close();
  h.events.get('window-all-closed')();
  assert.equal(h.quits(), 1);
});

test('save requests reject invalid data and strip directory components from suggested names', async t => {
  const h = await harness(t, () => ({ canceled: true }));
  await assert.rejects(h.save('bad.json', 'not bytes'), /Bad save request/);
  assert.equal(h.dialogs.length, 0);
  await h.save('../../photo.jpg', new Uint8Array([1]));
  assert.equal(h.dialogs[0].defaultPath, path.join(h.root, 'pictures', '相角', 'photo.jpg'));
});
