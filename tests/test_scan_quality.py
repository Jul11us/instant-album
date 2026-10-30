"""Synthetic scan-quality cases plus desktop/mobile scan interaction regression.

These fixtures verify the heuristic and UI contract, not real-photo accuracy.
"""
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PAGE = Path(os.environ.get("INSTANT_ALBUM_TEST_PAGE", ROOT / "相角.html"))

FIXTURES = """() => {
  window.qualityFixture = (glare = false, flat = false) => {
    const canvas = document.createElement('canvas');
    canvas.width = 1000; canvas.height = 1300;
    const x = canvas.getContext('2d'), F = FORMATS.mini;
    x.fillStyle = '#302c29'; x.fillRect(0,0,1000,1300);
    const left = 180, top = 140, w = 640, h = 640 * F.H / F.W;
    x.fillStyle = '#fff'; x.fillRect(left,top,w,h);
    const px = left + w * F.img[0] / F.W;
    const py = top + h * F.img[1] / F.H;
    const pw = w * F.img[2] / F.W, ph = h * F.img[3] / F.H;
    x.save(); x.beginPath(); x.rect(px,py,pw,ph); x.clip();
    x.fillStyle = '#667788'; x.fillRect(px,py,pw,ph);
    if (!flat) for (let y = 0; y < ph; y += 12) for (let z = 0; z < pw; z += 12) {
      x.fillStyle = ((y/12 + z/12) % 2) ? '#9c8170' : '#294d68';
      x.fillRect(px+z,py+y,12,12);
    }
    const spot = [px + pw * .78, py + ph * .22];
    if (glare) {
      x.fillStyle = '#fff';
      x.fillRect(spot[0]-pw*.08,spot[1]-ph*.07,pw*.16,ph*.14);
    }
    x.restore();
    return {canvas, sd:x.getImageData(0,0,1000,1300),
      q:[[left,top],[left+w,top],[left+w,top+h],[left,top+h]], spot};
  };
  window.showQualityFixture = glare => {
    const f = qualityFixture(glare);
    setSource(f.canvas, f.q);
    format = 'mini'; quad = f.q.map(p=>p.slice()); autoFound = true;
    showScan(); refreshScanCheck();
  };
}"""

PURE_CASES = """() => {
  const good = qualityFixture(), bright = qualityFixture(true), flat = qualityFixture(false,true);
  const codes = a => a.map(v=>v.code);
  const check = (f, F=FORMATS.mini, opts={}) => scanQuality(f.sd,f.q,F,opts);
  const plain = check(good), glare = check(bright), lowTexture = check(flat);
  const free = {free:true};
  const full = [[0,0],[1000,0],[1000,1300],[0,1300]];
  const small = [[430,490],[570,490],[570,710],[430,710]];
  const base = scanQuality(good.sd,small,FORMATS.mini,{nativeScale:1});
  const native = scanQuality(good.sd,small,FORMATS.mini,{nativeScale:12});
  // The marker must stay on the same source pixels after changing orientation.
  const freeCanvas=document.createElement('canvas'); freeCanvas.width=1000; freeCanvas.height=1300;
  const fx=freeCanvas.getContext('2d');fx.fillStyle='#335577';fx.fillRect(0,0,1000,1300);
  fx.fillStyle='#fff';fx.fillRect(bright.spot[0]-43,bright.spot[1]-51,86,102);
  const freeData=fx.getImageData(0,0,1000,1300);
  const orientA = scanQuality(freeData,bright.q,free).find(v=>v.code==='glare');
  const orientB = scanQuality(freeData,rotQuad(bright.q,1),free).find(v=>v.code==='glare');
  const badInputs = [null, [[100,100],[200,100],[300,100]],
    [null,[200,100],[200,300],[100,300]], [[100,100],[200,100],[300,100],[400,100]]];
  const bad = badInputs.map(q=>codes(scanQuality(good.sd,q,FORMATS.mini)));
  // The same contrast chart should warn only after an actual blur operation.
  const chart=mkCv(800,1000),cx=chart.getContext('2d');
  for(let y=0;y<1000;y+=200)for(let x=0;x<800;x+=200){
    cx.fillStyle=((y/200+x/200)%2)?'#c5ab80':'#203750';cx.fillRect(x,y,200,200);
  }
  const focus=[0,16].map(radius=>{
    const c=mkCv(800,1000),x=c.getContext('2d');
    x.filter=`blur(${radius}px)`;x.drawImage(chart,0,0);
    return codes(scanQuality(x.getImageData(0,0,800,1000),
      [[20,20],[780,20],[780,980],[20,980]],free));
  });
  return {plain:codes(plain),glare,lowTexture:codes(lowTexture),
    framing:codes(check(good,FORMATS.mini,{trusted:false})),
    fullFree:codes(scanQuality(good.sd,full,free)),
    base:codes(base),native:codes(native),bad,focus,orientA,orientB,
    back:codes(check(bright,FORMATS.mini,{back:true})),spot:bright.spot};
}"""

