"""Isolated application scenario with real accounts, SQLite and an in-process fake provider."""
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
from uuid import uuid4
data_dir = Path(sys.argv[1]).resolve()
data_dir.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.update(DATA_DIR=str(data_dir), DATABASE_URL=f'sqlite:///{(data_dir / "app.db").as_posix()}',
    WEBUI_SECRET_KEY='isolated-openrouter-test-secret', USE_SLIM_DOCKER='true', OFFLINE_MODE='true',
    ENABLE_DB_MIGRATIONS='true', ENABLE_PLUGINS='false', ENABLE_OLLAMA_API='false', ENABLE_OPENAI_API='true',
    OPENAI_API_BASE_URL='https://openrouter.ai/api/v1', OPENAI_API_KEY='',
    OPENROUTER_STRICT_USER_ISOLATION='true', DEFAULT_USER_ROLE='pending', ENABLE_SIGNUP='true', ENV='test')
from fastapi.testclient import TestClient
from open_webui.main import app
from open_webui.routers import openai
from open_webui.internal.db import async_engine, engine
from open_webui.models.config import Config
from open_webui.config import CACHE_DIR
from open_webui.models.files import Files, FileForm
provider_calls = []
async def models_request(*args, **kwargs):
    return {'data': [{'id': 'mock/reasoning', 'name': 'Mock reasoning', 'supported_parameters': ['reasoning', 'temperature', 'max_tokens', 'tools']}]}
async def provider_request(**kwargs):
    body = json.loads(kwargs['data'])
    provider_calls.append(body)
    generation = f'gen-{uuid4()}'
    result = {'id': generation, 'model': 'mock/reasoning', 'choices': [{'index': 0,
        'message': {'role': 'assistant', 'content': 'Mock answer with a tool-capable model.', 'reasoning': 'Provider-returned reasoning.',
            'reasoning_details': [{'type': 'reasoning.encrypted', 'data': 'opaque-provider-block', 'index': 0}]},
        'finish_reason': 'stop'}], 'usage': {'prompt_tokens': 5, 'completion_tokens': 8, 'cost': 0.001}}
    if body.get('stream'):
        result['choices'][0]['delta'] = result['choices'][0].pop('message')
        raw = ('data: ' + json.dumps(result) + '\n\ndata: [DONE]\n\n').encode()
    else:
        raw = json.dumps(result).encode()
    async def chunks():
        yield raw[:17]
        yield raw[17:]
    async def pairs():
        async for chunk in chunks():
            yield chunk, False
    return SimpleNamespace(status=200, headers={'Content-Type': 'text/event-stream' if body.get('stream') else 'application/json'}, charset='utf-8',
        content=SimpleNamespace(iter_any=chunks, iter_chunks=pairs), closed=False, close=lambda: None)
async def provider_session():
    return SimpleNamespace(request=provider_request)
openai.get_models_request = models_request
openai.get_session = provider_session
def successful(response):
    response.raise_for_status()
    return response.json()
def auth(user):
    return {'Authorization': f'Bearer {user["token"]}'}
