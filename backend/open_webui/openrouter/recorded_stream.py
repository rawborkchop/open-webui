import asyncio
from open_webui.openrouter.exchange_recorder import ExchangeRecorder
class RecordedStream:
    def __init__(self, content, recorder: ExchangeRecorder):
        self.content = content
        self.recorder = recorder
    async def iterate(self, chunks):
        try:
            async for chunk in chunks:
                body = chunk[0] if isinstance(chunk, tuple) else chunk
                await self.recorder.record(body)
                yield chunk
            await self.recorder.finish()
        except (asyncio.CancelledError, GeneratorExit):
            await self.recorder.finish('cancelled')
            raise
        except Exception as error:
            await self.recorder.finish('incomplete', type(error).__name__)
            raise
    def iter_chunks(self):
        return self.iterate(self.content.iter_chunks())
    def iter_any(self):
        return self.iterate(self.content.iter_any())
