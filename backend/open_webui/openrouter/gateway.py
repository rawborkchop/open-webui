import asyncio
from copy import deepcopy
import json
from urllib.parse import urlparse
from uuid import uuid4
from fastapi import HTTPException
from open_webui.openrouter.exchange_recorder import ExchangeRecorder
from open_webui.openrouter.parameter_input import canonical_payload, parameter_input
from open_webui.openrouter.policy_runtime import evaluator_for, repository
from open_webui.openrouter.recorded_response import RecordedResponse
def is_openrouter_url(url):
    parsed = urlparse(str(url))
    return parsed.hostname == 'openrouter.ai'
async def validate_references(payload, user, store):
    def has_unowned_reference(value):
        if isinstance(value, list):
            return any(has_unowned_reference(item) for item in value)
        if isinstance(value, dict):
            return value.get('type') == 'item_reference' or 'file_id' in value or any(has_unowned_reference(item) for item in value.values())
        return False
    if user.role != 'admin' and has_unowned_reference(payload.get('input', [])):
        raise HTTPException(403, 'Provider item and file references are not supported for ordinary users')
    previous = payload.get('previous_response_id')
    if previous and user.role != 'admin':
        records = await store.list(user.id, False, provider_id=previous, limit=1)
        if not records['items']:
            raise HTTPException(403, 'Previous response does not belong to this user')
    if payload.get('models') and user.role != 'admin':
        from open_webui.models.models import Models
        from open_webui.utils.access_control import check_model_access
        for model in payload['models']:
            if not isinstance(model, str):
                raise HTTPException(400, 'Fallback model IDs must be strings')
            await check_model_access(user, await Models.get_model_by_id(model), False)
async def governed_request(session, request, user, *, metadata=None, passthrough=False, store=None, evaluator=None, **kwargs):
    if not is_openrouter_url(kwargs.get('url', '')):
        return await session.request(**kwargs)
    endpoint = urlparse(str(kwargs['url'])).path.removeprefix('/api/v1/').strip('/')
    if passthrough or kwargs.get('method', 'POST') != 'POST' or endpoint not in {'chat/completions', 'responses', 'embeddings'}:
        raise HTTPException(403, 'This OpenRouter endpoint is not available through the audited gateway')
    if user is None or user.role not in {'admin', 'user'}:
        raise HTTPException(403, 'An active user is required')
    store = store or repository()
    payload = json.loads(kwargs['data'])
    model = payload.get('model', '')
    model_targets = {model, getattr(request.state, 'model_id', model)}
    evaluator = evaluator or await evaluator_for(user, model_targets, store=store)
    original = getattr(request.state, 'openrouter_client_input', None)
    internal = getattr(request.state, 'internal', False) is True
    if original is None:
        if internal:
            original = deepcopy(payload)
        else:
            # Direct route tests and older internal callers may not use the capture middleware.
            try:
                original = json.loads(await request.body())
            except (RuntimeError, ValueError):
                path = getattr(getattr(request, 'url', None), 'path', '')
                if not path or path.startswith(('/openai/', '/api/chat/completions', '/api/v1/chat/completions', '/api/v1/tasks/')):
                    raise HTTPException(400, 'Original inference input is unavailable') from None
                # File processing and other server-created embedding calls have no JSON chat envelope.
                original = deepcopy(payload)
                internal = True
    try:
        if not internal:
            if user.role != 'admin' and (original.get('params') or {}).get('model_controls'):
                raise ValueError('Use authorized OpenRouter parameters instead of model control expansions')
            evaluator.authorize(parameter_input(original), is_admin=user.role == 'admin')
        effective = evaluator.apply(canonical_payload(payload))
    except ValueError as error:
        raise HTTPException(403, f'OpenRouter policy: {error}') from error
    # User identity is never accepted from a client or model preset.
    effective['user'] = user.id
    if 'system' in effective:
        system = effective.pop('system')
        if endpoint == 'responses':
            effective['instructions'] = system if isinstance(system, str) else '\n'.join(system)
        elif endpoint == 'chat/completions':
            messages = [message for message in effective.get('messages', []) if message.get('role') not in {'system', 'developer'}]
            effective['messages'] = [{'role': 'system', 'content': system}] + messages
    if endpoint == 'responses' and 'max_tokens' in effective:
        effective['max_output_tokens'] = effective.pop('max_tokens')
    if endpoint == 'embeddings':
        effective.pop('reasoning', None)
    if not effective.get('stream'):
        effective.pop('stream_options', None)
    await validate_references(effective, user, store)
    body = json.dumps(effective, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')
    kwargs['data'] = body
    # Redirects must not move a governed request to an unaudited provider.
    kwargs['allow_redirects'] = False
    context = getattr(request.state, 'metadata', None) or {}
    run_id = getattr(request.state, 'openrouter_run_id', None)
    if run_id is None:
        run_id = str(uuid4())
        request.state.openrouter_run_id = run_id
    exchange_id = str(uuid4())
    purpose = (metadata or {}).get('task') or ('embeddings' if endpoint == 'embeddings' else 'chat')
    if not isinstance(purpose, str):
        purpose = 'internal'
    values = {'id': exchange_id, 'user_id': user.id, 'run_id': run_id,
        'chat_id': context.get('chat_id') or None,
        'message_id': context.get('assistant_message_id') or context.get('message_id'),
        'model': model, 'endpoint': endpoint, 'purpose': purpose,
        'original_request': deepcopy(original), 'request_body': body, 'policies': evaluator.snapshot(),
        'files': deepcopy(context.get('files') or [])}
    chain = getattr(request.state, 'openrouter_exchange_chain', None)
    if chain is None:
        chain = {}
        request.state.openrouter_exchange_chain = chain
    chain_key = (values['chat_id'], values['message_id'], purpose, model)
    values['parent_id'] = chain.get(chain_key)
    recorder = ExchangeRecorder(store, values)
    await recorder.begin()
    chain[chain_key] = exchange_id
    try:
        response = await session.request(**kwargs)
    except (asyncio.CancelledError, GeneratorExit):
        await recorder.finish('cancelled')
        raise
    except Exception as error:
        await recorder.finish('error', type(error).__name__)
        raise
    recorder.bind(response.status, 'text/event-stream' in response.headers.get('Content-Type', ''))
    return RecordedResponse(response, recorder)
