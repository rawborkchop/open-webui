from sqlalchemy import JSON, BigInteger, Column, Integer, Text
from open_webui.internal.db import Base
class ParameterPolicyRecord(Base):
    __tablename__ = 'openrouter_policy'
    key = Column(Text, primary_key=True)
    scope = Column(Text, nullable=False)
    target = Column(Text, nullable=False)
    version = Column(Integer, nullable=False)
    rules = Column(JSON, nullable=False)
    actor_id = Column(Text, nullable=False)
    updated_at = Column(BigInteger, nullable=False)
