"""Optional UI test: pip install playwright; uses system Chromium."""
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import threading
from pathlib import Path
from playwright.sync_api import sync_playwright

root = Path(__file__).resolve().parents[1]
server = ThreadingHTTPServer(('127.0.0.1', 0), partial(SimpleHTTPRequestHandler, directory=str(root)))
threading.Thread(target=server.serve_forever, daemon=True).start()
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path='/usr/bin/chromium', args=['--no-sandbox'])
    page = browser.new_page(viewport={'width': 1440, 'height': 1100})
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.goto(f'http://127.0.0.1:{server.server_port}/demo.html')
    assert page.locator('#kpis .kpi').count() == 7
    assert page.locator('[data-ws]').count() == 3
    assert page.evaluate('aggregate().turns') > 1000
    for selector in ['#mdSvg', '#dmSvg', '#rdSvg']:
        assert page.locator(selector).inner_html()
    page.locator('#themeBtn').click()
    assert page.locator('body').evaluate("e => e.classList.contains('dark')")
    page.reload()
    assert page.locator('body').evaluate("e => e.classList.contains('dark')")
    for days in [1, 3, 7, 30]:
        page.locator(f'.pill[data-w="{days}"]').click()
        assert page.evaluate('aggregate().turns') > 0
    page.locator('[data-ws]').first.click()
    page.locator('[data-ses]').first.click()
    assert page.locator('#reqView svg').count() == 1
    page.locator('[data-v="tb"]').click()
    assert page.locator('table.rt tbody tr').count() > 0
    page.locator('[data-a="root"]').click()
    page.locator('#wsSearch').fill('没有此工作空间')
    assert page.locator('#panel .empty').count() == 1
    page.locator('#wsSearch').fill('')
    page.locator('[data-dm]').first.click()
    page.locator('[data-hrm]').first.click()
    day = page.evaluate('new Date(D.genMs-86400000).toISOString().slice(0,10)')
    page.locator('#dStart').fill(day)
    page.locator('#dEnd').fill(day)
    assert page.evaluate('aggregate().turns') > 0
    assert page.evaluate('(()=>{let n=0;iterReq((s,r)=>n+=r.length);return n===aggregate().turns})()')
    page.locator('.pill[data-w="30"]').click()
    page.set_viewport_size({'width': 390, 'height': 844})
    page.wait_for_timeout(300)
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    assert not errors, errors
    browser.close()
server.shutdown()
print('PASS: KPI, charts, themes, windows, dates, search, model highlights, drill-down and mobile layout')
