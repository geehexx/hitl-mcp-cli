"""OpenTelemetry distributed tracing for coordination system."""

import logging
from contextlib import asynccontextmanager
from typing import Any

try:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    trace = None

logger = logging.getLogger(__name__)


class TracingManager:
    """Manage OpenTelemetry tracing for coordination system."""

    def __init__(self, service_name: str = "hitl-mcp-coordination", otlp_endpoint: str | None = None):
        """Initialize tracing manager.

        Args:
            service_name: Service name for traces
            otlp_endpoint: OTLP collector endpoint (e.g., "localhost:4317")
        """
        self.service_name = service_name
        self.otlp_endpoint = otlp_endpoint
        self.tracer_provider: Any = None
        self.tracer: Any = None
        self.enabled = False

        if OTEL_AVAILABLE and otlp_endpoint:
            self._setup_tracing()

    def _setup_tracing(self):
        """Setup OpenTelemetry tracing."""
        try:
            # Create resource with service info
            resource = Resource.create({"service.name": self.service_name})

            # Create tracer provider
            self.tracer_provider = TracerProvider(resource=resource)

            # Create OTLP exporter
            otlp_exporter = OTLPSpanExporter(endpoint=self.otlp_endpoint, insecure=True)

            # Add batch processor
            span_processor = BatchSpanProcessor(otlp_exporter)
            self.tracer_provider.add_span_processor(span_processor)

            # Set global tracer provider
            trace.set_tracer_provider(self.tracer_provider)

            # Get tracer
            self.tracer = trace.get_tracer(__name__)

            self.enabled = True
            logger.info(f"OpenTelemetry tracing enabled, exporting to {self.otlp_endpoint}")

        except Exception as e:
            logger.warning(f"Failed to setup tracing: {e}")
            self.enabled = False

    @asynccontextmanager
    async def trace_operation(self, operation_name: str, attributes: dict[str, Any] | None = None):
        """Trace an async operation.

        Args:
            operation_name: Name of operation
            attributes: Span attributes

        Yields:
            Span context
        """
        if not self.enabled or not self.tracer:
            yield None
            return

        with self.tracer.start_as_current_span(operation_name) as span:
            if attributes:
                for key, value in attributes.items():
                    span.set_attribute(key, value)
            yield span

    def trace_sync(self, operation_name: str, attributes: dict[str, Any] | None = None):
        """Trace a synchronous operation (context manager).

        Args:
            operation_name: Name of operation
            attributes: Span attributes

        Returns:
            Context manager
        """
        if not self.enabled or not self.tracer:
            # Return dummy context manager
            class DummyContext:
                def __enter__(self):
                    return None

                def __exit__(self, *args):
                    pass

            return DummyContext()

        span = self.tracer.start_as_current_span(operation_name)
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)
        return span

    def shutdown(self):
        """Shutdown tracer provider."""
        if self.tracer_provider:
            self.tracer_provider.shutdown()
            logger.info("Tracing shutdown complete")


# Singleton instance
_tracing_manager: TracingManager | None = None


def get_tracing_manager() -> TracingManager | None:
    """Get global tracing manager instance."""
    return _tracing_manager


def init_tracing(service_name: str = "hitl-mcp-coordination", otlp_endpoint: str | None = None) -> TracingManager:
    """Initialize global tracing manager.

    Args:
        service_name: Service name
        otlp_endpoint: OTLP collector endpoint

    Returns:
        TracingManager instance
    """
    global _tracing_manager

    if _tracing_manager is None:
        _tracing_manager = TracingManager(service_name, otlp_endpoint)

    return _tracing_manager
