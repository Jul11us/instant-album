"""Editable backup round-trip, hostile archive rejection, and explicit UI restore.

Uses isolated Chromium contexts and generated images; no personal data is read.
"""
import base64
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PAGE = Path(os.environ.get('INSTANT_ALBUM_TEST_PAGE', ROOT / '相角.html'))

SEED = """async () => {
  ed.demo=false;
  ed.src._file=new File([await toBlob(ed.src,'image/png')],'original.png',{type:'image/png'});
  ed.src._saved=false;
  ed.st.filter='海盐';ed.st.bright=11;ed.st.contrast=-7;ed.st.warm=13;ed.st.grain=6;
  ed.st.caption='海边的那一天';ed.st.font='song';ed.st.sticker=2;ed.st.sx=.3;ed.st.sy=.7;
  ed.st.memo={place:'海边',people:'朋友',story:'完整回忆 <也允许普通文字>',print:['place','people']};
  ed.st.date={on:true,d:'2024-07-20',fmt:'YY.MM.DD',look:'ink',pos:'frame',guess:false,p:'month'};
  ed.st.spots=[[.2,.3,.025]];
  ed.back=mkCv(ed.W,ed.H);ed.back.getContext('2d').fillStyle='#c2a481';
  ed.back.getContext('2d').fillRect(0,0,ed.W,ed.H);
  customFrame=mkCv(ed.W,ed.H);customFrame.getContext('2d').fillStyle='#55aa99';
  customFrame.getContext('2d').fillRect(0,0,ed.W,ed.H);ed.st.frame='draw';
  uploadFrame=mkCv(ed.W,ed.H);uploadFrame.getContext('2d').fillStyle='#997755';
  uploadFrame.getContext('2d').fillRect(0,0,ed.W,ed.H);
  cols=[{id:newId(),name:'夏天',cover:ed.id,ids:[ed.id]}];
  pages=[{id:newId(),tpl:'wall',pick:[ed.id],title:'海边的一页',bg:'#DCE7DA',tape:'kraft',tilt:1,seed:3,t:Date.now()}];
  clearTimeout(draftT);if(!await saveDraft())throw Error('seed save failed');
  const keys=await KV.keys();
  window.backupSeed=await Promise.all(keys.map(async k=>[k,await KV.get(k)]));
  return {photo:ed.id,meta:await KV.get('meta'),keys:keys.sort()};
}"""

