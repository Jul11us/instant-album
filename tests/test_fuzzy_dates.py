"""Exercise photo dates that are only remembered as a month, season, year or not at all."""
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
with sync_playwright() as playwright:
    options = {"headless": True}
    executable = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH")
    if executable:
        options["executable_path"] = executable
    browser = playwright.chromium.launch(**options)
    for width, height in ((1440, 900), (390, 844)):
        context = browser.new_context(viewport={"width": width, "height": height},
                                      is_mobile=width < 500, has_touch=width < 500)
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto((ROOT / "贴进相册.html").as_uri())
        page.wait_for_function("() => !restoring")
        page.locator("#homeDemo").click()
        page.wait_for_selector("#save", state="visible", timeout=30000)
        page.click("#back")
        page.locator("#fileIn").set_input_files(str(ROOT / "design-demos/assets/sample.jpg"))
        page.click("#straighten")
        page.locator('#tabs [data-t="memo"]').click()

        # Moving a 31st into February must leave a valid date, and each
        # select change must have its own undo step.
        page.evaluate("""() => {
          ed.st.date = {...ed.st.date, p:'day', d:'2025-01-31', guess:false};
          history.length = 0; syncControls();
        }""")
        page.locator('#memo [data-dp="month"]').click()
        page.locator('#mMon').select_option('2')
        assert page.evaluate('ed.st.date.d') == '2025-02-28'
        page.click('#undo')
        assert page.evaluate("[ed.st.date.p, ed.st.date.d]") == ['month', '2025-01-31']
        page.locator('#mMon').select_option('2')
        page.locator('#memo [data-dp="day"]').click()
        assert page.locator('#mDate').input_value() == '2025-02-28'
        assert '自动调整过，请核对' in page.locator('#memo').inner_text()
        page.locator('#mDate').fill('2025-02-27')
        page.locator('#mDate').dispatch_event('change')
        assert not page.evaluate('ed.st.date.adjusted')

        # A leap day changed to a non-leap year must also remain valid.
        page.evaluate("""() => {
          ed.st.date = {...ed.st.date, p:'day', d:'2024-02-29', guess:false};
          history.length = 0; syncControls();
        }""")
        page.locator('#memo [data-dp="year"]').click()
        page.locator('#mYear').fill('2023')
        page.locator('#mYear').dispatch_event('change')
        assert page.evaluate('ed.st.date.d') == '2023-02-28'
        page.click('#undo')
        assert page.evaluate("[ed.st.date.p, ed.st.date.d]") == ['year', '2024-02-29']
        page.locator('#mYear').fill('2023')
        page.locator('#mYear').dispatch_event('change')
        page.locator('#memo [data-dp="day"]').click()
        assert page.locator('#mDate').input_value() == '2023-02-28'

        # A season selection is independently undoable too.
        page.evaluate("""() => {
          ed.st.date = {...ed.st.date, p:'season', d:'2023-04-28', s:'spring', guess:false};
          history.length = 0; syncControls();
        }""")
        page.locator('#mSea').select_option('summer')
        page.click('#undo')
        assert page.evaluate("[ed.st.date.p, ed.st.date.s, ed.st.date.d]") == ['season', 'spring', '2023-04-28']

        # Only the season is remembered: "2023 summer".
        page.locator('#memo [data-dp="season"]').click()
        page.locator("#mYear").fill("2023")
        page.locator("#mYear").dispatch_event("change")
        page.locator("#mSea").select_option("summer")
        state = page.evaluate("() => ({p: ed.st.date.p, s: ed.st.date.s, label: dLabel(ed.st.date), stamp: dateText(ed.st.date), guess: ed.st.date.guess})")
        assert state == {"p": "season", "s": "summer", "label": "2023 夏天", "stamp": "2023", "guess": False}, state

        # A bad year is rejected and the old one kept.
        page.locator("#mYear").fill("23")
        page.locator("#mYear").dispatch_event("change")
        assert page.evaluate("() => ed.st.date.d.slice(0, 4)") == "2023"

        # Timeline order: unknown first, then year-only, month, the days of that month, the season.
        order = page.evaluate("""() => {
            const mk = (p, d, s) => ({st: {date: {p, d, s}}, n: [p, d, s].join('|')});
            const xs = [mk('season', '2023-07-01', 'summer'), mk('day', '2023-07-14'), mk('month', '2023-07-01'),
                        mk('year', '2023-01-01'), mk('none', '2020-01-01'), mk('day', '2022-12-31')];
            return xs.sort(cmpD).map(x => x.n);
        }""")
        assert order == ["none|2020-01-01|", "day|2022-12-31|", "year|2023-01-01|", "month|2023-07-01|",
                         "day|2023-07-14|", "season|2023-07-01|summer"], order

        page.click("#libBtn", timeout=5000)
        assert page.locator("#libGrid h4").first.text_content() == "2023 年夏天"
        for query in ("2023年夏天", "夏天", "2023"):
            page.locator("#libQ").fill(query)
            page.wait_for_function(f"() => lib.q === '{query}' && document.querySelectorAll('#libGrid .lc').length === 1")
        page.locator("#libQ").fill("2023.07")
        page.wait_for_function("() => lib.q === '2023.07' && document.querySelectorAll('#libGrid .lc').length === 0")
        page.locator("#libQ").fill("")
        page.click("#libClose")

        # Not remembered at all: nothing is stamped and the library says so.
        page.locator('#tabs [data-t="memo"]').click()
        page.locator('#memo [data-dp="none"]').click()
        assert page.evaluate("() => [dLabel(ed.st.date), dateText(ed.st.date), dGroup(ed.st.date)]") == ["", "", "日期未知"]
        page.click("#libBtn", timeout=5000)
        page.locator("#libQ").fill("日期未知")
        page.wait_for_function("() => document.querySelectorAll('#libGrid .lc').length === 1")
        page.locator("#libQ").fill("")
        page.click("#libClose")

        # "About 2019" renders on a timeline page and survives a reload.
        page.locator('#tabs [data-t="memo"]').click()
        page.locator('#memo [data-dp="about"]').click()
        page.locator("#mYear").fill("2019")
        page.locator("#mYear").dispatch_event("change")
        assert page.evaluate("() => dLabel(ed.st.date)") == "约 2019"
        page.evaluate("async () => { openAlbum([ed.id]); alb.tpl = 'timeline'; await albumCanvas() }")
        page.evaluate("() => { clearTimeout(draftT); return saveDraft() }")
        page.reload()
        page.wait_for_function("() => !restoring && ed && !ed.demo", timeout=30000)
        page.locator("#homeContinue").click()
        restored = page.evaluate("() => ed.st.date")
        assert restored["p"] == "about" and restored["d"].startswith("2019"), restored
        assert page.evaluate("() => document.documentElement.scrollWidth === document.documentElement.clientWidth")
        assert not errors, errors
        print(f"fuzzy date regression passed at {width}x{height}")
        context.close()
    browser.close()
