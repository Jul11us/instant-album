"""A transient full/partial restore failure must never clean up unread photos."""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PAGE = Path(os.environ.get("INSTANT_ALBUM_TEST_PAGE", ROOT / "相角.html"))

SNAPSHOT = """async () => {
  const keys=(await KV.keys()).sort(), blobs=[];
  for(const key of keys){if(key==='meta')continue;const blob=await KV.get(key);
    blobs.push({key,size:blob.size,type:blob.type,crc:crc32(new Uint8Array(await blob.arrayBuffer()))});
  }
  return {keys,meta:await KV.get('meta'),blobs};
}"""

with sync_playwright() as p:
    options = {"headless": True}
    if os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH"):
        options["executable_path"] = os.environ["PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH"]
    browser = p.chromium.launch(**options)
    for mode in ("meta", "partial-film"):
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(PAGE.as_uri())
        page.wait_for_function("() => !restoring")
        page.locator("#homeDemo").click()
        page.wait_for_selector("#editView", state="visible")
        ids = page.evaluate("""async () => {
          ed.demo=false;ed.st.memo.place='第一张的地点';
          const first=ed,second={...ed,id:newId(),st:JSON.parse(JSON.stringify(ed.st)),hist:[],_saved:false};
          second.st.memo.place='第二张的地点';
          const back=mkCv(200,300);back.getContext('2d').fillStyle='#abc123';
          back.getContext('2d').fillRect(0,0,200,300);second.back=back;
          scans.push(second);newCol('不能丢失的相册',first.id);cols[0].ids.push(second.id);
          openEdit(1);clearTimeout(draftT);await saveDraft();
          return [first.id,second.id];
        }""")
        before = page.evaluate(SNAPSHOT)
        assert len(before["meta"]["list"]) == 2, before
        # Install only after seeding. This reload throws once, then subsequent
        # reads in the same document (the retry button) behave normally.
        key = "meta" if mode == "meta" else "film:" + ids[1]
        context.add_init_script("""(() => {
          const key=TARGET_KEY, originalGet=IDBObjectStore.prototype.get;
          window.restoreReadFailedOnce=false;window.restoreWriteTransactions=0;
          IDBObjectStore.prototype.get=function(requestKey){
            if(requestKey===key&&!window.restoreReadFailedOnce){
              window.restoreReadFailedOnce=true;
              throw new DOMException('Simulated transient read failure','UnknownError');
            }
            return originalGet.call(this,requestKey);
          };
          const originalTransaction=IDBDatabase.prototype.transaction;
          IDBDatabase.prototype.transaction=function(...args){
            if(args[1]==='readwrite')window.restoreWriteTransactions++;
            return originalTransaction.apply(this,args);
          };
        })();""".replace("TARGET_KEY", json.dumps(key)))
        page.reload()
        page.wait_for_function("() => !restoring")
        assert page.evaluate("window.restoreReadFailedOnce"), mode
        assert page.locator("#homeView").is_visible()
        assert page.locator("#homeRestoreRetry").is_visible()
        for control in ("#homeImport", "#homeDemo", "#homeLibrary"):
            assert page.locator(control).is_disabled(), (mode, control)
        blocked = page.evaluate("""async () => {
          const c=mkCv(180,120);c.getContext('2d').fillStyle='#345678';
          c.getContext('2d').fillRect(0,0,180,120);
          await loadFiles([new File([await toBlob(c,'image/png')],'new-photo.png',{type:'image/png'})]);
          return {normal:await saveDraft(),forced:await saveDraft(true)};
        }""")
        assert blocked == {"normal": False, "forced": False}, blocked
        assert page.evaluate("window.restoreWriteTransactions") == 0
        after_attempt = page.evaluate(SNAPSHOT)
        assert after_attempt == before, (mode, before, after_attempt)
        page.locator("#homeRestoreRetry").click()
        page.wait_for_function("() => !restoring")
        assert not page.locator("#homeRestoreRetry").is_visible()
        for control in ("#homeImport", "#homeDemo", "#homeLibrary"):
            assert page.locator(control).is_enabled(), (mode, control)
        assert page.evaluate("scans.map(s=>s.id)") == ids
        assert page.evaluate("scans.map(s=>s.st.memo.place)") == ["第一张的地点", "第二张的地点"]
        assert page.evaluate("!!scans[1].back")
        assert page.evaluate("cols[0].ids") == ids
        assert page.evaluate(SNAPSHOT) == before
        page.locator("#homeContinue").click()
        page.wait_for_selector("#editView", state="visible")
        assert page.evaluate("ed.id") == ids[1]
        assert not errors, errors
        print(f"{mode} restore failure preserved every photo and retry recovered all")
        context.close()
    browser.close()
