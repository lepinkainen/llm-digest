#!/usr/bin/env python3
"""
Enhanced URL Summarizer CLI Tool
A comprehensive command-line utility that summarizes URLs using appropriate LLM fragments.

This tool combines the best features from multiple implementations:
- Comprehensive error handling and validation
- Interactive and single-command modes
- Robust URL parsing with multiple extraction methods
- Configurable output formats and models
- Professional logging and progress indicators
"""

__version__ = "1.0.0"

import argparse
import re
import subprocess
import sys
import urllib.parse
from dataclasses import dataclass
from typing import Optional

# Import model discovery if available (for validation)
try:
    from services import LLMModelDiscovery

    MODEL_DISCOVERY_AVAILABLE = True
except ImportError:
    MODEL_DISCOVERY_AVAILABLE = False


@dataclass
class SummaryConfig:
    """Configuration for summary generation."""

    model: str = "gpt-4"
    format: str = "bullet"  # bullet, paragraph, detailed
    timeout: int = 120
    system_prompt: Optional[str] = None
    debug: bool = False


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
            "bullet": "Summarize this content concisely in 3-5 bullet points.",
            "paragraph": "Provide a concise paragraph summary of this content.",
            "detailed": "Provide a detailed summary including key points, context, and implications.",
        }

        # Validate llm installation
        if not self._check_llm_installed():
            print(
                "❌ Error: 'llm' library not found. Please install it with: uv add llm"
            )
            sys.exit(1)

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
        if self.config.debug:
            print(f"🔧 DEBUG: {message}")

    def validate_url(self, url: str) -> bool:
        """Validate if the provided string is a valid URL."""
        try:
            result = urllib.parse.urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False

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

    def get_system_prompt(self) -> str:
        """Get the appropriate system prompt based on configuration."""
        if self.config.system_prompt:
            return self.config.system_prompt
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

        try:
            # Build command with comprehensive options
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
        print("🔗 Enhanced URL Summarizer v" + __version__)
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

                    if not self.validate_url(url):
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


def create_config_from_args(args: argparse.Namespace) -> SummaryConfig:
    """Create configuration from command line arguments."""
    return SummaryConfig(
        model=args.model,
        format=args.format,
        timeout=args.timeout,
        system_prompt=args.system_prompt,
        debug=args.debug,
    )


def main() -> None:
    """Main entry point with comprehensive argument parsing."""
    parser = argparse.ArgumentParser(
        description="Enhanced URL Summarizer using LLM fragments",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                           # Interactive mode
  %(prog)s "https://reddit.com/r/python/..."        # Single URL
  %(prog)s --model gpt-3.5-turbo --format paragraph "https://news.ycombinator.com/item?id=123"
  %(prog)s --debug --timeout 180 "https://youtube.com/watch?v=abc"
        """,
    )

    parser.add_argument(
        "url",
        nargs="?",
        help="URL to summarize (if not provided, runs in interactive mode)",
    )
    parser.add_argument(
        "--model", "-m", default="gpt-4", help="LLM model to use (default: gpt-4)"
    )
    parser.add_argument(
        "--format",
        "-f",
        choices=["bullet", "paragraph", "detailed"],
        default="bullet",
        help="Output format (default: bullet)",
    )
    parser.add_argument(
        "--timeout",
        "-t",
        type=int,
        default=120,
        help="Timeout in seconds (default: 120)",
    )
    parser.add_argument(
        "--system-prompt", "-s", help="Custom system prompt (overrides format setting)"
    )
    parser.add_argument(
        "--debug", "-d", action="store_true", help="Enable debug output"
    )
    parser.add_argument(
        "--version", "-v", action="version", version=f"%(prog)s {__version__}"
    )

    args = parser.parse_args()
    config = create_config_from_args(args)
    summarizer = URLSummarizer(config)

    # Validate model before proceeding
    is_valid, suggestion_msg = summarizer.validate_model(config.model)
    if not is_valid and suggestion_msg:
        print(f"⚠️  {suggestion_msg}")
        print("   💡 Continuing anyway, but this may fail during execution.")
        print()

    if args.url:
        # Single URL mode
        if summarizer.validate_url(args.url):
            success = summarizer.summarize_url(args.url)
            sys.exit(0 if success else 1)
        else:
            print("❌ Invalid URL provided")
            sys.exit(1)
    else:
        # Interactive mode
        summarizer.run_interactive()


if __name__ == "__main__":
    main()
