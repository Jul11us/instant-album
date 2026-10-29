"""Exercise the photo library and mobile editing layout with Playwright."""
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
with sync_playwright() as playwright:
    options = {"headless": True}
    executable = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH")
    if executable:
        options["executable_path"] = executable
    browser = playwright.chromium.launch(**options)
    for width, height in ((1440, 900), (390, 844), (320, 568)):
        context = browser.new_context(viewport={"width": width, "height": height},
                                      is_mobile=width < 500, has_touch=width < 500)
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto((ROOT / "贴进相册.html").as_uri())
        page.wait_for_function("() => !restoring")
        page.locator("#homeDemo").click()
        page.wait_for_selector("#save", state="visible", timeout=30000)
        page.click("#back")
        page.locator("#fileIn").set_input_files(str(ROOT / "design-demos/assets/sample.jpg"))
        page.click("#straighten")
        page.locator('#tabs [data-t="memo"]').click()
        page.locator("#mPlace").fill("\u4e1c\u4eac")
        page.locator("#mPeople").fill("\u5c0f\u6797")
        page.locator("#mStory").fill("\u6a31\u82b1\u7684\u6545\u4e8b")
        # The real click must work even when the long memo tab is open.
        page.click("#libBtn", timeout=5000)
        page.locator("#libNew").fill("\u65c5\u884c")
        page.locator("#libNew").press("Enter")
        page.locator("#libGrid .lc .flip").first.click()
        page.locator("#colPick").click()
        page.locator('#libGrid [data-op="cover"]').first.click()
        page.locator("#libQ").fill("\u4e1c\u4eac")
        page.wait_for_function("() => lib.q === '\u4e1c\u4eac' && document.querySelectorAll('#libGrid .lc').length === 1")
        page.locator("#libQ").fill("\u6a31\u82b1")
        page.wait_for_function("() => lib.q === '\u6a31\u82b1' && document.querySelectorAll('#libGrid .lc').length === 1")
        page.evaluate("() => { clearTimeout(draftT); return saveDraft() }")
        page.reload()
        page.wait_for_function("() => !restoring && ed && !ed.demo", timeout=30000)
        page.locator("#homeContinue").click()
        restored = page.evaluate("() => ({cols, memo: ed.st.memo, id: ed.id})")
        assert restored["memo"]["place"] == "\u4e1c\u4eac", restored
        assert len(restored["cols"]) == 1, restored
        assert restored["cols"][0]["name"] == "\u65c5\u884c", restored
        assert restored["cols"][0]["ids"] == [restored["id"]], restored
        assert restored["cols"][0]["cover"] == restored["id"], restored
        assert page.evaluate("() => document.documentElement.scrollWidth === document.documentElement.clientWidth")
        assert not errors, errors
        print(f"library regression passed at {width}x{height}")
        context.close()
    browser.close()
