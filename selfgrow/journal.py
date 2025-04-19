"""
Journal Module

Handles appending entries to the Lab Journal (README.md) and committing them to git.
"""

import re
import os
import datetime
import subprocess

README_PATH = "README.md"
ENTRY_REGEX = re.compile(r"## Entry (\d+)")


class Journal:
    """
    Append chronicle entries to the Lab Journal in README.md, commit, and push.
    """

    def __init__(self, git_remote: str = None, git_branch: str = "main"):
        self.readme_path = README_PATH
        self.git_remote = git_remote
        self.git_branch = git_branch

    def _get_next_entry_number(self) -> int:
        max_num = 0
        try:
            with open(self.readme_path, "r", encoding="utf-8") as f:
                for line in f:
                    m = ENTRY_REGEX.match(line)
                    if m:
                        num = int(m.group(1))
                        if num > max_num:
                            max_num = num
        except FileNotFoundError:
            return 1
        return max_num + 1

    def log(self, description: str) -> None:
        """
        Append a new journal entry with the given description and current timestamp.

        Args:
            description: Short description of the event.
        """
        entry_num = self._get_next_entry_number()
        timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        header = f"## Entry {entry_num:03d} — {description} ({timestamp})\n"
        # Read existing README
        with open(self.readme_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        # Find insertion point: before the final '---' separator
        insert_idx = None
        for idx, line in enumerate(lines):
            if line.strip() == "---":
                insert_idx = idx
        # Default to appending at end if not found
        if insert_idx is None:
            insert_idx = len(lines)
        # Insert header and a blank line
        new_lines = lines[:insert_idx] + [header, "\n"] + lines[insert_idx:]
        # Write back
        with open(self.readme_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        # Commit and push
        cwd = os.getcwd()
        subprocess.run(["git", "add", self.readme_path], cwd=cwd, check=True)
        commit_msg = f"Journal: {description[:50]}"
        subprocess.run(["git", "commit", "-m", commit_msg], cwd=cwd, check=True)
        # Attempt to push journal commit, ignore failures
        if self.git_remote:
            try:
                subprocess.run(
                    ["git", "push", self.git_remote, self.git_branch],
                    cwd=cwd,
                    check=True,
                )
            except subprocess.CalledProcessError:
                pass
