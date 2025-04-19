"""Entry point for the Self-Growing AI Agent CLI."""

import typer
from .cli import app


def load_configuration(config_file_path: str = "config.yaml") -> dict:
    """
    Load and parse the YAML configuration file.
    """
    if not os.path.exists(config_file_path):
        raise FileNotFoundError(f"Configuration file not found: {config_file_path}")
    with open(config_file_path, "r") as config_file:
        return yaml.safe_load(config_file)


def main() -> None:
    """
    Orchestrate the self-growing loop: generate tasks, execute them, record results,
    and refine further tasks based on the outcomes.
    """
    configuration = load_configuration()
    client = OpenAIClient(config_path="config.yaml")
    memory_store = Memory()
    agent_settings = configuration.get("agent", {})
    # Initialize core components
    task_manager = TaskManager(memory_store, client, agent_settings)
    # Configure Git remote for pushing changes if specified
    vc_config = configuration.get("version_control", {})
    remote_name = vc_config.get("remote_name", "origin")
    remote_url = vc_config.get("remote_url")
    branch = vc_config.get("branch", "main")
    if remote_url:
        # Add or update Git remote
        existing_remotes = subprocess.run(
            ["git", "remote"], cwd=os.getcwd(), capture_output=True, text=True
        ).stdout.split()
        if remote_name not in existing_remotes:
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
    # Initialize executor with AI client and Git settings
    # Git push will only run if a remote_url was provided
    executor = CodeExecutor(
        openai_client=client,
        work_directory=None,
        git_remote=remote_name if remote_url else None,
        git_branch=branch,
    )

    # Generate initial tasks if none exist
    if not memory_store.get_pending_tasks():
        print("Generating initial tasks...")
        task_manager.generate_initial_tasks()

    iteration = 0
    max_iterations = agent_settings.get("max_iterations", 10)
    while iteration < max_iterations:
        next_item = task_manager.get_next_task()
        if not next_item:
            print("All tasks completed. Exiting.")
            break

        task_id, task_description = next_item
        print(
            f"[Iteration {iteration + 1}/{max_iterations}] Task {task_id}: {task_description}"
        )
        try:
            result_output = executor.execute(task_description)
            memory_store.update_task(task_id, "done", result_output)
            print(f"Task {task_id} result: {result_output}")
            task_manager.refine_tasks(task_description, result_output)
        except Exception as error:
            memory_store.update_task(task_id, "error", str(error))
            print(f"Error in Task {task_id}: {error}")

        iteration += 1


if __name__ == "__main__":
    app()
