"""Record actual provider response usage; no estimation or model calls."""
import datetime
import json
from pathlib import Path
import uuid

try:
    from .usage_sources import normalize_usage
except ImportError:
    from usage_sources import normalize_usage


def record_usage(response, *, log_path, project, session_id, provider='openai', model=None):
    """Call once after a completed SDK response with its actual usage object.

    Accepts SDK objects with model_dump() or dicts. Rejects absent usage.
    Full prompts, response text and API credentials are never written.
    """
    if hasattr(response, 'model_dump'):
        response = response.model_dump()
    if not isinstance(response, dict):
        raise ValueError('Expected a provider SDK response or dictionary')
    usage = response.get('usage')
    if hasattr(usage, 'model_dump'):
        usage = usage.model_dump()
    normalize_usage(usage)  # Validate before writing anything.
    obj = {'type': 'api_usage', 'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'request_id': response.get('id') or str(uuid.uuid4()), 'project': project,
           'session_id': session_id, 'provider': provider, 'model': model or response.get('model') or 'unknown',
           'usage': usage}
    path = Path(log_path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a', encoding='utf-8') as stream:
        stream.write(json.dumps(obj, ensure_ascii=False) + '\n')
    return obj['request_id']
