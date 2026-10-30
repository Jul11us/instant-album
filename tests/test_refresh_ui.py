"""Real interactions for the compact scanner and editable recent-photo gallery."""
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PAGE = Path(os.environ.get("INSTANT_ALBUM_TEST_PAGE", ROOT / "相角.html"))

THUMB = """async el => {
  const media=el.querySelector('canvas,img');
  if(media instanceof HTMLImageElement)await media.decode();
  const c=document.createElement('canvas');c.width=c.height=32;
  const x=c.getContext('2d');x.drawImage(media,0,0,32,32);
  const d=x.getImageData(8,8,16,16).data;
  return [...d].filter((_,i)=>i%4!==3).reduce((s,v)=>s+v,0)/(16*16*3);
}"""

with sync_playwright() as p:
    options = {"headless": True}
    if os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH"):
        options["executable_path"] = os.environ["PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH"]
    browser = p.chromium.launch(**options)
    for width, height in ((1440,900),(390,844),(320,568)):
        context = browser.new_context(viewport={"width":width,"height":height},
                                      is_mobile=width<500,has_touch=width<500)
        page = context.new_page()
        errors=[]
        page.on("pageerror",lambda e:errors.append(str(e)))
        page.goto(PAGE.as_uri())
        page.wait_for_function("() => !restoring")
        assert page.locator(".home-print:not(.rear)").is_visible()
        assert page.locator("#homeGallery button").count()==0
        assert page.evaluate("document.documentElement.scrollWidth === document.documentElement.clientWidth")
        (ROOT/"_audit").mkdir(exist_ok=True)
        page.screenshot(path=str(ROOT/"_audit"/f"refresh-cold-home-{width}.png"),full_page=True,animations="disabled")
        with page.expect_file_chooser() as chooser:
            page.locator("#homeImport").click()
        chooser.value.set_files(str(ROOT/"design-demos/assets/sample.jpg"))
        page.wait_for_selector("#scanView",state="visible")
        page.wait_for_function("() => !importBusy")
        assert not page.locator("#formats").is_visible()
        assert not page.locator("#scanMore").evaluate("e=>e.open")
        assert not page.locator("#camBtn").is_visible()
        assert page.locator("#formatCurrent").inner_text().strip()
        if width<500:
            button=page.locator("#straighten").bounding_box()
            assert button and button["y"]>=0 and button["y"]+button["height"]<=height+1,button
        # Camera exploration is available, but no longer occupies the default scan view.
        page.locator("#scanMore summary").click()
        assert page.locator("#camBtn").is_visible()
        assert page.locator("#td3d").is_visible()
        page.locator("#scanMore summary").click()
        # The collapsed format control must actually expose a working selection.
        page.locator("#formatToggle").click()
        page.wait_for_selector("#formats",state="visible")
        page.locator('#formats [data-f="square"]').click()
        assert "SQUARE" in page.locator("#formatCurrent").inner_text()
        assert page.evaluate("format") == "square"
        page.locator("#fullPhoto").click()
        assert page.evaluate("format") == "free"
        assert "原比例" in page.locator("#formatCurrent").inner_text()
        old_quad=page.evaluate("quad.map(p=>p.slice())")
        old_ratio=page.evaluate("FORMATS.free.img[2]/FORMATS.free.img[3]")
        page.locator("#rot").click()
        assert page.evaluate("quad[0]") == old_quad[1]
        new_ratio=page.evaluate("FORMATS.free.img[2]/FORMATS.free.img[3]")
        assert abs(old_ratio*new_ratio-1)<.001,(old_ratio,new_ratio)
        page.locator("#desk").scroll_into_view_if_needed()
        drag=page.evaluate("""() => {
          const r=$('desk').getBoundingClientRect();
          return {x:r.left+view.ox+quad[0][0]*view.k,
            y:r.top+view.oy+quad[0][1]*view.k};
        }""")
        before=page.evaluate("quad[0].slice()")
        # Grab the visible inner portion; the desk rounds off its outer corner.
        page.mouse.move(drag["x"]-8,drag["y"]+8)
        page.mouse.down()
        page.mouse.move(drag["x"]-20,drag["y"]+20,steps=5)
        page.mouse.up()
        assert page.evaluate("quad[0]") != before
        page.locator("#fullPhoto").click()
        page.locator("#straighten").click()
        page.wait_for_selector("#editView",state="visible")
        photo_id=page.evaluate("ed.id")
        page.wait_for_function("() => $('draftStatus').dataset.state==='saved'")
        page.locator("#editHome").click()
        card=page.locator(f'#homeGallery button[data-id="{photo_id}"]')
        card.wait_for(state="visible")
        page.wait_for_function("""id => {
          const m=document.querySelector(`#homeGallery button[data-id="${id}"] canvas,#homeGallery button[data-id="${id}"] img`);
          return m && (m instanceof HTMLCanvasElement ? m.width>0 : m.dataset.ready==='1'&&m.complete&&m.naturalWidth>0);
        }""",arg=photo_id)
        before_thumb=card.evaluate(THUMB)
        card.click()
        page.wait_for_selector("#editView",state="visible")
        assert page.evaluate("ed.id") == photo_id
        page.locator('#tabs [data-t="sliders"]').click()
        slider=page.locator('#sliders input[data-k="bright"]')
        slider.focus()
        page.keyboard.press("End")
        assert page.evaluate("ed.st.bright") == 50
        page.locator("#editHome").click()
        card.wait_for(state="visible")
        # Wait for the asynchronous edited card to replace the previous preview.
        page.wait_for_function("""({id,old}) => {
          const m=document.querySelector(`#homeGallery button[data-id="${id}"] canvas,#homeGallery button[data-id="${id}"] img`);
          if(!m||(m instanceof HTMLImageElement&&(!m.complete||m.dataset.ready!=='1')))return false;
          const c=document.createElement('canvas');c.width=c.height=32;
          const x=c.getContext('2d');x.drawImage(m,0,0,32,32);
          const d=x.getImageData(8,8,16,16).data;let n=0;
          for(let i=0;i<d.length;i++)if(i%4!==3)n+=d[i];
          return n/(16*16*3)>old+5;
        }""",arg={"id":photo_id,"old":before_thumb})
        assert card.evaluate(THUMB)>before_thumb+5
        assert page.locator(".home-print:not(.rear)").is_visible()
        assert page.evaluate("document.documentElement.scrollWidth === document.documentElement.clientWidth")
        (ROOT/"_audit").mkdir(exist_ok=True)
        page.locator("#homeView").evaluate("el=>el.scrollTop=0")
        page.screenshot(path=str(ROOT/"_audit"/f"refresh-home-{width}.png"),full_page=True,animations="disabled")
        assert not errors,errors
        print(f"compact scan controls and recent edited gallery passed at {width}x{height}")
        context.close()
    # Long editor forms must leave a usable photo preview in portrait and landscape.
    for width,height in ((320,568),(740,320),(844,390)):
        context=browser.new_context(viewport={"width":width,"height":height},
                                   is_mobile=True,has_touch=True,reduced_motion='reduce')
        page=context.new_page()
        page.goto(PAGE.as_uri())
        page.wait_for_function('() => !restoring')
        page.locator('#homeDemo').click()
        page.wait_for_selector('#editView',state='visible')
        page.locator('#tabs [data-t="memo"]').click()
        geometry=page.evaluate("""() => {
          layoutCard();
          const card=$('card').getBoundingClientRect(),note=$('note').getBoundingClientRect(),
            stage=$('stage').getBoundingClientRect(),save=$('save').getBoundingClientRect();
          return {height:card.height,top:card.top,bottom:card.bottom,noteBottom:note.bottom,
            stageBottom:stage.bottom,saveTop:save.top,saveBottom:save.bottom};
        }""")
        assert geometry['height']>=80,geometry
        assert geometry['top']>=geometry['noteBottom']+4,geometry
        assert geometry['bottom']<=geometry['stageBottom']-4,geometry
        assert geometry['saveTop']>=0 and geometry['saveBottom']<=height+1,geometry
        assert page.evaluate('document.documentElement.scrollWidth === innerWidth')
        page.screenshot(path=str(ROOT/'_audit'/f'editor-short-{width}x{height}.png'),animations='disabled')
        context.close()
        print(f'usable editor preview and camera help passed at {width}x{height}')
    browser.close()
