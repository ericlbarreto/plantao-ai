"""OpenTelemetry setup – exports traces to LangSmith via OTLP/HTTP."""

import logging

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from openinference.instrumentation.agno import AgnoInstrumentor

from app.common.config import settings

logger = logging.getLogger(__name__)


def setup_tracing() -> None:
    """Initialise TracerProvider, OTLP exporter, and Agno instrumentor."""
    if not settings.LANGSMITH_API_KEY:
        logger.warning("LANGSMITH_API_KEY not set – tracing disabled.")
        return

    headers = {
        "x-api-key": settings.LANGSMITH_API_KEY,
        "Langsmith-Project": settings.LANGSMITH_PROJECT,
    }

    provider = TracerProvider()

    # When endpoint is passed explicitly, the SDK uses it as-is (no auto-append).
    # So we must include /v1/traces in the full URL.
    base = settings.OTEL_EXPORTER_OTLP_ENDPOINT.rstrip("/")
    exporter = OTLPSpanExporter(
        endpoint=f"{base}/v1/traces",
        headers=headers,
    )

    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    # Instrument Agno so agent/skill calls show up as spans
    AgnoInstrumentor().instrument()

    logger.info("Tracing configured → LangSmith project '%s'", settings.LANGSMITH_PROJECT)