"""
Task Manager Module

Manages the lifecycle of tasks: initial generation, retrieval, and refinement using the AI client.
"""
from .openai_client import OpenAIClient
from .memory import Memory
import re
import json

class TaskManager:
    """
    Coordinates task creation, retrieval, and refinement for the self-growing agent.
    """
    def __init__(
        self,
        memory_store: Memory,
        openai_client: OpenAIClient,
        agent_config: dict
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
        # Function schema for generating tasks
        system_prompt = self.agent_config.get("initial_prompt", "")
        user_prompt = "Provide the next development tasks as a JSON array under 'tasks'."
        function_def = {
            "name": "generate_tasks",
            "description": "Returns the next set of tasks as a list of strings.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tasks": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["tasks"]
            }
        }
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        # Invoke AI with function definitions
        msg = self.client.chat(messages, functions=[function_def])
        func_call = getattr(msg, 'function_call', None)
        # Parse function_call if present
        if func_call and hasattr(func_call, 'arguments'):
            try:
                payload = json.loads(func_call.arguments)
                for task in payload.get('tasks', []):
                    self.memory.add_task(task)
                return
            except Exception:
                pass
        # Fallback: parse as newline-separated text
        text = getattr(msg, 'content', '') or ''
        for line in text.split("\n"):
            desc = line.strip()
            if not desc:
                continue
            desc = re.sub(r'^[\s\d\-\*\.\)]+', '', desc)
            desc = desc.replace('*', '').strip()
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
    def refine_tasks(self, previous_task_description: str, previous_task_result: str) -> None:
        """
        Generate follow-up tasks based on the last task and its result.
        Uses function-calling to get a structured task list first, then falls back to text parsing.
        """
        system_prompt = self.agent_config.get("initial_prompt", "")
        user_prompt = (
            f"Last task: {previous_task_description}\n"
            f"Result:\n{previous_task_result}\n\n"
            "Provide the next development tasks as a JSON array under 'tasks'."
        )
        function_def = {
            "name": "generate_tasks",
            "description": "Returns the next set of tasks as a list of strings.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tasks": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["tasks"]
            }
        }
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        # AI call with function schema
        msg = self.client.chat(messages, functions=[function_def])
        func_call = getattr(msg, 'function_call', None)
        if func_call and hasattr(func_call, 'arguments'):
            try:
                payload = json.loads(func_call.arguments)
                for task in payload.get('tasks', []):
                    self.memory.add_task(task)
                return
            except Exception:
                pass
        # Fallback: parse plain text
        text = getattr(msg, 'content', '') or ''
        for line in text.split("\n"):
            desc = line.strip()
            if not desc:
                continue
            desc = re.sub(r'^[\s\d\-\*\.\)]+', '', desc)
            desc = desc.replace('*', '').strip()
            self.memory.add_task(desc)