import base64
import json
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response, StreamingResponse
from open_webui.models.users import Users
from open_webui.openrouter.catalog import CATALOG_VERSION, catalog, default_rules
from open_webui.openrouter.parameter_input import parameter_input
from open_webui.openrouter.parameter_policy import ParameterPolicy
from open_webui.openrouter.parameter_policy_evaluator import ParameterPolicyEvaluator
from open_webui.openrouter.policy_description import describe
from open_webui.openrouter.policy_runtime import evaluator_for, repository
from open_webui.openrouter.policy_update_form import PolicyUpdateForm
from open_webui.utils.auth import get_admin_user, get_verified_user
router = APIRouter()
@router.get('/catalog')
async def get_catalog(request: Request, model: str = '', user=Depends(get_verified_user)):
    models = getattr(request.app.state, 'OPENAI_MODELS', {}) or {}
    selected = models.get(model) or {}
    supported = selected.get('supported_parameters') or (selected.get('openai') or {}).get('supported_parameters')
    entries = catalog()
    for item in entries:
        parent = item['path'].split('.')[0]
        item['supported'] = (parent in supported) if isinstance(supported, list) else None
    return {'version': CATALOG_VERSION, 'items': entries, 'reasoning': selected.get('reasoning'), 'model': model,
        'documentation': 'https://openrouter.ai/docs/api/reference/parameters'}
@router.get('/policies')
async def get_policies(user=Depends(get_admin_user), store=Depends(repository)):
    records = await store.policies()
    if not any(record['scope'] == 'global' for record in records):
        records.insert(0, {'key': 'global:*', 'scope': 'global', 'target': '*', 'version': 0, 'rules': default_rules()})
    return records
@router.put('/policies')
async def save_policy(form: PolicyUpdateForm, user=Depends(get_admin_user), store=Depends(repository)):
    try:
        return await store.save_policy(form.scope, form.target, form.rules, user.id, expected_version=form.expected_version)
    except ValueError as error:
        raise HTTPException(409 if 'reload' in str(error) else 422, str(error)) from error
@router.get('/policies/history')
async def policy_history(scope: Literal['global', 'model', 'group', 'user'], target: str, user=Depends(get_admin_user), store=Depends(repository)):
    return await store.policy_history(scope, target)
@router.get('/effective')
async def get_effective(model: str = '', user_id: str | None = None, user=Depends(get_verified_user), store=Depends(repository)):
    target = user
    if user_id and user_id != user.id:
        if user.role != 'admin':
            raise HTTPException(403, 'Only an administrator can preview another user')
        target = await Users.get_user_by_id(user_id)
        if target is None:
            raise HTTPException(404, 'User not found')
    from open_webui.models.models import Models
    model_info = await Models.get_model_by_id(model) if model else None
    targets = {model, model_info.base_model_id} if model_info and model_info.base_model_id else {model}
    evaluator = await evaluator_for(target, targets, store=store)
    return {'model': model, 'user_id': target.id, 'rules': describe(evaluator, is_admin=user.role == 'admin'),
        'versions': [{'scope': policy.scope, 'version': policy.version} for policy in evaluator.policies]}
@router.get('/exchanges')
async def list_exchanges(limit: int = Query(30, ge=1, le=100), offset: int = Query(0, ge=0),
    owner: str | None = None, chat_id: str | None = None, model: str | None = None,
    state: str | None = None, provider_id: str | None = None, after: int | None = None, before: int | None = None,
    user=Depends(get_verified_user), store=Depends(repository)):
    return await store.list(user.id, user.role == 'admin', limit=limit, offset=offset, owner=owner, chat_id=chat_id,
        model=model, state=state, provider_id=provider_id, after=after, before=before)
async def visible_exchange(exchange_id, user, store):
    record = await store.get(exchange_id, user.id, user.role == 'admin')
    if record is None:
        raise HTTPException(404, 'Exchange not found')
    body = record.pop('request_body')
    payload = json.loads(body)
    if user.role == 'admin':
        record['request_raw_base64'] = base64.b64encode(body).decode('ascii')
    else:
        historical = ParameterPolicyEvaluator([ParameterPolicy(**policy) for policy in record['policies']])
        current = await evaluator_for(user, record['model'], store=store)
        payload = current.visible(historical.visible(payload))
        hide_system = any(policy.rules.get('system', {}).get('access') in {'hidden', 'server_only'} for policy in [*historical.policies, *current.policies])
        if hide_system:
            if isinstance(payload.get('messages'), list):
                payload['messages'] = [message for message in payload['messages'] if message.get('role') not in {'system', 'developer'}]
            payload.pop('instructions', None)
        original = record['original_request']
        record['original_request'] = {key: original[key] for key in ('model', 'messages', 'input', 'prompt') if key in original}
        record['original_request']['parameters'] = current.visible(historical.visible(parameter_input(original)))
        record['policies'] = [{'scope': policy['scope'], 'version': policy['version']} for policy in record['policies']]
        record['files'] = [{'id': item.get('id'), 'name': item.get('name')} for item in record['files'] if isinstance(item, dict)]
    record['request'] = payload
    return record
@router.get('/exchanges/{exchange_id}')
async def get_exchange(exchange_id: str, user=Depends(get_verified_user), store=Depends(repository)):
    return await visible_exchange(exchange_id, user, store)
@router.get('/exchanges/{exchange_id}/raw')
async def download_raw(exchange_id: str, direction: Literal['request', 'response'] = 'response', user=Depends(get_verified_user), store=Depends(repository)):
    record = await store.get(exchange_id, user.id, user.role == 'admin')
    if record is None:
        raise HTTPException(404, 'Exchange not found')
    headers = {'Content-Disposition': f'attachment; filename="{record["id"]}-{direction}.bin"', 'Cache-Control': 'no-store'}
    if direction == 'request':
        if user.role != 'admin':
            raise HTTPException(403, 'Original request bytes are available only to administrators')
        return Response(record['request_body'], media_type='application/octet-stream', headers=headers)
    return StreamingResponse(store.chunks(exchange_id, user.id, user.role == 'admin'), media_type='application/octet-stream', headers=headers)
@router.get('/exchanges/{exchange_id}/export')
async def export_exchange(exchange_id: str, user=Depends(get_verified_user), store=Depends(repository)):
    record = await visible_exchange(exchange_id, user, store)
    async def document():
        yield '{"exchange":' + json.dumps(record, ensure_ascii=False) + ',"response_chunks_base64":['
        separator = ''
        async for part in store.chunks(exchange_id, user.id, user.role == 'admin'):
            yield separator + json.dumps(base64.b64encode(part).decode('ascii'))
            separator = ','
        yield ']}'
    return StreamingResponse(document(), media_type='application/json', headers={
        'Content-Disposition': f'attachment; filename="{record["id"]}.json"', 'Cache-Control': 'no-store'})
