
import subprocess
from unittest.mock import MagicMock

import pytest

from services import LLMModelDiscovery


@pytest.fixture
def model_discovery() -> LLMModelDiscovery:
    """Provides an LLMModelDiscovery instance for testing."""
    return LLMModelDiscovery(cache_timeout=0)  # Disable cache for tests

@pytest.fixture
def mock_llm_output() -> str:
    """Provides mock output from the 'llm models list' command."""
    return """
    OpenAI Chat: gpt-4o (aliases: 4o)
    OpenAI Chat: gpt-4o-mini
    OpenAI Completion: gpt-3.5-turbo-instruct
    GeminiPro: gemini-1.5-pro-latest
    Anthropic: claude-3-opus-20240229 (experimental)
    """

def test_discover_models_success(monkeypatch, model_discovery: LLMModelDiscovery, mock_llm_output: str):
    """Tests successful discovery and parsing of models."""
    mock_run = MagicMock()
    mock_run.return_value = subprocess.CompletedProcess(
        args=["llm", "models", "list"], returncode=0, stdout=mock_llm_output, stderr=""
    )
    monkeypatch.setattr(subprocess, "run", mock_run)

    models = model_discovery.discover_models(force_refresh=True)

    assert len(models) > 0
    assert any(model.name == "gpt-4o" for model in models)
    assert all(not model.is_experimental for model in models)

def test_discover_models_fallback(monkeypatch, model_discovery: LLMModelDiscovery):
    """Tests the fallback mechanism when 'llm models list' fails."""
    mock_run = MagicMock()
    mock_run.return_value = subprocess.CompletedProcess(
        args=["llm", "models", "list"], returncode=1, stdout="", stderr="Error"
    )
    monkeypatch.setattr(subprocess, "run", mock_run)

    models = model_discovery.discover_models(force_refresh=True)

    assert models == model_discovery.fallback_models

def test_model_prioritization(monkeypatch, model_discovery: LLMModelDiscovery, mock_llm_output: str):
    """Tests that models are correctly prioritized."""
    mock_run = MagicMock()
    mock_run.return_value = subprocess.CompletedProcess(
        args=["llm", "models", "list"], returncode=0, stdout=mock_llm_output, stderr=""
    )
    monkeypatch.setattr(subprocess, "run", mock_run)

    models = model_discovery.discover_models(force_refresh=True)

    # gpt-4o should have the highest priority (lowest number)
    assert models[0].name == "gpt-4o"
    assert models[1].name == "gpt-4o-mini"

def test_get_model_by_alias(monkeypatch, model_discovery: LLMModelDiscovery, mock_llm_output: str):
    """Tests retrieving a model by its alias."""
    mock_run = MagicMock()
    mock_run.return_value = subprocess.CompletedProcess(
        args=["llm", "models", "list"], returncode=0, stdout=mock_llm_output, stderr=""
    )
    monkeypatch.setattr(subprocess, "run", mock_run)

    model = model_discovery.get_model_by_name("4o")
    assert model is not None
    assert model.name == "gpt-4o"

def test_get_model_by_full_name(monkeypatch, model_discovery: LLMModelDiscovery, mock_llm_output: str):
    """Tests retrieving a model by its full name."""
    mock_run = MagicMock()
    mock_run.return_value = subprocess.CompletedProcess(
        args=["llm", "models", "list"], returncode=0, stdout=mock_llm_output, stderr=""
    )
    monkeypatch.setattr(subprocess, "run", mock_run)

    model = model_discovery.get_model_by_name("gemini-1.5-pro-latest")
    assert model is not None
