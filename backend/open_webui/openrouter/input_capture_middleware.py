import json
from uuid import uuid4
class InputCaptureMiddleware:
    def __init__(self, app):
        self.app = app
    async def __call__(self, scope, receive, send):
        prefixes = ('/api/chat/completions', '/api/v1/chat/completions', '/openai/', '/api/v1/tasks/')
        if scope['type'] != 'http' or not scope.get('path', '').startswith(prefixes):
            return await self.app(scope, receive, send)
        state = scope.setdefault('state', {})
        state['openrouter_run_id'] = str(uuid4())
        parts = []
        async def captured_receive():
            message = await receive()
            if message['type'] == 'http.request':
                parts.append(message.get('body', b''))
                if not message.get('more_body', False):
                    try:
                        state['openrouter_client_input'] = json.loads(b''.join(parts))
                    except (ValueError, UnicodeDecodeError):
                        state['openrouter_client_input'] = None
                    parts.clear()
            return message
        return await self.app(scope, captured_receive, send)
