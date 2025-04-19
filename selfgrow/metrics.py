"""
Metrics Module

Tracks execution statistics for GrowAI tasks.
"""
from typing import Dict

class Metrics:
    """
    Simple metrics collector for task executions.
    """
    def __init__(self):
        self.total_tasks = 0
        self.successful_tasks = 0
        self.failed_tasks = 0

    def record_success(self) -> None:
        """Record a successfully executed task."""
        self.total_tasks += 1
        self.successful_tasks += 1

    def record_failure(self) -> None:
        """Record a failed task execution."""
        self.total_tasks += 1
        self.failed_tasks += 1

    def summary(self) -> Dict[str, int]:
        """Return a summary of metrics."""
        return {
            "total_tasks": self.total_tasks,
            "successful_tasks": self.successful_tasks,
            "failed_tasks": self.failed_tasks,
        }