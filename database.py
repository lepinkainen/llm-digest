#!/usr/bin/env python3
"""
Database models and operations for LLM Digest web application.
Handles SQLite database with FTS5 for full-text search capabilities.
"""

import sqlite3
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class URLRecord:
    """Represents a URL record with OpenGraph data."""
    id: Optional[int] = None
    url: str = ""
    title: Optional[str] = None
    description: Optional[str] = None
    image: Optional[str] = None
    site_name: Optional[str] = None
    og_type: Optional[str] = None
    created_at: Optional[str] = None


@dataclass
class SummaryRecord:
    """Represents an LLM summary record."""
    id: Optional[int] = None
    url_id: int = 0
    content: str = ""
    model_used: str = ""
    format_type: str = ""
    fragment_used: Optional[str] = None
    created_at: Optional[str] = None


class DatabaseManager:
    """Manages SQLite database operations with FTS5 support."""
    
    def __init__(self, db_path: str = "llm_digest.db"):
        """Initialize database manager with path."""
        self.db_path = Path(db_path)
        self.init_database()
    
    def get_connection(self) -> sqlite3.Connection:
        """Get database connection with proper configuration."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        # Enable FTS5
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    
    def init_database(self) -> None:
        """Initialize database schema with FTS5 search tables."""
        with self.get_connection() as conn:
            # URLs table for OpenGraph data
            conn.execute("""
                CREATE TABLE IF NOT EXISTS urls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT UNIQUE NOT NULL,
                    title TEXT,
                    description TEXT,
                    image TEXT,
                    site_name TEXT,
                    og_type TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Summaries table for LLM output
            conn.execute("""
                CREATE TABLE IF NOT EXISTS summaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url_id INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    model_used TEXT NOT NULL,
                    format_type TEXT NOT NULL,
                    fragment_used TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (url_id) REFERENCES urls (id) ON DELETE CASCADE
                )
            """)
            
            # FTS5 virtual table for URL search
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS urls_fts USING fts5(
                    url, title, description, site_name,
                    content='urls',
                    content_rowid='id'
                )
            """)
            
            # FTS5 virtual table for summary search
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS summaries_fts USING fts5(
                    content, model_used, format_type,
                    content='summaries',
                    content_rowid='id'
                )
            """)
            
            # Triggers to keep FTS5 tables in sync
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS urls_fts_insert AFTER INSERT ON urls BEGIN
                    INSERT INTO urls_fts(rowid, url, title, description, site_name)
                    VALUES (new.id, new.url, new.title, new.description, new.site_name);
                END
            """)
            
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS urls_fts_delete AFTER DELETE ON urls BEGIN
                    INSERT INTO urls_fts(urls_fts, rowid, url, title, description, site_name)
                    VALUES ('delete', old.id, old.url, old.title, old.description, old.site_name);
                END
            """)
            
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS urls_fts_update AFTER UPDATE ON urls BEGIN
                    INSERT INTO urls_fts(urls_fts, rowid, url, title, description, site_name)
                    VALUES ('delete', old.id, old.url, old.title, old.description, old.site_name);
                    INSERT INTO urls_fts(rowid, url, title, description, site_name)
                    VALUES (new.id, new.url, new.title, new.description, new.site_name);
                END
            """)
            
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS summaries_fts_insert AFTER INSERT ON summaries BEGIN
                    INSERT INTO summaries_fts(rowid, content, model_used, format_type)
                    VALUES (new.id, new.content, new.model_used, new.format_type);
                END
            """)
            
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS summaries_fts_delete AFTER DELETE ON summaries BEGIN
                    INSERT INTO summaries_fts(summaries_fts, rowid, content, model_used, format_type)
                    VALUES ('delete', old.id, old.content, old.model_used, old.format_type);
                END
            """)
            
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS summaries_fts_update AFTER UPDATE ON summaries BEGIN
                    INSERT INTO summaries_fts(summaries_fts, rowid, content, model_used, format_type)
                    VALUES ('delete', old.id, old.content, old.model_used, old.format_type);
                    INSERT INTO summaries_fts(rowid, content, model_used, format_type)
                    VALUES (new.id, new.content, new.model_used, new.format_type);
                END
            """)
            
            conn.commit()
    
    def insert_url(self, url_record: URLRecord) -> int:
        """Insert URL record and return the ID."""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT OR REPLACE INTO urls (url, title, description, image, site_name, og_type)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                url_record.url,
                url_record.title,
                url_record.description,
                url_record.image,
                url_record.site_name,
                url_record.og_type
            ))
            return cursor.lastrowid
    
    def insert_summary(self, summary_record: SummaryRecord) -> int:
        """Insert summary record and return the ID."""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO summaries (url_id, content, model_used, format_type, fragment_used)
                VALUES (?, ?, ?, ?, ?)
            """, (
                summary_record.url_id,
                summary_record.content,
                summary_record.model_used,
                summary_record.format_type,
                summary_record.fragment_used
            ))
            return cursor.lastrowid
    
    def get_url_by_url(self, url: str) -> Optional[URLRecord]:
        """Get URL record by URL string."""
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM urls WHERE url = ?", (url,)
            ).fetchone()
            
            if row:
                return URLRecord(**dict(row))
            return None
    
    def get_url_by_id(self, url_id: int) -> Optional[URLRecord]:
        """Get URL record by ID."""
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM urls WHERE id = ?", (url_id,)
            ).fetchone()
            
            if row:
                return URLRecord(**dict(row))
            return None
    
    def get_summaries_for_url(self, url_id: int) -> List[SummaryRecord]:
        """Get all summaries for a URL."""
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM summaries WHERE url_id = ? ORDER BY created_at DESC",
                (url_id,)
            ).fetchall()
            
            return [SummaryRecord(**dict(row)) for row in rows]
    
    def get_recent_entries(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent URL entries with their latest summaries."""
        with self.get_connection() as conn:
            rows = conn.execute("""
                SELECT 
                    u.*,
                    s.id as summary_id,
                    s.content as summary_content,
                    s.model_used,
                    s.format_type,
                    s.fragment_used,
                    s.created_at as summary_created_at
                FROM urls u
                LEFT JOIN summaries s ON u.id = s.url_id
                WHERE s.id IN (
                    SELECT MAX(id) FROM summaries GROUP BY url_id
                ) OR s.id IS NULL
                ORDER BY u.created_at DESC
                LIMIT ?
            """, (limit,)).fetchall()
            
            return [dict(row) for row in rows]
    
    def search_urls(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Full-text search URLs using FTS5."""
        with self.get_connection() as conn:
            rows = conn.execute("""
                SELECT u.*, rank
                FROM urls_fts
                JOIN urls u ON urls_fts.rowid = u.id
                WHERE urls_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """, (query, limit)).fetchall()
            
            return [dict(row) for row in rows]
    
    def search_summaries(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Full-text search summaries using FTS5."""
        with self.get_connection() as conn:
            rows = conn.execute("""
                SELECT s.*, u.url, u.title, rank
                FROM summaries_fts
                JOIN summaries s ON summaries_fts.rowid = s.id
                JOIN urls u ON s.url_id = u.id
                WHERE summaries_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """, (query, limit)).fetchall()
            
            return [dict(row) for row in rows]
    
    def get_stats(self) -> Dict[str, int]:
        """Get database statistics."""
        with self.get_connection() as conn:
            url_count = conn.execute("SELECT COUNT(*) FROM urls").fetchone()[0]
            summary_count = conn.execute("SELECT COUNT(*) FROM summaries").fetchone()[0]
            
            return {
                "url_count": url_count,
                "summary_count": summary_count
            }