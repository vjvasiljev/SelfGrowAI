"""
Task Manager Module

Manages the lifecycle of tasks: initial generation, retrieval, and refinement using the AI client.
"""

from .openai_client import OpenAIClient
from .memory import Memory
import os
import subprocess
import re
import json


class TaskManager:
    """
    Coordinates task creation, retrieval, and refinement for the self-growing agent.
    """

    def __init__(
        self, memory_store: Memory, openai_client: OpenAIClient, agent_config: dict
    ):
        """
        Initialize TaskManager.

        Args:
            memory_store: Memory instance for persisting tasks.
            openai_client: OpenAIClient instance for generating tasks.
            agent_config: Dictionary containing agent settings (initial prompt, max iterations).
        """
        self.memory = memory_store
        self.client = openai_client
        self.agent_config = agent_config

    def generate_initial_tasks(self) -> None:
        """
        Generate the initial batch of tasks.
        - If memory is empty and 'initial_task' is configured, add it.
        - Otherwise, request a structured JSON list via the 'generate_tasks' function.
        """
        # Seed fallback initial task if none exist
        if not self.memory.get_pending_tasks():
            fallback = self.agent_config.get("initial_task")
            if fallback:
                self.memory.add_task(fallback)
                return
        # Function schema for generating tasks; include context for better task relevance
        base_prompt = self.agent_config.get("initial_prompt", "")
        # Gather project file list for context
        file_list = []
        for dirpath, _, filenames in os.walk(os.getcwd()):
            for fname in filenames:
                file_list.append(
                    os.path.relpath(os.path.join(dirpath, fname), os.getcwd())
                )
        file_context = "\n".join(file_list)
        system_prompt = (
            f"{base_prompt}\n\n"
            "You may call the function generate_tasks(tasks) to register new tasks.\n"
            f"Project files:\n{file_context}"
        )
        user_prompt = (
            "Invoke generate_tasks with an array of the next development tasks as strings. "
            "Do not reply with any other text."
        )
        function_def = {
            "name": "generate_tasks",
            "description": "Returns the next set of tasks as a list of strings.",
            "parameters": {
                "type": "object",
                "properties": {"tasks": {"type": "array", "items": {"type": "string"}}},
                "required": ["tasks"],
            },
        }
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        # Invoke AI with function definitions
        # Request tasks via AI function-calling, using 'planning' model
        msg = self.client.chat(messages, functions=[function_def], stage="planning")
        func_call = getattr(msg, "function_call", None)
        # Parse function_call if present
        if func_call and hasattr(func_call, "arguments"):
            try:
                payload = json.loads(func_call.arguments)
                for task in payload.get("tasks", []):
                    self.memory.add_task(task)
                return
            except Exception:
                pass
        # Fallback: parse as newline-separated text
        text = getattr(msg, "content", "") or ""
        for line in text.split("\n"):
            desc = line.strip()
            if not desc:
                continue
            desc = re.sub(r"^[\s\d\-\*\.\)]+", "", desc)
            desc = desc.replace("*", "").strip()
            self.memory.add_task(desc)

    def get_next_task(self):
        """
        Retrieve the next pending task from memory.

        Returns:
            A tuple (task_id, task_description) for the next pending task,
            or None if no pending tasks remain.
        """
        pending_tasks = self.memory.get_pending_tasks()
        if not pending_tasks:
            return None
        task_id, task_description = pending_tasks[0]
        return task_id, task_description

    def refine_tasks(
        self, previous_task_description: str, previous_task_result: str
    ) -> None:
        """
        Generate follow-up tasks based on the last task and its result.
        Uses function-calling to get a structured task list first, then falls back to text parsing.
        """
        # Prepare context: initial prompt, last result, recent code diff
        base_prompt = self.agent_config.get("initial_prompt", "")
        # Attempt to get recent diff
        try:
            diff_proc = subprocess.run(
                ["git", "diff", "HEAD~1", "HEAD"],
                cwd=os.getcwd(),
                capture_output=True,
                text=True,
                check=True,
            )
            recent_diff = diff_proc.stdout
        except Exception:
            recent_diff = ""
        system_prompt = (
            f"{base_prompt}\n\n"
            "You may call function generate_tasks(tasks) to enqueue follow-up tasks.\n"
            f"Last result for '{previous_task_description}':\n{previous_task_result}\n"
            f"Recent diff:\n{recent_diff}"
        )
        # Attempt to get diff of last commit
        try:
            import subprocess

            diff_proc = subprocess.run(
                ["git", "diff", "HEAD~1", "HEAD"],
                cwd=os.getcwd(),
                capture_output=True,
                text=True,
                check=True,
            )
            recent_diff = diff_proc.stdout
        except Exception:
            recent_diff = ""
        # Build user prompt with result and diff context
        user_prompt = (
            f"Last task: {previous_task_description}\n"
            f"Result:\n{previous_task_result}\n\n"
            f"Recent changes (diff):\n{recent_diff}\n"
            "Provide the next development tasks as a JSON array under 'tasks'."
        )
        function_def = {
            "name": "generate_tasks",
            "description": "Returns the next set of tasks as a list of strings.",
            "parameters": {
                "type": "object",
                "properties": {"tasks": {"type": "array", "items": {"type": "string"}}},
                "required": ["tasks"],
            },
        }
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        # AI call with function schema
        # Request refinement via AI function-calling, using 'refinement' model
        msg = self.client.chat(messages, functions=[function_def], stage="refinement")
        func_call = getattr(msg, "function_call", None)
        if func_call and hasattr(func_call, "arguments"):
            try:
                payload = json.loads(func_call.arguments)
                for task in payload.get("tasks", []):
                    self.memory.add_task(task)
                return
            except Exception:
                pass
        # Fallback: parse plain text
        text = getattr(msg, "content", "") or ""
        for line in text.split("\n"):
            desc = line.strip()
            if not desc:
                continue
            desc = re.sub(r"^[\s\d\-\*\.\)]+", "", desc)
            desc = desc.replace("*", "").strip()
            self.memory.add_task(desc)
