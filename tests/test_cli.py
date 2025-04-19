import os
import sys
from typer.testing import CliRunner

# Ensure project root is on PYTHONPATH for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from selfgrow.cli import app
from selfgrow import __version__

runner = CliRunner()

def test_version_flag():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout