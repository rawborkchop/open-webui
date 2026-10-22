import json
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from fastapi import HTTPException
from open_webui.openrouter.gateway import governed_request
from open_webui.openrouter.parameter_policy import ParameterPolicy
from open_webui.openrouter.parameter_policy_evaluator import ParameterPolicyEvaluator
def response(body, status=200, streaming=False):
    async def chunks():
        yield body[:5]
        yield body[5:]
    async def pairs():
        async for part in chunks():
            yield part, False
    return SimpleNamespace(status=status, headers={'Content-Type': 'text/event-stream' if streaming else 'application/json'}, charset='utf-8', content=SimpleNamespace(iter_any=chunks, iter_chunks=pairs))
def request(original):
    return SimpleNamespace(state=SimpleNamespace(openrouter_client_input=original, metadata={}))
def evaluator(rules=None):
    return ParameterPolicyEvaluator([ParameterPolicy('global', '*', 1, rules or {'reasoning.exclude': {'access': 'read_only', 'value': False}})])
@pytest.mark.asyncio
async def test_guard_persists_input_before_send_and_keeps_provider_output(store):
    # Arrange
    origin = {'model': 'm', 'messages': [{'role': 'user', 'content': 'question'}]}
    user = SimpleNamespace(id='a', role='user')
    wire = b'{ "id":"gen1", "choices":[{"message":{"content":"answer","reasoning":"returned thinking"}}] }'
    sent = []
    async def send(**kwargs):
        records = await store.list('a', False)
        sent.append((records['total'], kwargs))
        return response(wire)
    session = SimpleNamespace(request=send)
    # Act
    result = await governed_request(session, request(origin), user, store=store, evaluator=evaluator(), method='POST', url='https://openrouter.ai/api/v1/chat/completions', data=json.dumps(origin), headers={'Authorization': 'Bearer NEVER-LOG-THIS'}, cookies={'token': 'NEVER-LOG-THIS'})
    parsed = await result.json()
    records = await store.list('a', False)
    record = await store.get(records['items'][0]['id'], 'a', False)
    raw = b''.join([part async for part in store.chunks(record['id'], 'a', False)])
    # Assert
    assert sent[0][0] == 1
    assert record['request_body'] == sent[0][1]['data']
    assert b'NEVER-LOG-THIS' not in record['request_body']
    assert 'NEVER-LOG-THIS' not in json.dumps(record['original_request'])
    assert json.loads(record['request_body'])['reasoning']['exclude'] is False
    assert parsed['id'] == 'gen1'
    assert raw == wire
    assert record['state'] == 'completed'
@pytest.mark.asyncio
@pytest.mark.parametrize('body', [{'temperature': 2}, {'params': {'custom_params': {'temperature': '2'}}}, {'max_output_tokens': 999}, {'params': {'model_controls': {'m': {'choice': 'unauthorized-expansion'}}}}])
async def test_disallowed_parameters_never_reach_provider(store, body):
    # Arrange
    original = {'model': 'm', 'messages': [], **body}
    session = SimpleNamespace(request=AsyncMock())
    error = None
    # Act
    try:
        await governed_request(session, request(original), SimpleNamespace(id='a', role='user'), store=store, evaluator=evaluator(), method='POST', url='https://openrouter.ai/api/v1/chat/completions', data=json.dumps(original))
    except HTTPException as failure:
        error = failure
    # Assert
    assert error.status_code == 403
    assert session.request.await_count == 0
@pytest.mark.asyncio
async def test_direct_responses_route_has_same_policy_and_correct_token_alias(store):
    # Arrange
    origin = {'model': 'm', 'input': 'question', 'max_output_tokens': 100}
    session = SimpleNamespace(request=AsyncMock(return_value=response(b'{"id":"r"}')))
    rules = {'max_tokens': {'access': 'editable', 'type': 'integer', 'maximum': 100}}
    # Act
    result = await governed_request(session, request(origin), SimpleNamespace(id='a', role='user'), store=store, evaluator=evaluator(rules), method='POST', url='https://openrouter.ai/api/v1/responses', data=json.dumps(origin))
    await result.read()
    payload = json.loads(session.request.call_args.kwargs['data'])
    # Assert
    assert payload['max_output_tokens'] == 100
    assert 'max_tokens' not in payload
@pytest.mark.asyncio
async def test_legacy_passthrough_cannot_bypass_governance(store):
    # Arrange
    session = SimpleNamespace(request=AsyncMock())
    error = None
    # Act
    try:
        await governed_request(session, request({}), SimpleNamespace(id='a', role='admin'), store=store, passthrough=True, method='POST', url='https://openrouter.ai/api/v1/completions', data='{}')
    except HTTPException as failure:
        error = failure
    # Assert
    assert error.status_code == 403
    assert session.request.await_count == 0
@pytest.mark.asyncio
async def test_other_providers_keep_existing_behavior():
    # Arrange
    upstream = object()
    session = SimpleNamespace(request=AsyncMock(return_value=upstream))
    # Act
    result = await governed_request(session, request({}), None, method='POST', url='http://localhost:1234/v1/chat/completions', data='{}')
    # Assert
    assert result is upstream
    assert session.request.call_args.kwargs['data'] == '{}'
@pytest.mark.asyncio
async def test_foreign_previous_response_cannot_be_reused(store):
    # Arrange
    body = {'model': 'm', 'input': 'continue', 'previous_response_id': 'foreign'}
    session = SimpleNamespace(request=AsyncMock())
    rules = {'previous_response_id': {'access': 'editable', 'type': 'string'}}
    error = None
    # Act
    try:
        await governed_request(session, request(body), SimpleNamespace(id='a', role='user'), store=store, evaluator=evaluator(rules), method='POST', url='https://openrouter.ai/api/v1/responses', data=json.dumps(body))
    except HTTPException as failure:
        error = failure
    # Assert
    assert error.status_code == 403
    assert session.request.await_count == 0
@pytest.mark.asyncio
async def test_provider_item_reference_cannot_retrieve_another_users_output(store):
    # Arrange
    body = {'model': 'm', 'input': [{'type': 'item_reference', 'id': 'foreign-item'}]}
    session = SimpleNamespace(request=AsyncMock())
    error = None
    # Act
    try:
        await governed_request(session, request(body), SimpleNamespace(id='a', role='user'), store=store, evaluator=evaluator(), method='POST', url='https://openrouter.ai/api/v1/responses', data=json.dumps(body))
    except HTTPException as failure:
        error = failure
    # Assert
    assert error.status_code == 403
    assert session.request.await_count == 0
@pytest.mark.asyncio
async def test_server_created_embedding_call_without_json_chat_envelope_is_audited(store):
    # Arrange
    incoming = SimpleNamespace(state=SimpleNamespace(), url=SimpleNamespace(path='/api/v1/files/'), body=AsyncMock(side_effect=RuntimeError('already consumed multipart')))
    payload = {'model': 'm', 'input': 'extracted document content'}
    session = SimpleNamespace(request=AsyncMock(return_value=response(b'{"data":[{"embedding":[1,2]}]}')))
    # Act
    result = await governed_request(session, incoming, SimpleNamespace(id='a', role='user'), store=store, evaluator=evaluator(), method='POST', url='https://openrouter.ai/api/v1/embeddings', data=json.dumps(payload))
    await result.read()
    records = await store.list('a', False)
    # Assert
    assert records['total'] == 1
    assert records['items'][0]['endpoint'] == 'embeddings'
    assert 'reasoning' not in json.loads(session.request.call_args.kwargs['data'])