MODULE_CASES = """async () => {
  const blob=await AlbumBackup.create(backupSeed),archive=JSON.parse(await blob.text());
  const restored=await AlbumBackup.parse(blob),byKey=new Map(restored);
  const equal=[];
  for(const [key,value] of backupSeed){const b=byKey.get(key),bytes=key==='meta'?null:new Uint8Array(await b.arrayBuffer());
    equal.push(key==='meta'?JSON.stringify(value)===JSON.stringify(b):
      value.type===b.type&&value.size===b.size&&
        [...new Uint8Array(await value.arrayBuffer())].every((v,i)=>v===bytes[i]));
  }
  const mutate=fn=>{const a=structuredClone(archive);fn(a);return new Blob([JSON.stringify(a)],{type:'application/json'})};
  const meta=a=>a.entries.find(e=>e.key==='meta').value;
  const attempts={
    invalid_json:new Blob(['{broken']),
    unknown_version:mutate(a=>a.version=999),
    wrong_marker:mutate(a=>a.marker='unrelated-file'),
    duplicate_key:mutate(a=>a.entries.push(a.entries[0])),
    foreign_key:mutate(a=>a.entries.push({key:'secrets',kind:'json',value:{}})),
    missing_film:mutate(a=>a.entries=a.entries.filter(e=>!e.key.startsWith('film:'))),
    missing_source:mutate(a=>a.entries=a.entries.filter(e=>!e.key.startsWith('src:'))),
    missing_back:mutate(a=>a.entries=a.entries.filter(e=>!e.key.startsWith('back:'))),
    missing_frame:mutate(a=>a.entries=a.entries.filter(e=>e.key!=='frame:draw')),
    injected_id:mutate(a=>meta(a).list[0].id='x\" onclick=\"alert(1)'),
    prototype_id:mutate(a=>meta(a).list[0].srcId='__proto__'),
    injected_date:mutate(a=>meta(a).list[0].st.date.d='\" autofocus onfocus=alert(1)'),
    invalid_date:mutate(a=>meta(a).list[0].st.date.d='2023-02-30'),
    injected_label:mutate(a=>meta(a).list[0].F.label='<img src=x onerror=alert(1)>'),
    invalid_free_flag:mutate(a=>meta(a).list[0].F.free='yes'),
    injected_color:mutate(a=>meta(a).pages[0].bg='red\" onclick=\"alert(1)'),
    invalid_template:mutate(a=>meta(a).pages[0].tpl='__proto__'),
    dangling_album:mutate(a=>meta(a).cols[0].ids=['missing-photo']),
    dangling_page:mutate(a=>meta(a).pages[0].pick=['missing-photo']),
    crossed_quad:mutate(a=>{const q=meta(a).list[0].quad;[q[1],q[2]]=[q[2],q[1]]}),
    oversized_quad:mutate(a=>meta(a).list[0].quad[0][0]=8000),
    nonfinite_number:mutate(a=>meta(a).list[0].st.bright=null),
    corrupted_base64:mutate(a=>{const e=a.entries.find(e=>e.kind==='blob');e.data='!'+e.data.slice(1)}),
    corrupted_bytes:mutate(a=>{const e=a.entries.find(e=>e.kind==='blob');e.data=(e.data[0]==='A'?'B':'A')+e.data.slice(1)}),
    wrong_size:mutate(a=>a.entries.find(e=>e.kind==='blob').size++),
    enormous_size:mutate(a=>a.entries.find(e=>e.kind==='blob').size=AlbumBackup.limits.blobBytes+1),
    wrong_raster_type:mutate(a=>a.entries.find(e=>e.key.startsWith('film:')).mime='image/svg+xml'),
    oversized_raster:mutate(a=>{const e=a.entries.find(e=>e.key==='frame:draw');
      const bytes=Uint8Array.from(atob(e.data),c=>c.charCodeAt(0));new DataView(bytes.buffer).setUint32(16,1000000);
      e.data=btoa(String.fromCharCode(...bytes));e.checksum=crc32(bytes).toString(16).padStart(8,'0')}),
    prototype_property:mutate(a=>Object.defineProperty(meta(a).list[0].st,'__proto__',{value:{polluted:true},enumerable:true}))
  };
  const rejected={};for(const [name,file] of Object.entries(attempts)){
    try{await AlbumBackup.parse(file);rejected[name]=false}catch(e){rejected[name]=true}
  }
  const empty=await AlbumBackup.parse(await AlbumBackup.create([]));
  const metaOnly={v:1,cur:0,list:[],cols:[{id:'empty-album',name:'等下一张',cover:null,ids:[]}],pages:[]};
  const emptyAlbum=await AlbumBackup.parse(await AlbumBackup.create([['meta',metaOnly]]));
  const extremeRow=structuredClone(archive.entries.find(e=>e.key==='meta').value.list[0]);
  extremeRow.fmt='free';extremeRow.F={name:'原比例',label:'原比例 · 不按相纸',W:8.62,H:82,img:[4,4,.62,62],free:true};
  extremeRow.ow=40;extremeRow.quad=[[0,0],[40,0],[40,4000],[0,4000]];extremeRow.back=false;extremeRow.st.frame='orig';
  const extremeMeta={v:1,cur:0,list:[extremeRow],cols:[],pages:[]};
  const src=mkCv(40,4000),film=mkCv(168,1600);
  const extreme=await AlbumBackup.parse(await AlbumBackup.create([['meta',extremeMeta],
    ['src:'+extremeRow.srcId,await toBlob(src,'image/png')],['film:'+extremeRow.id,await toBlob(film,'image/png')]]));
  window.backupValidBytes=new Uint8Array(await blob.arrayBuffer());
  window.backupBadBytes=new TextEncoder().encode(JSON.stringify({...archive,version:999}));
  return {equal,rejected,empty:empty.length,emptyAlbum:emptyAlbum[0][1],extreme:extreme.length,size:blob.size};
}"""

