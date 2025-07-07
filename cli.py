#!/usr/bin/env python3
"""
Command-line interface for URL Summarizer CLI Tool.
Handles argument parsing and main entry point.
"""

import argparse
import sys

from models import SummaryConfig
from url_summarizer import URLSummarizer
from utils import validate_url

__version__ = "1.0.0"


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
        choices=[
            "bullet",
            "paragraph",
            "detailed",
            "key-points",
            "discussion",
            "technical",
        ],
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
        if validate_url(args.url):
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