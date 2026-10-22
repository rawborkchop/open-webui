from sqlalchemy import JSON, BigInteger, Column, Integer, Text, UniqueConstraint
from open_webui.internal.db import Base
class ParameterPolicyRevision(Base):
    __tablename__ = 'openrouter_policy_revision'
    id = Column(Text, primary_key=True)
    policy_key = Column(Text, nullable=False)
    version = Column(Integer, nullable=False)
    rules = Column(JSON, nullable=False)
    actor_id = Column(Text, nullable=False)
    created_at = Column(BigInteger, nullable=False)
    __table_args__ = (UniqueConstraint('policy_key', 'version', name='uq_openrouter_policy_revision'),)
