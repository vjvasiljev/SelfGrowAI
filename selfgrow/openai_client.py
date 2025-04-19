"""
OpenAI Client Wrapper

Provides a simple interface for sending chat requests to OpenAI's ChatCompletion API using a configured model.
"""
import os
import openai
from dotenv import load_dotenv
import yaml

class OpenAIClient:
    """Client to interact with OpenAI's ChatCompletion API."""
    def __init__(self, config_path="config.yaml"):
        load_dotenv()
        with open(config_path, "r") as f:
            cfg = yaml.safe_load(f)
        api_key = cfg.get("openai", {}).get("api_key") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key not found in config or environment")
        openai.api_key = api_key
        self.model = cfg.get("openai", {}).get("model", "gpt-4")
    def chat(self, messages: list, **kwargs) -> str:
        """
        Send a sequence of messages to the ChatCompletion API and return the model's response content.

        Args:
            messages: A list of message dicts with 'role' and 'content' keys.
            **kwargs: Additional arguments to pass to the API (e.g., temperature, max_tokens).

        Returns:
            The textual content of the first choice returned by the model.
        """
        response = openai.ChatCompletion.create(
            model=self.model,
            messages=messages,
            **kwargs
        )
        return response.choices[0].message.content