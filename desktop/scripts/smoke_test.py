"""电脑版冒烟检查：真的启动 Electron 窗口（隐藏、断网），通过 DevTools 协议操作页面。

检查：离线字体和库都能用、导入拉正、导出和完整备份写到磁盘、3D 拆解能打开、重启后草稿还在。
用单独的临时数据文件夹，不碰本机真正的「相角」数据。运行：npm run check（需要先 npm run prepare-web）；
加 --packaged 检查 npm run dist 打出来的 dist/win-unpacked/XiangJiao.exe（Mac 上是 npm run dist:mac 打出来的、
本机芯片对应的 相角.app）；--app <路径> 检查指定的程序，比如从 dmg 里拷出来的 相角.app；--show 让窗口显示出来；
--shots <文件夹> 存下首页、编辑和 3D 拆解的截图（Mac 上加 --show 时连整个屏幕一起截，看得到菜单栏）。
"""
import os
import platform
import plistlib
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

DESKTOP = Path(__file__).resolve().parents[1]
REPO = DESKTOP.parent
ARGS = sys.argv[1:]
APP = Path(ARGS[ARGS.index('--app') + 1]) if '--app' in ARGS else None
PACKAGED = '--packaged' in ARGS or APP is not None
SHOW = '--show' in ARGS
SHOTS = Path(ARGS[ARGS.index('--shots') + 1]) if '--shots' in ARGS else None
if sys.platform == 'darwin':
    APP = APP or (DESKTOP / 'dist' / ('mac-arm64' if platform.machine() == 'arm64' else 'mac') / '相角.app' if PACKAGED
                  else DESKTOP / 'node_modules' / 'electron' / 'dist' / 'Electron.app')
    if APP.suffix == '.app':
        APP = APP / 'Contents' / 'MacOS' / plistlib.loads((APP / 'Contents' / 'Info.plist').read_bytes())['CFBundleExecutable']
    COMMAND = [str(APP)] if PACKAGED else [str(APP), str(DESKTOP)]
else:
    COMMAND = ([str(APP or DESKTOP / 'dist' / 'win-unpacked' / 'XiangJiao.exe')] if PACKAGED
               else [str(DESKTOP / 'node_modules' / 'electron' / 'dist' / 'electron.exe'), str(DESKTOP)])
PRINT = REPO / 'tests' / 'fixtures' / 'real-prints' / 'print-on-beige-paper.jpg'


def free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def launch(user_data, save_dir):
    port = free_port()
    env = dict(os.environ, XIANGJIAO_USER_DATA=str(user_data), XIANGJIAO_SAVE_DIR=str(save_dir),
               XIANGJIAO_HIDDEN='0' if SHOW else '1', XIANGJIAO_OFFLINE='1')
    proc = subprocess.Popen([*COMMAND, f'--remote-debugging-port={port}'], env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(100):
        try:
            with socket.create_connection(('127.0.0.1', port), timeout=.2):
                return proc, f'http://127.0.0.1:{port}'
        except OSError:
            time.sleep(.2)
    proc.kill()
    raise RuntimeError('Electron 没有打开调试端口')


def app_page(browser):
    for _ in range(100):
        for ctx in browser.contexts:
            for page in ctx.pages:
                if page.url.startswith('app://bundle/'):
                    return page
        time.sleep(.1)
    raise RuntimeError('没找到相角的窗口')


def shot(page, name):
    if not SHOTS:
        return
    SHOTS.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(SHOTS / f'{name}.png'))
    if sys.platform == 'darwin' and SHOW:
        subprocess.run(['screencapture', '-x', str(SHOTS / f'{name}-screen.png')], check=False)


def close(proc):
    proc.terminate()
    try:
        proc.wait(10)
    except subprocess.TimeoutExpired:
        proc.kill()


