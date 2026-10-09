"""Local live dashboard: reads real logs, never creates sample usage."""
import argparse
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time

try:
    from .usage_sources import normalize_logs
except ImportError:
    from usage_sources import normalize_logs

PAGE = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>实时 Token 看板</title><style>body{margin:0;background:#fafaf9;font:14px system-ui}header{padding:14px 20px;border-bottom:1px solid #ddd}#status{margin-left:16px;color:#666}iframe{width:100%;height:calc(100vh - 65px);border:0}</style><header><b>真实用量 · 实时采集</b><span id="status">正在读取日志…</span></header><iframe title="真实 Token 消耗看板" id="dashboard"></iframe><script>
let version='';async function poll(){try{const r=await fetch('/api/status',{cache:'no-store'});if(!r.ok)throw Error('服务响应异常');const s=await r.json();document.querySelector('#status').textContent=s.error?'采集失败：'+s.error:s.available?(s.source==='codex'?'Codex 用量增量（非精确请求数） · ':s.source==='api'?'API 响应 usage · ':'WorkBuddy 日志 · ')+s.requests+' 条用量记录 · 最后读取 '+new Date(s.updated*1000).toLocaleTimeString():'暂无数据：未发现包含真实 usage 的日志';if(s.error){document.querySelector('#dashboard').removeAttribute('src');version='';}else if(s.version!==version){document.querySelector('#dashboard').src='/dashboard.html?v='+s.version;version=s.version;}}catch(e){document.querySelector('#status').textContent='连接中断，正在重试';}finally{setTimeout(poll,2000)}}poll();</script></html>'''

class Collector:
    def __init__(self, projects, output, source="workbuddy", project_root=None):
        self.source = source
        self.project_root = project_root
        self.projects = Path(projects).expanduser().resolve()
        self.output = Path(output)
        self.lock = threading.Lock()
        self.fingerprint = None
        self.checked = 0
        self.updated = 0
        self.status = {'version': '', 'available': False, 'requests': 0, 'updated': 0, 'error': None}

    def refresh(self):
        with self.lock:
            now = time.time()
            if now - self.checked < 1:
                return dict(self.status)
            self.checked = now
            try:
                files = sorted(self.projects.rglob('*.jsonl')) if self.projects.is_dir() else []
                fingerprint = [(str(f), f.stat().st_mtime_ns, f.stat().st_size) for f in files]
                if fingerprint == self.fingerprint and now - self.updated < 60:
                    return dict(self.status)
                # An absent source is an empty state, never a demonstration fallback.
                labels = {}
                with tempfile.TemporaryDirectory() as empty:
                    source = self.projects if self.projects.is_dir() else Path(empty)
                    if self.source != 'workbuddy':
                        source = Path(empty)
                        labels = normalize_logs(files, source, self.source, self.project_root)
                    run = subprocess.run([sys.executable, str(Path(__file__).with_name('gen_dashboard.py')), '--projects', str(source), '--out', str(self.output)], capture_output=True, text=True, timeout=60)
                if run.returncode:
                    raise RuntimeError('日志解析失败，请检查文件格式和读取权限')
                html = self.output.read_text(encoding='utf-8')
                raw = html.split('<script>const D=', 1)[1].split(';</script>', 1)[0]
                data = json.loads(raw.replace('<\\/', '</'))
                data['ws'] = [labels.get(name, name) for name in data['ws']]
                new_raw = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
                html = html.replace('<script>const D=' + raw + ';</script>', '<script>const D=' + new_raw + ';</script>')
                if self.source == 'codex':
                    html = html.replace('请求级真实 usage', 'Codex 日志真实累计用量增量').replace('次请求', '条用量记录').replace('单次请求', '单条用量记录').replace("['轮次',", "['用量记录',")
                if self.source in ('codex', 'api'):
                    html = html.replace("['预估金额（元）',money]", "['参考预估金额（元）',D.models.every(m=>Object.keys(PRICE).some(k=>m.toLowerCase().startsWith(k)))?money:'未配置价格']")
                self.output.write_text(html, encoding='utf-8')
                count = sum(len(s['r']) for s in data['sess'])
                tokens = sum(r[2] for s in data['sess'] for r in s['r'])
                self.status = {'version': hashlib.sha256(html.encode()).hexdigest()[:16], 'available': bool(count), 'requests': count, 'total_tokens': tokens, 'updated': now, 'error': None, 'source': self.source}
                self.fingerprint, self.updated = fingerprint, now
            except (OSError, RuntimeError, ValueError, IndexError, subprocess.TimeoutExpired):
                self.status = {**self.status, 'error': '无法读取真实日志，请检查目录、权限或日志格式'}
            return dict(self.status)


def handler_for(collector):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            path = self.path.split('?', 1)[0]
            if path == '/':
                body, kind, status = PAGE.encode(), 'text/html; charset=utf-8', 200
            elif path == '/api/status':
                body, kind, status = json.dumps(collector.refresh(), ensure_ascii=False).encode(), 'application/json; charset=utf-8', 200
            elif path == '/dashboard.html':
                state = collector.refresh()
                if state['error']:
                    body, kind, status = b'Log collection failed', 'text/plain', 503
                else:
                    body, kind, status = collector.output.read_bytes(), 'text/html; charset=utf-8', 200
            else:
                body, kind, status = b'Not found', 'text/plain', 404
            self.send_response(status)
            self.send_header('Content-Type', kind)
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            self.wfile.write(body)
    return Handler


def main():
    parser = argparse.ArgumentParser(description='实时统计 Codex / API / WorkBuddy 的真实 usage（无模拟数据）')
    parser.add_argument('--source', choices=['codex', 'api', 'workbuddy'], default='codex')
    parser.add_argument('--projects', help='真实日志目录；Codex 默认 ~/.codex/sessions')
    parser.add_argument('--project-root', help='Codex 只统计此项目路径及其子目录的会话')
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        defaults = {'codex': Path.home() / '.codex/sessions', 'api': Path.home() / '.token-dashboard/api', 'workbuddy': Path.home() / '.workbuddy/projects'}
        collector = Collector(args.projects or defaults[args.source], Path(tmp) / 'dashboard.html', args.source, args.project_root)
        server = ThreadingHTTPServer(('127.0.0.1', args.port), handler_for(collector))
        print(f'实时看板：http://127.0.0.1:{server.server_port}（只读取本机日志，不上传）', flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()

if __name__ == '__main__':
    main()
