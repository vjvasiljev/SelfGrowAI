"""
Task Manager Module

Manages the lifecycle of tasks: initial generation, retrieval, and refinement using the AI client.
"""
from .openai_client import OpenAIClient
from .memory import Memory
import re

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
        Generate the initial batch of tasks based on the agent's initial prompt.
        Parses the model's response as a newline-separated list of tasks
        and stores each in memory.
        """
        # Build messages to solicit a clean list of tasks
        """
        Generate the initial batch of actionable code-change tasks.
        """
        system_prompt = self.agent_config.get("initial_prompt", "")
        user_prompt = (
            "Based on your initial directive, provide a newline-separated list of "
            "short, actionable code-change tasks (e.g., 'Refactor X for readability'). "
            "Do not include explanations."
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        response_content = self.client.chat(messages)
        # Split and clean each task description
        for line in response_content.split("\n"):
            desc = line.strip()
            if not desc:
                continue
            # Remove leading numbers or bullet characters
            desc = re.sub(r'^[\s\d\-\*\.\)]+', '', desc)
            # Remove any markdown asterisks and trim whitespace
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
        Use the AI client to generate follow-up tasks based on the result
        of the previous task and add them to memory.

        Args:
            previous_task_description: The description of the task just executed.
            previous_task_result: The result or output from executing that task.
        """
        system_prompt = self.agent_config.get("initial_prompt", "")
        user_prompt = (
            f"Last task: {previous_task_description}\n"
            f"Result:\n{previous_task_result}\n\n"
            "Based on this outcome, list the next short, actionable code-change tasks "
            "as a newline-separated list. Do not include explanations."
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        response_content = self.client.chat(messages)
        # Split and clean new task descriptions
        for line in response_content.split("\n"):
            desc = line.strip()
            if not desc:
                continue
            desc = re.sub(r'^[\s\d\-\*\.\)]+', '', desc)
            desc = desc.replace('*', '').strip()
            self.memory.add_task(desc)