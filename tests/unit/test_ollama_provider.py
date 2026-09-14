"""Unit tests for Ollama local LLM provider integration."""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from pydantic import BaseModel

from src.config import LLMProvider as LLMProviderEnum, Settings
from src.errors import ErrorCategory, InfrastructureFailure
from src.llm.provider import LLMProvider, LLMProviderError


class LessonOutlineSchema(BaseModel):
    title: str
    key_concepts: list[str]


@pytest.fixture
def mock_ollama_settings():
    with patch("src.llm.provider.get_settings") as mock:
        settings = MagicMock()
        settings.llm_provider = LLMProviderEnum.OLLAMA
        settings.ollama_base_url = "http://localhost:11434"
        settings.ollama_model = "llama3.2"
        settings.gemini_api_key = ""
        settings.openai_api_key = ""
        settings.enable_fallback = False
        settings.llm_temperature = 0.3
        settings.llm_max_tokens = 2048
        mock.return_value = settings
        yield settings


def test_config_model_resolution():
    """Settings resolves llm_model to llama3.2 when provider is ollama."""
    s = Settings(
        llm_provider=LLMProviderEnum.OLLAMA,
        ollama_model="llama3.2",
    )
    assert s.llm_provider == LLMProviderEnum.OLLAMA
    assert s.llm_model == "llama3.2"


def test_ollama_provider_initialization(mock_ollama_settings):
    """LLMProvider initializes Ollama client when LLM_PROVIDER=ollama."""
    provider = LLMProvider()

    assert provider._ollama_client is not None
    assert provider.model == "llama3.2"
    assert provider.ollama_model == "llama3.2"
    # OpenAI client should be None because provider is Ollama
    assert provider._gemini_client is None


@pytest.mark.asyncio
async def test_ollama_generate_success(mock_ollama_settings):
    """When Ollama is called, it returns text response from llama3.2."""
    provider = LLMProvider()

    mock_choice = MagicMock()
    mock_choice.message.content = "Neural networks are computational models inspired by the brain."
    mock_resp = MagicMock()
    mock_resp.choices = [mock_choice]
    mock_resp.usage.prompt_tokens = 15
    mock_resp.usage.completion_tokens = 25

    provider._ollama_client.chat.completions.create = AsyncMock(return_value=mock_resp)

    result = await provider.generate(
        system_prompt="You are an educator.",
        user_prompt="Explain neural networks simply.",
        node_name="lesson_generator",
    )

    assert "Neural networks" in result
    assert provider._ollama_client.chat.completions.create.await_count == 1
    call_kwargs = provider._ollama_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["model"] == "llama3.2"


@pytest.mark.asyncio
async def test_ollama_generate_structured_with_markdown_fences(mock_ollama_settings):
    """Ollama structured response correctly parses JSON enclosed in markdown code fences."""
    provider = LLMProvider()

    mock_choice = MagicMock()
    mock_choice.message.content = '```json\n{"title": "Intro to AI", "key_concepts": ["Weights", "Biases"]}\n```'
    mock_resp = MagicMock()
    mock_resp.choices = [mock_choice]
    mock_resp.usage.prompt_tokens = 20
    mock_resp.usage.completion_tokens = 30

    provider._ollama_client.chat.completions.create = AsyncMock(return_value=mock_resp)

    parsed = await provider.generate_structured(
        system_prompt="Return JSON only.",
        user_prompt="Outline an AI lesson.",
        output_model=LessonOutlineSchema,
        node_name="curriculum_planner",
    )

    assert parsed.title == "Intro to AI"
    assert parsed.key_concepts == ["Weights", "Biases"]


@pytest.mark.asyncio
async def test_ollama_generate_structured_with_conversational_preamble(mock_ollama_settings):
    """Ollama structured response extracts JSON even if model adds conversational preamble."""
    provider = LLMProvider()

    mock_choice = MagicMock()
    mock_choice.message.content = 'Here is the requested outline:\n{"title": "Deep Learning", "key_concepts": ["Backprop"]}\nHope this helps!'
    mock_resp = MagicMock()
    mock_resp.choices = [mock_choice]
    mock_resp.usage.prompt_tokens = 20
    mock_resp.usage.completion_tokens = 30

    provider._ollama_client.chat.completions.create = AsyncMock(return_value=mock_resp)

    parsed = await provider.generate_structured(
        system_prompt="Return JSON only.",
        user_prompt="Outline deep learning.",
        output_model=LessonOutlineSchema,
        node_name="curriculum_planner",
    )

    assert parsed.title == "Deep Learning"
    assert parsed.key_concepts == ["Backprop"]


@pytest.mark.asyncio
async def test_ollama_daemon_offline_normalizes_to_system_error(mock_ollama_settings):
    """When Ollama daemon is offline (connection refused), error is normalized to SYSTEM_ERROR."""
    provider = LLMProvider()

    # Simulate connection error to Ollama port 11434
    provider._ollama_client.chat.completions.create = AsyncMock(
        side_effect=ConnectionRefusedError("Connect call failed ('127.0.0.1', 11434)")
    )

    with pytest.raises(LLMProviderError) as exc_info:
        await provider.generate(
            system_prompt="system",
            user_prompt="prompt",
            node_name="generator",
        )

    err = exc_info.value
    assert isinstance(err, InfrastructureFailure)
    assert err.detail.category == ErrorCategory.PROVIDER_UNAVAILABLE.value
    assert err.detail.consumes_content_retry is False
    assert err.detail.provider == "ollama"
    assert err.detail.retryable is True
    assert "Ollama" in err.detail.message or "Ollama" in err.detail.detail


@pytest.mark.asyncio
async def test_health_check_ollama_connected():
    """Health check reports connected status when Ollama returns 200 OK."""
    from src.api.routes import health_check

    with patch("src.api.routes.get_settings") as mock_settings, \
         patch("httpx.AsyncClient.get") as mock_get:
        settings = MagicMock()
        settings.llm_provider = LLMProviderEnum.OLLAMA
        settings.ollama_base_url = "http://localhost:11434"
        settings.ollama_model = "llama3.2"
        mock_settings.return_value = settings

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp

        health = await health_check()
        assert health.llm_provider == "ollama"
        assert health.llm_model == "llama3.2"
        assert health.llm_status == "connected"
