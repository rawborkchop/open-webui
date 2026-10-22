from sqlalchemy import JSON, BigInteger, Column, Index, Integer, LargeBinary, Text
from open_webui.internal.db import Base
class ProviderExchange(Base):
    __tablename__ = 'openrouter_exchange'
    id = Column(Text, primary_key=True)
    user_id = Column(Text, nullable=False)
    run_id = Column(Text, nullable=False)
    chat_id = Column(Text, nullable=True)
    message_id = Column(Text, nullable=True)
    parent_id = Column(Text, nullable=True)
    model = Column(Text, nullable=False)
    endpoint = Column(Text, nullable=False, default='chat/completions')
    purpose = Column(Text, nullable=False, default='chat')
    original_request = Column(JSON, nullable=False)
    request_body = Column(LargeBinary, nullable=False)
    request_sha256 = Column(Text, nullable=False)
    policies = Column(JSON, nullable=False)
    files = Column(JSON, nullable=False, default=list)
    response = Column(JSON, nullable=True)
    response_sha256 = Column(Text, nullable=True)
    byte_count = Column(BigInteger, nullable=False, default=0)
    state = Column(Text, nullable=False, default='recording')
    status_code = Column(Integer, nullable=True)
    error = Column(Text, nullable=True)
    provider_id = Column(Text, nullable=True)
    created_at = Column(BigInteger, nullable=False)
    finished_at = Column(BigInteger, nullable=True)
    __table_args__ = (
        Index('ix_openrouter_exchange_owner_created', 'user_id', 'created_at', 'id'),
        Index('ix_openrouter_exchange_chat', 'chat_id', 'created_at'),
        Index('ix_openrouter_exchange_run', 'run_id'),
        Index('ix_openrouter_exchange_provider', 'provider_id'),
    )
