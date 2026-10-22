import json
from pathlib import Path
import subprocess
import sys
def test_full_application_with_real_accounts_and_simulated_provider(tmp_path):
    # Arrange
    script = Path(__file__).with_name('full_app_scenario.py')
    # Act
    result = subprocess.run([sys.executable, str(script), str(tmp_path)], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=180)
    report = next((line.removeprefix('RESULT_JSON=') for line in result.stdout.splitlines() if line.startswith('RESULT_JSON=')), '{}')
    checks = json.loads(report)
    # Assert
    assert result.returncode == 0, result.stderr[-7000:] + result.stdout[-4000:]
    assert len(checks) >= 20
    assert all(checks.values()), checks
