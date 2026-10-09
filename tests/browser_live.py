"""UI regression with temporary fixtures, never real personal logs."""
import datetime
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import sys
import tempfile
import threading
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from serve_dashboard import Collector, handler_for

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    logs = root / 'sessions'
    logs.mkdir()
    path = logs / 'session.jsonl'
    def event(inp, out):
        return {'type': 'event_msg', 'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'payload': {'type': 'token_count', 'info': {'total_token_usage': {'input_tokens': inp, 'output_tokens': out, 'cached_input_tokens': 0, 'total_tokens': inp + out}}}}
    rows = [{'type': 'session_meta', 'payload': {'id': 'test-only-session', 'cwd': '/projects/test-only'}}, {'type': 'turn_context', 'payload': {'model': 'gpt-test-only'}}, event(100, 20)]
    path.write_text('\n'.join(json.dumps(r) for r in rows) + '\n')
    collector = Collector(logs, root / 'dashboard.html', 'codex')
    server = ThreadingHTTPServer(('127.0.0.1', 0), handler_for(collector))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path='/usr/bin/chromium', args=['--no-sandbox'])
            page = browser.new_page()
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(f'http://127.0.0.1:{server.server_port}')
            frame = page.frame_locator('#dashboard')
            frame.locator('#kpis .kpi .v').first.filter(has_text='120').wait_for()
            assert frame.locator('#kpis').inner_text().find('用量记录') >= 0
            assert '未配置价格' in frame.locator('#kpis').inner_text()
            with path.open('a') as stream:
                stream.write(json.dumps(event(250, 50)) + '\n')
            frame.locator('#kpis .kpi .v').first.filter(has_text='300').wait_for(timeout=10000)
            assert 'Codex' in page.locator('#status').inner_text()
            assert collector.status['total_tokens'] == 300
            assert not errors, errors
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
print('PASS: real-usage adapter UI auto-refresh, cumulative dedup, no invented model prices')
