"""Run licensed photographs of real instant prints through import, scan and straighten.

These images exercise the workflow on real scenes: cluttered tables, hands,
overlapping prints and scans cropped to the card. Each print's true corners are
in fixtures/real-prints/labels.json, so automatic framing is checked for
accuracy: a proposed frame must match a labelled print (tests/detect_report.py
prints the full table), and the number of prints found must not drop.
Sources and licenses: tests/fixtures/real-prints/CREDITS.md
"""
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

from detect_report import LABELS, classify

ROOT = Path(__file__).resolve().parents[1]
PAGE = Path(os.environ.get("INSTANT_ALBUM_TEST_PAGE", ROOT / "相角.html"))
FIXTURES = ROOT / "tests/fixtures/real-prints"
PRINTS = sorted(FIXTURES.glob("*.jpg"))
assert len(PRINTS) >= 10, PRINTS
assert {p.name for p in PRINTS} == {k for k in LABELS if not k.startswith("_")}, "every fixture needs a label"
MIN_FOUND, MIN_AUTO = 7, 5   # measured 2026-10: 7 of 9 labelled photos framed, 5 without confirmation

with sync_playwright() as playwright:
    options = {"headless": True}
    executable = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH")
    if executable:
        options["executable_path"] = executable
    browser = playwright.chromium.launch(**options)
    found, auto = [], []
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
        scan = page.evaluate("() => ({confirm: scanNeedsConfirm, format, W: src.width, H: src.height, quad, found: autoFound})")
        kind, err, format_ok = classify(photo.name, scan)
        # Uncertain scenes fall back to the whole image; any frame shown must be a real print, the right way up.
        assert kind != "WRONG", (photo.name, scan)
        status = page.locator("#found").inner_text()
        if kind == "fallback":
            assert not scan["found"] and "没认出" in status, (photo.name, status)
        else:
            found.append(photo.name)
            assert scan["found"] and "没认出" not in status, (photo.name, status)
            if kind == "auto":
                # Accepted without confirmation: a real film format, and the right one.
                assert scan["format"] != "free" and format_ok, (photo.name, scan)
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
    assert len(found) >= MIN_FOUND and len(auto) >= MIN_AUTO, (found, auto)
    print(f"real prints passed: {len(PRINTS)} photos, {len(found)} framed ({len(auto)} automatically) {found}")
