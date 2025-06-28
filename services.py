#!/usr/bin/env python3
"""
Core services for LLM Digest web application.
Extracted and refactored from the original CLI URLSummarizer.
"""

import re
import subprocess
import sys
import urllib.parse
from dataclasses import dataclass
from typing import Optional, Tuple
import requests
from bs4 import BeautifulSoup

from database import URLRecord, SummaryRecord


@dataclass
class SummaryConfig:
    """Configuration for summary generation."""
    model: str = "gpt-4"
    format: str = "bullet"  # bullet, paragraph, detailed
    timeout: int = 120
    system_prompt: Optional[str] = None
    debug: bool = False


class OpenGraphExtractor:
    """Extract OpenGraph metadata from URLs."""
    
    def __init__(self, timeout: int = 30):
        """Initialize with request timeout."""
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def extract(self, url: str) -> URLRecord:
        """Extract OpenGraph data from URL and return URLRecord."""
        record = URLRecord(url=url)
        
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract OpenGraph properties
            record.title = self._get_meta_content(soup, 'og:title') or self._get_title(soup)
            record.description = self._get_meta_content(soup, 'og:description') or self._get_meta_content(soup, 'description')
            record.image = self._get_meta_content(soup, 'og:image')
            record.site_name = self._get_meta_content(soup, 'og:site_name')
            record.og_type = self._get_meta_content(soup, 'og:type')
            
            # Fallback to basic HTML if OpenGraph not available
            if not record.title:
                title_tag = soup.find('title')
                if title_tag:
                    record.title = title_tag.get_text().strip()
            
            if not record.description:
                desc_tag = soup.find('meta', attrs={'name': 'description'})
                if desc_tag:
                    record.description = desc_tag.get('content', '').strip()
                    
        except Exception as e:
            print(f"🔧 DEBUG: Failed to extract OpenGraph data from {url}: {e}")
            # Return basic record with just the URL
            
        return record
    
    def _get_meta_content(self, soup: BeautifulSoup, property_name: str) -> Optional[str]:
        """Get content from meta tag by property or name."""
        # Try OpenGraph property first
        tag = soup.find('meta', property=property_name)
        if tag and tag.get('content'):
            return tag['content'].strip()
        
        # Try name attribute
        tag = soup.find('meta', attrs={'name': property_name})
        if tag and tag.get('content'):
            return tag['content'].strip()
            
        return None
    
    def _get_title(self, soup: BeautifulSoup) -> Optional[str]:
        """Get page title from title tag."""
        title_tag = soup.find('title')
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
            raise RuntimeError("'llm' library not found. Please install it with: uv add llm")
    
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
        except:
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
        except:
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
        except:
            pass
        
        return None
    
    def detect_url_type(self, url: str) -> Optional[Tuple[str, str]]:
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
    
    def generate_summary(self, url: str) -> Tuple[bool, Optional[SummaryRecord], Optional[str]]:
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
                    fragment_used=fragment_name
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
    
    def process_url(self, url: str) -> Tuple[URLRecord, Optional[SummaryRecord], Optional[str]]:
        """
        Process URL to extract OpenGraph data and generate summary.
        Returns tuple of (url_record, summary_record, error_message)
        """
        # Extract OpenGraph data
        url_record = self.og_extractor.extract(url)
        
        # Generate summary
        success, summary_record, error_msg = self.summary_service.generate_summary(url)
        
        return url_record, summary_record, error_msg