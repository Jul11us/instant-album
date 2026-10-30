"""Browser regression for album page ordering and persistence (Playwright + Chromium)."""
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
with sync_playwright() as playwright:
    options = {"headless": True}
    if os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH"):
        options["executable_path"] = os.environ["PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH"]
    browser = playwright.chromium.launch(**options)
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    source = Path(os.environ.get("ALBUM_TEST_HTML", ROOT / "相角.html"))
    page.goto(source.resolve().as_uri())
    page.wait_for_function("() => !restoring")
    page.locator("#homeDemo").click()
    page.wait_for_selector("#save", state="visible", timeout=30000)
    page.locator("#album").click()
    page.locator("#albKeep").click()
    assert page.evaluate("() => pages.length") == 0
    assert "示例照片不会保存" in page.locator("#toast").inner_text()
    page.locator("#albClose").click()
    page.evaluate("""() => {
      ed.demo = false;
      const other = {...ed, id: newId(), st: JSON.parse(JSON.stringify(ed.st)), _saved: false};
      scans.push(other);
      alb = newAlb();
      openAlbum();
    }""")
    original_order = page.evaluate("() => [...alb.pick]")
    first = page.locator("#albOrder .it").first
    first.focus()
    page.keyboard.press("ArrowRight")
    assert page.evaluate("() => [...alb.pick]") == list(reversed(original_order))
    start = page.locator("#albOrder .it").first.bounding_box()
    target = page.locator("#albOrder .it").last.bounding_box()
    page.mouse.move(start["x"] + start["width"] / 2, start["y"] + start["height"] / 2)
    page.mouse.down()
    page.mouse.move(target["x"] + target["width"] * .8, target["y"] + target["height"] / 2, steps=5)
    page.mouse.up()
    assert page.evaluate("() => [...alb.pick]") == original_order
    page.locator("#albLook [data-bg]").last.click()
    page.locator("#albKeep").click()
    before = page.evaluate("""() => {
      const savedId = alb.id;
      const input = document.getElementById('albTitle');
      input.value = '海边的夏天';
      input.dispatchEvent(new Event('input', {bubbles:true}));
      document.querySelector('[data-page="new"]').click();
      const p = pages.find(p => p.id === savedId);
      return {id:savedId, title:p.title, pick:p.pick, bg:p.bg};
    }""")
    assert before["title"] == "海边的夏天", before
    assert len(before["pick"]) == 2 and before["bg"], before
    page.evaluate("async () => { clearTimeout(draftT); await saveDraft(); }")
    page.reload()
    page.wait_for_function("() => !restoring && ed && !ed.demo", timeout=30000)
    page.locator("#homeContinue").click()
    restored = page.evaluate("""id => {
      const p = pages.find(p => p.id === id);
      loadPage(p);
      return {id:p.id, title:p.title, pick:p.pick, bg:p.bg,
        titleInput:document.getElementById('albTitle').value};
    }""", before["id"])
    assert restored == {**before, "titleInput":"海边的夏天"}, restored
    assert not errors, errors
    print("album page ordering and persistence passed", restored)
    browser.close()
