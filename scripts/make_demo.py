"""Generate a dashboard using synthetic logs only; never reads personal logs."""
import datetime
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as directory:
    base = Path(directory)
    now = datetime.datetime.now(datetime.timezone.utc)
    models = ['deepseek-v4-flash', 'glm-5.2', 'claude-opus-4-8', 'qwen-plus']
    for w in range(3):
        folder = base / ['产品研发', '数据分析', '个人助理'][w]
        folder.mkdir()
        for session in range(4):
            records = [{'role': 'user', 'content': ['设计用量统计界面', '分析模型调用成本', '整理项目开发计划', '优化缓存命中率'][session]}]
            for day in range(30):
                for turn in range(3):
                    ts = now - datetime.timedelta(days=day, hours=turn * 3 + session)
                    inp = 1000 + (w + 1) * (session + 1) * (day + 1) * 173
                    out = 200 + turn * 321
                    records.append({'timestamp': ts.strftime('%Y-%m-%dT%H:%M:%SZ'), 'providerData': {'model': models[(w + session + turn) % 4], 'rawUsage': {'total_tokens': inp + out, 'prompt_tokens': inp, 'completion_tokens': out, 'prompt_tokens_details': {'cached_tokens': inp // 3}}}})
            (folder / f'session-{session}.jsonl').write_text('\n'.join(json.dumps(r, ensure_ascii=False) for r in records), encoding='utf-8')
    subprocess.run([sys.executable, str(ROOT / 'scripts/gen_dashboard.py'), '--projects', directory, '--out', str(ROOT / 'demo.html')], check=True)
    target = ROOT / 'demo.html'
    text = target.read_text(encoding='utf-8').replace('请求级真实 usage', '合成演示数据 · 非真实使用记录')
    text = text.replace('<body>', '<body><div style="padding:16px;margin-bottom:16px;background:#fff3cd;color:#664d03;border:2px solid #ffca2c;border-radius:10px;font-size:16px;font-weight:700">演示模式：以下所有用量及金额均为模拟数据，不是你的实际消耗。真实统计请运行 scripts/serve_dashboard.py。</div>')
    target.write_text(text, encoding='utf-8')
