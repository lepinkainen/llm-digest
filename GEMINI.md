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
  - `beautifulsoup4`, `requests`: For web scraping.
- **Linting & Formatting:**
  - `black`: Code formatting.
  - `ruff`: Linting.
- **Testing:**
  - `pytest`: Testing framework.

## Key Files

- `claude_llm.py`: Main entry point for the command-line tool.
- `web_app.py`: The FastAPI web application.
- `database.py`: Likely handles database interactions.
- `services.py`: Contains business logic.
- `pyproject.toml`: Defines project metadata and dependencies.
- `README.md`: Detailed project documentation.
- `start_datasette.sh`: a shell script that starts the datasette server

## How to Run

### Command-Line Tool

To run the URL summarizer:

```bash
uv sync
url-summarizer
```

### Web Application

To run the web application:

```bash
uv sync
uvicorn web_app:app --reload
```

### Datasette

To start the Datasette server:

```bash
./start_datasette.sh
```
