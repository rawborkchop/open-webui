import json
def merge_delta(target, delta):
    for key, value in delta.items():
        if isinstance(value, dict):
            if not isinstance(target.get(key), dict):
                target[key] = {}
            merge_delta(target[key], value)
        elif isinstance(value, str) and key not in {'id', 'type', 'role', 'format'}:
            target[key] = target.get(key, '') + value
        elif isinstance(value, list) and key in {'tool_calls', 'reasoning_details'}:
            current = target.setdefault(key, [])
            for item in value:
                if not isinstance(item, dict) or 'index' not in item:
                    current.append(item)
                    continue
                previous = next((part for part in current if isinstance(part, dict) and part.get('index') == item['index']), None)
                if previous is None:
                    current.append(dict(item))
                else:
                    merge_delta(previous, item)
        else:
            target[key] = value
class ResponseProjection:
    def __init__(self):
        self.buffer = b''
        self.data_lines = []
        self.result = {}
        self.terminal = False
        self.error = False
    def feed(self, data):
        self.buffer += data
        while b'\n' in self.buffer:
            line, self.buffer = self.buffer.split(b'\n', 1)
            line = line.rstrip(b'\r')
            if not line:
                self.dispatch()
            elif line.startswith(b'data:'):
                self.data_lines.append(line[5:].lstrip(b' '))
    def dispatch(self):
        data = b'\n'.join(self.data_lines)
        self.data_lines = []
        if data == b'[DONE]':
            self.terminal = True
            return
        try:
            item = json.loads(data)
        except (ValueError, UnicodeDecodeError):
            return
        if not isinstance(item, dict):
            return
        kind = item.get('type', '')
        if item.get('error') or kind in {'error', 'response.failed', 'response.incomplete'}:
            self.error = True
            self.result['error'] = item.get('error', item)
        if kind in {'response.completed', 'response.failed', 'response.incomplete'}:
            self.terminal = True
            self.result.update(item.get('response') or {})
        for key in ('id', 'model', 'usage', 'provider', 'system_fingerprint'):
            if item.get(key) is not None:
                self.result[key] = item[key]
        for choice in item.get('choices') or []:
            if not isinstance(choice, dict):
                continue
            choices = self.result.setdefault('choices', [])
            index = choice.get('index', 0)
            current = next((part for part in choices if part['index'] == index), None)
            if current is None:
                current = {'index': index, 'message': {}}
                choices.append(current)
            merge_delta(current['message'], choice.get('delta') or choice.get('message') or {})
            if choice.get('finish_reason') is not None:
                current['finish_reason'] = choice['finish_reason']
        if kind == 'response.output_item.added':
            self.result.setdefault('output', []).append(item.get('item', {}))
        elif kind.endswith('.delta') and 'delta' in item:
            # Preserve a useful partial projection if a Responses stream is interrupted.
            self.result.setdefault('partial_output', []).append({key: value for key, value in item.items() if key != 'sequence_number'})
