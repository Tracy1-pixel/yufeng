import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/gen_dashboard.py'

class DashboardTests(unittest.TestCase):
    def test_missing_directory_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = subprocess.run([sys.executable, str(SCRIPT), '--projects', tmp + '/missing'], capture_output=True, text=True)
            self.assertNotEqual(run.returncode, 0)
            self.assertIn('会话日志目录不存在', run.stderr)

    def test_usage_workspace_isolation_subagents_and_escaping(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            logs = base / 'logs'
            def write(path, timestamp, model='glm-5.2-x'):
                path.parent.mkdir(parents=True, exist_ok=True)
                obj = {'timestamp': timestamp, 'providerData': {'model': model, 'rawUsage': {'total_tokens': 150, 'prompt_tokens': 100, 'completion_tokens': 50, 'prompt_cache_hit_tokens': 30}}}
                path.write_text('invalid json\n' + json.dumps(obj), encoding='utf-8')
            write(logs / 'one' / 'shared.jsonl', '2026-10-08T12:00:00Z')
            write(logs / 'one' / 'shared' / 'subagents' / 'agent.jsonl', '2026-10-08T10:00:00Z')
            write(logs / 'two' / 'shared.jsonl', '2026-10-08T13:00:00Z', '</script><img src=x>')
            write(logs / 'root.jsonl', '2026-10-08T14:00:00Z')
            out = base / 'dashboard.html'
            subprocess.run([sys.executable, str(SCRIPT), '--projects', str(logs), '--out', str(out)], check=True, capture_output=True)
            html = out.read_text(encoding='utf-8')
            data = json.loads(re.search(r'const D=(.*?);</script>', html).group(1).replace('<\\/', '</'))
            self.assertEqual(len(data['sess']), 3)
            self.assertEqual(sum(r[2] for s in data['sess'] for r in s['r']), 600)
            parent = next(s for s in data['sess'] if len(s['r']) == 2)
            self.assertLess(parent['r'][0][0], parent['r'][1][0])
            self.assertIn('glm-5.2', data['models'])
            self.assertNotIn('</script><img', html)

if __name__ == '__main__':
    unittest.main()
