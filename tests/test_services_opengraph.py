import pytest
import responses

from services import OpenGraphExtractor, URLRecord


@pytest.fixture
def og_extractor() -> OpenGraphExtractor:
    """Provides an OpenGraphExtractor instance for testing."""
    return OpenGraphExtractor(timeout=5)


@responses.activate
def test_extract_with_full_opengraph_tags(og_extractor: OpenGraphExtractor):
    """Tests extraction from a URL with complete OpenGraph tags."""
    html_content = """
    <html>
        <head>
            <title>Old Title</title>
            <meta property="og:title" content="Test Title"/>
            <meta property="og:description" content="Test Description"/>
            <meta property="og:image" content="https://example.com/image.png"/>
            <meta property="og:site_name" content="Test Site"/>
            <meta property="og:type" content="article"/>
        </head>
        <body></body>
    </html>
    """
    test_url = "https://example.com/test-page"
    responses.add(responses.GET, test_url, body=html_content, status=200)

    record = og_extractor.extract(test_url)

    assert isinstance(record, URLRecord)
    assert record.url == test_url
    assert record.title == "Test Title"
    assert record.description == "Test Description"
    assert record.image == "https://example.com/image.png"
    assert record.site_name == "Test Site"
    assert record.og_type == "article"


@responses.activate
def test_extract_with_missing_opengraph_tags(og_extractor: OpenGraphExtractor):
    """Tests extraction from a URL with fallback to standard meta tags."""
    html_content = """
    <html>
        <head>
            <title>Fallback Title</title>
            <meta name="description" content="Fallback Description"/>
        </head>
        <body></body>
    </html>
    """
    test_url = "https://fallback.com"
    responses.add(responses.GET, test_url, body=html_content, status=200)

    record = og_extractor.extract(test_url)

    assert record.title == "Fallback Title"
    assert record.description == "Fallback Description"
    assert record.image is None


@responses.activate
def test_extract_handles_http_error(og_extractor: OpenGraphExtractor):
    """Tests that the extractor handles HTTP errors gracefully."""
    test_url = "https://error.com"
    responses.add(responses.GET, test_url, status=404)

    record = og_extractor.extract(test_url)

    # Should return a basic record with just the URL
    assert record.url == test_url
    assert record.title is None
    assert record.description is None
