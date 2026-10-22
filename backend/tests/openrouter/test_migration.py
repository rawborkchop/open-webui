import importlib.util
from pathlib import Path
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text
def test_migration_roundtrip_preserves_existing_application_data(tmp_path):
    # Arrange
    path = Path(__file__).resolve().parents[2] / 'open_webui/migrations/versions/7d2a9b4c810e_add_openrouter_governance.py'
    spec = importlib.util.spec_from_file_location('governance_migration', path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = create_engine(f'sqlite:///{tmp_path / "migration.db"}')
    with engine.begin() as db:
        db.execute(text('create table existing_data (value text)'))
        db.execute(text("insert into existing_data values ('keep')"))
    # Act
    with engine.begin() as db:
        with Operations.context(MigrationContext.configure(db)):
            migration.upgrade()
        upgraded = set(inspect(db).get_table_names())
        with Operations.context(MigrationContext.configure(db)):
            migration.downgrade()
        remaining = set(inspect(db).get_table_names())
        preserved = db.execute(text('select value from existing_data')).scalar_one()
    engine.dispose()
    # Assert
    assert 'openrouter_exchange_chunk' in upgraded
    assert 'openrouter_policy_revision' in upgraded
    assert remaining == {'existing_data'}
    assert preserved == 'keep'