checks = {}
with TestClient(app) as client:
    admin = successful(client.post('/api/v1/auths/signup', json={'name': 'Admin test', 'email': 'admin@example.test', 'password': 'TestingPassword123!'}))
    client.portal.call(Config.upsert, {'ui.enable_signup': True})
    a = successful(client.post('/api/v1/auths/signup', json={'name': 'User A', 'email': 'a@example.test', 'password': 'TestingPassword123!'}))
    b = successful(client.post('/api/v1/auths/signup', json={'name': 'User B', 'email': 'b@example.test', 'password': 'TestingPassword123!'}))
    checks['pending_blocked'] = client.get('/api/v1/openrouter/exchanges', headers=auth(a)).status_code == 401
    for user in (a, b):
        successful(client.post(f'/api/v1/users/{user["id"]}/update', headers=auth(admin), json={'role': 'user'}))
    successful(client.post('/api/v1/models/create', headers=auth(admin), json={
        'id': 'mock/reasoning', 'name': 'Mock reasoning', 'meta': {}, 'params': {},
        'access_grants': [{'principal_type': 'user', 'principal_id': user['id'], 'permission': 'read'} for user in (a, b)]}))
    policy = successful(client.get('/api/v1/openrouter/policies', headers=auth(admin)))[0]
    policy['rules']['temperature'] = {'access': 'editable', 'type': 'number', 'minimum': 0, 'maximum': 1}
    successful(client.put('/api/v1/openrouter/policies', headers=auth(admin), json={
        'scope': 'global', 'target': '*', 'expected_version': 0, 'rules': policy['rules']}))
    chat_a = successful(client.post('/api/v1/chats/new', headers=auth(a), json={'chat': {'title': 'Private A', 'history': {'messages': {}, 'currentId': None}}}))
    chat_b = successful(client.post('/api/v1/chats/new', headers=auth(b), json={'chat': {'title': 'Private B', 'history': {'messages': {}, 'currentId': None}}}))
    checks['foreign_chat_denied'] = client.get(f'/api/v1/chats/{chat_a["id"]}', headers=auth(b)).status_code in (401, 403, 404)
    checks['admin_reads_foreign_chat'] = client.get(f'/api/v1/chats/{chat_a["id"]}', headers=auth(admin)).status_code == 200
    own_list = successful(client.get('/api/v1/chats/', headers=auth(a)))
    checks['chat_list_isolated'] = all(chat['id'] != chat_b['id'] for chat in own_list)
    model_list = successful(client.get('/api/models', headers=auth(a)))
    checks['openrouter_model_marker'] = any(model.get('openrouter') for model in model_list['data'])
    message_id = str(uuid4())
    body = {'model': 'mock/reasoning', 'stream': False, 'messages': [{'role': 'user', 'content': 'Question A'}],
        'params': {'temperature': 0.5}, 'chat_id': chat_a['id'], 'id': str(uuid4()),
        'user_message': {'id': message_id, 'role': 'user', 'content': 'Question A', 'parentId': None, 'childrenIds': []}}
    completion = client.post('/api/chat/completions', headers=auth(a), json=body)
    successful(completion)
    records_a = successful(client.get('/api/v1/openrouter/exchanges', headers=auth(a)))
    checks['chat_exchange_recorded'] = records_a['total'] >= 1
    record_id = records_a['items'][0]['id']
    detail = successful(client.get(f'/api/v1/openrouter/exchanges/{record_id}', headers=auth(a)))
    checks['effective_input_recorded'] = detail['request']['temperature'] == 0.5
    checks['reasoning_recorded'] = 'Provider-returned reasoning.' in json.dumps(detail['response']) and 'opaque-provider-block' in json.dumps(detail['response'])
    checks['chat_link_recorded'] = detail['chat_id'] == chat_a['id']
    checks['user_identity_not_spoofed'] = provider_calls[-1]['user'] == a['id']
    calls_before_rejection = len(provider_calls)
    rejected = client.post('/openai/chat/completions', headers=auth(a), json={'model': 'mock/reasoning', 'messages': [], 'temperature': 2})
    checks['direct_route_policy_enforced'] = rejected.status_code == 403 and len(provider_calls) == calls_before_rejection
    streamed = client.post('/openai/chat/completions', headers=auth(a), json={'model': 'mock/reasoning', 'messages': [{'role': 'user', 'content': 'Streamed question'}], 'stream': True})
    streamed.raise_for_status()
    checks['streaming_route_preserved'] = 'data: [DONE]' in streamed.text
    streamed_records = successful(client.get('/api/v1/openrouter/exchanges', headers=auth(a)))
    stream_record = successful(client.get(f'/api/v1/openrouter/exchanges/{streamed_records["items"][0]["id"]}', headers=auth(a)))
    checks['stream_record_completed'] = stream_record['state'] == 'completed' and stream_record['byte_count'] > 0
    checks['stream_reasoning_recorded'] = 'Provider-returned reasoning.' in json.dumps(stream_record['response'])
    foreign = [client.get(f'/api/v1/openrouter/exchanges/{record_id}' + suffix, headers=auth(b)).status_code for suffix in ('', '/raw', '/export')]
    checks['all_exchange_routes_isolated'] = foreign == [404, 404, 404]
    exported = successful(client.get(f'/api/v1/openrouter/exchanges/{record_id}/export', headers=auth(a)))
    checks['export_contains_provider_bytes'] = bool(exported['response_chunks_base64'])
    checks['admin_sees_all_exchanges'] = successful(client.get('/api/v1/openrouter/exchanges', headers=auth(admin)))['total'] >= records_a['total']
    checks['ordinary_policy_write_denied'] = client.put('/api/v1/openrouter/policies', headers=auth(b), json={'scope': 'global', 'target': '*', 'expected_version': 1, 'rules': {}}).status_code in (401, 403)
    upload = successful(client.post('/api/v1/files/?process=false', headers=auth(a), files={'file': ('private.txt', b'Private attachment A', 'text/plain')}))
    checks['file_access_isolated'] = client.get(f'/api/v1/files/{upload["id"]}', headers=auth(b)).status_code in (401, 403, 404)
    checks['admin_reads_foreign_file'] = client.get(f'/api/v1/files/{upload["id"]}', headers=auth(admin)).status_code == 200
    cache_file = CACHE_DIR / 'private-test.txt'
    cache_file.write_text('Private cached output A', encoding='utf-8')
    client.portal.call(Files.insert_new_file, a['id'], FileForm(id=str(uuid4()), filename=cache_file.name, path=str(cache_file)))
    checks['cache_owner_reads'] = client.get('/cache/private-test.txt', headers=auth(a)).status_code == 200
    checks['cache_foreign_denied'] = client.get('/cache/private-test.txt', headers=auth(b)).status_code == 404
    checks['cache_admin_reads'] = client.get('/cache/private-test.txt', headers=auth(admin)).status_code == 200
    checks['sharing_disabled_in_backend'] = client.post(f'/api/v1/chats/{chat_a["id"]}/share', headers=auth(a), json={}).status_code == 403
    checks['channels_disabled_in_backend'] = client.get('/api/v1/channels/', headers=auth(a)).status_code == 403
    checks['shared_lists_empty'] = successful(client.get('/api/v1/folders/shared', headers=auth(a))) == [] and successful(client.get('/api/v1/chats/shared', headers=auth(a))) == []
    folder = successful(client.post('/api/v1/folders/', headers=auth(a), json={'name': 'Private folder'}))
    checks['folder_access_isolated'] = client.get(f'/api/v1/folders/{folder["id"]}', headers=auth(b)).status_code in (401, 403, 404)
    reread = successful(client.get(f'/api/v1/chats/{chat_a["id"]}', headers=auth(a)))
    checks['conversation_persisted'] = 'Question A' in json.dumps(reread)
    successful(client.post(f'/api/v1/users/{a["id"]}/update', headers=auth(admin), json={'role': 'pending'}))
    checks['role_revocation_effective'] = client.get('/api/v1/openrouter/exchanges', headers=auth(a)).status_code == 401
    if '--serve' in sys.argv:
        successful(client.post(f'/api/v1/users/{a["id"]}/update', headers=auth(admin), json={'role': 'user'}))
    client.portal.call(async_engine.dispose)
engine.dispose()
print('RESULT_JSON=' + json.dumps(checks))
if '--serve' in sys.argv:
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=8088)
