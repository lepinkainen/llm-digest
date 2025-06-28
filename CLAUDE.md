# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python application that provides both CLI and web interfaces for URL summarization using the `llm` library with LLM fragments. It extracts OpenGraph metadata and generates AI summaries for supported websites (Reddit, Hacker News, YouTube). Data is stored in SQLite with FTS5 full-text search and can be analyzed using Datasette.

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

#### CLI Tool
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

#### Web Application
```bash
# Start the web server
python web_app.py

# With custom options
python web_app.py --host 0.0.0.0 --port 8080 --reload

# Access at http://localhost:8000
```

#### Data Analysis
```bash
# Generate Datasette configuration
python datasette_config.py

# Start Datasette for data analysis
./start_datasette.sh

# Access at http://localhost:8001
```

## Architecture

### Core Components

#### CLI Tool (`claude-llm.py`)
- **URLSummarizer class**: Original CLI logic with URL detection, fragment mapping, and LLM interaction
- **SummaryConfig dataclass**: Configuration management for models, formats, timeouts, and debug settings

#### Web Application (`web_app.py`)
- **FastAPI application**: Web interface with form submission and results display
- **URL processor service**: Combines OpenGraph extraction with LLM summarization
- **Database integration**: SQLite storage with FTS5 full-text search

#### Services (`services.py`)
- **OpenGraphExtractor**: Extracts metadata from web pages using BeautifulSoup
- **LLMSummaryService**: Refactored summarization logic using LLM fragments
- **URLProcessor**: High-level service combining extraction and summarization

#### Database (`database.py`)
- **DatabaseManager**: SQLite operations with FTS5 search capabilities
- **URLRecord/SummaryRecord**: Data models for URL metadata and summaries
- **FTS5 integration**: Full-text search on URLs and summary content

#### Fragment Mappings
- `reddit.com` → `llm-fragments-reddit`
- `news.ycombinator.com` → `llm-hacker-news`
- `youtube.com`/`youtu.be` → `llm-fragments-youtube`

### Processing Pipeline

1. **Web Form Submission**: User submits URL via web interface
2. **OpenGraph Extraction**: Fetch page metadata (title, description, image, site info)
3. **URL Validation**: Check format and detect supported site type
4. **Fragment Selection**: Choose appropriate LLM fragment based on domain
5. **LLM Summarization**: Generate summary using selected fragment and model
6. **Database Storage**: Save URL metadata and summary with FTS5 indexing
7. **Results Display**: Show combined OpenGraph data and summary

### Dependencies

- **Core**: `llm`, `fastapi`, `uvicorn`, `beautifulsoup4`, `requests`, `datasette`
- **LLM Fragments**: `llm-fragments-reddit`, `llm-hacker-news`, `llm-fragments-youtube`
- **Dev**: `black`, `ruff`, `mypy`, `pytest`, `pre-commit`
- **Python**: Requires Python 3.12+

## Configuration

The application uses `pyproject.toml` for comprehensive configuration including:

- Build system with `hatchling`
- Web and CLI dependencies management
- Black, Ruff, and MyPy settings
- Pytest configuration with coverage
- Multiple entry point scripts: `url-summarizer`, `summarize-url`, `llm-summarizer`, `esum`, `llm-digest-web`

## External Dependencies

The application requires:
- `llm` CLI tool installed and configured with API keys for the chosen model provider (OpenAI, etc.)
- LLM fragment packages for supported sites
- For web deployment: FastAPI and Uvicorn
- For data analysis: Datasette with the generated database

## Data Storage

- **SQLite Database**: `llm_digest.db` with FTS5 full-text search
- **Tables**: `urls` (OpenGraph data), `summaries` (LLM output), FTS5 virtual tables
- **Datasette Integration**: Web-based database exploration and analysis

## Memories

- Read @llm-shared/project_tech_stack.md for information about technology choices in the project
