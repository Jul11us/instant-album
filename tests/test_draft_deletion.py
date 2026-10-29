"""Regression for in-flight draft writes during deletion; requires Playwright and Chromium."""
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
with sync_playwright() as playwright:
    options = {"headless": True}
    if os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH"):
        options["executable_path"] = os.environ["PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH"]
    browser = playwright.chromium.launch(**options)
    for mode in ("delete", "clear"):
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto((ROOT / "贴进相册.html").as_uri())
        page.wait_for_function("() => !restoring")
        page.locator("#homeDemo").click()
        page.wait_for_selector("#save", state="visible", timeout=30000)
        outcome = page.evaluate("""async mode => {
          await KV.run('readwrite', s => s.clear());
          ed.demo = false;
          ed.st.frame = 'upload';
          uploadFrame = document.createElement('canvas'); uploadFrame.width = ed.W; uploadFrame.height = ed.H;
          uploadFrame.getContext('2d').fillStyle = '#1256ab'; uploadFrame.getContext('2d').fillRect(0, 0, ed.W, ed.H);
          const first = ed.id, second = {...ed, id: newId(), st: JSON.parse(JSON.stringify(ed.st)), _saved: false};
          scans.push(second); clearTimeout(draftT); await saveDraft();
          // Force a snapshot to be in flight when the user deletes.
          ed.src._saved = false; ed._saved = false; second._saved = false;
          const original = HTMLCanvasElement.prototype.toBlob;
          HTMLCanvasElement.prototype.toBlob = function(...args) { setTimeout(() => original.apply(this, args), 250) };
          const pending = saveDraft(); await new Promise(r => setTimeout(r, 30));
          if (mode === 'delete') await dropCurrent(); else await clearAll();
          await pending; HTMLCanvasElement.prototype.toBlob = original;
          const meta = await KV.get('meta'), keys = await KV.keys();
          return {first, second: second.id, ids: meta?.list?.map(s => s.id) || [], keys};
        }""", mode)
        if mode == "delete":
            assert outcome["ids"] == [outcome["second"]], outcome
            assert "film:" + outcome["first"] not in outcome["keys"], outcome
            page.reload()
            page.wait_for_function("() => !restoring && ed && !ed.demo", timeout=30000)
            page.locator("#homeContinue").click()
            restored = page.evaluate("""() => ({id: ed.id, frame: ed.st.frame, color: Array.from(uploadFrame.getContext('2d').getImageData(4,4,1,1).data)})""")
            assert restored["id"] == outcome["second"] and restored["frame"] == "upload", restored
            assert restored["color"][:3] == [18, 86, 171], restored
        else:
            assert outcome["ids"] == [] and outcome["keys"] == [], outcome
            assert page.locator("#homeView").is_visible()
            assert page.evaluate("scans.length") == 0
        assert not errors, errors
        print(mode, "draft regression passed")
        context.close()
    context = browser.new_context()
    page = context.new_page()
    page.goto((ROOT / "贴进相册.html").as_uri())
    page.wait_for_function("() => !restoring")
    page.locator("#homeDemo").click()
    page.wait_for_selector("#save", state="visible", timeout=30000)
    failure = page.evaluate("""async () => {
      ed.demo = false; clearTimeout(draftT); await saveDraft();
      const original = KV.run;
      KV.run = async function(mode, fn) {
        if (mode === 'readwrite') throw new Error('simulated storage failure');
        return original.call(this, mode, fn);
      };
      await dropCurrent();
      const message = $('toast').textContent;
      KV.run = original;
      const remaining = (await KV.get('meta')).list.length;
      clearTimeout(draftT);
      return {message, remaining};
    }""")
    assert "草稿删除失败" in failure["message"] and failure["remaining"] == 1, failure
    print("delete failure notification passed")
    context.close()
    context = browser.new_context()
    page = context.new_page()
    page.goto((ROOT / "贴进相册.html").as_uri())
    page.wait_for_function("() => !restoring")
    page.locator("#homeDemo").click()
    page.wait_for_selector("#save", state="visible")
    failure = page.evaluate("""async () => {
      ed.demo=false;clearTimeout(draftT);await saveDraft();
      const id=ed.id;window.clearOriginalRun=KV.run;
      KV.run=async function(mode,fn){
        if(mode==='readwrite')throw new Error('simulated clear failure');
        return clearOriginalRun.call(this,mode,fn);
      };
      await clearAll();
      return {id,memory:scans.filter(s=>!s.demo).map(s=>s.id),
        saved:(await KV.get('meta')).list.map(s=>s.id)};
    }""")
    assert failure["memory"] == [failure["id"]] == failure["saved"], failure
    assert page.locator("#editView").is_visible()
    assert page.locator("#draftStatus").get_attribute("data-state") == "error"
    page.evaluate("() => {KV.run=window.clearOriginalRun}")
    page.locator("#draftRetry").click()
    page.wait_for_function("() => $('draftStatus').dataset.state === 'saved'")
    assert page.evaluate("scans.length") == 1
    page.evaluate("clearAll()")
    assert page.locator("#homeView").is_visible()
    assert page.evaluate("scans.length") == 0
    assert page.evaluate("KV.keys()") == []
    print("clear failure preserves photos and can retry successfully")
    context.close()
    browser.close()