with sync_playwright() as p:
    options = {"headless": True}
    if os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH"):
        options["executable_path"] = os.environ["PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH"]
    browser = p.chromium.launch(**options)
    for width, height in ((1440, 900), (320, 568)):
        context = browser.new_context(viewport={"width": width, "height": height},
                                      is_mobile=width < 500, has_touch=width < 500)
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(PAGE.as_uri())
        page.wait_for_function("() => !restoring")
        page.locator("#homeDemo").click()
        page.wait_for_selector("#save", state="visible")
        page.wait_for_function("() => !restoring")
        page.evaluate(FIXTURES)
        if width == 1440:
            result = page.evaluate(PURE_CASES)
            assert "glare" not in result["plain"], result
            assert "soft" not in result["lowTexture"], result
            assert "framing" in result["framing"], result
            assert "edge" not in result["fullFree"], result
            assert {"small", "resolution"} & set(result["base"]), result
            assert not ({"small", "resolution"} & set(result["native"])), result
            assert all("quad" in codes for codes in result["bad"]), result
            assert "soft" not in result["focus"][0] and "soft" in result["focus"][1], result
            assert not ({"glare", "soft"} & set(result["back"])), result
            patch = next(v for v in result["glare"] if v["code"] == "glare")
            for mark in (patch, result["orientA"], result["orientB"]):
                assert mark and mark.get("point"), result
                assert sum((a-b)**2 for a,b in zip(mark["point"],result["spot"])) < 80**2, result
            print("scan-quality synthetic heuristic cases passed")

        page.evaluate("showQualityFixture(true)")
        page.wait_for_function("() => document.querySelector('#scanMarks').children.length > 0")
        if width < 500:
            button = page.locator("#straighten").bounding_box()
            assert button and button["y"] >= 0 and button["y"] + button["height"] <= height + 1, button
        assert page.locator("#scanCheckTitle").inner_text().strip()
        assert page.locator("#scanCheckLead").inner_text().strip()
        if not page.locator("#scanCheck").evaluate("el => el.open"):
            page.locator("#scanCheckTitle").click()
        page.locator("#scanCheckTitle").click()
        assert not page.locator("#scanCheck").evaluate("el => el.open")
        page.locator("#scanCheckTitle").click()
        assert page.locator("#scanCheckBody").inner_text().strip()
        assert page.evaluate("document.documentElement.scrollWidth === document.documentElement.clientWidth")
        (ROOT / "_audit").mkdir(exist_ok=True)
        page.wait_for_selector("#toast", state="hidden")
        page.screenshot(path=str(ROOT / "_audit" / f"scan-quality-{'mobile' if width<500 else 'desktop'}.png"),
                        full_page=True)
        page.locator("#scanIgnore").click()
        page.wait_for_function("""() => {
          const g=document.querySelector('#scanMarks');
          return !g.children.length || getComputedStyle(g).display==='none' || getComputedStyle(g).visibility==='hidden';
        }""")
        page.locator("#scanIgnore").click()
        page.wait_for_function("""() => {
          const g=document.querySelector('#scanMarks');
          return g.children.length && getComputedStyle(g).display!=='none' && getComputedStyle(g).visibility!=='hidden';
        }""")
        # A new source must not inherit a dismissal made for the previous source.
        page.locator("#scanIgnore").click()
        page.evaluate("showQualityFixture(true)")
        page.wait_for_function("() => document.querySelector('#scanMarks').children.length > 0")
        # Moving a real corner to the source boundary must schedule a fresh check.
        page.locator("#desk").scroll_into_view_if_needed()
        drag = page.evaluate("""() => {
          const r=$('desk').getBoundingClientRect();
          return {x:r.left+view.ox+quad[0][0]*view.k,
            y:r.top+view.oy+quad[0][1]*view.k, edge:r.left+view.ox};
        }""")
        page.mouse.move(drag["x"], drag["y"])
        page.mouse.down()
        page.mouse.move(drag["edge"], drag["y"], steps=5)
        page.mouse.up()
        page.wait_for_function("() => scanHints.some(h=>h.code==='edge')")
        edge_title = page.evaluate("scanHints.find(h=>h.code==='edge').title")
        assert edge_title in page.locator("#scanCheckTitle").inner_text()
        # The real button must remain reachable and warnings must not block it.
        count = page.evaluate("scans.length")
        page.locator("#straighten").click(timeout=5000)
        page.wait_for_selector("#editView", state="visible")
        assert page.evaluate("scans.length") == count + 1
        assert not errors, errors
        print(f"scan-quality interaction passed at {width}x{height}")
        context.close()
    browser.close()
