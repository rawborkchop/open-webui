"""Add versioned OpenRouter policies and durable provider exchange capture."""
from alembic import op
import sqlalchemy as sa
revision = '7d2a9b4c810e'
down_revision = '0bd252b206fb'
branch_labels = None
depends_on = None
def upgrade():
    op.create_table('openrouter_policy',
        sa.Column('key', sa.Text(), primary_key=True),
        sa.Column('scope', sa.Text(), nullable=False),
        sa.Column('target', sa.Text(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('rules', sa.JSON(), nullable=False),
        sa.Column('actor_id', sa.Text(), nullable=False),
        sa.Column('updated_at', sa.BigInteger(), nullable=False))
    op.create_table('openrouter_policy_revision',
        sa.Column('id', sa.Text(), primary_key=True),
        sa.Column('policy_key', sa.Text(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('rules', sa.JSON(), nullable=False),
        sa.Column('actor_id', sa.Text(), nullable=False),
        sa.Column('created_at', sa.BigInteger(), nullable=False),
        sa.UniqueConstraint('policy_key', 'version', name='uq_openrouter_policy_revision'))
    op.create_table('openrouter_exchange',
        sa.Column('id', sa.Text(), primary_key=True),
        sa.Column('user_id', sa.Text(), nullable=False),
        sa.Column('run_id', sa.Text(), nullable=False),
        sa.Column('chat_id', sa.Text(), nullable=True),
        sa.Column('message_id', sa.Text(), nullable=True),
        sa.Column('parent_id', sa.Text(), nullable=True),
        sa.Column('model', sa.Text(), nullable=False),
        sa.Column('endpoint', sa.Text(), nullable=False),
        sa.Column('purpose', sa.Text(), nullable=False),
        sa.Column('original_request', sa.JSON(), nullable=False),
        sa.Column('request_body', sa.LargeBinary(), nullable=False),
        sa.Column('request_sha256', sa.Text(), nullable=False),
        sa.Column('policies', sa.JSON(), nullable=False),
        sa.Column('files', sa.JSON(), nullable=False),
        sa.Column('response', sa.JSON(), nullable=True),
        sa.Column('response_sha256', sa.Text(), nullable=True),
        sa.Column('byte_count', sa.BigInteger(), nullable=False),
        sa.Column('state', sa.Text(), nullable=False),
        sa.Column('status_code', sa.Integer(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('provider_id', sa.Text(), nullable=True),
        sa.Column('created_at', sa.BigInteger(), nullable=False),
        sa.Column('finished_at', sa.BigInteger(), nullable=True))
    op.create_index('ix_openrouter_exchange_owner_created', 'openrouter_exchange', ['user_id', 'created_at', 'id'])
    op.create_index('ix_openrouter_exchange_chat', 'openrouter_exchange', ['chat_id', 'created_at'])
    op.create_index('ix_openrouter_exchange_run', 'openrouter_exchange', ['run_id'])
    op.create_index('ix_openrouter_exchange_provider', 'openrouter_exchange', ['provider_id'])
    op.create_table('openrouter_exchange_chunk',
        sa.Column('exchange_id', sa.Text(), sa.ForeignKey('openrouter_exchange.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('sequence', sa.Integer(), primary_key=True),
        sa.Column('body', sa.LargeBinary(), nullable=False))
def downgrade():
    op.drop_table('openrouter_exchange_chunk')
    for name in ('provider', 'run', 'chat', 'owner_created'):
        op.drop_index(f'ix_openrouter_exchange_{name}', table_name='openrouter_exchange')
    op.drop_table('openrouter_exchange')
    op.drop_table('openrouter_policy_revision')
    op.drop_table('openrouter_policy')
