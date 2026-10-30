"""Exercise manual batch scanning and native text shortcuts in real Chromium."""
import base64
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PAGE = Path(os.environ.get('INSTANT_ALBUM_TEST_PAGE', ROOT / '相角.html'))
with sync_playwright() as p:
    options = {'headless': True}
    if os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH'):
        options['executable_path'] = os.environ['PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH']
    browser = p.chromium.launch(**options)
    for width, height in ((1440, 900), (390, 844)):
        context = browser.new_context(viewport={'width': width, 'height': height})
        page = context.new_page()
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto(PAGE.as_uri())
        page.wait_for_function("() => !restoring")
        page.locator("#homeDemo").click()
        page.wait_for_selector('#save', state='visible')
        page.wait_for_function('() => !restoring')
        page.evaluate('() => { commit(); ed.st.bright = 25; }')
        page.locator('#tabs [data-t="memo"]').click()
        for field in ('#mPlace', '#mPeople', '#mStory'):
            page.locator(field).click()
            page.keyboard.type('test memory')
            text_history_size = page.evaluate('history.length')
            page.keyboard.press('Control+z')
            assert page.evaluate('history.length') == text_history_size, field
            remaining = page.locator(field).input_value()
            assert remaining != 'test memory' and 'test memory'.startswith(remaining), (field, remaining)
            assert page.evaluate('ed.st.bright') == 25, field
        # Non-text focus still supports photo undo.
        history_size = page.evaluate('history.length')
        page.locator('#peek').focus()
        page.keyboard.press('Control+z')
        assert page.evaluate('history.length') == history_size - 1
        images = page.evaluate('''() => ['#775533','#336655','#445577'].map(color => {
          const c=document.createElement('canvas');c.width=300;c.height=300;
          const x=c.getContext('2d');x.fillStyle=color;x.fillRect(0,0,300,300);
          return c.toDataURL().split(',')[1];
        })''')
        files = [{'name': f'blank-{i}.png', 'mimeType': 'image/png',
                  'buffer': base64.b64decode(data)} for i, data in enumerate(images)]
        before = page.evaluate('scans.length')
        page.locator('#fileIn').set_input_files(files)
        page.wait_for_selector('#scanView', state='visible')
        page.wait_for_function('() => !importBusy')
        # Leave the first unfinished scan, then resume from the visible queue.
        page.locator('#tray button.t').first.click()
        assert page.locator('#tray2 .pending').inner_text() == '继续框选（3 张）'
        page.locator('#back').click()
        page.locator('#tray .pending').click()
        page.wait_for_function('() => !importBusy')
        for i in range(3):
            page.locator('#straighten').click()
            page.wait_for_function('() => !importBusy')
            assert page.evaluate('scans.length') == before + i + 1
            if i < 2:
                assert page.locator('#scanView').is_visible()
        assert page.locator('#editView').is_visible()
        assert page.locator('.pending').count() == 0
        colors = page.evaluate('''() => scans.filter(s=>!s.demo).map(s=>
          [...s.srcData.data.slice(0,3)])''')
        assert colors == [[119,85,51],[51,102,85],[68,85,119]], colors
        assert page.evaluate('() => document.documentElement.scrollWidth === document.documentElement.clientWidth')
        assert page.evaluate('() => {clearTimeout(draftT);return saveDraft()}')
        page.reload()
        page.wait_for_function('() => !restoring && ed && !ed.demo')
        page.locator("#homeContinue").click()
        assert page.evaluate('scans.length') == 3
        assert not errors, errors
        print(f'import queue and text shortcuts passed at {width}px')
        context.close()
    browser.close()
