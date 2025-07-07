#!/usr/bin/env python3
"""
High-level URL processing services for LLM Digest.
Orchestrates OpenGraph extraction and LLM summarization.
"""

from typing import Optional

from database import SummaryRecord, URLRecord
from extractors import OpenGraphExtractor
from models import SummaryConfig
from summarizers import LLMSummaryService


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
        _, summary_record, error_msg = self.summary_service.generate_summary(url)

        return url_record, summary_record, error_msg