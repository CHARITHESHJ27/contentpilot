"""LLM provider abstraction layer.

Supports structured output parsing and infrastructure-level retries.
Infrastructure retries (API timeout, rate limit) are separate from
content regeneration retries in the LangGraph workflow.
"""

import json
import time
from typing import Any, Optional, TypeVar

from openai import AsyncOpenAI, APIError, APITimeoutError, InternalServerError, RateLimitError
from pydantic import BaseModel, ValidationError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.config import LLMProvider as LLMProviderEnum, get_settings
from src.errors import ErrorCategory, InfrastructureErrorDetail, InfrastructureFailure, normalize_infrastructure_error
from src.observability import get_logger
from src.observability.tracing import MetricsCollector

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


class LLMProviderError(InfrastructureFailure):
    """Raised when the LLM provider fails after all infrastructure retries."""

    def __init__(self, message: str, detail: Optional[InfrastructureErrorDetail] = None) -> None:
        if detail is None:
            detail = normalize_infrastructure_error(Exception(message))
            detail.message = message
        super().__init__(detail=detail)


class StructuredOutputError(Exception):
    """Raised when LLM output cannot be parsed into the expected schema."""
    pass


class LLMProvider:
    """Abstraction over LLM APIs with structured output support and automatic provider failover.

    Handles:
    - Primary provider execution (Google Gemini, OpenAI, or local Ollama)
    - Automatic fallback execution (OpenAI) if primary encounters rate limits, quota issues, or errors
    - Local LLM inference via Ollama (OpenAI-compatible /v1 endpoint)
    - Structured output parsing with Pydantic validation
    - Token tracking and observability metrics
    - Bounded infrastructure retries
    """

    def __init__(
        self,
        metrics: MetricsCollector | None = None,
    ) -> None:
        settings = get_settings()
        self.settings = settings
        self.gemini_model = settings.gemini_model
        self.openai_model = settings.openai_model
        self.ollama_model = getattr(settings, "ollama_model", "llama3.2")
        self.ollama_base_url = getattr(settings, "ollama_base_url", "http://localhost:11434")
        self.enable_fallback = settings.enable_fallback
        self.temperature = settings.llm_temperature
        self.max_tokens = settings.llm_max_tokens
        self.metrics = metrics or MetricsCollector()

        # Check configured provider
        provider_val = getattr(settings, "llm_provider", None)
        is_ollama = (
            provider_val == LLMProviderEnum.OLLAMA
            or (isinstance(provider_val, str) and provider_val.lower() == "ollama")
        )

        # Initialize Ollama client if provider is ollama
        self._ollama_client: AsyncOpenAI | None = None
        if is_ollama:
            base_url = f"{self.ollama_base_url.rstrip('/')}/v1"
            self._ollama_client = AsyncOpenAI(
                base_url=base_url,
                api_key="ollama",
            )
            self.model = self.ollama_model

        # Initialize Gemini client if key is present
        self._gemini_client: AsyncOpenAI | None = None
        if getattr(settings, "gemini_api_key", ""):
            self._gemini_client = AsyncOpenAI(
                api_key=settings.gemini_api_key,
                base_url=settings.gemini_base_url,
            )

        # Initialize OpenAI client if key is present or as fallback
        self._openai_client: AsyncOpenAI | None = None
        if getattr(settings, "openai_api_key", ""):
            self._openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
        elif not self._gemini_client and not self._ollama_client:
            # Default placeholder client for offline/mock environments
            self._openai_client = AsyncOpenAI(api_key="sk-placeholder")

        if not is_ollama:
            self.model = settings.gemini_model if self._gemini_client else settings.openai_model

        primary_desc = "ollama" if self._ollama_client else ("gemini" if self._gemini_client else "openai")
        logger.info(
            "llm_provider_initialized",
            primary=primary_desc,
            provider=str(provider_val),
            gemini_model=self.gemini_model,
            openai_model=self.openai_model,
            ollama_model=self.ollama_model,
            fallback_enabled=self.enable_fallback and bool(self._openai_client),
            temperature=self.temperature,
        )

    @retry(
        retry=retry_if_exception_type((APITimeoutError, RateLimitError, InternalServerError)),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=3, max=30),
        reraise=True,
    )
    async def _call_api(
        self,
        client: AsyncOpenAI,
        model: str,
        provider_name: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
        node_name: str = "unknown",
    ) -> str:
        """Execute chat completion call against an OpenAI-compatible client."""
        start_time = time.time()
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature or self.temperature,
            max_tokens=max_tokens or self.max_tokens,
        )

        content = response.choices[0].message.content or ""
        latency_ms = (time.time() - start_time) * 1000

        input_tokens = response.usage.prompt_tokens if response.usage else 0
        output_tokens = response.usage.completion_tokens if response.usage else 0

        self.metrics.record_llm_call(
            node_name=node_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            model=model,
        )

        logger.info(
            "llm_call_completed",
            provider=provider_name,
            node=node_name,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=round(latency_ms, 2),
        )

        return content

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
        node_name: str = "unknown",
    ) -> str:
        """Generate text response: Ollama if configured, else Gemini primary with OpenAI fallback."""
        provider_val = getattr(self.settings, "llm_provider", None)
        is_ollama = (
            provider_val == LLMProviderEnum.OLLAMA
            or (isinstance(provider_val, str) and provider_val.lower() == "ollama")
            or (self._ollama_client and not self._gemini_client and not self._openai_client)
        )

        # 1. Ollama (Local LLM Provider)
        if is_ollama:
            if not self._ollama_client:
                base_url = f"{self.ollama_base_url.rstrip('/')}/v1"
                self._ollama_client = AsyncOpenAI(base_url=base_url, api_key="ollama")
            try:
                return await self._call_api(
                    client=self._ollama_client,
                    model=self.ollama_model,
                    provider_name="ollama",
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    node_name=node_name,
                )
            except Exception as e:
                norm_detail = normalize_infrastructure_error(
                    e,
                    stage="generation",
                    provider="ollama",
                    model=self.ollama_model,
                )
                logger.error(
                    "infrastructure_failure",
                    stage="generation",
                    provider="ollama",
                    category=norm_detail.category,
                    status_code=norm_detail.status_code,
                    retryable=norm_detail.retryable,
                    consumes_content_retry=False,
                    error_type=norm_detail.type,
                )
                raise LLMProviderError(norm_detail.message, detail=norm_detail) from e

        # 2. Try Gemini (Primary) if configured
        if self._gemini_client:
            try:
                return await self._call_api(
                    client=self._gemini_client,
                    model=self.gemini_model,
                    provider_name="gemini",
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    node_name=node_name,
                )
            except Exception as e:
                if self._openai_client and self.enable_fallback:
                    logger.warning(
                        "gemini_call_failed_falling_back_to_openai",
                        node=node_name,
                        primary_model=self.gemini_model,
                        fallback_model=self.openai_model,
                        error_type=type(e).__name__,
                    )
                else:
                    norm_detail = normalize_infrastructure_error(
                        e,
                        stage="generation",
                        provider="gemini",
                        model=self.gemini_model,
                    )
                    logger.error(
                        "infrastructure_failure",
                        stage="generation",
                        provider="gemini",
                        category=norm_detail.category,
                        status_code=norm_detail.status_code,
                        retryable=norm_detail.retryable,
                        consumes_content_retry=False,
                        error_type=norm_detail.type,
                    )
                    raise LLMProviderError(norm_detail.message, detail=norm_detail) from e

        # 3. Try OpenAI (Fallback or Primary if Gemini not configured)
        if self._openai_client:
            try:
                return await self._call_api(
                    client=self._openai_client,
                    model=self.openai_model,
                    provider_name="openai_fallback" if self._gemini_client else "openai",
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    node_name=node_name,
                )
            except Exception as e:
                norm_detail = normalize_infrastructure_error(
                    e,
                    stage="generation",
                    provider="openai",
                    model=self.openai_model,
                )
                logger.error(
                    "infrastructure_failure",
                    stage="generation",
                    provider="openai",
                    category=norm_detail.category,
                    status_code=norm_detail.status_code,
                    retryable=norm_detail.retryable,
                    consumes_content_retry=False,
                    error_type=norm_detail.type,
                )
                raise LLMProviderError(norm_detail.message, detail=norm_detail) from e

        norm_detail = InfrastructureErrorDetail(
            category=ErrorCategory.AUTHENTICATION.value,
            message="No LLM client configured (Gemini, OpenAI, or Ollama missing).",
            detail="Configure GEMINI_API_KEY, OPENAI_API_KEY, or set LLM_PROVIDER=ollama.",
            retryable=False,
            consumes_content_retry=False,
            status_code=401,
        )
        raise LLMProviderError(norm_detail.message, detail=norm_detail)

    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        output_model: type[T],
        temperature: float | None = None,
        max_tokens: int | None = None,
        node_name: str = "unknown",
    ) -> T:
        """Generate a structured response and validate against a Pydantic model.

        Supports fallback provider if primary generation or parsing fails.
        """
        schema_instruction = (
            f"\n\nYou MUST respond with valid JSON matching this schema:\n"
            f"```json\n{json.dumps(output_model.model_json_schema(), indent=2)}\n```\n"
            f"Respond with ONLY the JSON object, no additional text."
        )

        full_system_prompt = system_prompt + schema_instruction
        raw_response = await self.generate(
            system_prompt=full_system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            node_name=node_name,
        )

        # Strip markdown code fences if present
        cleaned = raw_response.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        try:
            parsed = json.loads(cleaned, strict=False)
            return output_model.model_validate(parsed)
        except (json.JSONDecodeError, ValidationError) as e:
            # Recovery attempt: extract first JSON object between { and }
            first_brace = cleaned.find("{")
            last_brace = cleaned.rfind("}")
            if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
                try:
                    sub_json = cleaned[first_brace : last_brace + 1]
                    parsed = json.loads(sub_json, strict=False)
                    return output_model.model_validate(parsed)
                except Exception:
                    pass

            # If primary produced malformed output and fallback is available, retry once with fallback
            if self._gemini_client and self._openai_client and self.enable_fallback:
                logger.warning(
                    "primary_json_parse_failed_trying_fallback",
                    node=node_name,
                    error=str(e),
                )
                try:
                    fallback_raw = await self._call_api(
                        client=self._openai_client,
                        model=self.openai_model,
                        provider_name="openai_fallback",
                        system_prompt=full_system_prompt,
                        user_prompt=user_prompt,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        node_name=node_name + "_fallback",
                    )
                    f_cleaned = fallback_raw.strip()
                    if f_cleaned.startswith("```json"):
                        f_cleaned = f_cleaned[7:]
                    if f_cleaned.startswith("```"):
                        f_cleaned = f_cleaned[3:]
                    if f_cleaned.endswith("```"):
                        f_cleaned = f_cleaned[:-3]
                    f_parsed = json.loads(f_cleaned.strip(), strict=False)
                    return output_model.model_validate(f_parsed)
                except Exception as fb_err:
                    logger.error("fallback_structured_output_also_failed", error=str(fb_err))

            logger.error(
                "llm_structured_output_error",
                node=node_name,
                error=str(e),
                raw_response=raw_response[:500],
            )
            raise StructuredOutputError(
                f"Failed to parse LLM response into schema: {e}"
            ) from e
