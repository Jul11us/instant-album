"""Home motion stays accessible, optional, and separate from photo data."""
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PAGE = Path(os.environ.get('INSTANT_ALBUM_TEST_PAGE', ROOT/'相角.html'))

SETUP = """(() => {
  const request=window.requestAnimationFrame;
  const animate=Element.prototype.animate;
  window.motionRafCalls=0;window.motionAnimateCalls=0;window.motionTitleEntries=0;
  window.requestAnimationFrame=function(...args){window.motionRafCalls++;return request.apply(this,args)};
  if(animate)Element.prototype.animate=function(...args){
    if(this.closest('#homeView'))window.motionAnimateCalls++;
    if(this.id==='homeTitle')window.motionTitleEntries++;
    return animate.apply(this,args);
  };
})()"""
SEED = """async () => {
  ed.demo=false;ed.st.filter='原片';ed.st.grain=0;ed.st.caption='';ed.st.date.on=false;
  ed.st.sticker=0;const current=ed.id;
  for(let i=0;i<3;i++)scans.push({...ed,id:newId(),st:structuredClone(ed.st),hist:[]});
  clearTimeout(draftT);if(!await saveDraft())throw Error('sample setup failed');
  return current;
}"""
PIXELS = """async id => {
  const item=scans.find(s=>s.id===id),c=await renderItem(item,{bare:true,long:240});
  return crc32(c.getContext('2d').getImageData(0,0,c.width,c.height).data);
}"""
VARS = """el => {
  const s=getComputedStyle(el);
  return ['--card-rx','--card-ry'].map(k=>parseFloat(s.getPropertyValue(k))||0);
}"""
ANIMATIONS = """() => document.getAnimations().filter(a=>
  (a.playState==='running'||a.pending)&&a.effect?.target&&$('homeView').contains(a.effect.target)).length"""
FRONT = "() => $('homeStack').querySelector('.home-print:not(.rear) img').id"
VISIBLE = """el => {
  for(let n=el;n;n=n.parentElement){const s=getComputedStyle(n);
    if(s.visibility==='hidden'||s.display==='none'||+s.opacity<.99)return false}
  return !!el.getClientRects().length;
}"""

def start(browser, width=1440, height=900, reduced=False, no_observer=False):
    context=browser.new_context(viewport={'width':width,'height':height},
        is_mobile=width<500,has_touch=width<500,
        reduced_motion='reduce' if reduced else 'no-preference')
    context.add_init_script(SETUP)
    if no_observer:
        context.add_init_script("Object.defineProperty(window,'IntersectionObserver',{value:undefined,configurable:true})")
    page=context.new_page()
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(PAGE.as_uri())
    page.wait_for_function('() => !restoring')
    page.wait_for_selector('#homeStack',state='visible')
    return context,page,errors

def owned_gallery(page):
    page.locator('#homeDemo').click()
    page.wait_for_selector('#editView',state='visible')
    photo=page.evaluate(SEED)
    pixels=page.evaluate(PIXELS,photo)
    meta=page.evaluate("async () => await KV.get('meta')")
    page.locator('#editHome').click()
    page.wait_for_selector('#homeGallery button',state='visible')
    return photo,pixels,meta