with tempfile.TemporaryDirectory() as tmp, sync_playwright() as p:
    user_data, save_dir = Path(tmp, 'profile'), Path(tmp, 'saved')
    save_dir.mkdir()

    # 第一次打开：导入、拉正、导出、备份、3D
    proc, endpoint = launch(user_data, save_dir)
    try:
        browser = p.chromium.connect_over_cdp(endpoint)
        page = app_page(browser)
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.wait_for_function('() => typeof restoring !== "undefined" && !restoring')
        assert page.evaluate('!!window.desktop && typeof window.desktop.saveFile === "function"')
        assert page.evaluate('typeof require === "undefined" && typeof process === "undefined"'), 'Node 不能暴露给页面'
        assert '电脑' in page.locator('#homeFootNote').inner_text()

        # 断网状态下字体照样从本地读到
        page.evaluate("""async () => { await document.fonts.load('500 32px "Noto Serif SC"', '给拍立得');
                                      await document.fonts.load('32px "Long Cang"', '10.29'); await document.fonts.ready }""")
        loaded = page.evaluate("[...new Set([...document.fonts].filter(f => f.status === 'loaded').map(f => f.family.replace(/\"/g, '')))]")
        assert 'Noto Serif SC' in loaded and 'Long Cang' in loaded, loaded
        external = page.evaluate("performance.getEntriesByType('resource').map(e => e.name).filter(n => /^https?:/.test(n))")
        assert not external, external
        shot(page, '1-home')

        # 导入一张真实翻拍，拉正，进编辑
        with page.expect_file_chooser() as chooser:
            page.locator('#homeImport').click()
        chooser.value.set_files(str(PRINT))
        page.wait_for_selector('#scanView', state='visible')
        page.wait_for_function('() => !importBusy')
        page.locator('#fullPhoto').click()
        page.locator('#straighten').click()
        page.wait_for_selector('#editView', state='visible')
        page.wait_for_function("() => $('draftStatus').dataset.state === 'saved'", timeout=15000)
        photo_id = page.evaluate('ed.id')
        shot(page, '2-edit')

        # 导出图片：走电脑版的保存，文件真的写到磁盘，提示里给出路径
        page.locator('#save').click()
        page.wait_for_selector('#expPanel', state='visible')
        assert '这台电脑' in page.locator('#draftInfo').inner_text()
        page.locator('#expGo').click()
        page.wait_for_function("() => /存好了：/.test(document.body.innerText)", timeout=20000)
        images = list(save_dir.glob('instant-*.jpg'))
        assert len(images) == 1 and images[0].stat().st_size > 20000, images
        assert images[0].read_bytes()[:3] == b'\xff\xd8\xff', '导出的不是 JPEG'

        # 3D 拆解：Three.js 从本地加载
        page.locator('#editHome').click()
        page.wait_for_selector('#homeView', state='visible')
        page.locator('#homeContinue').click()
        page.wait_for_selector('#editView', state='visible')
        page.locator('#back').click()
        page.wait_for_selector('#scanView', state='visible')
        page.locator('#scanMore summary').click()
        page.locator('#td3d').click()
        page.wait_for_selector('#tdPanel', state='visible')
        page.wait_for_function("() => typeof THREE !== 'undefined' && !!THREE && $('tdLoad').hidden", timeout=20000)
        assert '没加载出来' not in page.locator('#tdLoad').inner_text()
        if SHOTS:
            page.wait_for_timeout(1000)
            shot(page, '3-teardown')
        page.locator('#tdClose').click()

        # 完整备份：同样写到磁盘
        page.locator('#scanHome').click()
        page.wait_for_selector('#homeView', state='visible')
        page.locator('#backupOpen').click()
        page.wait_for_selector('#backupPanel', state='visible')
        page.locator('#backupExport').click()
        page.wait_for_function("() => /完整备份已保存到/.test($('backupMessage').textContent)", timeout=20000)
        backups = list(save_dir.glob('*.instant-album.json'))
        assert len(backups) == 1 and backups[0].stat().st_size > 20000, backups
        image_kb, backup_kb = images[0].stat().st_size // 1024, backups[0].stat().st_size // 1024
        gpu = page.evaluate('async () => {try {return !!(await navigator.gpu?.requestAdapter())} catch {return false}}')
        assert not errors, errors
        browser.close()
    finally:
        close(proc)

    # 第二次打开：草稿还在，能接着整理
    proc, endpoint = launch(user_data, save_dir)
    try:
        browser = p.chromium.connect_over_cdp(endpoint)
        page = app_page(browser)
        page.wait_for_function('() => typeof restoring !== "undefined" && !restoring')
        assert page.locator('#homeContinue').is_visible(), '重启后应该能继续上次整理'
        page.locator('#homeContinue').click()
        page.wait_for_selector('#editView', state='visible')
        assert page.evaluate('ed.id') == photo_id
        if gpu:  # 纸面光影：本地打包的 Shaders 能在断网时启动
            page.wait_for_function("() => $('amb').classList.contains('on')", timeout=20000)
        browser.close()
    finally:
        close(proc)

print(f'电脑版{"安装包" if PACKAGED else ""}检查通过：离线字体 {len(loaded)} 种、导出 {image_kb} KB、'
      f'备份 {backup_kb} KB、3D 拆解、重启后草稿保留；WebGPU {"可用" if gpu else "不可用"}')
