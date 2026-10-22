from sqlalchemy import Column, ForeignKey, Integer, LargeBinary, Text
from open_webui.internal.db import Base
class ProviderExchangeChunk(Base):
    __tablename__ = 'openrouter_exchange_chunk'
    exchange_id = Column(Text, ForeignKey('openrouter_exchange.id', ondelete='CASCADE'), primary_key=True)
    sequence = Column(Integer, primary_key=True)
    body = Column(LargeBinary, nullable=False)
