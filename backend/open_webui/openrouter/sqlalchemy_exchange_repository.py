from copy import deepcopy
import hashlib
import time
from uuid import uuid4
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from open_webui.openrouter.parameter_policy import ParameterPolicy
from open_webui.openrouter.parameter_policy_record import ParameterPolicyRecord
from open_webui.openrouter.parameter_policy_revision import ParameterPolicyRevision
from open_webui.openrouter.provider_exchange import ProviderExchange
from open_webui.openrouter.provider_exchange_chunk import ProviderExchangeChunk
def row_dict(row):
    return {column.name: getattr(row, column.name) for column in row.__table__.columns}
class SQLAlchemyExchangeRepository:
    def __init__(self, session_factory):
        self.sessions = session_factory
    async def start(self, values):
        values = deepcopy(values)
        values.setdefault('created_at', time.time_ns() // 1_000_000)
        values['request_sha256'] = hashlib.sha256(values['request_body']).hexdigest()
        async with self.sessions() as db:
            db.add(ProviderExchange(**values))
            await db.commit()
    async def append(self, exchange_id, sequence, body):
        async with self.sessions() as db:
            db.add(ProviderExchangeChunk(exchange_id=exchange_id, sequence=sequence, body=body))
            await db.execute(update(ProviderExchange).where(ProviderExchange.id == exchange_id, ProviderExchange.state == 'recording').values(byte_count=ProviderExchange.byte_count + len(body)))
            await db.commit()
    async def finish(self, exchange_id, **values):
        values['finished_at'] = time.time_ns() // 1_000_000
        async with self.sessions() as db:
            await db.execute(update(ProviderExchange).where(ProviderExchange.id == exchange_id, ProviderExchange.state == 'recording').values(**values))
            await db.commit()
    async def get(self, exchange_id, user_id, is_admin):
        query = select(ProviderExchange).where(ProviderExchange.id == exchange_id)
        if not is_admin:
            query = query.where(ProviderExchange.user_id == user_id)
        async with self.sessions() as db:
            row = (await db.execute(query)).scalar_one_or_none()
            return row_dict(row) if row else None
    async def list(self, user_id, is_admin, *, limit=30, offset=0, owner=None, chat_id=None, model=None, state=None, provider_id=None, after=None, before=None):
        conditions = []
        if not is_admin:
            conditions.append(ProviderExchange.user_id == user_id)
        for column, value in ((ProviderExchange.user_id, owner), (ProviderExchange.chat_id, chat_id), (ProviderExchange.model, model), (ProviderExchange.state, state), (ProviderExchange.provider_id, provider_id)):
            if value:
                conditions.append(column == value)
        if after is not None:
            conditions.append(ProviderExchange.created_at >= after)
        if before is not None:
            conditions.append(ProviderExchange.created_at <= before)
        names = ['id', 'user_id', 'run_id', 'chat_id', 'message_id', 'model', 'endpoint', 'purpose', 'state', 'status_code', 'byte_count', 'created_at', 'finished_at', 'provider_id']
        columns = [getattr(ProviderExchange, name) for name in names]
        async with self.sessions() as db:
            total = (await db.execute(select(func.count()).select_from(ProviderExchange).where(*conditions))).scalar_one()
            result = await db.execute(select(*columns).where(*conditions).order_by(ProviderExchange.created_at.desc(), ProviderExchange.id.desc()).limit(min(limit, 100)).offset(offset))
            return {'items': [dict(row._mapping) for row in result], 'total': total}
    async def chunks(self, exchange_id, user_id, is_admin):
        if not await self.get(exchange_id, user_id, is_admin):
            return
        sequence = -1
        while True:
            async with self.sessions() as db:
                result = await db.execute(select(ProviderExchangeChunk.sequence, ProviderExchangeChunk.body).where(ProviderExchangeChunk.exchange_id == exchange_id, ProviderExchangeChunk.sequence > sequence).order_by(ProviderExchangeChunk.sequence).limit(64))
                rows = result.all()
            if not rows:
                return
            for sequence, body in rows:
                yield body
    async def policies(self):
        async with self.sessions() as db:
            result = await db.execute(select(ParameterPolicyRecord).order_by(ParameterPolicyRecord.key))
            return [row_dict(row) for row in result.scalars()]
    async def save_policy(self, scope, target, rules, actor_id, *, expected_version):
        ParameterPolicy(scope, target, expected_version + 1, rules)
        key = f'{scope}:{target}'
        now = time.time_ns() // 1_000_000
        values = {'scope': scope, 'target': target, 'version': expected_version + 1, 'rules': rules, 'actor_id': actor_id, 'updated_at': now}
        try:
            async with self.sessions() as db:
                if expected_version == 0:
                    db.add(ParameterPolicyRecord(key=key, **values))
                else:
                    result = await db.execute(update(ParameterPolicyRecord).where(ParameterPolicyRecord.key == key, ParameterPolicyRecord.version == expected_version).values(**values))
                    if result.rowcount != 1:
                        raise ValueError('Policy changed; reload before saving')
                db.add(ParameterPolicyRevision(id=str(uuid4()), policy_key=key, version=values['version'], rules=rules, actor_id=actor_id, created_at=now))
                await db.commit()
            return {'key': key, **values}
        except IntegrityError as error:
            raise ValueError('Policy changed; reload before saving') from error
    async def policy_history(self, scope, target):
        async with self.sessions() as db:
            result = await db.execute(select(ParameterPolicyRevision).where(ParameterPolicyRevision.policy_key == f'{scope}:{target}').order_by(ParameterPolicyRevision.version.desc()))
            return [row_dict(row) for row in result.scalars()]