with sync_playwright() as p:
    options={'headless':True}
    if os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH'):
        options['executable_path']=os.environ['PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH']
    browser=p.chromium.launch(**options)

    # Mouse and keyboard interactions change presentation only.
    ctx,page,errors=start(browser)
    stack=page.locator('#homeStack')
    assert stack.get_attribute('role')=='button'
    assert stack.get_attribute('tabindex')=='0'
    assert stack.get_attribute('aria-label')
    photo,pixels,meta=owned_gallery(page)
    # Click (without hovering), Enter and Space each send the front photo to the back; one photo is in front.
    assert page.evaluate(FRONT)=='homeSample'
    stack.dispatch_event('click')
    assert page.evaluate(FRONT)=='homeSecond'
    assert page.locator('#homeStack .home-print:not(.rear)').count()==1
    stack.focus();page.keyboard.press('Enter')
    assert page.evaluate(FRONT)=='homeThird'
    page.keyboard.press('Space')
    assert page.evaluate(FRONT)=='homeSample'
    stack.dispatch_event('keydown',{'key':' ','repeat':True})
    assert page.evaluate(FRONT)=='homeSample'
    # A mouse moving onto the stack rotates at once and keeps rotating while it stays.
    rect=stack.bounding_box()
    page.mouse.move(rect['x']+rect['width']*.8,rect['y']+rect['height']*.2)
    assert page.evaluate(FRONT)=='homeSecond'
    page.wait_for_function("() => $('homeStack').querySelector('.home-print:not(.rear) img').id==='homeThird'",timeout=4000)
    page.wait_for_function("() => ['--card-rx','--card-ry'].some(k=>Math.abs(parseFloat(getComputedStyle($('homeStack')).getPropertyValue(k))||0)>.1)")
    tilted=stack.evaluate(VARS)
    assert all(abs(v)<=4 for v in tilted),tilted
    page.mouse.move(2,2)
    page.wait_for_function("() => ['--card-rx','--card-ry'].every(k=>Math.abs(parseFloat(getComputedStyle($('homeStack')).getPropertyValue(k))||0)<.01)")
    # Leaving the stack stops the rotation.
    left_on=page.evaluate(FRONT)
    page.wait_for_timeout(2200)
    assert page.evaluate(FRONT)==left_on,'Rotation must stop once the mouse leaves'
    # Leaving in the same task must cancel a queued pointer frame, too.
    stack.evaluate("""el => {
      const r=el.getBoundingClientRect();el.dispatchEvent(new PointerEvent('pointermove',
        {pointerType:'mouse',clientX:r.right-5,clientY:r.top+5}));
      el.dispatchEvent(new PointerEvent('pointerleave',{pointerType:'mouse'}));
    }""")
    page.wait_for_timeout(50)
    assert stack.evaluate(VARS)==[0,0]
    assert page.evaluate("async () => await KV.get('meta')")==meta
    assert page.evaluate(PIXELS,photo)==pixels
    assert page.evaluate('motionTitleEntries')==1,'Returning home must not replay the opening title animation'
    page.wait_for_function(ANIMATIONS.replace('.length','.length===0'))
    calls=page.evaluate('motionRafCalls')
    page.wait_for_timeout(300)
    assert page.evaluate('motionRafCalls')-calls<=2,'Home must not run an endless animation-frame loop'
    # Changing the system preference cancels running motion and hover tilt; photos still rotate, instantly.
    rect=stack.bounding_box();page.mouse.move(rect['x']+rect['width']*.8,rect['y']+rect['height']*.2)
    stack.click()
    page.emulate_media(reduced_motion='reduce')
    page.wait_for_function("() => !document.getAnimations().some(a=>(a.playState==='running'||a.pending)&&a.effect?.target&&$('homeView').contains(a.effect.target))")
    assert stack.evaluate(VARS)==[0,0]
    assert stack.get_attribute('aria-disabled')=='false'
    before=page.evaluate(FRONT);calls=page.evaluate('motionAnimateCalls')
    stack.focus();page.keyboard.press('Space')
    assert page.evaluate(FRONT)!=before
    assert page.evaluate('motionAnimateCalls')==calls,'Reduced motion swaps photos without animating them'
    assert page.evaluate(ANIMATIONS)==0
    # Hover rotation is off under reduced motion, even with the mouse resting on the stack.
    resting=page.evaluate(FRONT)
    page.mouse.move(2,2);rect=stack.bounding_box();page.mouse.move(rect['x']+rect['width']*.5,rect['y']+rect['height']*.5)
    page.wait_for_timeout(2200)
    assert page.evaluate(FRONT)==resting,'Reduced motion must not rotate photos on hover'
    page.emulate_media(reduced_motion='no-preference')
    before=page.evaluate(FRONT)
    stack.focus();page.keyboard.press('Enter')
    assert page.evaluate(FRONT)!=before
    page.locator(f'#homeGallery button[data-id="{photo}"]').click()
    page.wait_for_selector('#editView',state='visible')
    assert page.evaluate('ed.id')==photo
    assert page.evaluate(PIXELS,photo)==pixels
    assert not errors,errors
    ctx.close()
    print('home hover rotation, mouse tilt, click and keyboard rotation, live reduced motion and unchanged photo data passed')

    # Touch taps rotate the photos; touch movement leaves tilt at zero and preserves pan-y.
    ctx,page,errors=start(browser,width=390,height=568)
    photo,pixels,meta=owned_gallery(page)
    stack=page.locator('#homeStack')
    stack.scroll_into_view_if_needed()
    page.touchscreen.tap(**{k:round(v) for k,v in zip(('x','y'),(
        stack.bounding_box()['x']+stack.bounding_box()['width']/2,
        stack.bounding_box()['y']+stack.bounding_box()['height']/2))})
    assert page.evaluate(FRONT)=='homeSecond'
    rect=stack.bounding_box()
    stack.dispatch_event('pointermove',{'pointerType':'touch','clientX':rect['x']+rect['width']*.8,'clientY':rect['y']+20})
    assert stack.evaluate(VARS)==[0,0]
    page.touchscreen.tap(x=round(rect['x']+rect['width']/2),y=round(rect['y']+rect['height']/2))
    assert page.evaluate(FRONT)=='homeThird'
    page.locator('#homeView').evaluate('el=>el.scrollTop=0')
    stack.scroll_into_view_if_needed()
    rect=stack.bounding_box();x=round(rect['x']+rect['width']/2)
    y=round(min(rect['y']+rect['height']*.75,535))
    before=page.locator('#homeView').evaluate('el=>el.scrollTop')
    session=ctx.new_cdp_session(page)
    session.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':x,'y':y}]})
    for i in range(1,9):
        session.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':x,'y':y-i*22}]})
        page.wait_for_timeout(20)
    session.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]})
    page.wait_for_function('old => $("homeView").scrollTop>old+10',arg=before)
    assert page.evaluate(FRONT)=='homeThird','A scroll gesture must not rotate the photos'
    assert stack.evaluate(VARS)==[0,0]
    page.locator(f'#homeGallery button[data-id="{photo}"]').click()
    page.wait_for_selector('#editView',state='visible')
    assert page.evaluate('ed.id')==photo
    assert page.evaluate(PIXELS,photo)==pixels
    assert not errors,errors
    ctx.close()
    print('mobile card tap, native vertical scroll, no touch tilt and gallery navigation passed')

    # Reduced-motion cold start and unavailable observer both leave content usable.
    for reduced,no_observer in ((True,False),(False,True)):
        ctx,page,errors=start(browser,width=390,height=844,reduced=reduced,no_observer=no_observer)
        page.wait_for_function(ANIMATIONS.replace('.length','.length===0'))
        assert page.locator('#homeTitle').evaluate(VISIBLE)
        assert page.locator('#homeImport').is_enabled()
        if reduced:
            assert page.evaluate('motionAnimateCalls')==0,'Reduced-motion cold start must not run entrance animations'
            assert page.evaluate(FRONT)=='homeSample'
            assert page.locator('#homeStack').evaluate(VARS)==[0,0]
            assert page.locator('#homeStack').get_attribute('aria-disabled')=='false'
        photo,pixels,meta=owned_gallery(page)
        page.locator(f'#homeGallery button[data-id="{photo}"]').scroll_into_view_if_needed()
        page.wait_for_function(ANIMATIONS.replace('.length','.length===0'))
        assert page.locator(f'#homeGallery button[data-id="{photo}"]').evaluate(VISIBLE)
        if reduced:
            assert page.evaluate('motionAnimateCalls')==0
        assert not errors,errors
        ctx.close()
        print(f'home content fallback passed: reduced={reduced}, observer_missing={no_observer}')
    # A small personal collection must never cycle through the stock examples.
    # The last-focused photo also belongs in the stack only once.
    for count in (1,2,3):
        ctx,page,errors=start(browser,reduced=True)
        page.locator('#homeDemo').click()
        page.wait_for_selector('#editView',state='visible')
        page.evaluate("""async count => {
          ed.demo=false;ed.st.caption='personal-1';
          for(let i=1;i<count;i++){
            const copy={...ed,id:newId(),st:structuredClone(ed.st),hist:[]};
            copy.st.caption='personal-'+(i+1);scans.push(copy);
          }
          clearTimeout(draftT);if(!await saveDraft())throw Error('sample setup failed');
        }""",count)
        page.locator('#editHome').click()
        stack=page.locator('#homeStack')
        assert page.locator('#homeStack .home-print:visible').count()==count
        assert stack.get_attribute('aria-disabled')==str(count==1).lower()
        seen=set()
        for _ in range(count+1):
            front=page.locator('#homeStack .home-print:not(.rear) img')
            seen.add(front.get_attribute('alt'))
            assert front.evaluate('el => ![HOME_FRONT,SAMPLE_SECOND,SAMPLE_THIRD].includes(el.src)')
            stack.dispatch_event('click')
        assert len(seen)==count,seen
        assert any('personal-1' in label for label in seen),seen
        assert page.evaluate('scans.length')==count
        assert not errors,errors
        ctx.close()
        print(f'personal-only carousel passed with {count} photo(s)')
    browser.close()
