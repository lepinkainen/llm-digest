# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python CLI tool called "Enhanced URL Summarizer" that uses the `llm` library with LLM fragments to summarize content from supported websites (Reddit, Hacker News, YouTube). The tool is a single-file Python application with comprehensive configuration and error handling.

## Development Commands

### Package Management (uv)

```bash
# Install dependencies
uv sync

# Install with development dependencies
uv sync --group dev

# Add new dependencies
uv add <package>

# Install the tool locally
uv tool install .
```

### Code Quality & Testing

```bash
# Format code
black claude-llm.py

# Lint code
ruff check claude-llm.py

# Type checking
mypy claude-llm.py

# Run tests (if tests directory exists)
pytest

# Run tests with coverage
pytest --cov=enhanced_url_summarizer --cov-report=html
```

### Running the Application

```bash
# Interactive mode
python claude-llm.py

# Single URL mode
python claude-llm.py "https://reddit.com/r/python/comments/abc123/example"

# With options
python claude-llm.py --model gpt-3.5-turbo --format paragraph "https://news.ycombinator.com/item?id=123"

# Debug mode
python claude-llm.py --debug "https://youtube.com/watch?v=abc123"
```

## Architecture

### Core Components

- **URLSummarizer class**: Main application logic with URL detection, fragment mapping, and LLM interaction
- **SummaryConfig dataclass**: Configuration management for models, formats, timeouts, and debug settings
- **Fragment mappings**: Maps domains to appropriate LLM fragment packages:
  - `reddit.com` → `llm-fragments-reddit`
  - `news.ycombinator.com` → `llm-hacker-news`
  - `youtube.com`/`youtu.be` → `llm-fragments-youtube`

### URL Processing Pipeline

1. URL validation using `urllib.parse`
2. Domain detection and fragment selection
3. ID extraction using regex patterns and URL parsing fallbacks
4. LLM fragment execution via subprocess calls to `llm` CLI
5. Error handling with user-friendly messages and troubleshooting guidance

### Dependencies

- **Core**: `llm` library and site-specific fragment packages
- **Dev**: `black`, `ruff`, `mypy`, `pytest`, `pre-commit`
- **Python**: Requires Python 3.12+

## Configuration

The tool uses `pyproject.toml` for comprehensive configuration including:

- Build system with `hatchling`
- Black, Ruff, and MyPy settings
- Pytest configuration with coverage
- Multiple entry point scripts: `url-summarizer`, `summarize-url`, `llm-summarizer`, `esum`

## External Dependencies

The application requires the `llm` CLI tool to be installed and configured with API keys for the chosen model provider (OpenAI, etc.).

## Memories

- Read @llm-shared/project_tech_stack.md for information about technology choices in the project
