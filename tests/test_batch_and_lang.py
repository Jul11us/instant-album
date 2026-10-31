"""Tips before import, batch-applying an edit, and the English interface."""
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "相角.html"
SAMPLE = ROOT / "design-demos/assets/sample.jpg"

with sync_playwright() as playwright:
    options = {"headless": True}
    executable = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH")
    if executable:
        options["executable_path"] = executable
    browser = playwright.chromium.launch(**options)
    for width, height in ((1440, 900), (390, 844)):
        context = browser.new_context(viewport={"width": width, "height": height},
                                      is_mobile=width < 500, has_touch=width < 500)
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(PAGE.as_uri())
        page.wait_for_function("() => !restoring")

        # The first import shows the four checks instead of opening the picker.
        page.evaluate("localStorage.removeItem('tiejin.tipsSeen')")
        page.locator("#homeImport").click()
        page.wait_for_selector("#tipsPanel", state="visible")
        assert "四件事" in page.locator("#tipsPanel").inner_text()
        page.locator("#tipsClose").click()
        assert not page.locator("#tipsPanel").is_visible()

        # Import the same print twice, then style the second one.
        for _ in range(2):
            page.set_input_files("#fileIn", str(SAMPLE))
            page.wait_for_selector("#scanView", state="visible")
            page.wait_for_function("() => !importBusy")
            page.locator("#straighten").click()
            page.wait_for_selector("#editView", state="visible")
        page.locator('#tabs [data-t="fl"]').click()
        page.locator('#fl [data-f="旧夏"]').click()
        assert page.evaluate("ed.st.filter") == "旧夏"

        page.locator("#batchOpen").click()
        page.wait_for_selector("#batchPanel", state="visible")
        assert page.locator("#batchGrid .bit").count() == 1
        page.locator("#batchGrid .bit").first.click()
        assert "1" in page.locator("#batchCount").inner_text()
        page.locator("#batchGo").click()
        page.wait_for_selector("#batchPanel", state="hidden")
        filters = page.evaluate("() => scans.map(s => s.st.filter)")
        assert filters == ["旧夏", "旧夏"], filters
        # The batch action is undoable per photo.
        assert page.evaluate("() => scans[0].hist.length") >= 1
        page.wait_for_function("() => $('draftStatus').dataset.state === 'saved'", timeout=30000)

        # English interface, persisted across reloads, and reversible.
        page.locator("#editHome").click()
        page.locator("#langBtn").click()
        assert page.evaluate("document.documentElement.lang") == "en"
        assert page.locator("#homeTitle").inner_text() == "Pick up where\nyou left off."
        page.reload()
        page.wait_for_function("() => !restoring")
        assert page.evaluate("document.documentElement.lang") == "en"
        assert page.locator("#langBtn").inner_text() == "中文"
        page.locator("#langBtn").click()
        assert page.evaluate("document.documentElement.lang") == "zh-CN"
        assert "接着整理" in page.locator("#homeTitle").inner_text()

        assert not errors, errors
        print(f"tips, batch apply and language passed at {width}x{height}")
        context.close()
    browser.close()
