import pytest

from database import DatabaseManager, SummaryRecord, URLRecord


@pytest.fixture
def db_manager():
    """Provides an in-memory database manager for testing."""
    db = DatabaseManager(db_path=":memory:")
    yield db
    db.close()


def test_database_initialization(db_manager: DatabaseManager):
    """Tests that the database and its tables are created correctly."""
    cursor = db_manager.conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='urls'")
    assert cursor.fetchone() is not None, "'urls' table should exist."
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='summaries'"
    )
    assert cursor.fetchone() is not None, "'summaries' table should exist."
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='urls_fts'"
    )
    assert cursor.fetchone() is not None, "'urls_fts' virtual table should exist."
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='summaries_fts'"
    )
    assert cursor.fetchone() is not None, "'summaries_fts' virtual table should exist."


def test_insert_and_get_url(db_manager: DatabaseManager):
    """Tests inserting and retrieving a URL record."""
    url_record = URLRecord(
        url="https://example.com",
        title="Example Domain",
        description="An example domain for use in documentation.",
        site_name="ExampleCorp",
    )
    url_id = db_manager.insert_url(url_record)
    assert isinstance(url_id, int)

    retrieved_url = db_manager.get_url_by_id(url_id)
    assert retrieved_url is not None
    assert retrieved_url.url == "https://example.com"
    assert retrieved_url.title == "Example Domain"

    retrieved_by_url = db_manager.get_url_by_url("https://example.com")
    assert retrieved_by_url is not None
    assert retrieved_by_url.id == url_id


def test_insert_and_get_summary(db_manager: DatabaseManager):
    """Tests inserting and retrieving a summary record."""
    url_record = URLRecord(url="https://summary.test")
    url_id = db_manager.insert_url(url_record)

    assert isinstance(url_id, int)

    summary_record = SummaryRecord(
        url_id=url_id,
        content="This is a test summary.",
        model_used="test-model",
        format_type="test-format",
    )
    summary_id = db_manager.insert_summary(summary_record)
    assert isinstance(summary_id, int)

    summaries = db_manager.get_summaries_for_url(url_id)
    assert len(summaries) == 1
    assert summaries[0].content == "This is a test summary."
    assert summaries[0].model_used == "test-model"


def test_full_text_search(db_manager: DatabaseManager):
    """Tests the FTS5 search functionality for URLs and summaries."""
    # Insert URL
    url_record = URLRecord(
        url="https://search.test",
        title="Searchable Content",
        description="A test page for searching.",
    )
    url_id = db_manager.insert_url(url_record)

    assert isinstance(url_id, int)

    # Insert Summary
    summary_record = SummaryRecord(
        url_id=url_id,
        content="A searchable summary about LLMs.",
        model_used="search-model",
    )
    db_manager.insert_summary(summary_record)

    # Search URLs
    url_results = db_manager.search_urls("searchable")
    assert len(url_results) == 1
    assert url_results[0]["title"] == "Searchable Content"

    # Search Summaries
    summary_results = db_manager.search_summaries("LLMs")
    assert len(summary_results) == 1
    assert "searchable summary" in summary_results[0]["content"].lower()


def test_get_stats(db_manager: DatabaseManager):
    """Tests the statistics gathering functionality."""
    stats = db_manager.get_stats()
    assert stats["url_count"] == 0
    assert stats["summary_count"] == 0

    db_manager.insert_url(URLRecord(url="https://stats.test"))
    stats = db_manager.get_stats()
    assert stats["url_count"] == 1
