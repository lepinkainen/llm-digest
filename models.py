#!/usr/bin/env python3
"""
Data models and configuration classes for LLM Digest.
Shared data structures used across the application.
"""

from dataclasses import dataclass
from typing import Optional

from config import settings


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