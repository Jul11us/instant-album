"""Exercise back-side import, draft restore, export, and abandoned scans in Chromium."""
import base64
import os
from pathlib import Path
from zipfile import ZipFile

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PAGE = Path(os.environ.get("INSTANT_ALBUM_TEST_PAGE", ROOT / "相角.html"))
with sync_playwright() as playwright:
    options = {"headless": True}
    if os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH"):
        options["executable_path"] = os.environ["PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH"]
    browser = playwright.chromium.launch(**options)
    for width, height in ((1440, 900), (390, 844)):
        context = browser.new_context(viewport={"width": width, "height": height})
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(PAGE.as_uri())
        page.wait_for_function("() => !restoring")
        page.locator("#homeDemo").click()
        page.wait_for_selector("#save", state="visible", timeout=30000)
        page.evaluate("ed.demo = false")
        page.locator('#tabs [data-t="memo"]').click()
        with page.expect_file_chooser() as chooser:
            page.locator('[data-bk="add"]').click()
        chooser.value.set_files(str(ROOT / "design-demos/assets/sample.jpg"))
        page.wait_for_function("() => !!ed.back || !$('scanView').hidden", timeout=30000)
        if page.locator("#scanView").is_visible():
            page.locator("#straighten").click()
        page.wait_for_function("() => !!ed.back")
        assert page.evaluate("showingBack")
        page.locator("#flip").click()
        page.wait_for_function("() => !showingBack")
        page.evaluate("clearTimeout(draftT)")
        assert page.evaluate("saveDraft()")
        page.reload()
        page.wait_for_function("() => !restoring && ed && !ed.demo", timeout=30000)
        page.locator("#homeContinue").click()
        assert page.evaluate("!!ed.back")
        page.locator("#save").click()
        page.locator('#expBox [data-k="back"][data-v="sep"]').click()
        page.locator("#expGo").click()
        with page.expect_download() as download:
            page.locator("#sheetDl").click()
        with ZipFile(download.value.path()) as archive:
            names = archive.namelist()
            assert len(names) == 2 and sum(n.endswith("-back.jpg") for n in names) == 1, names
            assert archive.testzip() is None
        page.locator("#sheetClose").click()

        # A featureless input must be manually adjusted; leaving that screen
        # through a thumbnail must cancel the pending back/merge operation.
        image = page.evaluate("""() => {
          const c = document.createElement('canvas'); c.width = 300; c.height = 300;
          const x = c.getContext('2d'); x.fillStyle = '#888'; x.fillRect(0, 0, 300, 300);
          return c.toDataURL('image/png').split(',')[1];
        }""")
        data = base64.b64decode(image)
        page.locator('#tabs [data-t="memo"]').click()
        with page.expect_file_chooser() as chooser:
            page.locator('[data-bk="redo"]').click()
        chooser.value.set_files({"name": "blank.png", "mimeType": "image/png", "buffer": data})
        page.wait_for_selector("#scanView", state="visible")
        assert page.evaluate("backFor >= 0")
        page.locator("#tray button.t").first.click()
        assert page.evaluate("backFor === -1 && mergeFor === -1")
        page.locator('#tabs [data-t="memo"]').click()
        with page.expect_file_chooser() as chooser:
            page.locator('[data-bk="redo"]').click()
        chooser.value.set_files({"name": "blank.png", "mimeType": "image/png", "buffer": data})
        page.wait_for_selector("#scanView", state="visible")
        assert page.evaluate("backFor >= 0")
        before = page.evaluate("scans.length")
        with page.expect_file_chooser() as chooser:
            page.locator("#tray button.add").click()
        assert page.evaluate("backFor === -1 && mergeFor === -1")
        chooser.value.set_files({"name": "blank.png", "mimeType": "image/png", "buffer": data})
        page.wait_for_selector("#scanView", state="visible")
        page.locator("#straighten").click()
        assert page.evaluate("scans.length") == before + 1
        assert not errors, errors
        print(f"back-side workflow passed at {width}px")
        context.close()
    browser.close()
