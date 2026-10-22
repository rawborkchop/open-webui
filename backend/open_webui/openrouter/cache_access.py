from pathlib import Path
from sqlalchemy import select
from open_webui.internal.db import get_async_db_context
from open_webui.models.files import File
from open_webui.openrouter.private_data import strict_user_isolation
async def can_read_cache(path, user):
    if user.role == 'admin' or not strict_user_isolation():
        return True
    # Cached outputs must have a persisted owner, just like uploaded attachments.
    candidates = {str(Path(path)), Path(path).as_posix()}
    async with get_async_db_context() as db:
        result = await db.execute(select(File.id).where(File.path.in_(candidates), File.user_id == user.id).limit(1))
        return result.scalar_one_or_none() is not None
