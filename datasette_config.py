#!/usr/bin/env python3
"""
Datasette configuration and metadata for LLM Digest database.
Provides optimized views and search configuration for data analysis.
"""

import json
from pathlib import Path


def create_datasette_metadata():
    """Create metadata.json configuration for Datasette."""
    metadata = {
        "title": "LLM Digest Database",
        "description": "URL summaries and OpenGraph data analysis",
        "source": "LLM Digest Web Application",
        "source_url": "http://localhost:8000",
        "databases": {
            "llm_digest": {
                "title": "LLM Digest",
                "description": "URLs, OpenGraph metadata, and LLM-generated summaries",
                "tables": {
                    "urls": {
                        "title": "URLs and OpenGraph Data",
                        "description": "Collected URLs with extracted OpenGraph metadata",
                        "sort": [["created_at", "desc"]],
                        "facets": ["site_name", "og_type"],
                        "columns": {
                            "id": "Unique identifier",
                            "url": "Original URL",
                            "title": "Page title from OpenGraph or HTML",
                            "description": "Page description from OpenGraph or meta tags",
                            "image": "Preview image URL",
                            "site_name": "Site name from OpenGraph",
                            "og_type": "OpenGraph content type",
                            "created_at": "When the URL was first processed",
                        },
                    },
                    "summaries": {
                        "title": "LLM Summaries",
                        "description": "AI-generated summaries of URL content",
                        "sort": [["created_at", "desc"]],
                        "facets": ["model_used", "format_type", "fragment_used"],
                        "columns": {
                            "id": "Unique identifier",
                            "url_id": "Reference to URLs table",
                            "content": "Generated summary text",
                            "model_used": "LLM model that generated the summary",
                            "format_type": "Summary format (bullet, paragraph, detailed)",
                            "fragment_used": "LLM fragment used for processing",
                            "created_at": "When the summary was generated",
                        },
                    },
                    "urls_fts": {
                        "title": "URL Full-Text Search",
                        "description": "FTS5 virtual table for searching URL metadata",
                        "hidden": True,
                    },
                    "summaries_fts": {
                        "title": "Summary Full-Text Search",
                        "description": "FTS5 virtual table for searching summary content",
                        "hidden": True,
                    },
                },
                "queries": {
                    "recent_summaries": {
                        "title": "Recent Summaries with URLs",
                        "sql": """
                            SELECT
                                u.url,
                                u.title,
                                u.site_name,
                                s.content,
                                s.model_used,
                                s.format_type,
                                s.created_at
                            FROM summaries s
                            JOIN urls u ON s.url_id = u.id
                            ORDER BY s.created_at DESC
                            LIMIT 50
                        """,
                    },
                    "summary_by_model": {
                        "title": "Summaries by Model",
                        "sql": """
                            SELECT
                                model_used,
                                COUNT(*) as count,
                                AVG(LENGTH(content)) as avg_length
                            FROM summaries
                            GROUP BY model_used
                            ORDER BY count DESC
                        """,
                    },
                    "sites_summary": {
                        "title": "Summary by Site",
                        "sql": """
                            SELECT
                                u.site_name,
                                COUNT(DISTINCT u.id) as url_count,
                                COUNT(s.id) as summary_count
                            FROM urls u
                            LEFT JOIN summaries s ON u.id = s.url_id
                            WHERE u.site_name IS NOT NULL
                            GROUP BY u.site_name
                            ORDER BY url_count DESC
                        """,
                    },
                    "search_content": {
                        "title": "Search URLs and Summaries",
                        "sql": """
                            SELECT
                                'URL' as type,
                                u.id,
                                u.url,
                                u.title,
                                u.description as content,
                                u.created_at
                            FROM urls_fts
                            JOIN urls u ON urls_fts.rowid = u.id
                            WHERE urls_fts MATCH :query

                            UNION ALL

                            SELECT
                                'Summary' as type,
                                s.id,
                                u.url,
                                u.title,
                                s.content,
                                s.created_at
                            FROM summaries_fts
                            JOIN summaries s ON summaries_fts.rowid = s.id
                            JOIN urls u ON s.url_id = u.id
                            WHERE summaries_fts MATCH :query

                            ORDER BY created_at DESC
                        """,
                    },
                },
            }
        },
        "plugins": {
            "datasette-vega": {
                "charts": {
                    "summaries_over_time": {
                        "title": "Summaries Over Time",
                        "database": "llm_digest",
                        "query": """
                            SELECT
                                DATE(created_at) as date,
                                COUNT(*) as count
                            FROM summaries
                            GROUP BY DATE(created_at)
                            ORDER BY date
                        """,
                        "mark": "line",
                        "encoding": {
                            "x": {"field": "date", "type": "temporal"},
                            "y": {"field": "count", "type": "quantitative"},
                        },
                    },
                    "model_usage": {
                        "title": "Model Usage Distribution",
                        "database": "llm_digest",
                        "query": """
                            SELECT
                                model_used,
                                COUNT(*) as count
                            FROM summaries
                            GROUP BY model_used
                        """,
                        "mark": "arc",
                        "encoding": {
                            "theta": {"field": "count", "type": "quantitative"},
                            "color": {"field": "model_used", "type": "nominal"},
                        },
                    },
                }
            }
        },
    }

    return metadata


def create_datasette_config():
    """Create datasette configuration files."""
    metadata = create_datasette_metadata()

    # Write metadata.json
    metadata_path = Path("datasette_metadata.json")
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    # Create datasette startup script
    startup_script = """#!/bin/bash
# Datasette startup script for LLM Digest

# Default database path
DB_PATH=${1:-"llm_digest.db"}

# Check if database exists
if [ ! -f "$DB_PATH" ]; then
    echo "Database file not found: $DB_PATH"
    echo "Make sure to run the web application first to create the database."
    exit 1
fi

# Start Datasette with configuration
echo "Starting Datasette for LLM Digest..."
echo "Database: $DB_PATH"
echo "Datasette will be available at: http://localhost:8001"

datasette serve "$DB_PATH" \\
    --metadata datasette_metadata.json \\
    --host 0.0.0.0 \\
    --port 8001 \\
    --reload \\
    --setting sql_time_limit_ms 10000 \\
    --setting max_returned_rows 5000 \\
    --setting facet_time_limit_ms 1000 \\
    --setting allow_download on \\
    --setting allow_facet on \\
    --setting default_page_size 100
"""

    script_path = Path("start_datasette.sh")
    with open(script_path, "w") as f:
        f.write(startup_script)

    # Make script executable
    script_path.chmod(0o755)

    print("✅ Datasette configuration created:")
    print(f"   - metadata: {metadata_path}")
    print(f"   - startup script: {script_path}")
    print("\nTo start Datasette:")
    print("   ./start_datasette.sh")
    print("   ./start_datasette.sh custom_database.db")


if __name__ == "__main__":
    create_datasette_config()
