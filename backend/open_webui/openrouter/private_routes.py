from fastapi import Depends, HTTPException, Request
from open_webui.openrouter.private_data import strict_user_isolation
from open_webui.utils.auth import get_verified_user
async def enforce_private_routes(request: Request, user=Depends(get_verified_user)):
    if not strict_user_isolation() or user.role == 'admin':
        return
    path = request.url.path
    if request.method == 'GET' and path.rstrip('/') in {'/api/v1/folders/shared', '/api/v1/chats/shared'}:
        return
    segments = path.strip('/').split('/')
    if path.startswith('/api/v1/channels') or {'share', 'shared', 'access'} & set(segments):
        raise HTTPException(403, 'This instance keeps user conversations private')
