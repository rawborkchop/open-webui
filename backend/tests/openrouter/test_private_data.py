from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from fastapi import HTTPException
from open_webui.models.chats import Chats
from open_webui.models.shared_chats import SharedChats
from open_webui.models.files import Files
from open_webui.models.users import Users
from open_webui.openrouter.private_routes import enforce_private_routes
from open_webui.utils.access_control.files import has_access_to_file
from open_webui.utils.access_control.folders import has_folder_access
@pytest.mark.asyncio
async def test_shared_chat_does_not_grant_access_to_another_users_history(monkeypatch):
    # Arrange
    monkeypatch.setenv('OPENROUTER_STRICT_USER_ISOLATION', 'true')
    shared = AsyncMock(return_value=SimpleNamespace(chat={'share_mode': 'continue'}, chat_id='c'))
    monkeypatch.setattr(SharedChats, 'get_by_chat_id', shared)
    chat = SimpleNamespace(id='c', user_id='b', meta={})
    # Act
    result = await Chats.get_accessible_chat_by_id('c', SimpleNamespace(id='a', role='user'), chat=chat)
    # Assert
    assert result is None
    assert shared.await_count == 0
@pytest.mark.asyncio
async def test_shared_files_do_not_bypass_private_ownership(monkeypatch):
    # Arrange
    monkeypatch.setenv('OPENROUTER_STRICT_USER_ISOLATION', 'true')
    monkeypatch.setattr(Files, 'get_file_by_id', AsyncMock(return_value=SimpleNamespace(id='f', user_id='b')))
    # Act
    result = await has_access_to_file('f', 'read', SimpleNamespace(id='a', role='user'))
    # Assert
    assert result is False
@pytest.mark.asyncio
async def test_admin_can_review_foreign_folders_but_user_cannot(monkeypatch):
    # Arrange
    monkeypatch.setenv('OPENROUTER_STRICT_USER_ISOLATION', 'true')
    user = SimpleNamespace(id='a', role='user')
    monkeypatch.setattr(Users, 'get_user_by_id', AsyncMock(side_effect=lambda *args, **kwargs: user))
    folder = SimpleNamespace(id='f', user_id='b', parent_id=None)
    # Act
    ordinary = await has_folder_access('a', folder, 'read', None)
    user.role = 'admin'
    admin = await has_folder_access('a', folder, 'read', None)
    # Assert
    assert ordinary is False
    assert admin is True
@pytest.mark.asyncio
@pytest.mark.parametrize('path', ['/api/v1/chats/share/s', '/api/v1/chats/c/share', '/api/v1/folders/f/access/update', '/api/v1/channels/'])
async def test_sharing_routes_are_closed_to_ordinary_users(path, monkeypatch):
    # Arrange
    monkeypatch.setenv('OPENROUTER_STRICT_USER_ISOLATION', 'true')
    error = None
    # Act
    try:
        await enforce_private_routes(SimpleNamespace(url=SimpleNamespace(path=path), method='POST'), SimpleNamespace(id='a', role='user'))
    except HTTPException as failure:
        error = failure
    # Assert
    assert error.status_code == 403
