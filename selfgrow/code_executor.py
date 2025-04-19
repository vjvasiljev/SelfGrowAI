"""
Code Executor Module

Executes tasks by generating or running code changes using AI-generated patches.
"""
import os
import subprocess
from typing import Optional
from .openai_client import OpenAIClient

class CodeExecutor:
    """
    Executes tasks by generating unified diff patches via the AI client and applying them.
    """
    def __init__(
        self,
        openai_client: OpenAIClient,
        work_directory: Optional[str] = None,
        git_remote: Optional[str] = None,
        git_branch: str = "main"
    ):
        """
        Initialize the executor with an AI client and working directory.

        Args:
            openai_client: Instance of OpenAIClient for patch generation.
            work_directory: Directory in which to apply code changes. Defaults to current working directory.
        """
        self.client = openai_client
        self.work_directory = work_directory or os.getcwd()
        self.git_remote = git_remote
        self.git_branch = git_branch

    def execute(self, task_description: str) -> str:
        """
        Generate and apply a unified diff patch to implement the given task.

        Args:
            task_description: Description of the task to perform.

        Returns:
            The patch text that was applied.

        Raises:
            RuntimeError: If the patch fails to apply.
        """
        # Prepare prompts for patch generation
        system_message = (
            "You are an AI code generator. Generate a unified diff patch "
            "to implement the following task in the repository."
        )
        user_message = (
            f"Task: {task_description}\n"
            "Respond ONLY with the patch in unified diff format. Do not include any explanations."
        )
        # Request patch from OpenAI
        patch_text = self.client.chat(
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message},
            ],
            temperature=0,
            max_tokens=1500
        )
        # Apply patch via Git
        try:
            subprocess.run(
                ["git", "apply", "-"],
                input=patch_text.encode("utf-8"),
                cwd=self.work_directory,
                check=True
            )
        except subprocess.CalledProcessError as apply_error:
            raise RuntimeError(f"Failed to apply patch: {apply_error}")
        # Stage and commit changes
        subprocess.run(
            ["git", "add", "-A"],
            cwd=self.work_directory,
            check=True
        )
        commit_message = f"AI: {task_description}"[:50]
        subprocess.run(
            ["git", "commit", "-m", commit_message],
            cwd=self.work_directory,
            check=True
        )
        # Run test suite to validate changes
        try:
            subprocess.run(
                ["pytest", "-q"],
                cwd=self.work_directory,
                check=True,
                capture_output=True,
                text=True
            )
        except subprocess.CalledProcessError as test_error:
            # Roll back last commit if tests fail
            subprocess.run(
                ["git", "reset", "--hard", "HEAD~1"],
                cwd=self.work_directory,
                check=True
            )
            raise RuntimeError(
                f"Tests failed after applying patch for task '{task_description}':\n"
                f"{test_error.stdout}\n{test_error.stderr}"
            )
        # Push the new commit to the configured remote and branch
        if self.git_remote and self.git_branch:
            subprocess.run(
                ["git", "push", self.git_remote, self.git_branch],
                cwd=self.work_directory,
                check=True
            )
        return patch_text