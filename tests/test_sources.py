import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from usage_sources import codex_records, api_records, normalize_usage
from record_usage import record_usage
from serve_dashboard import Collector

class SourcesTests(unittest.TestCase):
    def test_codex_cumulative_dedup_and_project_filter(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            log = root / 'session.jsonl'
            def event(inp, out, cached):
                return {'type': 'event_msg', 'timestamp': '2026-10-09T01:00:00Z', 'payload': {'type': 'token_count', 'info': {'total_token_usage': {'input_tokens': inp, 'output_tokens': out, 'cached_input_tokens': cached, 'total_tokens': inp + out}}}}
            first, second = event(100, 20, 30), event(250, 50, 80)
            rows = [{'type': 'session_meta', 'payload': {'id': 'real-session-id', 'cwd': '/projects/app'}}, {'type': 'turn_context', 'payload': {'model': 'gpt-5-codex'}}, first, first, second, {'type': 'event_msg', 'payload': {'type': 'token_count', 'info': None}}]
            log.write_text('\n'.join(json.dumps(r) for r in rows))
            records = list(codex_records([log], '/projects/app'))
            self.assertEqual([r['raw']['total_tokens'] for r in records], [120, 180])
            self.assertEqual(sum(r['raw']['prompt_tokens_details']['cached_tokens'] for r in records), 80)
            self.assertEqual(list(codex_records([log], '/projects/other')), [])
            copy = root / 'copy.jsonl'
            copy.write_text(log.read_text() + '\n' + json.dumps(event(300, 60, 100)))
            self.assertEqual(sum(r['raw']['total_tokens'] for r in codex_records([log, copy])), 360)
            copy.unlink()
            collector = Collector(root, root / 'output.html', 'codex', '/projects/app')
            state = collector.refresh()
            self.assertIsNone(state['error'])
            self.assertEqual(state['total_tokens'], 300)
            self.assertEqual(state['requests'], 2)
            self.assertIn('/projects/app', collector.output.read_text())

    def test_api_actual_usage_dedup_and_privacy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            log = root / 'api.jsonl'
            response = {'id': 'resp_real_1', 'model': 'gpt-model', 'output': 'private response', 'usage': {'input_tokens': 400, 'output_tokens': 70, 'total_tokens': 470, 'input_tokens_details': {'cached_tokens': 100}, 'output_tokens_details': {'reasoning_tokens': 20}}}
            for _ in range(2):
                record_usage(response, log_path=log, project='my-app', session_id='development', provider='openai')
            self.assertNotIn('private response', log.read_text())
            records = list(api_records([log]))
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]['raw']['total_tokens'], 470)
            collector = Collector(root, root / 'out.html', 'api')
            self.assertEqual(collector.refresh()['total_tokens'], 470)
            with self.assertRaises(ValueError):
                record_usage({'output': 'no usage'}, log_path=log, project='app', session_id='a')

    def test_provider_cache_and_no_reasoning_double_count(self):
        usage = normalize_usage({'input_tokens': 100, 'output_tokens': 20, 'cache_read_input_tokens': 50, 'cache_creation_input_tokens': 30})
        self.assertEqual(usage['prompt_tokens'], 180)
        self.assertEqual(usage['total_tokens'], 200)
        usage = normalize_usage({'prompt_tokens': 100, 'completion_tokens': 50, 'total_tokens': 150, 'completion_tokens_details': {'reasoning_tokens': 30}})
        self.assertEqual(usage['total_tokens'], 150)
        with self.assertRaises(ValueError):
            normalize_usage({'input_tokens': -1, 'output_tokens': 2})

if __name__ == '__main__':
    unittest.main()
