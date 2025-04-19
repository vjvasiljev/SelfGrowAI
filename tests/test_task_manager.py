import os
import sys
import json
import sqlite3
import pytest

# Ensure project root is on PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from selfgrow.task_manager import TaskManager
from selfgrow.memory import Memory
from selfgrow.openai_client import OpenAIClient

class DummyFuncCall:
    def __init__(self, args):
        self.arguments = json.dumps(args)

class DummyMsg:
    def __init__(self, func_args=None, content=None):
        self.function_call = DummyFuncCall(func_args) if func_args else None
        self.content = content

class DummyClient:
    def __init__(self, func_args=None, content=None):
        self.func_args = func_args
        self.content = content
    def chat(self, messages, functions=None, **kwargs):
        # If functions provided, return DummyMsg with function_call
        if functions and self.func_args is not None:
            return DummyMsg(func_args=self.func_args)
        # Else return DummyMsg with content
        return DummyMsg(content=self.content)

@pytest.fixture(autouse=True)
def clear_memory(tmp_path, monkeypatch):
    # Use a temp sqlite for memory
    db_path = tmp_path / 'test_memory.db'
    monkeypatch.setenv('MEMORY_DB_PATH', str(db_path))
    # Monkeypatch Memory default path
    from selfgrow import memory as mem_mod
    mem_mod.DEFAULT_DB_PATH = str(db_path)
    yield

def test_generate_initial_tasks_fallback():
    memory = Memory()
    client = DummyClient()
    cfg = {'initial_task': 'fallback task'}
    tm = TaskManager(memory, client, cfg)
    tm.generate_initial_tasks()
    tasks = memory.get_pending_tasks()
    assert len(tasks) == 1
    assert tasks[0][1] == 'fallback task'

def test_generate_initial_tasks_function_call():
    memory = Memory()
    # Pre-add a dummy task so memory is not empty, skip fallback
    memory.add_task('dummy')
    func_args = {'tasks': ['task1', 'task2']}
    client = DummyClient(func_args=func_args)
    cfg = {'initial_prompt': 'prompt'}
    tm = TaskManager(memory, client, cfg)
    tm.generate_initial_tasks()
    tasks = memory.get_pending_tasks()
    # Should still have dummy, plus two new tasks
    assert len(tasks) == 3
    assert tasks[1][1] == 'task1'
    assert tasks[2][1] == 'task2'

def test_refine_tasks_text_fallback():
    memory = Memory()
    client = DummyClient(content='1. newtask')
    cfg = {'initial_prompt': 'prompt'}
    tm = TaskManager(memory, client, cfg)
    tm.refine_tasks('prev', 'result')
    tasks = memory.get_pending_tasks()
    assert tasks[0][1] == 'newtask'

def test_refine_tasks_function_call():
    memory = Memory()
    client = DummyClient(func_args={'tasks': ['a', 'b']})
    cfg = {'initial_prompt': 'prompt'}
    tm = TaskManager(memory, client, cfg)
    tm.refine_tasks('prev', 'result')
    tasks = memory.get_pending_tasks()
    assert tasks[0][1] == 'a'
    assert tasks[1][1] == 'b'