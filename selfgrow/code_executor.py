"""
Code Executor Module

Executes tasks by generating file changes via function-calling and applying them.
"""
import os
import subprocess
import json
from typing import Optional
from datetime import datetime
from .openai_client import OpenAIClient
import re

class CodeExecutor:
    """
    Executes tasks by generating file changes via the AI client and applying them.
    """
    def __init__(
        self,
        openai_client: OpenAIClient,
        work_directory: Optional[str] = None,
        git_remote: Optional[str] = None,
        git_branch: str = "main"
    ):
        """
        Initialize the executor.

        Args:
            openai_client: Instance of OpenAIClient for generating changes.
            work_directory: Directory to write files; defaults to CWD.
            git_remote: Git remote name for pushing (e.g., 'origin').
            git_branch: Git branch to push to.
        """
        self.client = openai_client
        self.work_directory = work_directory or os.getcwd()
        self.git_remote = git_remote
        self.git_branch = git_branch

    def execute(self, task_description: str) -> str:
        """
        Execute a task by requesting file changes and applying them.

        Returns:
            A summary of applied files.

        Raises:
            RuntimeError: If no valid function_call or JSON parse error.
        """
        # If task is a local fallback 'create file' command, handle directly
        m = re.match(r"create file (.+) with content '(.+)'", task_description, re.IGNORECASE)
        if m:
            file_rel, content = m.groups()
            file_path = os.path.join(self.work_directory, file_rel)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            # Commit fallback file creation
            # Stage and commit all changes to capture new and modified files
            subprocess.run(['git', 'add', '-A'], cwd=self.work_directory, check=True)
            commit_msg = f"Create {file_rel} (fallback)"[:50]
            subprocess.run(['git', 'commit', '-a', '-m', commit_msg], cwd=self.work_directory, check=True)
            # Push if configured
            if self.git_remote:
                subprocess.run(['git', 'push', self.git_remote, self.git_branch], cwd=self.work_directory, check=False)
            return f"Created file {file_rel} with content."
        # Define function schema for file changes
        functions = [
            {
                "name": "apply_file_changes",
                "description": "Write or update files as specified.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "changes": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "path": {"type": "string"},
                                    "content": {"type": "string"}
                                },
                                "required": ["path", "content"]
                            }
                        }
                    },
                    "required": ["changes"]
                }
            }
        ]
        system_prompt = "You are an AI that generates file changes via function call."
        user_prompt = (
            f"Task: {task_description}. Provide a function_call to apply_file_changes."
        )
        # Call AI with function definitions
        message = self.client.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            functions=functions,
            temperature=0
        )
        # Validate function_call
        if not hasattr(message, 'function_call') or message.function_call is None:
            raise RuntimeError("AI did not return function_call for file changes.")
        # Parse arguments
        try:
            args = json.loads(message.function_call.arguments)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON in function_call arguments: {e}")
        changes = args.get('changes')
        if not isinstance(changes, list) or not changes:
            raise RuntimeError("No file changes provided by AI.")
        applied_files = []
        for change in changes:
            file_path = os.path.join(self.work_directory, change['path'])
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(change['content'])
            applied_files.append(change['path'])
        # Commit file changes
        subprocess.run(['git', 'add'] + applied_files, cwd=self.work_directory, check=True)
        commit_msg = f"AI: {task_description}"[:50]
        subprocess.run(['git', 'commit', '-m', commit_msg], cwd=self.work_directory, check=True)
        # Run test suite to validate changes
        try:
            test_proc = subprocess.run(
                ['pytest', '-q'],
                cwd=self.work_directory,
                check=True,
                capture_output=True,
                text=True
            )
        except subprocess.CalledProcessError as e:
            # Tests failed: revert commit
            subprocess.run(
                ['git', 'reset', '--hard', 'HEAD~1'],
                cwd=self.work_directory,
                check=True
            )
            raise RuntimeError(f"Tests failed for task '{task_description}':\n{e.stdout}\n{e.stderr}")
        # Push commit if configured
        if self.git_remote:
            subprocess.run(['git', 'push', self.git_remote, self.git_branch], cwd=self.work_directory, check=False)
        return f"Applied changes to: {', '.join(applied_files)}; tests passed"