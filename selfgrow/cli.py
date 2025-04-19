"""
Command-Line Interface for Self-Growing AI Agent

Provides commands to run the agent, inspect task memory, and manage tasks.
"""

import os
import subprocess
import yaml
import typer
from .openai_client import OpenAIClient
from .memory import Memory
from .task_manager import TaskManager
from .code_executor import CodeExecutor
from .journal import Journal
from .metrics import Metrics

from .logger import setup_logging

logger = setup_logging()
app = typer.Typer(help="Self-Growing AI Agent CLI")


def load_configuration(config_file: str = "config.yaml") -> dict:
    if not os.path.exists(config_file):
        typer.echo(f"Configuration file not found: {config_file}")
        raise typer.Exit(code=1)
    with open(config_file, "r") as f:
        return yaml.safe_load(f)


@app.command()
def run(
    iterations: int = typer.Option(
        None, "-n", "--iterations", help="Max iterations to run"
    )
):
    """
    Run the self-growing loop: generate, execute, and refine tasks.
    """
    logger.info("Loading configuration...")
    config = load_configuration()
    logger.info("Initializing OpenAI client...")
    try:
        client = OpenAIClient(config_path="config.yaml")
    except ValueError as e:
        typer.secho(f"Configuration error: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    memory_store = Memory()
    agent_cfg = config.get("agent", {})

    logger.info("Configuring version control remote...")
    vc_cfg = config.get("version_control", {})
    remote_name = vc_cfg.get("remote_name", "origin")
    remote_url = vc_cfg.get("remote_url")
    branch = vc_cfg.get("branch", "main")
    if remote_url:
        existing = subprocess.run(
            ["git", "remote"], cwd=os.getcwd(), capture_output=True, text=True
        ).stdout.split()
        if remote_name not in existing:
            subprocess.run(
                ["git", "remote", "add", remote_name, remote_url],
                cwd=os.getcwd(),
                check=True,
            )
        else:
            subprocess.run(
                ["git", "remote", "set-url", remote_name, remote_url],
                cwd=os.getcwd(),
                check=True,
            )

    # Initialize the Task Manager and Code Executor
    task_manager = TaskManager(memory_store, client, agent_cfg)
    executor = CodeExecutor(
        openai_client=client,
        work_directory=None,
        git_remote=remote_name if remote_url else None,
        git_branch=branch,
    )
    # Initialize Journal for logging events
    journal = Journal(git_remote=remote_name if remote_url else None, git_branch=branch)
    # Initialize metrics tracking
    metrics = Metrics()

    # Generate initial tasks if none exist
    if not memory_store.get_pending_tasks():
        logger.info("Generating initial tasks...")
        typer.echo("Generating initial tasks...")
        try:
            task_manager.generate_initial_tasks()
        except Exception as e:
            logger.error(f"Failed to generate initial tasks: {e}")
            typer.secho(f"Failed to generate initial tasks: {e}", fg=typer.colors.RED)
            raise typer.Exit(code=1)

    max_iters = (
        iterations if iterations is not None else agent_cfg.get("max_iterations", 10)
    )
    logger.info(f"Starting run loop for {max_iters} iterations.")
    for i in range(1, max_iters + 1):
        next_item = task_manager.get_next_task()
        if not next_item:
            typer.echo("All tasks completed.")
            journal.log("All tasks completed")
            # Output metrics summary
            summary = metrics.summary()
            logger.info(f"Metrics summary: {summary}")
            typer.echo(f"Metrics: {summary}")
            journal.log(f"Metrics summary: {summary}")
            return
        task_id, desc = next_item
        logger.info(f"Executing task {task_id}/{max_iters}: {desc}")
        typer.echo(f"[{i}/{max_iters}] Task {task_id}: {desc}")
        try:
            result = executor.execute(desc)
            memory_store.update_task(task_id, "done", result)
            logger.info(f"Task {task_id} result: {result}")
            typer.echo(f"Result: {result}")
            # Record success
            metrics.record_success()
            # Log successful execution
            journal.log(f"Applied patch for task {task_id}: {desc}")
            # Generate follow-up tasks
            task_manager.refine_tasks(desc, result)
            journal.log(f"Refined tasks after task {task_id}")
        except Exception as e:
            memory_store.update_task(task_id, "error", str(e))
            logger.error(f"Error in Task {task_id}: {e}")
            typer.secho(f"Error in Task {task_id}: {e}", fg=typer.colors.RED)
            # Record failure and log
            metrics.record_failure()
            journal.log(f"Failed to apply patch for task {task_id}: {desc}")
            continue
    # If max iterations complete without exhausting tasks, report metrics
    summary = metrics.summary()
    logger.info(f"Metrics summary: {summary}")
    typer.echo(f"Metrics: {summary}")
    journal.log(f"Metrics summary: {summary}")


@app.command("list-tasks")
def list_tasks(
    status: str = typer.Option(
        None, "-s", "--status", help="Filter by status: pending, done, error"
    )
):
    """
    List tasks in memory, optionally filtered by status.
    """
    memory_store = Memory()
    if status:
        tasks = memory_store.get_tasks_by_status(status)
    else:
        tasks = memory_store.get_all_tasks()
    if not tasks:
        typer.echo("No tasks found.")
        return
    for task in tasks:
        task_id, desc, stat, result, created = task
        typer.echo(f"[{task_id}] {stat} - {desc} (created at {created})")


@app.command("clear-tasks")
def clear_tasks(
    yes: bool = typer.Option(False, "-y", "--yes", help="Confirm clearing all tasks")
):
    """
    Clear all tasks from memory.
    """
    if not yes:
        confirm = typer.confirm(
            "Are you sure you want to delete all tasks?", abort=True
        )
    memory_store = Memory()
    memory_store.clear_all_tasks()
    typer.secho("All tasks cleared.", fg=typer.colors.GREEN)
