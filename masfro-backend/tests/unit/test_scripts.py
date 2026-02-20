"""
Validation tests for operational scripts in the scripts/ directory.

Checks existence, executable permission, shebang line, and bash syntax
for all lifecycle management scripts added in the low-RAM branch.
"""

import os
import subprocess
from pathlib import Path

import pytest

# scripts/ is at project root, two levels up from this test file
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"

EXPECTED_SCRIPTS = [
    "build.sh",
    "start.sh",
    "stop.sh",
    "status.sh",
    "restart.sh",
    "setup-swap.sh",
    "setup-systemd.sh",
]


@pytest.mark.parametrize("script_name", EXPECTED_SCRIPTS)
class TestScriptValidation:
    """Validate each operational script."""

    def test_script_exists(self, script_name):
        path = SCRIPTS_DIR / script_name
        assert path.exists(), f"Script not found: {path}"

    def test_script_is_executable(self, script_name):
        path = SCRIPTS_DIR / script_name
        assert os.access(path, os.X_OK), f"Script is not executable: {path}"

    def test_script_has_shebang(self, script_name):
        path = SCRIPTS_DIR / script_name
        first_line = path.read_text().split("\n")[0]
        assert first_line.startswith("#!"), (
            f"Script {script_name} missing shebang. First line: {first_line!r}"
        )
        assert "bash" in first_line, (
            f"Script {script_name} shebang doesn't reference bash: {first_line!r}"
        )

    def test_script_passes_syntax_check(self, script_name):
        path = SCRIPTS_DIR / script_name
        result = subprocess.run(
            ["bash", "-n", str(path)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"Syntax error in {script_name}:\n{result.stderr}"
        )
