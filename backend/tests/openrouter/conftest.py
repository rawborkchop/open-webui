import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.setdefault('WEBUI_SECRET_KEY', 'test-only-secret-for-openrouter-tests')
os.environ.setdefault('ENABLE_DB_MIGRATIONS', 'false')
os.environ.setdefault('USE_SLIM_DOCKER', 'true')
