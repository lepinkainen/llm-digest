#!/usr/bin/env python3
"""
Core services for LLM Digest web application.
Extracted and refactored from the original CLI URLSummarizer.
"""

import re
import subprocess
import urllib.parse
from dataclasses import dataclass
from typing import Optional

import requests
from bs4 import BeautifulSoup

from config import settings
from database import SummaryRecord, URLRecord


@dataclass
class SummaryConfig:
    """Configuration for summary generation."""

    model: str = settings.LLM_DEFAULT_MODEL
    format: str = settings.LLM_DEFAULT_FORMAT
    timeout: int = settings.LLM_TIMEOUT
    system_prompt: Optional[str] = None
    debug: bool = settings.LLM_DEBUG_MODE


@dataclass
class LLMModel:
    """Represents an available LLM model."""

    name: str
    provider: str
    aliases: list[str]
    is_chat: bool = True
    is_experimental: bool = False
    priority: int = 100  # Lower = higher priority


class LLMModelDiscovery:
    """Service for discovering and filtering available LLM models."""

    def __init__(self, cache_timeout: int = 300):
        """Initialize with cache timeout in seconds."""
        self.cache_timeout = cache_timeout
        self._cached_models: Optional[list[LLMModel]] = None
        self._cache_timestamp = 0

        # Fallback models if discovery fails
        self.fallback_models = [
            LLMModel("gpt-4o", "OpenAI Chat", ["4o"], True, False, 1),
            LLMModel("gpt-4o-mini", "OpenAI Chat", ["4o-mini"], True, False, 2),
            LLMModel("gpt-4", "OpenAI Chat", ["4", "gpt4"], True, False, 3),
            LLMModel(
                "gpt-3.5-turbo", "OpenAI Chat", ["3.5", "chatgpt"], True, False, 4
            ),
        ]

        # Model prioritization rules
        self.priority_rules = {
            # Provider preferences (lower = higher priority)
            "OpenAI Chat": 10,
            "GeminiPro": 20,
            "OpenAI Completion": 30,
            # Model type preferences
            "chat_bonus": -5,  # Chat models are preferred
            "experimental_penalty": 50,  # Experimental models get lower priority
            # Specific model bonuses (applied to base priority)
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

        for model_key, bonus in sorted_model_bonuses:
            priority += bonus
            break  # Apply only the most specific bonus

        for model_key, bonus in sorted_model_bonuses:
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

        categories = {"recommended": [], "budget": [], "alternative": []}

        # Categorize models
        for model in all_models:
            # Budget models (fast and cost-effective)
            if any(
                keyword in model.name.lower()
                for keyword in ["mini", "3.5", "flash-8b", "nano"]
            ):
                categories["budget"].append(model)
            # Alternative providers (non-OpenAI)
            elif not model.provider.startswith("OpenAI"):
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


class OpenGraphExtractor:
    """Extract OpenGraph metadata from URLs."""

    def __init__(self, timeout: int = settings.OG_EXTRACTOR_TIMEOUT):
        """Initialize with request timeout."""
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
        )

    def extract(self, url: str) -> URLRecord:
        """Extract OpenGraph data from URL and return URLRecord."""
        record = URLRecord(url=url)

        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")

            # Extract OpenGraph properties
            record.title = self._get_meta_content(soup, "og:title") or self._get_title(
                soup
            )
            record.description = self._get_meta_content(
                soup, "og:description"
            ) or self._get_meta_content(soup, "description")
            record.image = self._get_meta_content(soup, "og:image")
            record.site_name = self._get_meta_content(soup, "og:site_name")
            record.og_type = self._get_meta_content(soup, "og:type")

            # Fallback to basic HTML if OpenGraph not available
            if not record.title:
                title_tag = soup.find("title")
                if title_tag:
                    record.title = title_tag.get_text().strip()

            if not record.description:
                desc_tag = soup.find("meta", attrs={"name": "description"})
                if desc_tag:
                    record.description = desc_tag.get("content", "").strip()

        except Exception as e:
            print(f"🔧 DEBUG: Failed to extract OpenGraph data from {url}: {e}")
            # Return basic record with just the URL

        return record

    def _get_meta_content(
        self, soup: BeautifulSoup, property_name: str
    ) -> Optional[str]:
        """Get content from meta tag by property or name."""
        # Try OpenGraph property first
        tag = soup.find("meta", property=property_name)
        if tag and tag.get("content"):
            return tag["content"].strip()

        # Try name attribute
        tag = soup.find("meta", attrs={"name": property_name})
        if tag and tag.get("content"):
            return tag["content"].strip()

        return None

    def _get_title(self, soup: BeautifulSoup) -> Optional[str]:
        """Get page title from title tag."""
        title_tag = soup.find("title")
        if title_tag:
            return title_tag.get_text().strip()
        return None


