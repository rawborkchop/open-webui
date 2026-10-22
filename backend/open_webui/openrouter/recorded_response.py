import json
from open_webui.openrouter.recorded_stream import RecordedStream
class RecordedResponse:
    def __init__(self, response, recorder):
        self.response = response
        self.recorder = recorder
        self.content = RecordedStream(response.content, recorder)
        self.body = None
    def __getattr__(self, name):
        return getattr(self.response, name)
    async def read(self):
        if self.body is None:
            parts = []
            # Non-streaming bodies are parsed only after all bytes have been persisted.
            try:
                async for part in self.response.content.iter_any():
                    await self.recorder.record(part)
                    parts.append(part)
                self.body = b''.join(parts)
                self.recorder.normal_response(self.body)
                await self.recorder.finish()
            except BaseException:
                await self.recorder.finish('incomplete')
                raise
        return self.body
    async def json(self, *, loads=json.loads, **kwargs):
        return loads(await self.read())
    async def text(self, encoding=None, errors='strict'):
        return (await self.read()).decode(encoding or self.response.charset or 'utf-8', errors=errors)
