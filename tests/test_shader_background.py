"""Regression for responsive, optional shader background (Playwright + Chromium)."""
import base64
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / "src/app.html").read_text(encoding="utf-8")
sample = base64.b64encode((ROOT / "design-demos/assets/sample.jpg").read_bytes()).decode()
html = ('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
        '</head><body>' + source.replace('__IMG__', 'data:image/jpeg;base64,' + sample) + '</body></html>')

with TemporaryDirectory() as temp, sync_playwright() as playwright:
    path = Path(temp) / "page.html"
    path.write_text(html, encoding="utf-8")
    options = {"headless": True}
    if os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH"):
        options["executable_path"] = os.environ["PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH"]
    browser = playwright.chromium.launch(**options)
    for reduced in (False, True):
        context = browser.new_context(viewport={"width": 390, "height": 844},
                                      reduced_motion="reduce" if reduced else "no-preference")
        context.add_init_script("Object.defineProperty(navigator, 'gpu', {value: {}, configurable: true})")
        # Mirrors the library's inline sizing behavior while avoiding a GPU dependency.
        context.route("https://cdn.jsdelivr.net/npm/shaders@4.0.4/dist/js/index.js/+esm", lambda route: route.fulfill(
            status=200, content_type="application/javascript", body="""
              export async function createShader(canvas, preset, options) {
                const rect = canvas.getBoundingClientRect();
                if (!canvas.style.width) canvas.style.width = rect.width + 'px';
                if (!canvas.style.height) canvas.style.height = rect.height + 'px';
                window.__shaderOptions = {telemetry: options.disableTelemetry,
                  speeds: preset.components.slice(0, 2).map(c => c.props.speed)};
                options.onReady();
                window.__shaderError = options.onError;
              }
            """))
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(path.as_uri())
        page.wait_for_function("() => !!window.__shaderOptions", timeout=30000)
        assert page.evaluate("() => window.__shaderOptions.telemetry") is True
        speeds = page.evaluate("() => window.__shaderOptions.speeds")
        assert speeds == ([0, 0] if reduced else [.18, .35]), speeds
        assert page.locator("#amb").evaluate("e => e.classList.contains('on')")
        page.set_viewport_size({"width": 320, "height": 568})
        page.wait_for_function("""() => {
          const a = $('amb').getBoundingClientRect(), s = $('stage').getBoundingClientRect();
          return Math.abs(a.width - s.width) < 1 && Math.abs(a.height - s.height) < 1;
        }""", timeout=5000)
        page.evaluate("() => window.__shaderError('no-adapter')")
        assert not page.locator("#amb").evaluate("e => e.classList.contains('on')")
        assert not errors, errors
        context.close()
    browser.close()
print("shader background responsive and fallback regression passed")
