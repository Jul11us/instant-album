"""Browser regression for render caches. Requires Playwright and Chromium.

Run: python tests/test_render_cache.py
Set PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH to use an existing Chromium installation.
"""
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
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto((ROOT / "相角.html").as_uri())
    page.wait_for_function("() => !restoring")
    page.locator("#homeDemo").click()
    page.wait_for_selector("#save", state="visible", timeout=30000)
    result = page.evaluate("""async () => {
      const makeFrame = color => {
        const c = document.createElement('canvas'); c.width = ed.W; c.height = ed.H;
        const x = c.getContext('2d'); x.fillStyle = color; x.fillRect(0, 0, c.width, c.height); return c;
      };
      const pixel = async file => {
        const image = await createImageBitmap(file), c = document.createElement('canvas');
        c.width = image.width; c.height = image.height;
        const x = c.getContext('2d'); x.drawImage(image, 0, 0); return Array.from(x.getImageData(4, 4, 1, 1).data);
      };
      const exportFile = async () => { openExport(); await doExport(false); return expCache.files[0] };
      ed.st.frame = 'upload'; uploadFrame = makeFrame('red');
      const redFile = await exportFile(), redCard = await cardOf(ed, false);
      uploadFrame = makeFrame('blue');
      const blueFile = await exportFile(), blueCard = await cardOf(ed, false);
      const blue = await pixel(blueFile);
      ed.st.frame = 'draw'; customFrame = makeFrame('red');
      const firstDrawFile = await exportFile(), firstDrawCard = await cardOf(ed, false);
      customFrame = makeFrame('blue');
      const nextDrawFile = await exportFile(), nextDrawCard = await cardOf(ed, false);
      const before = ed, beforeFile = nextDrawFile, beforeCard = nextDrawCard;
      setSourceFromScan(); quad[0][0] += 40; straighten(true);
      // A revised image can have exactly the same glare reading and settings.
      ed.glareAmt = before.glareAmt;
      const afterFile = await exportFile(), afterCard = await cardOf(ed, false);
      return {uploadFileChanged: redFile !== blueFile, uploadCardChanged: redCard !== blueCard,
        blue, drawFileChanged: firstDrawFile !== nextDrawFile, drawCardChanged: firstDrawCard !== nextDrawCard,
        sameId: before.id === ed.id, newScan: before !== ed,
        scanFileChanged: beforeFile !== afterFile, scanCardChanged: beforeCard !== afterCard};
    }""")
    browser.close()
    assert result["blue"][2] > 200 and result["blue"][0] < 50, result
    for key in ("uploadFileChanged", "uploadCardChanged", "drawFileChanged", "drawCardChanged",
                "sameId", "newScan", "scanFileChanged", "scanCardChanged"):
        assert result[key], result
    assert not errors, errors
    print("render cache regression passed", result)
