#!/usr/bin/env python3
"""
FastAPI web application for LLM Digest.
Provides web interface for URL submission, OpenGraph extraction, and LLM summarization.
"""

import urllib.parse
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from database import DatabaseManager
from services import SummaryConfig, URLProcessor

# Initialize FastAPI app
app = FastAPI(
    title="LLM Digest",
    description="Web interface for URL summarization using LLM fragments",
    version="1.0.0"
)

# Initialize services
db = DatabaseManager()
url_processor = URLProcessor()

# Setup templates and static files
templates_dir = Path("templates")
static_dir = Path("static")

# Create directories if they don't exist
templates_dir.mkdir(exist_ok=True)
static_dir.mkdir(exist_ok=True)

templates = Jinja2Templates(directory=str(templates_dir))

# Mount static files
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page with URL submission form and recent entries."""
    recent_entries = db.get_recent_entries(limit=20)
    stats = db.get_stats()

    return templates.TemplateResponse("index.html", {
        "request": request,
        "recent_entries": recent_entries,
        "stats": stats
    })


@app.post("/submit")
async def submit_url(
    request: Request,
    url: str = Form(...),
    model: str = Form("gpt-4"),
    format_type: str = Form("bullet")
):
    """Submit URL for processing."""
    # Validate URL
    if not _is_valid_url(url):
        raise HTTPException(status_code=400, detail="Invalid URL format")

    # Check if URL already exists
    existing_url = db.get_url_by_url(url)

    if existing_url:
        # URL exists, redirect to its page
        return RedirectResponse(url=f"/results/{existing_url.id}", status_code=303)

    # Configure processing
    config = SummaryConfig(
        model=model,
        format=format_type,
        debug=False
    )

    # Create processor with custom config
    processor = URLProcessor(config)

    try:
        # Process URL
        url_record, summary_record, error_msg = processor.process_url(url)

        # Save to database
        url_id = db.insert_url(url_record)

        if summary_record:
            summary_record.url_id = url_id
            summary_id = db.insert_summary(summary_record)

        # Redirect to results page
        return RedirectResponse(url=f"/results/{url_id}", status_code=303)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@app.get("/results/{url_id}", response_class=HTMLResponse)
async def view_results(request: Request, url_id: int):
    """View results for a specific URL."""
    url_record = db.get_url_by_id(url_id)
    if not url_record:
        raise HTTPException(status_code=404, detail="URL not found")

    summaries = db.get_summaries_for_url(url_id)

    return templates.TemplateResponse("results.html", {
        "request": request,
        "url_record": url_record,
        "summaries": summaries
    })


@app.get("/search", response_class=HTMLResponse)
async def search(
    request: Request,
    q: Optional[str] = Query(None),
    type: str = Query("all")  # all, urls, summaries
):
    """Search interface and results."""
    results = []

    if q:
        if type == "urls":
            results = db.search_urls(q)
        elif type == "summaries":
            results = db.search_summaries(q)
        else:  # all
            url_results = db.search_urls(q)
            summary_results = db.search_summaries(q)
            results = {
                "urls": url_results,
                "summaries": summary_results
            }

    return templates.TemplateResponse("search.html", {
        "request": request,
        "query": q,
        "search_type": type,
        "results": results
    })


@app.get("/api/stats")
async def get_stats():
    """API endpoint for database statistics."""
    return db.get_stats()


@app.get("/api/recent")
async def get_recent(limit: int = Query(50, le=100)):
    """API endpoint for recent entries."""
    return db.get_recent_entries(limit)


@app.get("/api/search/urls")
async def search_urls_api(q: str = Query(...), limit: int = Query(50, le=100)):
    """API endpoint for URL search."""
    return db.search_urls(q, limit)


@app.get("/api/search/summaries")
async def search_summaries_api(q: str = Query(...), limit: int = Query(50, le=100)):
    """API endpoint for summary search."""
    return db.search_summaries(q, limit)


@app.get("/datasette")
async def datasette_redirect():
    """Redirect to Datasette instance."""
    # This would redirect to a separately running Datasette instance
    return RedirectResponse(url="http://localhost:8001", status_code=302)


def _is_valid_url(url: str) -> bool:
    """Validate URL format."""
    try:
        result = urllib.parse.urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False


def main():
    """Main entry point for the web application."""
    import argparse

    parser = argparse.ArgumentParser(description="LLM Digest Web Application")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    parser.add_argument("--db", default="llm_digest.db", help="Database file path")

    args = parser.parse_args()

    # Initialize database with custom path
    global db
    db = DatabaseManager(args.db)

    # Run the application
    uvicorn.run(
        "web_app:app",
        host=args.host,
        port=args.port,
        reload=args.reload
    )


if __name__ == "__main__":
    main()
