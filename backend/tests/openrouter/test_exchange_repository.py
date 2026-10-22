import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from open_webui.openrouter.sqlalchemy_exchange_repository import SQLAlchemyExchangeRepository
from open_webui.openrouter.tables import tables
@pytest_asyncio.fixture
async def repository(tmp_path):
    engine = create_async_engine(f'sqlite+aiosqlite:///{tmp_path / "ledger.db"}')
    async with engine.begin() as connection:
        for table in tables():
            await connection.run_sync(table.create)
    yield SQLAlchemyExchangeRepository(async_sessionmaker(engine, expire_on_commit=False))
    await engine.dispose()
@pytest.mark.asyncio
async def test_only_owner_or_admin_can_read_exchange_and_chunks(repository):
    # Arrange
    await repository.start({'id': 'e1', 'user_id': 'a', 'run_id': 'r1', 'model': 'm', 'original_request': {'messages': []}, 'request_body': b'{"messages":[]}', 'policies': []})
    await repository.append('e1', 0, b'private output')
    # Act
    owner = await repository.get('e1', 'a', False)
    other = await repository.get('e1', 'b', False)
    admin = await repository.get('e1', 'root', True)
    foreign_chunks = [part async for part in repository.chunks('e1', 'b', False)]
    own_chunks = [part async for part in repository.chunks('e1', 'a', False)]
    # Assert
    assert owner['user_id'] == 'a'
    assert other is None
    assert admin['id'] == 'e1'
    assert foreign_chunks == []
    assert b''.join(own_chunks) == b'private output'
@pytest.mark.asyncio
async def test_list_filters_owner_in_database_and_does_not_load_payloads(repository):
    # Arrange
    for number, owner in enumerate(['a', 'b', 'a']):
        await repository.start({'id': str(number), 'user_id': owner, 'run_id': 'r', 'model': 'm', 'original_request': {'secret': 'large'}, 'request_body': b'{}', 'policies': []})
    # Act
    own = await repository.list('a', False, limit=1)
    other_filter = await repository.list('a', False, owner='b')
    all_records = await repository.list('root', True)
    # Assert
    assert own['total'] == 2
    assert len(own['items']) == 1
    assert 'original_request' not in own['items'][0]
    assert other_filter['total'] == 0
    assert all_records['total'] == 3
@pytest.mark.asyncio
async def test_policy_changes_have_optimistic_version_and_immutable_history(repository):
    # Arrange
    rule = {'temperature': {'access': 'editable', 'type': 'number', 'maximum': 1}}
    # Act
    first = await repository.save_policy('global', '*', rule, 'admin-a', expected_version=0)
    second = await repository.save_policy('global', '*', {}, 'admin-b', expected_version=first['version'])
    conflict = None
    try:
        await repository.save_policy('global', '*', rule, 'admin-c', expected_version=first['version'])
    except ValueError as error:
        conflict = error
    history = await repository.policy_history('global', '*')
    # Assert
    assert second['version'] == 2
    assert conflict is not None
    assert len(history) == 2
    assert history[-1]['rules'] == rule
    assert history[-1]['actor_id'] == 'admin-a'
@pytest.mark.asyncio
async def test_final_state_keeps_original_request_and_persists_usage(repository):
    # Arrange
    await repository.start({'id': 'e', 'user_id': 'a', 'run_id': 'r', 'model': 'm', 'original_request': {'prompt': 'original'}, 'request_body': b'{ "raw": true }', 'policies': []})
    await repository.append('e', 0, b'{"usage":{"cost":0.1}}')
    # Act
    await repository.finish('e', state='completed', status_code=200, response={'usage': {'cost': 0.1}}, response_sha256='digest', byte_count=22)
    result = await repository.get('e', 'a', False)
    # Assert
    assert result['request_body'] == b'{ "raw": true }'
    assert result['original_request'] == {'prompt': 'original'}
    assert result['response']['usage']['cost'] == 0.1
    assert result['state'] == 'completed'
