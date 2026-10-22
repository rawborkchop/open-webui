import os
def strict_user_isolation():
    return os.getenv('OPENROUTER_STRICT_USER_ISOLATION', 'true').lower() == 'true'
