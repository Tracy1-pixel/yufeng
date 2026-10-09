import importlib.util
import json
from pathlib import Path
import tempfile
import threading
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from http.server import ThreadingHTTPServer
import unittest
from urllib.request import urlopen

spec = importlib.util.spec_from_file_location('live', Path(__file__).resolve().parents[1] / 'scripts/serve_dashboard.py')
live = importlib.util.module_from_spec(spec)
spec.loader.exec_module(live)

class LiveTests(unittest.TestCase):
    def test_missing_then_appended_usage_is_counted_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'projects'
            collector = live.Collector(source, root / 'out.html')
            server = ThreadingHTTPServer(('127.0.0.1', 0), live.handler_for(collector))
            threading.Thread(target=server.serve_forever, daemon=True).start()
            address = f'http://127.0.0.1:{server.server_port}'
            try:
                def status():
                    collector.checked = 0
                    with urlopen(address + '/api/status') as response:
                        return json.load(response)
                initial = status()
                self.assertFalse(initial['available'])
                self.assertEqual(initial['requests'], 0)
                folder = source / 'workspace'
                folder.mkdir(parents=True)
                entry = {'timestamp': '2026-10-09T00:00:00Z', 'providerData': {'model': 'deepseek', 'rawUsage': {'total_tokens': 123, 'prompt_tokens': 100, 'completion_tokens': 23}}}
                logfile = folder / 'session.jsonl'
                logfile.write_text(json.dumps(entry) + '\n', encoding='utf-8')
                first = status()
                self.assertTrue(first['available'])
                self.assertEqual(first['requests'], 1)
                self.assertNotEqual(initial['version'], first['version'])
                self.assertEqual(status()['requests'], 1)
                with logfile.open('a') as stream:
                    stream.write(json.dumps(entry) + '\n')
                self.assertEqual(status()['requests'], 2)
                with urlopen(address + '/dashboard.html') as response:
                    html = response.read().decode()
                data = json.loads(html.split('<script>const D=')[1].split(';</script>')[0])
                self.assertEqual(sum(r[2] for s in data['sess'] for r in s['r']), 246)
                self.assertNotIn('合成演示数据', html)
            finally:
                server.shutdown()
                server.server_close()

if __name__ == '__main__':
    unittest.main()
