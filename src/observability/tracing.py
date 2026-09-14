"""Tracing integration for LangSmith and OpenTelemetry.

Tracing is optional and controlled via environment configuration.
When disabled, all tracing operations are no-ops.
"""

from contextlib import contextmanager
from datetime import datetime
from typing import Any, Generator
from dataclasses import dataclass, field

from src.observability import get_logger

logger = get_logger(__name__)


@dataclass
class SpanData:
    """Lightweight span data for tracing."""

    name: str
    attributes: dict[str, Any] = field(default_factory=dict)
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: datetime | None = None
    status: str = "ok"
    error: str | None = None


class TracingManager:
    """Manages distributed tracing with optional LangSmith/OTel backends."""

    def __init__(self, enabled: bool = False) -> None:
        self.enabled = enabled
        self._spans: list[SpanData] = []

    @contextmanager
    def span(
        self,
        name: str,
        attributes: dict[str, Any] | None = None,
    ) -> Generator[SpanData, None, None]:
        """Create a tracing span. No-op if tracing is disabled."""
        span_data = SpanData(name=name, attributes=attributes or {})

        if self.enabled:
            logger.info("trace_span_start", span_name=name, attributes=attributes)

        try:
            yield span_data
        except Exception as e:
            span_data.status = "error"
            span_data.error = str(e)
            raise
        finally:
            span_data.end_time = datetime.utcnow()
            self._spans.append(span_data)
            if self.enabled:
                duration_ms = (
                    (span_data.end_time - span_data.start_time).total_seconds() * 1000
                )
                logger.info(
                    "trace_span_end",
                    span_name=name,
                    status=span_data.status,
                    duration_ms=round(duration_ms, 2),
                )

    def get_spans(self) -> list[SpanData]:
        """Return collected spans for inspection."""
        return list(self._spans)


@dataclass
class MetricsCollector:
    """Collects latency, token usage, and cost metrics per run."""

    total_llm_calls: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_embedding_calls: int = 0
    total_retrieval_calls: int = 0
    estimated_cost_usd: float = 0.0
    latencies_ms: dict[str, float] = field(default_factory=dict)

    def record_llm_call(
        self,
        node_name: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: float,
        model: str = "gpt-4o",
    ) -> None:
        """Record an LLM API call with token usage and latency."""
        self.total_llm_calls += 1
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.latencies_ms[f"llm_{node_name}"] = latency_ms

        # Cost estimation (approximate, for observability only)
        cost_per_input = {"gpt-4o": 2.50, "gpt-4o-mini": 0.15}.get(model, 2.50)
        cost_per_output = {"gpt-4o": 10.00, "gpt-4o-mini": 0.60}.get(model, 10.00)
        self.estimated_cost_usd += (
            (input_tokens / 1_000_000) * cost_per_input
            + (output_tokens / 1_000_000) * cost_per_output
        )

    def record_embedding_call(self, num_texts: int, latency_ms: float) -> None:
        """Record an embedding API call."""
        self.total_embedding_calls += 1
        self.latencies_ms[f"embedding_{self.total_embedding_calls}"] = latency_ms

    def record_retrieval(self, latency_ms: float) -> None:
        """Record a retrieval operation."""
        self.total_retrieval_calls += 1
        self.latencies_ms[f"retrieval_{self.total_retrieval_calls}"] = latency_ms

    def to_dict(self) -> dict[str, Any]:
        """Export metrics as a dictionary."""
        return {
            "total_llm_calls": self.total_llm_calls,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_embedding_calls": self.total_embedding_calls,
            "total_retrieval_calls": self.total_retrieval_calls,
            "estimated_cost_usd": round(self.estimated_cost_usd, 6),
            "latencies_ms": self.latencies_ms,
        }
