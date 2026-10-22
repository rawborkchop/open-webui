import os
from pathlib import Path
import sys
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.setdefault('WEBUI_SECRET_KEY', 'test-only-secret-for-openrouter-tests')
os.environ.setdefault('ENABLE_DB_MIGRATIONS', 'false')
os.environ.setdefault('USE_SLIM_DOCKER', 'true')
_test_data = tempfile.TemporaryDirectory(prefix='openrouter-tests-')
os.environ.setdefault('DATABASE_URL', f'sqlite:///{Path(_test_data.name).as_posix()}/upstream.db')
os.environ.setdefault('DATABASE_POOL_SIZE', '5')