with sync_playwright() as p:
    options = {'headless': True}
    if os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH'):
        options['executable_path'] = os.environ['PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH']
    browser = p.chromium.launch(**options)
    context = browser.new_context(viewport={'width':1440,'height':900},accept_downloads=True)
    page = context.new_page()
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(PAGE.as_uri())
    page.wait_for_function('() => !restoring')
    page.locator('#homeDemo').click()
    page.wait_for_selector('#editView',state='visible')
    if not page.evaluate('typeof AlbumBackup !== "undefined"'):
        page.add_script_tag(path=str(ROOT/'src/backup.js'))
    seeded=page.evaluate(SEED)
    result=page.evaluate(MODULE_CASES)
    assert all(result['equal']),result
    assert all(result['rejected'].values()),result['rejected']
    assert result['empty']==0 and result['emptyAlbum']['cols'][0]['name']=='等下一张' and result['extreme']==3,result
    assert page.evaluate('({}).polluted === undefined')
    assert page.evaluate('async () => (await KV.keys()).sort()')==seeded['keys']
    print(f"backup byte-exact round-trip and {len(result['rejected'])} invalid archive cases passed")

    if page.locator('#backupOpen').count():
        page.locator('#editHome').click()
        page.locator('#backupOpen').click()
        page.wait_for_selector('#backupPanel',state='visible')
        with page.expect_download() as download:
            page.locator('#backupExport').click()
        exported=Path(download.value.path()).read_bytes()
        portable=json.loads(exported)
        assert portable['marker']=='instant-album-backup' and portable['version']==1
        data=bytes(page.evaluate('[...backupValidBytes]'))
        bad=bytes(page.evaluate('[...backupBadBytes]'))
        page.locator('#backupIn').set_input_files({'name':'invalid.instant-album.json','mimeType':'application/json','buffer':bad})
        page.wait_for_function("() => !backupBusy")
        assert page.locator('#backupApply').is_hidden()
        assert page.evaluate('async () => (await KV.keys()).sort()')==seeded['keys']
        page.locator('#backupIn').set_input_files({'name':'collection.instant-album.json','mimeType':'application/json','buffer':data})
        page.wait_for_function("() => !$('backupApply').disabled")
        assert page.locator('#backupSummary').inner_text().strip()
        assert page.evaluate('async () => (await KV.keys()).sort()')==seeded['keys']
        # Change current data after creating a backup; restoration must replace it.
        page.evaluate("async () => {cols[0].name='后来修改';ed.st.memo.story='后来写的故事';clearTimeout(draftT);await saveDraft()}")
        before_failure=page.evaluate("async () => ({meta:await KV.get('meta'),keys:(await KV.keys()).sort(),memory:JSON.stringify([scans.map(s=>[s.id,s.st]),cols,pages,ed?.id])})")
        # A synchronous put failure after clear and an earlier queued put must
        # abort the whole transaction, preserving the collection byte-for-byte.
        page.evaluate("""() => {
          window.backupPut=IDBObjectStore.prototype.put;let n=0;
          IDBObjectStore.prototype.put=function(...args){
            if(++n===2)throw new DOMException('simulated restore failure','DataCloneError');
            return window.backupPut.apply(this,args);
          };
        }""")
        page.locator('#backupApply').click()
        page.wait_for_function("() => !backupBusy")
        page.evaluate('() => {IDBObjectStore.prototype.put=window.backupPut}')
        after_failure=page.evaluate("async () => ({meta:await KV.get('meta'),keys:(await KV.keys()).sort(),memory:JSON.stringify([scans.map(s=>[s.id,s.st]),cols,pages,ed?.id])})")
        assert after_failure==before_failure,(before_failure,after_failure)
        assert page.locator('#backupPanel').is_visible()
        page.locator('#backupApply').click()
        page.wait_for_function("() => !restoring && !$('homeView').hidden && $('backupPanel').hidden")
        restored=page.evaluate("async () => ({meta:await KV.get('meta'),keys:(await KV.keys()).sort(),back:!!scans[0]?.back,draw:!!customFrame,upload:!!uploadFrame})")
        assert restored['meta']==seeded['meta'],restored
        assert restored['keys']==seeded['keys'] and restored['back'] and restored['draw'] and restored['upload'],restored
        assert page.evaluate("async () => {const b=await KV.get('orig:'+scans[0].src._id);return b instanceof Blob&&b.type==='image/png'}")
        page.locator('#homeContinue').click()
        page.locator('#save').click()
        assert page.locator('#expPanel').is_visible()
        print('backup export, validation preview, explicit replacement and editability passed')
        page.locator('#expClose').click()
        page.locator('#editHome').click()
        page.set_viewport_size({'width':320,'height':568})
        page.evaluate("""async () => {
          const get=KV.get;KV.get=async function(k){if(k==='meta')throw Error('simulated read failure');return get.call(this,k)};
          await loadHomeDrafts();KV.get=get;
        }""")
        assert page.evaluate('restoreFailed')
        assert page.locator('#backupOpen').is_enabled()
        page.locator('#backupOpen').click()
        assert page.locator('#backupExport').is_disabled()
        page.locator('#backupIn').set_input_files({'name':'recovery.instant-album.json','mimeType':'application/json','buffer':data})
        page.wait_for_function("() => !backupBusy && !$('backupApply').hidden")
        assert page.evaluate('document.documentElement.scrollWidth === document.documentElement.clientWidth')
        page.locator('#backupApply').click()
        page.wait_for_function("() => !restoring && !restoreFailed && !$('homeView').hidden")
        assert page.evaluate('scans.length')==1
        assert page.evaluate('!!scans[0].back')
        print('mobile backup recovery remains available after a failed initial read')
    else:
        print('backup UI not embedded yet; module tests completed')
    assert not errors,errors
    context.close()
    browser.close()
