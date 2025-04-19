"""
Memory Module

Provides a persistent task memory using a SQLite database to track pending and completed tasks.
"""
import sqlite3
import threading
from datetime import datetime

DEFAULT_DB_PATH = "selfgrow_memory.db"

class Memory:
    """
    Task memory manager that stores tasks, statuses, and results in SQLite.
    Thread-safe for concurrent access.
    """
    _lock = threading.Lock()

    def __init__(self, db_path: str = None):
        """
        Initialize the SQLite connection and ensure required tables exist.

        Args:
            db_path: Optional path to the SQLite database file. If None, uses DEFAULT_DB_PATH.
        """
        # Determine database path
        if not db_path:
            db_path = DEFAULT_DB_PATH
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._ensure_tables()
    def _ensure_tables(self) -> None:
        """
        Create the tasks table if it does not already exist.
        """
        with self.conn:
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    description TEXT NOT NULL,
                    status TEXT NOT NULL,
                    result TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
    def add_task(self, description: str) -> None:
        """
        Add a new task to the memory with status 'pending'.

        Args:
            description: Text description of the task.
        """
        with Memory._lock:
            with self.conn:
                self.conn.execute(
                    "INSERT INTO tasks (description, status, created_at) VALUES (?, ?, ?)",
                    (description, "pending", datetime.utcnow().isoformat())
                )
    def get_pending_tasks(self) -> list:
        """
        Retrieve all tasks with 'pending' status, ordered by their insertion order.

        Returns:
            A list of tuples (task_id, task_description).
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT id, description FROM tasks WHERE status = 'pending' ORDER BY id"
        )
        return cursor.fetchall()
    def update_task(self, task_id: int, status: str, result: str = None) -> None:
        """
        Update the status and optional result of a task.

        Args:
            task_id: The integer ID of the task.
            status: New status (e.g., 'done', 'error').
            result: Optional textual result of task execution.
        """
        with Memory._lock:
            with self.conn:
                self.conn.execute(
                    "UPDATE tasks SET status = ?, result = ? WHERE id = ?",
                    (status, result, task_id)
                )
    def get_tasks_by_status(self, status: str) -> list:
        """
        Retrieve tasks filtered by status.

        Args:
            status: Task status to filter on ('pending', 'done', 'error').

        Returns:
            A list of tuples (id, description, status, result, created_at).
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT id, description, status, result, created_at FROM tasks WHERE status = ? ORDER BY id",  # noqa: E501
            (status,)
        )
        return cursor.fetchall()

    def get_all_tasks(self) -> list:
        """
        Retrieve all tasks in memory, ordered by insertion.

        Returns:
            A list of tuples (id, description, status, result, created_at).
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT id, description, status, result, created_at FROM tasks ORDER BY id"
        )
        return cursor.fetchall()

    def clear_all_tasks(self) -> None:
        """
        Delete all tasks from memory.
        """
        with Memory._lock:
            with self.conn:
                self.conn.execute("DELETE FROM tasks")