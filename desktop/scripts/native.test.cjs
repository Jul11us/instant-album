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

test('save requests reject invalid data and strip directory components from suggested names', async t => {
  const h = await harness(t, () => ({ canceled: true }));
  await assert.rejects(h.save('bad.json', 'not bytes'), /Bad save request/);
  assert.equal(h.dialogs.length, 0);
  await h.save('../../photo.jpg', new Uint8Array([1]));
  assert.equal(h.dialogs[0].defaultPath, path.join(h.root, 'pictures', '相角', 'photo.jpg'));
});
