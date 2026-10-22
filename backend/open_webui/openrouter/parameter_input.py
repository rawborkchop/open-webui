from copy import deepcopy
import json
from open_webui.openrouter.json_paths import get_path, set_path
ENVELOPE = {'model', 'messages', 'input', 'prompt', 'params',
    'chat_id', 'id', 'message_ids', 'parent_id', 'parent_message', 'user_message', 'assistant_message_id',
    'session_id', 'folder_id', 'files', 'filter_ids', 'tool_ids', 'skill_ids', 'terminal_id', 'tool_servers',
    'features', 'variables', 'chat_variables', 'model_item', 'background_tasks', 'regeneration_prompt',
    'automation_id', 'new_chat', 'responses', 'type'}
WEBUI_PARAMS = {'stream_response', 'stream_delta_chunk_size', 'function_calling', 'reasoning_tags',
    'compact_token_threshold', 'note_id', 'tool_approval_mode', 'model_controls'}
ALIASES = {'max_completion_tokens': 'max_tokens', 'max_output_tokens': 'max_tokens', 'reasoning_effort': 'reasoning.effort'}
def canonical_payload(payload):
    result = deepcopy(payload)
    for alias, canonical in ALIASES.items():
        if alias in result:
            value = result.pop(alias)
            sentinel = object()
            existing = get_path(result, canonical, sentinel)
            if existing is not sentinel and existing != value:
                raise ValueError(f'Conflicting values for {canonical}')
            set_path(result, canonical, value)
    return result
def parameter_input(body):
    if not isinstance(body, dict):
        raise ValueError('Request body must be an object')
    result = {key: deepcopy(value) for key, value in body.items() if key not in ENVELOPE}
    params = body.get('params') or {}
    if not isinstance(params, dict):
        raise ValueError('params must be an object')
    params = deepcopy(params)
    custom = params.pop('custom_params', {}) or {}
    if not isinstance(custom, dict):
        raise ValueError('custom_params must be an object')
    for key, value in custom.items():
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except ValueError:
                pass
        if key in params and params[key] is not None and params[key] != value:
            raise ValueError(f'Conflicting values for {key}')
        params[key] = value
    for key, value in params.items():
        if key in WEBUI_PARAMS or value is None or (key == 'stop' and value == []):
            continue
        if key in {'model', 'messages', 'input', 'prompt', 'headers', 'authorization', 'api_key', 'params', 'custom_params'}:
            raise ValueError(f'{key}: structural fields cannot be overridden through params')
        if key in result and result[key] != value:
            raise ValueError(f'Conflicting values for {key}')
        result[key] = value
    systems = [message.get('content') for message in body.get('messages', []) if isinstance(message, dict) and message.get('role') in {'system', 'developer'}]
    if systems:
        if 'system' in result:
            raise ValueError('Conflicting system prompt sources')
        result['system'] = systems
    if body.get('instructions') is not None:
        result['system'] = body['instructions']
        result.pop('instructions', None)
    return canonical_payload(result)
