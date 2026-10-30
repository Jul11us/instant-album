"""A large collection keeps only thumbnails in memory; full photos load on demand and render identically."""
import os
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PAGE = Path(os.environ.get("INSTANT_ALBUM_TEST_PAGE", ROOT / "相角.html"))
N = 12

# Distinct source photos (as after importing N real photos); the fourth one gets a back side.
SEED = """async n => {
  ed.demo=false;ed.st.filter='原片';const base=ed;
  for(let i=0;i<n;i++){
    const c=document.createElement('canvas');c.width=base.src.width;c.height=base.src.height;
    const x=c.getContext('2d',{willReadFrequently:true});x.drawImage(base.src,0,0);
    x.fillStyle=`rgb(${20*i},90,${200-10*i})`;x.fillRect(0,0,40,40);c._ow=base.src._ow||c.width;
    const it={...base,id:newId(),src:c,srcData:x.getImageData(0,0,c.width,c.height),st:structuredClone(base.st),hist:[],_saved:false,_pix:{}};
    if(i===3){const b=mkCv(300,400),bx=b.getContext('2d');bx.fillStyle='#abc123';bx.fillRect(0,0,300,400);it.back=b}
    scans.push(it);
  }
  clearTimeout(draftT);if(!await saveDraft(true))throw Error('seed save failed');
  return scans.map(s=>s.id);
}"""
STATE = """() => {const bytes=s=>{let b=0;for(const v of Object.values(s)){
    if(v instanceof HTMLCanvasElement)b+=v.width*v.height*4;else if(v instanceof ImageData)b+=v.data.byteLength}return b};
  const light=scans.filter(s=>s!==ed);
  return {n:scans.length,cur:ed&&ed.id,full:scans.filter(s=>!!s.scanCv).map(s=>s.id),
    lazySrc:light.every(s=>s.src.width===0),lazyBack:light.filter(s=>s.back).every(s=>s.back.width===0),
    thumbs:scans.every(s=>s.thumb&&s.thumb.width>0&&Math.max(s.thumb.width,s.thumb.height)<=240),
    lightBytes:Math.max(...light.map(bytes))}}"""
OPEN = """id => ed && ed.id===id && !$('editView').hidden && !!ed.scanCv"""


def until(page, js, arg=None, timeout=20):
    # wait_for_function treats an async predicate's Promise as already truthy, so poll evaluate instead
    end = time.time() + timeout
    while time.time() < end:
        if page.evaluate(js, arg):
            return
        page.wait_for_timeout(100)
    raise AssertionError(f"timed out: {js}")


def fresh(ctx, errors):
    page = ctx.new_page()
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(PAGE.as_uri())
    page.wait_for_function("() => !restoring", timeout=60000)
    return page


