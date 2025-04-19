# Self-Growing AI Agent

This project implements a self-growing AI agent that uses OpenAI's GPT models to recursively generate and execute tasks, improving itself over time.

Features:
- Task memory with SQLite
- Task management via GPT prompts
- Stubbed code executor for executing tasks

Setup:
1. Copy `.env.template` to `.env` and set your `OPENAI_API_KEY`.
2. Install dependencies: `pip install -r requirements.txt`
3. Configure `config.yaml`:
   - Set `openai.api_key` or via `.env`.
   - Under `agent`, adjust `initial_prompt` and `max_iterations` if desired.
   - Under `version_control`, set `remote_url` to your GitHub repo URL (SSH or HTTPS).
4. Run the agent via the selfgrow package:
   ```
   python -m selfgrow
   ```

Future work:
- Integrate code synthesis and automated commits
- Add testing harness and validation
- Advanced feedback loops and version control integration