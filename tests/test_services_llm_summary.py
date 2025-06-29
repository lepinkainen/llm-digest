
import pytest
import subprocess
from unittest.mock import MagicMock
from services import LLMSummaryService, SummaryConfig, SummaryRecord

@pytest.fixture
def summary_service() -> LLMSummaryService:
    """Provides an LLMSummaryService instance for testing."""
    config = SummaryConfig(model="test-model", debug=True)
    return LLMSummaryService(config)

def test_generate_summary_success(monkeypatch, summary_service: LLMSummaryService):
    """Tests successful summary generation."""
    mock_run = MagicMock()
    mock_run.return_value = subprocess.CompletedProcess(
        args=["llm", "..."],
        returncode=0,
        stdout="This is a summary.",
        stderr=""
    )
    monkeypatch.setattr(subprocess, "run", mock_run)

    success, record, error = summary_service.generate_summary("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

    assert success
    assert isinstance(record, SummaryRecord)
    assert record.content == "This is a summary."
    assert record.model_used == "test-model"
    assert error is None

def test_generate_summary_llm_command_fails(monkeypatch, summary_service: LLMSummaryService):
    """Tests handling of a failed LLM command."""
    mock_run = MagicMock()
    mock_run.return_value = subprocess.CompletedProcess(
        args=["llm", "..."],
        returncode=1,
        stdout="",
        stderr="LLM error"
    )
    monkeypatch.setattr(subprocess, "run", mock_run)

    success, record, error = summary_service.generate_summary("https://www.reddit.com/r/python/comments/12345/")

    assert not success
    assert record is None
    assert "LLM command failed" in error

def test_unsupported_url(summary_service: LLMSummaryService):
    """Tests that an unsupported URL is handled correctly."""
    success, record, error = summary_service.generate_summary("https://www.google.com")

    assert not success
    assert record is None
    assert "No matching fragment found" in error

def test_youtube_id_extraction(summary_service: LLMSummaryService):
    """Tests various YouTube URL formats for ID extraction."""
    urls = {
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ": "dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ": "dQw4w9WgXcQ",
        "https://www.youtube.com/embed/dQw4w9WgXcQ": "dQw4w9WgXcQ",
    }
    for url, expected_id in urls.items():
        assert summary_service.extract_youtube_id(url) == expected_id

def test_reddit_id_extraction(summary_service: LLMSummaryService):
    """Tests various Reddit URL formats for ID extraction."""
    urls = {
        "https://www.reddit.com/r/programming/comments/12345/a_post_title/": "12345",
        "https://reddit.com/comments/67890": "67890",
    }
    for url, expected_id in urls.items():
        assert summary_service.extract_reddit_id(url) == expected_id

def test_hn_id_extraction(summary_service: LLMSummaryService):
    """Tests various Hacker News URL formats for ID extraction."""
    url = "https://news.ycombinator.com/item?id=12345678"
    assert summary_service.extract_hn_id(url) == "12345678"