class LLMSummaryService:
    """Service for generating LLM summaries using fragments."""

    def __init__(self, config: Optional[SummaryConfig] = None):
        """Initialize with configuration."""
        self.config = config or SummaryConfig()

        # Fragment mappings from original CLI
        self.fragment_mappings = {
            "reddit.com": "llm-fragments-reddit",
            "news.ycombinator.com": "llm-hacker-news",
            "youtube.com": "llm-fragments-youtube",
            "youtu.be": "llm-fragments-youtube",
        }

        # URL patterns for robust extraction
        self.url_patterns = {
            "reddit": re.compile(
                r"^(https?://)?(www\.)?reddit\.com/(r/[^/]+/comments/|comments/)([a-zA-Z0-9_]+).*"
            ),
            "youtube": re.compile(
                r"^(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]+).*"
            ),
            "hacker_news": re.compile(
                r"^(https?://)?(www\.)?news\.ycombinator\.com/item\?id=([0-9]+).*"
            ),
        }

        # System prompts for different formats
        self.system_prompts = {
            "bullet": "Summarize this content concisely in 3-5 bullet points.",
            "paragraph": "Provide a concise paragraph summary of this content.",
            "detailed": "Provide a detailed summary including key points, context, and implications.",
        }

        # Validate llm installation
        if not self._check_llm_installed():
            raise RuntimeError(
                "'llm' library not found. Please install it with: uv add llm"
            )

    def _check_llm_installed(self) -> bool:
        """Check if the llm command is available."""
        try:
            result = subprocess.run(
                ["llm", "--version"], capture_output=True, text=True, timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def _log_debug(self, message: str) -> None:
        """Log debug messages if debug mode is enabled."""
        if settings.LLM_DEBUG_MODE:
            print(f"🔧 DEBUG: {message}")

    def extract_youtube_id(self, url: str) -> Optional[str]:
        """Extract YouTube video ID using multiple methods."""
        patterns = [
            r"(?:v=|\/)([0-9A-Za-z_-]{11}).*",
            r"(?:embed\/)([0-9A-Za-z_-]{11})",
            r"(?:youtu\.be\/)([0-9A-Za-z_-]{11})",
            r"youtube\.com/watch\?v=([^&]+)",
            r"youtube\.com/v/([^?]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                video_id = match.group(1)
                self._log_debug(f"Extracted YouTube ID: {video_id}")
                return video_id

        # Fallback using URL parsing
        try:
            parsed = urllib.parse.urlparse(url)
            if (
                parsed.netloc in ["www.youtube.com", "youtube.com"]
                and parsed.path == "/watch"
            ):
                query = urllib.parse.parse_qs(parsed.query)
                if "v" in query:
                    return query["v"][0]
            elif parsed.netloc == "youtu.be":
                if parsed.path.startswith("/"):
                    return parsed.path[1:]
        except Exception:
            pass

        return None

    def extract_reddit_id(self, url: str) -> Optional[str]:
        """Extract Reddit post ID using multiple methods."""
        match = self.url_patterns["reddit"].match(url)
        if match:
            post_id = match.group(4)
            self._log_debug(f"Extracted Reddit ID via regex: {post_id}")
            return post_id

        # URL path parsing fallback
        try:
            parsed = urllib.parse.urlparse(url)
            path_parts = parsed.path.split("/")
            if (
                len(path_parts) >= 5
                and path_parts[1] == "r"
                and path_parts[3] == "comments"
            ):
                post_id = path_parts[4]
                self._log_debug(f"Extracted Reddit ID via path parsing: {post_id}")
                return post_id
        except Exception:
            pass

        return None

    def extract_hn_id(self, url: str) -> Optional[str]:
        """Extract Hacker News item ID using multiple methods."""
        match = self.url_patterns["hacker_news"].match(url)
        if match:
            item_id = match.group(3)
            self._log_debug(f"Extracted HN ID via regex: {item_id}")
            return item_id

        # URL query parsing fallback
        try:
            parsed = urllib.parse.urlparse(url)
            query = urllib.parse.parse_qs(parsed.query)
            if "id" in query:
                item_id = query["id"][0]
                self._log_debug(f"Extracted HN ID via query parsing: {item_id}")
                return item_id
        except Exception:
            pass

        return None

    def detect_url_type(self, url: str) -> Optional[tuple[str, str]]:
        """
        Detect URL type and return fragment name and identifier.
        Returns tuple of (fragment_name, fragment_identifier) or None.
        """
        try:
            parsed = urllib.parse.urlparse(url)
            domain = parsed.netloc.lower()

            # Remove www. prefix if present
            if domain.startswith("www."):
                domain = domain[4:]

            self._log_debug(f"Analyzing domain: {domain}")

            # Check direct matches and extract appropriate IDs
            if domain in ["reddit.com"] or domain.endswith(".reddit.com"):
                post_id = self.extract_reddit_id(url)
                if post_id:
                    return (self.fragment_mappings["reddit.com"], f"reddit:{post_id}")
                else:
                    return (self.fragment_mappings["reddit.com"], f"reddit:{url}")

            elif domain in ["youtube.com"] or domain.endswith(".youtube.com"):
                video_id = self.extract_youtube_id(url)
                if video_id:
                    return (
                        self.fragment_mappings["youtube.com"],
                        f"youtube:{video_id}",
                    )

            elif domain == "youtu.be":
                video_id = self.extract_youtube_id(url)
                if video_id:
                    return (self.fragment_mappings["youtu.be"], f"youtube:{video_id}")

            elif domain == "news.ycombinator.com":
                item_id = self.extract_hn_id(url)
                if item_id:
                    return (
                        self.fragment_mappings["news.ycombinator.com"],
                        f"hn:{item_id}",
                    )
                else:
                    return (self.fragment_mappings["news.ycombinator.com"], f"hn:{url}")

            return None

        except Exception as e:
            self._log_debug(f"Error parsing URL: {e}")
            return None

    def get_system_prompt(self) -> str:
        """Get the appropriate system prompt based on configuration."""
        if self.config.system_prompt:
            return self.config.system_prompt
        return self.system_prompts.get(
            self.config.format, self.system_prompts["bullet"]
        )

    def generate_summary(
        self, url: str
    ) -> tuple[bool, Optional[SummaryRecord], Optional[str]]:
        """
        Generate summary for URL.
        Returns tuple of (success, summary_record, error_message)
        """
        self._log_debug(f"Analyzing URL: {url}")

        # Detect URL type and get fragment info
        fragment_info = self.detect_url_type(url)

        if not fragment_info:
            supported_sites = list(self.fragment_mappings.keys())
            error_msg = f"No matching fragment found. Supported sites: {', '.join(supported_sites)}"
            return False, None, error_msg

        fragment_name, fragment_identifier = fragment_info
        self._log_debug(f"Using fragment: {fragment_name}")

        try:
            # Build command
            cmd = [
                "llm",
                "-m",
                self.config.model,
                "-f",
                fragment_identifier,
                "--system",
                self.get_system_prompt(),
            ]

            self._log_debug(f"Running command: {' '.join(cmd)}")

            # Execute with timeout
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.timeout,
                encoding="utf-8",
            )

            if result.returncode == 0:
                summary_record = SummaryRecord(
                    url_id=0,  # Will be set by caller
                    content=result.stdout.strip(),
                    model_used=self.config.model,
                    format_type=self.config.format,
                    fragment_used=fragment_name,
                )
                return True, summary_record, None
            else:
                error_msg = f"LLM command failed: {result.stderr}"
                return False, None, error_msg

        except subprocess.TimeoutExpired:
            error_msg = f"Request timed out after {self.config.timeout} seconds"
            return False, None, error_msg
        except FileNotFoundError:
            error_msg = "'llm' command not found. Install with: uv add llm"
            return False, None, error_msg
        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            return False, None, error_msg


class URLProcessor:
    """High-level service that combines OpenGraph extraction and LLM summarization."""

    def __init__(self, summary_config: Optional[SummaryConfig] = None):
        """Initialize with services."""
        self.og_extractor = OpenGraphExtractor()
        self.summary_service = LLMSummaryService(summary_config)

    def process_url(
        self, url: str
    ) -> tuple[URLRecord, Optional[SummaryRecord], Optional[str]]:
        """
        Process URL to extract OpenGraph data and generate summary.
        Returns tuple of (url_record, summary_record, error_message)
        """
        # Extract OpenGraph data
        url_record = self.og_extractor.extract(url)

        # Generate summary
        success, summary_record, error_msg = self.summary_service.generate_summary(url)

        return url_record, summary_record, error_msg
