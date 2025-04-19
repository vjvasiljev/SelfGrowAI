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

    def __init__(self, config_path: str = "config.yaml"):
        """
        Load configuration and initialize the OpenAI API client.

        The API key is read from the config file 'openai.api_key', which may contain
        an environment variable placeholder like ${OPENAI_API_KEY}, or from the
        OPENAI_API_KEY env var directly.
        """
        load_dotenv()
        with open(config_path, "r") as f:
            cfg = yaml.safe_load(f) or {}
        # Attempt to read API key from config (expand env var placeholders)
        raw_key = cfg.get("openai", {}).get("api_key")
        api_key = None
        if raw_key:
            # Expand placeholders like ${OPENAI_API_KEY}
            expanded = os.path.expandvars(str(raw_key))
            # If expansion succeeded (no leftover '$'), use it
            if expanded and "$" not in expanded:
                api_key = expanded
        # Fallback to environment variable
        if not api_key:
            api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OpenAI API key not found. Please set in config.yaml or via OPENAI_API_KEY env var"
            )
        openai.api_key = api_key
        # Default model to use if stage-specific model is not set
        self.model = cfg.get("openai", {}).get("model", "gpt-4")
        # Stage-to-model mapping for cost optimization
        self.models_map = cfg.get("openai", {}).get("models", {}) or {}

    def chat(self, messages: list, functions: list = None, stage: str = None, **kwargs):
        """
        Send messages to the ChatCompletion API.

        If 'functions' is provided, the model may respond with a function_call;
        this returns the full Message object. Otherwise, returns the text content.

        Args:
            messages: A list of message dicts with 'role' and 'content'.
            functions: Optional list of function definitions (for function-calling).
            **kwargs: Additional args for the API (temperature, max_tokens, etc.).

        Returns:
            If functions is None: str of the assistant's reply content.
            Else: the Message object including potential function_call.
        """
        # Determine which model to use: stage-specific or default
        model_to_use = self.models_map.get(stage, self.model) if stage else self.model
        request_args = {"model": model_to_use, "messages": messages, **kwargs}
        if functions is not None:
            request_args["functions"] = functions
        response = openai.chat.completions.create(**request_args)
        message = response.choices[0].message
        # If no functions provided, return text content
        if functions is None:
            return message.content
        # Else return full message for function_call handling
        return message
