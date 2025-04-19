import os
import sys

# Ensure project root is on sys.path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import json
import json
import subprocess
import pytest

from selfgrow.code_executor import CodeExecutor
from selfgrow.openai_client import OpenAIClient


class DummyFunctionCall:
    """Simulates a function_call object with JSON arguments."""

    def __init__(self, arguments: str):
        self.arguments = arguments


class DummyMessage:
    """Simulates a Message with a function_call attribute."""

    def __init__(self, func_args: dict):
        # Serialize arguments to JSON string
        self.function_call = DummyFunctionCall(json.dumps(func_args))


class DummyClient:
    """Dummy OpenAIClient that returns a predetermined function_call message."""

    def __init__(self, changes):
        self.changes = changes

    def chat(self, messages, functions=None, **kwargs):
        # Return a DummyMessage with the specified changes
        return DummyMessage({"changes": self.changes})


@pytest.fixture(autouse=True)
def stub_subprocess(monkeypatch):
    """Stub subprocess.run to record calls without executing Git commands."""
    calls = []

    def fake_run(cmd, cwd=None, check=False, **kwargs):
        calls.append(list(cmd))

        class Result:
            pass

        return Result()

    monkeypatch.setattr(subprocess, "run", fake_run)
    return calls


def test_execute_creates_files_and_commits(tmp_path, stub_subprocess):
    # Prepare dummy file changes
    changes = [
        {"path": "foo.txt", "content": "Hello"},
        {"path": "bar/baz.txt", "content": "World"},
    ]
    # Initialize executor with dummy client
    client = DummyClient(changes)
    executor = CodeExecutor(
        openai_client=client,
        work_directory=str(tmp_path),
        git_remote=None,
        git_branch="main",
    )
    # Execute task
    result = executor.execute("Test task")

    # Verify files were created with correct content
    file1 = tmp_path / "foo.txt"
    file2 = tmp_path / "bar" / "baz.txt"
    assert file1.exists()
    assert file1.read_text() == "Hello"
    assert file2.exists()
    assert file2.read_text() == "World"

    # Verify return message
    assert "Applied changes to: foo.txt, bar/baz.txt" in result

    # Verify subprocess.run was called for git add and commit
    assert ["git", "add", "foo.txt", "bar/baz.txt"] in stub_subprocess
    # Commit message should start with 'AI: Test task'
    commit_calls = [
        call for call in stub_subprocess if call[:3] == ["git", "commit", "-m"]
    ]
    assert any("AI: Test task" in call[3] for call in commit_calls)
    # Verify pytest was invoked to run tests
    assert ["pytest", "-q"] in stub_subprocess
    # Now test fallback 'create file' path
    # Clear recorded calls
    stub_subprocess.clear()
    # Create executor and run fallback task
    executor2 = CodeExecutor(
        openai_client=DummyClient([]),
        work_directory=str(tmp_path),
        git_remote=None,
        git_branch="main",
    )
    fallback_result = executor2.execute("create file alpha.txt with content 'XYZ'")
    # Verify fallback file creation
    alpha = tmp_path / "alpha.txt"
    assert alpha.exists()
    assert alpha.read_text() == "XYZ"
    assert "Created file alpha.txt" in fallback_result
    # Verify subprocess.run for add and commit
    # Now uses 'git add -A' to stage all changes
    assert ["git", "add", "-A"] in stub_subprocess
    # Commit should use '-a -m'
    commit_calls = [
        c for c in stub_subprocess if c[:4] == ["git", "commit", "-a", "-m"]
    ]
    assert commit_calls and "Create alpha.txt (fallback)" in commit_calls[0][4]


def test_format_code_task(tmp_path, stub_subprocess):
    # Initialize executor with dummy client (no function_call expected)
    client = DummyClient([])
    executor = CodeExecutor(
        openai_client=client,
        work_directory=str(tmp_path),
        git_remote=None,
        git_branch="main",
    )
    # Execute 'format code' fallback
    result = executor.execute("format code")
    # Verify result message
    assert result == "Code formatted with Black"
    # Verify black was invoked
    assert ["black", "."] in stub_subprocess
    # Verify git add and commit were invoked
    assert ["git", "add", "-A"] in stub_subprocess
    commit_calls = [
        c for c in stub_subprocess if c[:4] == ["git", "commit", "-a", "-m"]
    ]
    assert any("Apply code formatting via Black" in c[4] for c in commit_calls)
    # Now test 'install black' fallback
    stub_subprocess.clear()
    executor3 = CodeExecutor(
        openai_client=DummyClient([]),
        work_directory=str(tmp_path),
        git_remote=None,
        git_branch="main",
    )
    install_result = executor3.execute("install black for code formatting")
    assert install_result == "Installed Black via pip"
    # Verify pip install was invoked
    assert ["pip", "install", "black"] in stub_subprocess
    # Verify requirements.txt staged and committed
    assert ["git", "add", "requirements.txt"] in stub_subprocess
    commit_calls = [c for c in stub_subprocess if c[:3] == ["git", "commit", "-m"]]
    assert any("Install Black (fallback)" in c[3] for c in commit_calls)
