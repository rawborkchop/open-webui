import hashlib
import json
import anyio
from open_webui.openrouter.exchange_repository import ExchangeRepository
from open_webui.openrouter.response_projection import ResponseProjection
class ExchangeRecorder:
    def __init__(self, repository: ExchangeRepository, values):
        self.repository = repository
        self.values = values
        self.id = values['id']
        self.sequence = 0
        self.byte_count = 0
        self.digest = hashlib.sha256()
        self.projection = ResponseProjection()
        self.streaming = False
        self.status_code = None
        self.finished = False
        self.normal = None
    async def begin(self):
        # Fail closed: a provider call may not start until its input is durable.
        await self.repository.start(self.values)
    def bind(self, status_code, streaming):
        self.status_code = status_code
        self.streaming = streaming
    async def record(self, body):
        if not body:
            return
        await self.repository.append(self.id, self.sequence, bytes(body))
        self.sequence += 1
        self.byte_count += len(body)
        self.digest.update(body)
        if self.streaming:
            try:
                self.projection.feed(body)
            except (ValueError, TypeError, KeyError, AttributeError, RecursionError):
                # Projection is optional; original bytes remain authoritative and durable.
                self.projection.result['projection_warning'] = 'An unrecognized provider event was preserved in the raw response'
    def normal_response(self, body):
        try:
            self.normal = json.loads(body)
        except (ValueError, UnicodeDecodeError, RecursionError):
            self.normal = {'text': body.decode('utf-8', errors='replace')}
    async def finish(self, state=None, error=None):
        if self.finished:
            return
        response = (self.projection.result or self.normal) if self.streaming else self.normal
        if state is None:
            complete = self.projection.terminal if self.streaming else self.normal is not None
            state = 'completed' if complete else 'incomplete'
            if (self.status_code or 0) >= 400 or self.projection.error:
                state = 'error'
        with anyio.CancelScope(shield=True):
            await self.repository.finish(self.id, state=state, status_code=self.status_code,
                response=response, provider_id=response.get('id') if isinstance(response, dict) else None,
                response_sha256=self.digest.hexdigest(), byte_count=self.byte_count, error=error)
        self.finished = True
