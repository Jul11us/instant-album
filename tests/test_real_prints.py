"""Run licensed photographs of real instant prints through import, scan and straighten.

These images exercise the workflow on real scenes: cluttered tables, hands,
overlapping prints and scans cropped to the card. They are not labelled with
true corners, so this is a regression check, not an accuracy benchmark.
Sources and licenses: tests/fixtures/real-prints/CREDITS.md
"""
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PAGE = Path(os.environ.get("INSTANT_ALBUM_TEST_PAGE", ROOT / "相角.html"))
FIXTURES = ROOT / "tests/fixtures/real-prints"
PRINTS = sorted(FIXTURES.glob("*.jpg"))
assert len(PRINTS) >= 10, PRINTS

with sync_playwright() as playwright:
    options = {"headless": True}
    executable = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH")
    if executable:
        options["executable_path"] = executable
    browser = playwright.chromium.launch(**options)
    auto = []
    for photo in PRINTS:
        context = browser.new_context(viewport={"width": 1280, "height": 860})
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(PAGE.as_uri())
        page.wait_for_function("() => !restoring")
        with page.expect_file_chooser() as chooser:
            page.locator("#homeImport").click()
        chooser.value.set_files(str(photo))
        page.wait_for_selector("#scanView", state="visible", timeout=30000)
        page.wait_for_function("() => !importBusy")
        scan = page.evaluate("() => ({confirm: scanNeedsConfirm, fmt: format, W: src.width, H: src.height, quad})")
        if scan["confirm"]:
            # Uncertain scenes must fall back to the whole image, never to a
            # suspicious contour from inside the picture.
            full = [[0, 0], [scan["W"], 0], [scan["W"], scan["H"]], [0, scan["H"]]]
            assert all(abs(a - b) <= 1.1 for p, q in zip(scan["quad"], full) for a, b in zip(p, q)), (photo.name, scan)
        else:
            # Anything accepted without confirmation has to be a real film format.
            assert scan["fmt"] != "free", (photo.name, scan)
            auto.append(photo.name)

        # Whatever detection did, the full-image path straightens without distortion.
        page.locator("#fullPhoto").click()
        page.locator("#straighten").click()
        page.wait_for_selector("#editView", state="visible", timeout=30000)
        ratio = page.evaluate("() => ed.F.img[2] / ed.F.img[3]")
        assert abs(ratio / (scan["W"] / scan["H"]) - 1) < .01, (photo.name, ratio, scan)
        assert page.evaluate("() => document.documentElement.scrollWidth === document.documentElement.clientWidth")
        assert not errors, (photo.name, errors)
        context.close()
    browser.close()
    print(f"real prints passed: {len(PRINTS)} photos, {len(auto)} framed automatically {auto}")
