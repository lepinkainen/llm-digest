#!/usr/bin/env python3
"""
Web content extractors for LLM Digest.
Extract metadata and content from web pages.
"""

from typing import Optional

import requests
from bs4 import BeautifulSoup

from config import settings
from database import URLRecord


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
                if desc_tag and hasattr(desc_tag, "get") and desc_tag.name:
                    content = desc_tag.get("content")
                    if content:
                        record.description = str(content).strip()

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
        if tag and hasattr(tag, "get") and tag.name:
            content = tag.get("content")
            if content:
                return str(content).strip()

        # Try name attribute
        tag = soup.find("meta", attrs={"name": property_name})
        if tag and hasattr(tag, "get") and tag.name:
            content = tag.get("content")
            if content:
                return str(content).strip()

        return None

    def _get_title(self, soup: BeautifulSoup) -> Optional[str]:
        """Get page title from title tag."""
        title_tag = soup.find("title")
        if title_tag and hasattr(title_tag, "get_text"):
            return str(title_tag.get_text()).strip()
        return None