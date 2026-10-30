"""Exercise 3D entry points, responsive part access and model-specific facts.

Evo 2 expected specifications: https://www.instax.com/mini_evo_2/en/spec/
The browser 3D feature loads its pinned Three.js module from the CDN.
"""
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
    page = browser.new_page(viewport={'width': 1440, 'height': 900})
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(PAGE.as_uri(), wait_until='domcontentloaded')
    page.wait_for_function('() => !restoring')
    page.locator('#home3d').click()
    page.wait_for_function("() => typeof td!=='undefined' && td?.model && $('tdLoad').hidden", timeout=45000)
    page.locator('#tdCams [data-id="evo2"]').click()

    # A model loaded wide must still offer access to every part after narrowing.
    page.set_viewport_size({'width': 390, 'height': 844})
    more = page.locator('#tdParts [data-more]')
    assert more.is_visible(), 'wide-to-narrow resizing must retain the expand button'
    assert page.locator('#tdParts .more:visible').count() == 0
    more.click()
    assert page.locator('#tdParts [data-p]:visible').count() == page.locator('#tdParts [data-p]').count()

    # Clicking a model part also reveals its otherwise-collapsed list button.
    page.evaluate("loadModel('evo2'); select(td.parts.find(p=>p.id==='battery'),false)")
    assert page.locator('#tdParts [data-p="battery"]').is_visible()

    for part, expected, absent in [
        ('cmos', ['1/2.77', '2144 × 2860', '3100 × 4128'], ['1/5 英寸', '490 万']),
        ('battery', ['90 张'], ['100 张']),
        ('print', ['14 秒'], ['13 秒']),
    ]:
        page.locator(f'#tdParts [data-p="{part}"]').click()
        detail = page.locator('#tdDetail').inner_text()
        assert all(value in detail for value in expected), (part, detail)
        assert not any(value in detail for value in absent), (part, detail)

    # Switching models cannot carry Evo 2's values into the original Evo.
    page.locator('#tdCams [data-id="evo"]').click()
    page.locator('#tdParts [data-more]').click()
    page.locator('#tdParts [data-p="battery"]').click()
    assert '100 张' in page.locator('#tdDetail').inner_text()
    assert '90 张' not in page.locator('#tdDetail').inner_text()
    page.locator('#tdClose').click()
    assert page.locator('#homeView').is_visible()
    assert not errors, errors
    browser.close()

print('3D home entry, wide-to-narrow part access and model-specific details passed')
