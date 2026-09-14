"""Unit tests for Gemini primary with OpenAI automatic fallback."""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from pydantic import BaseModel

from src.llm.provider import LLMProvider, LLMProviderError, StructuredOutputError


class DummyOutputSchema(BaseModel):
    summary: str
    points: list[str]


@pytest.fixture
def mock_settings():
    with patch("src.llm.provider.get_settings") as mock:
        settings = MagicMock()
        settings.gemini_api_key = "AIzaSy-mock-gemini-key"
        settings.gemini_model = "gemini-2.0-flash"
        settings.gemini_base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
        settings.openai_api_key = "sk-mock-openai-key"
        settings.openai_model = "gpt-4o"
        settings.enable_fallback = True
        settings.llm_temperature = 0.3
        settings.llm_max_tokens = 2048
        mock.return_value = settings
        yield settings


@pytest.mark.asyncio
async def test_gemini_primary_success(mock_settings):
    """When Gemini succeeds, it returns the response and does not call OpenAI."""
    provider = LLMProvider()

    # Mock response from Gemini
    mock_choice = MagicMock()
    mock_choice.message.content = "Gemini generated content"
    mock_resp = MagicMock()
    mock_resp.choices = [mock_choice]
    mock_resp.usage.prompt_tokens = 20
    mock_resp.usage.completion_tokens = 50

    provider._gemini_client.chat.completions.create = AsyncMock(return_value=mock_resp)
    provider._openai_client.chat.completions.create = AsyncMock()

    result = await provider.generate(
        system_prompt="system prompt",
        user_prompt="user prompt",
        node_name="test_node",
    )

    assert result == "Gemini generated content"
    assert provider._gemini_client.chat.completions.create.await_count == 1
    assert provider._openai_client.chat.completions.create.await_count == 0


@pytest.mark.asyncio
async def test_gemini_fails_fallback_to_openai_succeeds(mock_settings):
    """When Gemini throws an API error, provider automatically falls back to OpenAI."""
    provider = LLMProvider()

    # Gemini throws error
    provider._gemini_client.chat.completions.create = AsyncMock(
        side_effect=Exception("Gemini 429 Quota Exceeded")
    )

    # OpenAI succeeds
    mock_choice = MagicMock()
    mock_choice.message.content = "OpenAI fallback generated content"
    mock_resp = MagicMock()
    mock_resp.choices = [mock_choice]
    mock_resp.usage.prompt_tokens = 25
    mock_resp.usage.completion_tokens = 60
    provider._openai_client.chat.completions.create = AsyncMock(return_value=mock_resp)

    result = await provider.generate(
        system_prompt="system prompt",
        user_prompt="user prompt",
        node_name="test_fallback_node",
    )

    assert result == "OpenAI fallback generated content"
    assert provider._gemini_client.chat.completions.create.await_count == 1
    assert provider._openai_client.chat.completions.create.await_count == 1


@pytest.mark.asyncio
async def test_both_providers_fail_raises_error(mock_settings):
    """When both Gemini and OpenAI fail, raises LLMProviderError."""
    provider = LLMProvider()

    provider._gemini_client.chat.completions.create = AsyncMock(
        side_effect=Exception("Gemini Unavailable")
    )
    provider._openai_client.chat.completions.create = AsyncMock(
        side_effect=Exception("OpenAI Timeout")
    )

    with pytest.raises(LLMProviderError):
        await provider.generate(
            system_prompt="system prompt",
            user_prompt="user prompt",
            node_name="test_double_fail",
        )


@pytest.mark.asyncio
async def test_generate_structured_with_fallback(mock_settings):
    """When Gemini returns invalid JSON, fallback to OpenAI parses successfully."""
    provider = LLMProvider()

    # Gemini returns invalid JSON
    gemini_choice = MagicMock()
    gemini_choice.message.content = "This is not JSON at all!"
    gemini_resp = MagicMock()
    gemini_resp.choices = [gemini_choice]
    gemini_resp.usage.prompt_tokens = 30
    gemini_resp.usage.completion_tokens = 10
    provider._gemini_client.chat.completions.create = AsyncMock(return_value=gemini_resp)

    # OpenAI returns valid JSON matching DummyOutputSchema
    openai_choice = MagicMock()
    openai_choice.message.content = '{"summary": "Structured summary", "points": ["P1", "P2"]}'
    openai_resp = MagicMock()
    openai_resp.choices = [openai_choice]
    openai_resp.usage.prompt_tokens = 35
    openai_resp.usage.completion_tokens = 40
    provider._openai_client.chat.completions.create = AsyncMock(return_value=openai_resp)

    result = await provider.generate_structured(
        system_prompt="system prompt",
        user_prompt="user prompt",
        output_model=DummyOutputSchema,
        node_name="test_structured_fallback",
    )

    assert isinstance(result, DummyOutputSchema)
    assert result.summary == "Structured summary"
    assert result.points == ["P1", "P2"]
