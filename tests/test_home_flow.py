"""Home, full-image confirmation, and truthful local-save status in Chromium."""
import base64
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PAGE = Path(os.environ.get("INSTANT_ALBUM_TEST_PAGE", ROOT / "相角.html"))

with sync_playwright() as p:
    options = {"headless": True}
    if os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH"):
        options["executable_path"] = os.environ["PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH"]
    browser = p.chromium.launch(**options)
    for width, height in ((1440, 900), (390, 844), (320, 568)):
        context = browser.new_context(viewport={"width": width, "height": height},
                                      is_mobile=width < 500, has_touch=width < 500)
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(PAGE.as_uri())
        page.wait_for_function("() => !restoring")
        assert page.locator("#homeView").is_visible()
        for control in ("#homeImport", "#homeDemo", "#homeLibrary"):
            assert page.locator(control).is_enabled(), control
        assert page.evaluate("scans.length") == 0
        assert not page.locator("#editView").is_visible()
        assert page.evaluate("document.documentElement.scrollWidth === document.documentElement.clientWidth")
        # An empty collection is a usable destination, not a disabled dead end.
        page.locator("#homeLibrary").click()
        page.wait_for_selector("#libPanel", state="visible")
        assert page.locator("#libGrid .lc").count() == 0
        page.locator("#libClose").click()
        assert page.locator("#homeView").is_visible()

        with page.expect_file_chooser() as chooser:
            page.locator("#homeImport").click()
        chooser.value.set_files([])
        assert page.locator("#homeView").is_visible()
        assert page.evaluate("scans.length") == 0
        # The sample is opt-in and must not claim to be a saved personal draft.
        page.locator("#homeDemo").click()
        page.wait_for_selector("#editView", state="visible")
        assert page.locator("#draftStatus").get_attribute("data-state") == "demo"
        page.locator("#editHome").click()
        assert page.locator("#homeView").is_visible()

        data = page.evaluate("""() => {
          const c=document.createElement('canvas');c.width=900;c.height=600;
          const x=c.getContext('2d'),im=x.createImageData(900,600);
          for(let y=0;y<600;y++)for(let z=0;z<900;z++){
            const i=(y*900+z)*4;im.data[i]=50+100*z/899;
            im.data[i+1]=60+100*y/599;im.data[i+2]=130;im.data[i+3]=255;
          }
          x.putImageData(im,0,0);
          return c.toDataURL('image/png').split(',')[1];
        }""")
        file = {"name": "ordinary-landscape.png", "mimeType": "image/png",
                "buffer": base64.b64decode(data)}
        with page.expect_file_chooser() as chooser:
            page.locator("#homeImport").click()
        chooser.value.set_files(file)
        page.wait_for_selector("#scanView", state="visible")
        page.wait_for_function("() => !importBusy")
        assert page.evaluate("scanNeedsConfirm"), "Ordinary photos need explicit framing review"
        page.locator("#fullPhoto").click()
        geometry = page.evaluate("() => ({fmt:format,q:quad,w:src.width,h:src.height})")
        assert geometry["fmt"] == "free", geometry
        expected = [[0,0],[geometry["w"],0],[geometry["w"],geometry["h"]],[0,geometry["h"]]]
        assert all(abs(a-b) <= 1.1 for point, target in zip(geometry["q"],expected)
                   for a,b in zip(point,target)), geometry
        page.locator("#straighten").click()
        page.wait_for_selector("#editView", state="visible")
        result = page.evaluate("""() => ({ratio:ed.F.img[2]/ed.F.img[3],
          colors:[[2,2],[ed.photoCv.width-3,2],[2,ed.photoCv.height-3],
            [ed.photoCv.width-3,ed.photoCv.height-3]].map(([x,y])=>
            [...ed.photoCv.getContext('2d').getImageData(x,y,1,1).data].slice(0,3))})""")
        assert abs(result["ratio"] - 1.5) < .01, result
        expected_colors = [[50,60,130],[150,60,130],[50,160,130],[150,160,130]]
        assert all(abs(a-b) < 5 for color, target in zip(result["colors"],expected_colors)
                   for a,b in zip(color,target)), result
        page.wait_for_function("() => $('draftStatus').dataset.state === 'saved'")
        page.locator('#tabs [data-t="memo"]').click()
        page.locator("#mPlace").fill("海边")
        page.locator("#mStory").fill("属于自己的照片")
        page.wait_for_function("() => $('draftStatus').dataset.state === 'saved'")

        if width == 1440:
            # Pause the next write before it reaches IndexedDB: a completed old
            # save must not be advertised as saving the new text.
            page.evaluate("""() => {
              window.originalKVRun=KV.run;window.writeBlocked=false;window.blockWrites=true;
              KV.run=function(mode,fn){
                if(mode==='readwrite'&&window.blockWrites)return new Promise((resolve,reject)=>{
                  window.writeBlocked=true;
                  window.releaseWrite=()=>{window.blockWrites=false;
                    originalKVRun.call(KV,mode,fn).then(resolve,reject)};
                });
                return originalKVRun.call(this,mode,fn);
              };
            }""")
            page.locator("#mPlace").fill("等保存完成的地点")
            page.wait_for_function("() => window.writeBlocked")
            assert page.locator("#draftStatus").get_attribute("data-state") == "saving"
            assert page.evaluate("async()=> (await KV.get('meta')).list.find(s=>s.id===ed.id).st.memo.place") == "海边"
            page.locator("#mPeople").fill("写入途中新增的人物")
            assert page.locator("#draftStatus").get_attribute("data-state") != "saved"
            page.evaluate("window.releaseWrite()")
            page.wait_for_function("() => $('draftStatus').dataset.state === 'saved'")
            assert page.evaluate("async()=> (await KV.get('meta')).list.find(s=>s.id===ed.id).st.memo.place") == "等保存完成的地点"
            assert page.evaluate("async()=> (await KV.get('meta')).list.find(s=>s.id===ed.id).st.memo.people") == "写入途中新增的人物"
            # Failed writes stay visible through subsequent edits until retry
            # actually succeeds, rather than claiming 'saved' on the next render.
            page.evaluate("""() => {
              KV.run=async function(mode,fn){if(mode==='readwrite')throw new Error('test storage failure');
                return originalKVRun.call(this,mode,fn)};
            }""")
            page.locator("#mStory").fill("未保存的故事")
            page.wait_for_function("() => $('draftStatus').dataset.state === 'error'")
            page.locator("#mPeople").fill("朋友")
            assert page.locator("#draftStatus").get_attribute("data-state") == "error"
            page.wait_for_timeout(1400)
            assert page.locator("#draftStatus").get_attribute("data-state") == "error"
            page.evaluate("() => {KV.run=window.originalKVRun}")
            page.locator("#draftRetry").click()
            page.wait_for_function("() => $('draftStatus').dataset.state === 'saved'")
            assert page.evaluate("async()=> (await KV.get('meta')).list.find(s=>s.id===ed.id).st.memo.story") == "未保存的故事"

        # Put a real back-side image and collection beside the editable photo.
        with page.expect_file_chooser() as chooser:
            page.locator('[data-bk="add"]').click()
        chooser.value.set_files(file)
        page.wait_for_function("() => !!ed.back || !$('scanView').hidden")
        if page.locator("#scanView").is_visible():
            page.locator("#straighten").click()
        page.wait_for_function("() => !!ed.back")
        page.locator("#libBtn").click()
        page.locator("#libNew").fill("海边相册")
        page.locator("#libNew").press("Enter")
        page.locator("#libGrid .lc .flip").first.click()
        page.locator("#colPick").click()
        page.locator("#libClose").click()
        page.wait_for_function("() => $('draftStatus').dataset.state === 'saved'")
        before = page.evaluate("() => ({id:ed.id,memo:ed.st.memo,cols:cols,back:!!ed.back})")
        page.reload()
        page.wait_for_function("() => !restoring")
        assert page.locator("#homeView").is_visible()
        assert not page.locator("#editView").is_visible()
        page.locator("#homeContinue").click()
        page.wait_for_selector("#editView", state="visible")
        restored = page.evaluate("() => ({id:ed.id,memo:ed.st.memo,cols:cols,back:!!ed.back})")
        assert restored == before, (before, restored)
        assert page.locator("#draftStatus").get_attribute("data-state") in ("saved", "pending", "saving")
        if width == 1440:
            # Selecting an older real photo is itself resumable. Trying the demo
            # afterwards must not steal the next Continue target.
            first_id = restored["id"]
            page.locator("#editHome").click()
            with page.expect_file_chooser() as chooser:
                page.locator("#homeImport").click()
            chooser.value.set_files(file)
            page.wait_for_selector("#scanView", state="visible")
            page.wait_for_function("() => !importBusy")
            page.locator("#fullPhoto").click()
            page.locator("#straighten").click()
            page.wait_for_selector("#editView", state="visible")
            assert page.evaluate("ed.id") != first_id
            page.locator("#libBtn").click()
            page.locator(f'#libGrid .lc[data-id="{first_id}"] [data-op="open"]').click()
            page.wait_for_function("() => $('draftStatus').dataset.state === 'saved'")
            page.locator("#editHome").click()
            page.locator("#homeDemo").click()
            page.wait_for_selector("#editView", state="visible")
            assert page.locator("#draftStatus").get_attribute("data-state") == "demo"
            page.locator("#editHome").click()
            page.locator("#homeContinue").click()
            assert page.evaluate("ed.id") == first_id
            page.reload()
            page.wait_for_function("() => !restoring")
            page.locator("#homeContinue").click()
            assert page.evaluate("ed.id") == first_id
        assert not errors, errors
        print(f"home, full image and save status passed at {width}x{height}")
        context.close()
    browser.close()
