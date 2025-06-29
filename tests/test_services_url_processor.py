
import pytest
from unittest.mock import MagicMock
from services import URLProcessor, URLRecord, SummaryRecord, SummaryConfig

@pytest.fixture
def mock_og_extractor():
    """Mocks the OpenGraphExtractor."""
    mock = MagicMock()
    mock.extract.return_value = URLRecord(
        url="https://example.com",
        title="Mocked Title",
        description="Mocked Description"
    )
    return mock

@pytest.fixture
def mock_summary_service():
    """Mocks the LLMSummaryService."""
    mock = MagicMock()
    mock.generate_summary.return_value = (
        True, 
        SummaryRecord(content="Mocked Summary", model_used="mock-model"), 
        None
    )
    return mock

@pytest.fixture
def url_processor(mock_og_extractor, mock_summary_service) -> URLProcessor:
    """Provides a URLProcessor instance with mocked dependencies."""
    processor = URLProcessor()
    processor.og_extractor = mock_og_extractor
    processor.summary_service = mock_summary_service
    return processor

def test_process_url_success(url_processor: URLProcessor):
    """Tests successful URL processing."""
    url = "https://example.com"
    url_record, summary_record, error_msg = url_processor.process_url(url)

    url_processor.og_extractor.extract.assert_called_once_with(url)
    url_processor.summary_service.generate_summary.assert_called_once_with(url)

    assert isinstance(url_record, URLRecord)
    assert url_record.url == url
    assert url_record.title == "Mocked Title"

    assert isinstance(summary_record, SummaryRecord)
    assert summary_record.content == "Mocked Summary"
    assert error_msg is None

def test_process_url_summary_failure(url_processor: URLProcessor, mock_summary_service: MagicMock):
    """Tests URL processing when summary generation fails."""
    mock_summary_service.generate_summary.return_value = (False, None, "LLM error")
    url = "https://example.com"
    url_record, summary_record, error_msg = url_processor.process_url(url)

    url_processor.og_extractor.extract.assert_called_once_with(url)
    url_processor.summary_service.generate_summary.assert_called_once_with(url)

    assert isinstance(url_record, URLRecord)
    assert url_record.url == url
    assert summary_record is None
    assert error_msg == "LLM error"

def test_process_url_og_extraction_failure(url_processor: URLProcessor, mock_og_extractor: MagicMock):
    """Tests URL processing when OpenGraph extraction fails."""
    mock_og_extractor.extract.return_value = URLRecord(url="https://example.com") # Simulate minimal record on failure
    url = "https://example.com"
    url_record, summary_record, error_msg = url_processor.process_url(url)

    url_processor.og_extractor.extract.assert_called_once_with(url)
    url_processor.summary_service.generate_summary.assert_called_once_with(url)

    assert isinstance(url_record, URLRecord)
    assert url_record.url == url
    assert url_record.title is None # Title should be None if OG extraction failed
    assert isinstance(summary_record, SummaryRecord)
    assert error_msg is None
