#!/usr/bin/env python3
"""
Shared utility functions for LLM Digest.
Common helpers used across the application.
"""

import subprocess
import urllib.parse
from typing import Optional

from config import settings


def validate_url(url: str) -> bool:
    """Validate if the provided string is a valid URL."""
    try:
        result = urllib.parse.urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def check_llm_installed() -> bool:
    """Check if the llm command is available."""
    try:
        result = subprocess.run(
            ["llm", "--version"], capture_output=True, text=True, timeout=5
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def log_debug(message: str, debug_mode: Optional[bool] = None) -> None:
    """Log debug messages if debug mode is enabled."""
    if debug_mode is None:
        debug_mode = settings.LLM_DEBUG_MODE
    
    if debug_mode:
        print(f"🔧 DEBUG: {message}")


def format_error_message(error: str, suggestions: Optional[list[str]] = None) -> str:
    """Format error message with optional suggestions."""
    message = f"❌ {error}"
    
    if suggestions:
        message += "\n💡 Suggestions:"
        for suggestion in suggestions:
            message += f"\n   • {suggestion}"
    
    return message