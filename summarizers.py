#!/usr/bin/env python3
"""
LLM summarization services for LLM Digest.
Service for generating LLM summaries using fragments.
"""

import re
import subprocess
import urllib.parse
from typing import Optional

from config import settings
from database import SummaryRecord
from models import SummaryConfig


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