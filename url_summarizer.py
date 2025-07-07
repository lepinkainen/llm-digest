#!/usr/bin/env python3
"""
URL Summarizer CLI Tool
A comprehensive command-line utility that summarizes URLs using appropriate LLM fragments.

This tool combines the best features from multiple implementations:
- Comprehensive error handling and validation
- Interactive and single-command modes
- Robust URL parsing with multiple extraction methods
- Configurable output formats and models
- Professional logging and progress indicators
"""

import re
import subprocess
import sys
import urllib.parse
from typing import Optional

from llm_discovery import LLMModelDiscovery
from models import SummaryConfig
from utils import check_llm_installed, log_debug, validate_url

# Import model discovery if available (for validation)
try:
    MODEL_DISCOVERY_AVAILABLE = True
except ImportError:
    MODEL_DISCOVERY_AVAILABLE = False


class URLSummarizer:
    """Enhanced URL summarizer with comprehensive feature set."""

    def __init__(self, config: Optional[SummaryConfig] = None):
        """Initialize the URL summarizer with configuration."""
        self.config = config or SummaryConfig()

        # Initialize model discovery if available
        self.model_discovery = None
        if MODEL_DISCOVERY_AVAILABLE:
            try:
                self.model_discovery = LLMModelDiscovery()
            except Exception:
                pass

        # Combined fragment mappings from all implementations
        self.fragment_mappings = {
            "reddit.com": "llm-fragments-reddit",
            "news.ycombinator.com": "llm-hacker-news",
            "youtube.com": "llm-fragments-youtube",
            "youtu.be": "llm-fragments-youtube",
        }

        # URL patterns for robust extraction (from Gemini implementation)
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
            "bullet": "Summarize this content in clear, comprehensive bullet points. Focus on the most important information, key arguments, and actionable insights. Include as many points as necessary to capture the essential content - don't limit yourself to a specific number.",
            "paragraph": "Provide a comprehensive paragraph summary that covers the main points, context, and significance of this content. Include relevant details that would help someone understand the full scope and implications of the information presented.",
            "detailed": "Provide an in-depth analysis and summary including: key points and arguments, relevant context and background, implications and significance, notable discussions or perspectives, and any actionable insights or takeaways. Structure your response to be thorough and informative.",
            "key-points": "Extract and present the most critical information as key points, focusing on facts, conclusions, and important details that someone would need to know. Prioritize accuracy and completeness over brevity.",
            "discussion": "Summarize the main discussion points, different perspectives presented, notable arguments or debates, and the overall sentiment or consensus if applicable. Include context about why this topic is significant.",
            "technical": "Provide a technical summary focusing on: specific details, methodologies, technical concepts, implementation details, and practical implications. Include relevant technical context and any limitations or considerations mentioned.",
        }

        # Platform-specific prompt enhancements
        self.platform_prompts = {
            "reddit": {
                "bullet": "Summarize this Reddit post and discussion in comprehensive bullet points. Include: the main post content, top discussion points from comments, different perspectives or arguments presented, community sentiment, and any notable insights or conclusions. Capture the full scope of the discussion.",
                "paragraph": "Provide a comprehensive summary of this Reddit post and its discussion. Include the main post content, key discussion points from comments, different viewpoints presented, community reaction, and the overall significance or conclusions drawn from the conversation.",
                "detailed": "Provide an in-depth analysis of this Reddit post and discussion including: the original post content and context, major discussion themes and arguments, different perspectives and viewpoints, community sentiment and reactions, notable insights or expert opinions, and any actionable takeaways or conclusions.",
                "discussion": "Focus on the Reddit discussion dynamics: main arguments and counterarguments, different user perspectives, community consensus or disagreements, notable expert contributions, and the overall direction and quality of the conversation.",
            },
            "hackernews": {
                "bullet": "Summarize this Hacker News post and discussion in comprehensive bullet points. Include: the main article/post content, key technical discussions, business implications, community insights, expert opinions, and practical takeaways. Focus on the technical and professional aspects.",
                "paragraph": "Provide a comprehensive summary of this Hacker News post and discussion. Include the main content, key technical points discussed, business or industry implications, notable expert opinions, and practical insights that would be valuable to developers or professionals.",
                "detailed": "Provide an in-depth analysis of this Hacker News post and discussion including: the original content and context, technical details and implications, business or industry significance, expert opinions and insights, practical applications or takeaways, and any concerns or limitations discussed.",
                "technical": "Focus on the technical aspects: specific technologies, methodologies, implementation details, performance considerations, technical challenges or solutions discussed, and practical implications for developers or engineers.",
            },
            "youtube": {
                "bullet": "Summarize this YouTube video content in comprehensive bullet points. Include: main topics covered, key information presented, important insights or conclusions, practical advice or takeaways, and any notable demonstrations or examples. Capture the full educational or entertainment value.",
                "paragraph": "Provide a comprehensive summary of this YouTube video content. Include the main topics discussed, key information and insights presented, practical advice or demonstrations, and the overall value or significance of the content for viewers.",
                "detailed": "Provide an in-depth analysis of this YouTube video including: main topics and themes, detailed content breakdown, key insights and conclusions, practical advice or tutorials, demonstrations or examples shown, and the overall educational or entertainment value.",
                "technical": "Focus on any technical content: specific concepts explained, methodologies demonstrated, technical details provided, practical implementations shown, and technical insights or advice given.",
            },
        }

        # Validate llm installation
        if not check_llm_installed():
            print(
                "❌ Error: 'llm' library not found. Please install it with: uv add llm"
            )
            sys.exit(1)

    def _log_debug(self, message: str) -> None:
        """Log debug messages if debug mode is enabled."""
        log_debug(message, self.config.debug)

    def validate_model(self, model_name: str) -> tuple[bool, Optional[str]]:
        """
        Validate if a model is available and provide suggestions if not.
        Returns (is_valid, suggestion_message).
        """
        if not self.model_discovery:
            # If model discovery is not available, assume model is valid
            return True, None

        try:
            return self.model_discovery.validate_model(model_name)
        except Exception:
            # If validation fails, assume model is valid to avoid blocking
            return True, None

    def extract_youtube_id(self, url: str) -> Optional[str]:
        """Extract YouTube video ID using multiple methods."""
        # Primary patterns (from multiple implementations)
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

        # Fallback using URL parsing (from Grok implementation)
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
        # Method 1: Regex pattern matching
        match = self.url_patterns["reddit"].match(url)
        if match:
            post_id = match.group(4)
            self._log_debug(f"Extracted Reddit ID via regex: {post_id}")
            return post_id

        # Method 2: URL path parsing (from Grok implementation)
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
        # Method 1: Regex pattern matching
        match = self.url_patterns["hacker_news"].match(url)
        if match:
            item_id = match.group(3)
            self._log_debug(f"Extracted HN ID via regex: {item_id}")
            return item_id

        # Method 2: URL query parsing (from Grok implementation)
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
                    # Fallback to full URL (from Gemini implementation)
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
                    # Try with full URL as fallback
                    return (self.fragment_mappings["news.ycombinator.com"], f"hn:{url}")

            return None

        except Exception as e:
            self._log_debug(f"Error parsing URL: {e}")
            return None

    def get_system_prompt(self, platform: Optional[str] = None) -> str:
        """Get the appropriate system prompt based on configuration and platform."""
        if self.config.system_prompt:
            return self.config.system_prompt

        # Use platform-specific prompts if available
        if platform and platform in self.platform_prompts:
            platform_prompts = self.platform_prompts[platform]
            if self.config.format in platform_prompts:
                return platform_prompts[self.config.format]

        # Fallback to general prompts
        return self.system_prompts.get(
            self.config.format, self.system_prompts["bullet"]
        )

    def summarize_url(self, url: str) -> bool:
        """
        Summarize the given URL using the appropriate fragment.
        Returns True if successful, False otherwise.
        """
        print(f"🔍 Analyzing URL: {url}")

        # Detect URL type and get fragment info
        fragment_info = self.detect_url_type(url)

        if not fragment_info:
            supported_sites = list(self.fragment_mappings.keys())
            print("❌ No matching fragment found for this URL.")
            print(f"💡 Supported sites: {', '.join(supported_sites)}")
            return False

        fragment_name, fragment_identifier = fragment_info
        print(f"📦 Using fragment: {fragment_name}")
        print(f"🔄 Processing URL with format: {self.config.format}")

        # Determine platform for prompt selection
        platform = None
        if "reddit" in fragment_name:
            platform = "reddit"
        elif "hacker-news" in fragment_name:
            platform = "hackernews"
        elif "youtube" in fragment_name:
            platform = "youtube"

        try:
            # Build command with comprehensive options
            cmd = [
                "llm",
                "-m",
                self.config.model,
                "-f",
                fragment_identifier,
                "--system",
                self.get_system_prompt(platform),
            ]

            self._log_debug(f"Running command: {' '.join(cmd)}")

            # Execute with timeout and comprehensive error handling
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.timeout,
                encoding="utf-8",  # Ensure proper encoding
            )

            if result.returncode == 0:
                print("\n" + "=" * 60)
                print("📄 SUMMARY")
                print("=" * 60)
                print(result.stdout.strip())
                print("=" * 60)
                return True
            else:
                print("❌ Error processing URL:")
                print(f"🔧 Command: {' '.join(cmd)}")
                print(f"📜 Error output: {result.stderr}")
                print("\n💡 Possible solutions:")
                print(f"   1. Install the fragment: uv add {fragment_name}")
                print("   2. Configure LLM model: llm keys set openai")
                print("   3. Verify URL format is supported")
                print("   4. Try a different model with: --model gpt-3.5-turbo")
                return False

        except subprocess.TimeoutExpired:
            print(f"❌ Request timed out after {self.config.timeout} seconds.")
            print("💡 Try increasing timeout with --timeout option.")
            return False
        except FileNotFoundError:
            print("❌ Error: 'llm' command not found.")
            print("💡 Install with: uv add llm")
            return False
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return False

    def run_interactive(self) -> None:
        """Run the interactive command-line interface."""
        print("🔗 Enhanced URL Summarizer")
        print("=" * 50)
        print("Supported sites:")
        for domain, fragment in self.fragment_mappings.items():
            print(f"  • {domain} ({fragment})")
        print("\nConfiguration:")
        print(f"  • Model: {self.config.model}")
        print(f"  • Format: {self.config.format}")
        print(f"  • Timeout: {self.config.timeout}s")
        print("\nEnter URLs to summarize (Ctrl+C to exit)")
        print("-" * 50)

        try:
            while True:
                try:
                    url = input("\n🌐 Enter URL: ").strip()

                    if not url:
                        continue

                    if url.lower() in ("quit", "exit", "q"):
                        break

                    if not validate_url(url):
                        print(
                            "❌ Invalid URL format. Please include http:// or https://"
                        )
                        continue

                    success = self.summarize_url(url)

                    if success:
                        print("\n✅ Summary completed!")
                    else:
                        print("\n❌ Summary failed!")

                except KeyboardInterrupt:
                    print("\n👋 Goodbye!")
                    break
                except EOFError:
                    print("\n👋 Goodbye!")
                    break

        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            sys.exit(0)