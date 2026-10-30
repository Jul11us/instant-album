"""The source template opens the app; the distributable works on its own."""
import os
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


with TemporaryDirectory() as directory, sync_playwright() as playwright:
    isolated = Path(directory)
    (isolated / 'src').mkdir()
    (isolated / '相角.html').write_bytes((ROOT / '相角.html').read_bytes())
    (isolated / 'src/app.html').write_bytes((ROOT / 'src/app.html').read_bytes())
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(isolated)))
    Thread(target=server.serve_forever, daemon=True).start()
    options = {'headless': True}
    if os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH'):
        options['executable_path'] = os.environ['PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH']
    browser = playwright.chromium.launch(**options)
    try:
        # No separate backup.js or image assets exist beside these copies.
        for url in ((isolated / '相角.html').as_uri(),
                    (isolated / 'src/app.html').as_uri(),
                    f'http://127.0.0.1:{server.server_port}/src/app.html'):
            context = browser.new_context()
            context.route('https://fonts.googleapis.com/**', lambda route: route.abort())
            page = context.new_page()
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(url)
            page.wait_for_url('**/%E7%9B%B8%E8%A7%92.html')
            page.wait_for_function('() => !restoring')
            page.wait_for_function("""() => ['homeSample','homeSecond','homeThird'].every(id => {
              const image=document.getElementById(id);
              return image.complete && image.naturalWidth>0;
            })""")
            assert page.locator('#homeImport').is_enabled()
            assert page.locator('#homeLibrary').is_enabled()
            assert page.evaluate('typeof AlbumBackup') == 'object'
            assert page.locator('script[type="text/x-instant-album-source"]').count() == 0
            assert not errors, errors
            context.close()
            print('standalone/source entry passed:', url.split('/')[-1])
    finally:
        browser.close()
        server.shutdown()
        server.server_close()
