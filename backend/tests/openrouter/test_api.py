from types import SimpleNamespace
from unittest.mock import AsyncMock
import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI
from open_webui.routers import openrouter
from open_webui.utils.auth import get_current_user
from open_webui.models.groups import Groups
from open_webui.models.models import Models
@pytest_asyncio.fixture
async def api(store, monkeypatch):
    app = FastAPI()
    app.state.OPENAI_MODELS = {}
    app.include_router(openrouter.router, prefix='/api/v1/openrouter')
    actor = SimpleNamespace(id='a', role='user')
    app.dependency_overrides[get_current_user] = lambda: actor
    app.dependency_overrides[openrouter.repository] = lambda: store
    monkeypatch.setattr(Groups, 'get_groups_by_member_id', AsyncMock(return_value=[]))
    monkeypatch.setattr(Models, 'get_model_by_id', AsyncMock(return_value=None))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
        yield client, actor
@pytest.mark.asyncio
async def test_api_enforces_ownership_on_detail_raw_export_and_lists(api, store):
    # Arrange
    client, actor = api
    await store.start({'id': 'foreign', 'user_id': 'b', 'run_id': 'r', 'model': 'm', 'original_request': {}, 'request_body': b'{}', 'policies': []})
    # Act
    ordinary = [await client.get('/api/v1/openrouter/exchanges/foreign' + suffix) for suffix in ['', '/raw', '/export']]
    listing = await client.get('/api/v1/openrouter/exchanges?owner=b')
    actor.role = 'admin'
    admin = await client.get('/api/v1/openrouter/exchanges/foreign')
    # Assert
    assert [result.status_code for result in ordinary] == [404, 404, 404]
    assert listing.json()['total'] == 0
    assert admin.status_code == 200
    assert admin.json()['user_id'] == 'b'
@pytest.mark.asyncio
async def test_only_admin_can_change_policies_and_conflicts_are_reported(api):
    # Arrange
    client, actor = api
    change = {'scope': 'global', 'target': '*', 'expected_version': 0, 'rules': {'temperature': {'access': 'editable', 'type': 'number'}}}
    # Act
    refused = await client.put('/api/v1/openrouter/policies', json=change)
    actor.role = 'admin'
    accepted = await client.put('/api/v1/openrouter/policies', json=change)
    conflict = await client.put('/api/v1/openrouter/policies', json=change)
    history = await client.get('/api/v1/openrouter/policies/history?scope=global&target=*')
    # Assert
    assert refused.status_code in (401, 403)
    assert accepted.status_code == 200
    assert conflict.status_code == 409
    assert len(history.json()) == 1
@pytest.mark.asyncio
async def test_pending_user_cannot_access_ledger(api):
    # Arrange
    client, actor = api
    actor.role = 'pending'
    # Act
    result = await client.get('/api/v1/openrouter/exchanges')
    # Assert
    assert result.status_code in (401, 403)
@pytest.mark.asyncio
async def test_user_inspection_hides_server_only_values_and_raw_request(api, store):
    # Arrange
    client, actor = api
    rules = {'provider.order': {'access': 'hidden', 'value': ['private-endpoint']}, 'user': {'access': 'server_only'}}
    await store.start({'id': 'own', 'user_id': 'a', 'run_id': 'r', 'model': 'm', 'original_request': {'messages': []}, 'request_body': b'{"messages":[],"user":"private-user","provider":{"order":["private-endpoint"]}}', 'policies': [{'scope': 'global', 'target': '*', 'version': 1, 'rules': rules}]})
    # Act
    own = await client.get('/api/v1/openrouter/exchanges/own')
    raw = await client.get('/api/v1/openrouter/exchanges/own/raw?direction=request')
    other_preview = await client.get('/api/v1/openrouter/effective?user_id=b')
    # Assert
    assert own.status_code == 200
    assert 'private-endpoint' not in own.text
    assert 'private-user' not in own.text
    assert 'request_raw_base64' not in own.json()
    assert raw.status_code == 403
    assert other_preview.status_code == 403
@pytest.mark.asyncio
async def test_alias_preview_includes_base_model_restrictions(api, store, monkeypatch):
    # Arrange
    client, actor = api
    monkeypatch.setattr(Models, 'get_model_by_id', AsyncMock(return_value=SimpleNamespace(base_model_id='provider/base')))
    await store.save_policy('model', 'provider/base', {'temperature': {'access': 'hidden'}}, 'admin', expected_version=0)
    # Act
    preview = await client.get('/api/v1/openrouter/effective?model=custom-alias')
    # Assert
    assert preview.status_code == 200
    assert 'temperature' not in preview.json()['rules']
