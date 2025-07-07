#!/usr/bin/env python3
"""
LLM model discovery and management for LLM Digest.
Service for discovering and filtering available LLM models.
"""

import re
import subprocess
from typing import Optional

from models import LLMModel


class LLMModelDiscovery:
    """Service for discovering and filtering available LLM models."""

    def __init__(self, cache_timeout: int = 300):
        """Initialize with cache timeout in seconds."""
        self.cache_timeout = cache_timeout
        self._cached_models: Optional[list[LLMModel]] = None
        self._cache_timestamp = 0.0

        # Fallback models if discovery fails
        self.fallback_models = [
            # Local Ollama models (highest priority)
            LLMModel(
                "llama3.2", "Ollama", ["llama3.2-3b", "llama3.2:latest"], True, False, 1
            ),
            LLMModel("llama3.1", "Ollama", ["llama3.1:latest"], True, False, 2),
            LLMModel("mistral", "Ollama", ["mistral:latest"], True, False, 3),
            LLMModel("codellama", "Ollama", ["codellama:latest"], True, False, 4),
            # OpenAI models as fallback
            LLMModel("gpt-4o", "OpenAI Chat", ["4o"], True, False, 10),
            LLMModel("gpt-4o-mini", "OpenAI Chat", ["4o-mini"], True, False, 11),
            LLMModel("gpt-4", "OpenAI Chat", ["4", "gpt4"], True, False, 12),
            LLMModel(
                "gpt-3.5-turbo", "OpenAI Chat", ["3.5", "chatgpt"], True, False, 13
            ),
        ]

        # Model prioritization rules
        self.priority_rules = {
            # Provider preferences (lower = higher priority)
            "Ollama": 5,  # Ollama models get highest priority for local inference
            "OpenAI Chat": 10,
            "GeminiPro": 20,
            "OpenAI Completion": 30,
            # Model type preferences
            "chat_bonus": -5,  # Chat models are preferred
            "experimental_penalty": 50,  # Experimental models get lower priority
            # Specific model bonuses (applied to base priority)
            # Ollama models
            "llama3.2": -15,  # Highest priority for local inference
            "llama3.1": -12,
            "mistral": -10,
            "codellama": -8,
            "llama2": -6,
            # OpenAI models
            "gpt-4o": -10,
            "gpt-4o-mini": -8,
            "gpt-4": -6,
            "gpt-3.5-turbo": -4,
            "gemini-2.0-flash": -3,
            "gemini-1.5-pro-latest": -2,
        }

    def _log_debug(self, message: str) -> None:
        """Log debug messages if debug mode is enabled."""
        # For testing, we'll just print to stdout
        print(f"DEBUG: {message}")

    def _run_llm_models_list(self) -> Optional[str]:
        """Run 'llm models list' and return output."""
        try:
            result = subprocess.run(
                ["llm", "models", "list"], capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                return result.stdout
            return None
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            return None

    def _parse_models_output(self, output: str) -> list[LLMModel]:
        """Parse the output of 'llm models list' into LLMModel objects."""
        models = []

        for line in output.strip().split("\n"):
            line = line.strip()
            if not line or line.startswith("Default:"):
                continue

            # Parse format: "Provider: model_name (aliases: alias1, alias2)"
            parts = line.split(": ", 1)
            if len(parts) != 2:
                continue

            provider = parts[0].strip()
            model_part = parts[1].strip()

            # Extract model name and aliases using regex
            match = re.match(r"^(.*?)(?: \(aliases: (.*)\))?$", model_part)
            if match:
                model_name = match.group(1).strip()
                aliases_str = match.group(2)
                aliases = (
                    [alias.strip() for alias in aliases_str.split(", ")]
                    if aliases_str
                    else []
                )
            else:
                model_name = model_part
                aliases = []
            # print(f"DEBUG: Parsed model_name: {model_name}, Aliases: {aliases}")

            # Determine model characteristics
            is_chat = provider.endswith("Chat") or not provider.endswith("Completion")
            is_experimental = any(
                re.search(r"\b" + keyword + r"\b", model_name.lower())
                for keyword in ["preview", "experimental", "exp", "thinking", "test"]
            )

            # Calculate priority
            priority = self._calculate_priority(
                provider, model_name, is_chat, is_experimental
            )

            models.append(
                LLMModel(
                    name=model_name,
                    provider=provider,
                    aliases=aliases,
                    is_chat=is_chat,
                    is_experimental=is_experimental,
                    priority=priority,
                )
            )

        return models

    def _calculate_priority(
        self, provider: str, model_name: str, is_chat: bool, is_experimental: bool
    ) -> int:
        """Calculate priority score for a model (lower = higher priority)."""
        priority = self.priority_rules.get(provider, 100)

        if is_chat:
            priority += self.priority_rules["chat_bonus"]

        if is_experimental:
            priority += self.priority_rules["experimental_penalty"]

        # Apply specific model bonuses - sort by length of key to apply most specific first
        sorted_model_bonuses = sorted(
            [
                (k, v)
                for k, v in self.priority_rules.items()
                if isinstance(v, int) and v < 0 and k in model_name
            ],
            key=lambda item: len(item[0]),
            reverse=True,
        )

        for _model_key, bonus in sorted_model_bonuses:
            priority += bonus
            break  # Apply only the most specific bonus

        for _model_key, bonus in sorted_model_bonuses:
            priority += bonus
            break  # Apply only the most specific bonus

        return priority

    def discover_models(self, force_refresh: bool = False) -> list[LLMModel]:
        """
        Discover available LLM models with caching.
        Returns filtered and prioritized list of models.
        """
        import time

        current_time = time.time()

        # Use cache if valid and not forcing refresh
        if (
            not force_refresh
            and self._cached_models is not None
            and current_time - self._cache_timestamp < self.cache_timeout
        ):
            return self._cached_models

        # Try to discover models
        output = self._run_llm_models_list()
        if output:
            models = self._parse_models_output(output)
            filtered_models = self._filter_and_prioritize(models)

            # Update cache
            self._cached_models = filtered_models
            self._cache_timestamp = current_time

            return filtered_models

        # Return fallback models if discovery fails
        return self.fallback_models

    def _filter_and_prioritize(self, models: list[LLMModel]) -> list[LLMModel]:
        """Filter and prioritize models for practical use."""
        # Filter out models we don't want to show
        filtered = []

        for model in models:
            # Skip if experimental and we have non-experimental alternatives
            if model.is_experimental:
                continue

            # Skip very old or deprecated models
            if any(
                keyword in model.name.lower()
                for keyword in [
                    "1106-preview",
                    "0125-preview",
                    "32k",
                    "instruct",
                    "davinci",
                    "curie",
                ]
            ):
                continue

            # Skip audio/specialized models for text summarization
            if any(keyword in model.name.lower() for keyword in ["audio"]):
                continue

            filtered.append(model)

        # Sort by priority (lower number = higher priority)
        filtered.sort(key=lambda m: m.priority)

        # Limit to top models to avoid overwhelming users
        return filtered[:15]

    def get_recommended_models(self) -> list[LLMModel]:
        """Get a curated list of recommended models for summarization."""
        all_models = self.discover_models()

        # Return top priority models
        return all_models[:6]

    def get_models_by_category(self) -> dict[str, list[LLMModel]]:
        """Get models organized by category for better user experience."""
        all_models = self.discover_models()

        categories: dict[str, list[LLMModel]] = {
            "recommended": [],
            "budget": [],
            "alternative": [],
        }

        # Categorize models
        for model in all_models:
            # Local Ollama models get highest priority in recommended
            if model.provider == "Ollama":
                categories["recommended"].append(model)
            # Budget models (fast and cost-effective)
            elif any(
                keyword in model.name.lower()
                for keyword in ["mini", "3.5", "flash-8b", "nano"]
            ):
                categories["budget"].append(model)
            # Alternative providers (non-OpenAI, non-Ollama)
            elif not model.provider.startswith("OpenAI") and model.provider != "Ollama":
                categories["alternative"].append(model)
            # Everything else goes to recommended
            else:
                categories["recommended"].append(model)

        # Ensure each category has reasonable limits
        for category in categories:
            categories[category] = categories[category][:5]

        return categories

    def get_model_by_name(self, name: str) -> Optional[LLMModel]:
        """Find a model by name or alias."""
        models = self.discover_models()
        self._log_debug(f"Searching for '{name}' in models: {[m.name for m in models]}")

        for model in models:
            if model.name == name or name in model.aliases:
                return model

        return None

    def validate_model(self, name: str) -> tuple[bool, Optional[str]]:
        """
        Validate if a model name is available.
        Returns (is_valid, suggestion_message).
        """
        model = self.get_model_by_name(name)
        if model:
            return True, None

        # Try to find similar models
        models = self.discover_models()
        suggestions = []

        # Look for partial matches
        name_lower = name.lower()
        for model in models[:5]:  # Top 5 models
            if name_lower in model.name.lower() or any(
                name_lower in alias.lower() for alias in model.aliases
            ):
                suggestions.append(model.name)

        if not suggestions:
            # Fallback to top recommended models
            recommended = self.get_recommended_models()
            suggestions = [m.name for m in recommended[:3]]

        suggestion_msg = f"Model '{name}' not found. Try: {', '.join(suggestions)}"
        return False, suggestion_msg