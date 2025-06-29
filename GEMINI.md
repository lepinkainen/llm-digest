# GEMINI.md

## Project Overview

This project is an enhanced URL summarizer. It's a command-line tool that takes a URL and uses a Large Language Model (LLM) to generate a summary of the content. It supports various URL types like Reddit, Hacker News, and YouTube, and can output summaries in different formats (bullet points, paragraph, detailed). The project also includes a web application component using FastAPI.

## Tech Stack

- **Language:** Python 3.12+
- **Package Manager:** uv
- **Core Libraries:**
  - `llm`: The core library for interacting with Large Language Models.
  - `llm-fragments-reddit`, `llm-hacker-news`, `llm-fragments-youtube`: Plugins for handling specific sites.
  - `fastapi`: For the web application.
  - `uvicorn`: ASGI server for FastAPI.
  - `datasette`: For data analysis and exploration.
  - `pydantic-settings`: For centralized configuration management.
  - `beautifulsoup4`, `requests`: For web scraping.
- **Linting & Formatting:**
  - `ruff`: Linting and formatting.
- **Type Checking:**
  - `mypy`: Static type checking.
- **Testing:**
  - `pytest`: Testing framework.

## Key Files

- `claude-llm.py`: A standalone script for URL summarization using LLM services.
- `web_app.py`: The FastAPI web application.
- `database.py`: Handles SQLite database interactions and FTS5.
- `services.py`: Contains core business logic for LLM model discovery, OpenGraph extraction, and LLM summarization.
- `config.py`: Centralized application configuration using `pydantic-settings`.
- `pyproject.toml`: Defines project metadata, dependencies, and tool configurations.
- `README.md`: Detailed project documentation.
- `start_datasette.sh`: A shell script to start the Datasette server separately.
- `Taskfile.yml`: Defines project tasks for building, testing, and linting.
- `tests/`: Directory containing all unit and integration tests.
- `llm-shared/`: Git submodule for shared resources and guidelines.

## How to Run

### Command-Line Tool

To run the URL summarizer (using the `llm` command with the `summarize` plugin):

```bash
uv sync
llm summarize <URL> -m <model> -f <format>
# Example:
# llm summarize https://www.youtube.com/watch?v=dQw4w9WgXcQ -m gpt-4o-mini -f bullet
```

To run the `claude-llm.py` script directly:

```bash
uv run python claude-llm.py <URL> --model <model> --format <format>
# Example:
# uv run python claude-llm.py https://www.youtube.com/watch?v=dQw4w9WgXcQ --model gpt-4o-mini --format bullet
```

### Web Application

To run the web application:

```bash
uv run python web_app.py
```

### Datasette

To start the Datasette server (run in a separate terminal):

```bash
./start_datasette.sh
```

### Running Tests and Linting

Use the `Taskfile.yml` for common development tasks:

```bash
task test
task lint
```