with sync_playwright() as p:
    options = {"headless": True}
    if os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH"):
        options["executable_path"] = os.environ["PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH"]
    browser = p.chromium.launch(**options)
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    errors = []

    seed = fresh(ctx, errors)
    seed.locator("#homeDemo").click()
    seed.wait_for_selector("#editView", state="visible")
    ids = seed.evaluate(SEED, N)
    back_id = ids[4]
    seed.close()

    # A new tab reads the collection back: only the photo to resume holds full data.
    page = fresh(ctx, errors)
    state = page.evaluate(STATE)
    assert state["n"] == N + 1, state
    assert state["full"] == [state["cur"]], state
    assert state["lazySrc"] and state["lazyBack"] and state["thumbs"], state
    assert state["lightBytes"] <= 240 * 240 * 4, state

    # The library draws every card and the back side without keeping photos loaded.
    page.locator("#homeLibrary").click()
    page.wait_for_selector("#libPanel", state="visible")
    page.wait_for_function("""n => {const cs=[...document.querySelectorAll('#libGrid .lc canvas.fc')];
      return cs.length===n&&cs.every(c=>c.getContext('2d').getImageData(c.width>>1,c.height>>1,1,1).data[3]>0)}""", arg=N + 1, timeout=60000)
    page.wait_for_function("""id => {const c=document.querySelector(`#libGrid .lc[data-id="${id}"] canvas.bk`);
      if(!c||c.width!==280)return false;const d=c.getContext('2d').getImageData(10,10,1,1).data;
      return Math.abs(d[0]-0xab)<8&&Math.abs(d[1]-0xc1)<8&&Math.abs(d[2]-0x23)<8}""", arg=back_id, timeout=30000)
    assert page.evaluate("scans.filter(s=>!!s.scanCv).length") == 1

    # Opening photos loads them on demand; at most three stay loaded, and switching never re-saves pixels.
    page.evaluate("""() => {window.putKeys=[];const put=IDBObjectStore.prototype.put;
      IDBObjectStore.prototype.put=function(v,k){window.putKeys.push(String(k));return put.apply(this,arguments)}}""")
    first = ids[6]
    page.locator(f'#libGrid .lc[data-id="{first}"] .flip').click()
    page.wait_for_function(OPEN, arg=first)
    for other in ids[7:11]:
        page.evaluate("id => openEdit(scans.findIndex(s=>s.id===id))", other)
        page.wait_for_function(OPEN, arg=other)
    page.wait_for_function("() => $('draftStatus').dataset.state==='saved'")
    page.wait_for_timeout(1800)
    loaded = page.evaluate("scans.filter(s=>!!s.scanCv).map(s=>s.id)")
    assert len(loaded) <= 3 and ids[10] in loaded and first not in loaded, loaded
    assert page.evaluate("id => scans.find(s=>s.id===id).src.width", first) == 0
    written = page.evaluate("window.putKeys")
    assert not [k for k in written if k.split(':')[0] in ('film', 'src', 'orig', 'back')], written

    # A slow disk read must not replace a more recent selection or reopen an editor after going home.
    race = page.evaluate("""async ([slow, latest]) => {
      const get=KV.get;KV.get=async function(k){if(k==='film:'+slow)await new Promise(r=>setTimeout(r,350));return get.call(this,k)};
      try{openEdit(scans.findIndex(s=>s.id===slow));openEdit(scans.findIndex(s=>s.id===latest));
        await new Promise(r=>setTimeout(r,650));return {current:ed.id,latest}}
      finally{KV.get=get}
    }""", [ids[0], ids[10]])
    assert race['current'] == race['latest'], race
    home_race = page.evaluate("""async id => {
      const it=scans.find(s=>s.id===id);releaseFull(it);
      const get=KV.get;KV.get=async function(k){if(k==='film:'+id)await new Promise(r=>setTimeout(r,350));return get.call(this,k)};
      try{openEdit(scans.indexOf(it));showHome();await new Promise(r=>setTimeout(r,650));return !$('homeView').hidden}
      finally{KV.get=get}
    }""", ids[0])
    assert home_race, 'a completed photo read must not reopen the editor after returning home'
    page.evaluate("id => openEdit(scans.findIndex(s=>s.id===id))", ids[10])
    page.wait_for_function(OPEN, arg=ids[10])

    # Library cards complete concurrently: cache eviction must happen when each result is inserted.
    cache_size = page.evaluate("""async () => {cardCache.clear();
      await Promise.all(Array.from({length:48},(_,i)=>cardOf({...ed,id:'cache-'+i},false,120)));
      const n=cardCache.size;cardCache.clear();return n}
    """)
    assert cache_size <= 40, cache_size

    # Exporting a photo that is not loaded gives exactly the pixels of the loaded photo.
    target = ids[2]
    result = page.evaluate("""async id => {const it=scans.find(s=>s.id===id),light=!it.scanCv;
      const crc=c=>crc32(c.getContext('2d').getImageData(0,0,c.width,c.height).data);
      const a=await renderItem(it,{long:1600}),stillLight=!it.scanCv;await ensureFull(it);const b=await renderItem(it,{long:1600});
      return {light,stillLight,same:crc(a)===crc(b),size:[a.width,a.height]}}""", target)
    assert result["light"] and result["stillLight"] and result["same"], result

    # The back side, re-scanning and high-resolution export read their pixels back when needed.
    back = page.evaluate("""async id => {const it=scans.find(s=>s.id===id),c=await backAtAsync(it,800),d=c.getContext('2d').getImageData(5,5,1,1).data;
      return {lazy:it.back.width===0,size:[c.width,c.height],rgb:[...d].slice(0,3)}}""", back_id)
    assert back["lazy"] and back["size"] == [300, 400] and abs(back["rgb"][1] - 0xc1) < 8, back
    rescan = ids[11]
    page.evaluate("id => openEdit(scans.findIndex(s=>s.id===id))", rescan)
    page.wait_for_function(OPEN, arg=rescan)
    assert page.evaluate("ed.src.width") == 0
    cancelled_rescan = page.evaluate("""async () => {
      const get=KV.get,key=ed.src._key;KV.get=async function(k){if(k===key)await new Promise(r=>setTimeout(r,350));return get.call(this,k)};
      try{setSourceFromScan();showHome();await new Promise(r=>setTimeout(r,650));return !$('homeView').hidden}
      finally{KV.get=get}
    }""")
    assert cancelled_rescan, 'a completed rescan read must not leave the home screen'
    page.locator('#homeContinue').click()
    page.wait_for_function(OPEN, arg=rescan)
    page.locator("#back").click()
    page.wait_for_selector("#scanView", state="visible")
    assert page.evaluate("src===ed.src && src.width>0 && !!srcData && JSON.stringify(quad)===JSON.stringify(ed.quad)")
    hd = page.evaluate("""async id => {const it=scans.find(s=>s.id===id),big=await itemAt(it,3000);
      return {grew:big.W>it.W,srcReleased:it.src.width===0}}""", ids[1])
    assert hd["grew"] and hd["srcReleased"], hd
    page.close()

    # The thumbnail cache is only a cache: wiped or stale, it is rebuilt from the drafts.
    page = fresh(ctx, errors)
    page.evaluate("async () => {await LITE.run('readwrite',s=>s.clear())}")
    stale = ids[5]
    page.close()
    page = fresh(ctx, errors)
    assert page.evaluate(STATE)["thumbs"]
    until(page, "async n => (await LITE.keys()).length===n", N + 1)
    page.evaluate("""async id => {const r=await LITE.get(id);r.film=1;await LITE.run('readwrite',s=>s.put(r,id))}""", stale)
    page.close()
    page = fresh(ctx, errors)
    until(page, """async id => {const r=await LITE.get(id),f=await KV.get('film:'+id);return !!(r&&f&&r.film===f.size)}""", stale)
    assert page.evaluate(STATE)["thumbs"]
    page.close()

    assert not errors, errors
    browser.close()
print(f"memory: {N + 1} photos restore as thumbnails, load on demand, keep at most 3 loaded and export identical pixels")
