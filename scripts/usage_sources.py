"""Normalize real Codex/API usage into the dashboard's log format."""
import datetime
import json
from pathlib import Path


def objects(path):
    with path.open(encoding='utf-8') as stream:
        for line in stream:
            try:
                obj = json.loads(line)
            except ValueError:
                continue  # Includes the last partially written line of a live log.
            if isinstance(obj, dict):
                yield obj


def number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
        raise ValueError('Usage must contain nonnegative numeric counts')
    return int(value)


def normalize_usage(usage):
    """Supports OpenAI Responses/Chat Completions and Anthropic usage."""
    if hasattr(usage, 'model_dump'):
        usage = usage.model_dump()
    if not isinstance(usage, dict):
        raise ValueError('Response has no supported usage object')
    inp = usage.get('input_tokens', usage.get('prompt_tokens'))
    out = usage.get('output_tokens', usage.get('completion_tokens'))
    if inp is None or out is None:
        raise ValueError('Response usage must include input and output tokens')
    inp, out = number(inp), number(out)
    details = usage.get('input_tokens_details') or usage.get('prompt_tokens_details') or {}
    cached = number(usage.get('cached_input_tokens', usage.get('cache_read_input_tokens', details.get('cached_tokens', 0))))
    created = number(usage.get('cache_creation_input_tokens', 0))
    # Anthropic input_tokens excludes cache reads/writes; OpenAI input includes them.
    if 'cache_read_input_tokens' in usage or 'cache_creation_input_tokens' in usage:
        inp += cached + created
    total = number(usage.get('total_tokens', inp + out))
    return {'total_tokens': total, 'prompt_tokens': inp, 'completion_tokens': out,
            'prompt_tokens_details': {'cached_tokens': cached, 'cached_creation_tokens': created}}


def api_records(files):
    seen = set()
    for path in files:
        for obj in objects(path):
            if obj.get('type') != 'api_usage':
                continue
            identity = (obj.get('provider', 'api'), obj.get('request_id'))
            if not identity[1] or identity in seen:
                continue
            raw = normalize_usage(obj.get('usage'))
            seen.add(identity)
            yield {'workspace': obj.get('project', 'API 调用'), 'session': obj.get('session_id', 'api'),
                   'timestamp': obj.get('timestamp'), 'model': obj.get('model', 'unknown'), 'raw': raw}


def codex_records(files, project_root=None):
    seen = set()
    previous_by_session = {}
    for path in files:
        rows = list(objects(path))
        meta = next((r.get('payload', {}) for r in rows if r.get('type') == 'session_meta'), {})
        cwd = meta.get('cwd') or 'Codex'
        if project_root:
            target = Path(project_root).expanduser().resolve()
            actual = Path(cwd).expanduser().resolve()
            if actual != target and target not in actual.parents:
                continue
        sid = meta.get('id') or path.stem
        model = 'unknown'
        previous = previous_by_session.get(sid)
        for row in rows:
            payload = row.get('payload') or {}
            if row.get('type') == 'turn_context':
                model = payload.get('model') or model
                continue
            if row.get('type') != 'event_msg' or payload.get('type') != 'token_count':
                continue
            info = payload.get('info') or {}
            totals = info.get('total_token_usage')
            if not isinstance(totals, dict):
                continue  # Rate-limit-only messages contain no usage.
            identity = (sid, json.dumps(totals, sort_keys=True))
            if identity in seen:
                continue
            seen.add(identity)
            current = {key: number(totals.get(key, 0)) for key in
                       ('input_tokens', 'cached_input_tokens', 'output_tokens', 'total_tokens')}
            if 'total_tokens' not in totals:
                current['total_tokens'] = current['input_tokens'] + current['output_tokens']
            if previous is None:
                delta = current
            elif any(current[k] < previous[k] for k in current):
                # If a cumulative counter resets, only a recorded last-call usage is usable.
                last = info.get('last_token_usage')
                if not isinstance(last, dict):
                    raise ValueError('Codex cumulative usage reset without last_token_usage')
                delta = last
            else:
                delta = {key: current[key] - previous[key] for key in current}
            previous = current
            previous_by_session[sid] = current
            if not delta.get('total_tokens', delta.get('input_tokens', 0) + delta.get('output_tokens', 0)):
                continue
            yield {'workspace': cwd, 'session': sid, 'timestamp': row.get('timestamp'),
                   'model': model, 'raw': normalize_usage(delta)}


def normalize_logs(files, output, source, project_root=None):
    output = Path(output)
    records = codex_records(files, project_root) if source == 'codex' else api_records(files)
    handles = {}
    labels = {}
    try:
        for rec in records:
            # Hash path components so user/project names never become filesystem paths.
            import hashlib
            key = (str(rec['workspace']), str(rec['session']))
            if key not in handles:
                folder = output / hashlib.sha256(key[0].encode()).hexdigest()[:16]
                folder.mkdir(parents=True, exist_ok=True)
                labels[folder.name] = key[0]
                name = hashlib.sha256(key[1].encode()).hexdigest()[:16]
                handles[key] = (folder / (name + '.jsonl')).open('w', encoding='utf-8')
                handles[key].write(json.dumps({'role': 'user', 'content': key[0] + ' · ' + key[1]}) + '\n')
            obj = {'sessionId': key[1], 'timestamp': rec['timestamp'],
                   'providerData': {'model': rec['model'], 'rawUsage': rec['raw']}}
            handles[key].write(json.dumps(obj) + '\n')
    finally:
        for handle in handles.values():
            handle.close()

    return labels
