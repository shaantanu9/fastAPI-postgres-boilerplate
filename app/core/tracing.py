"""
Distributed Tracing Module for FastAPI using OpenTelemetry

This module provides comprehensive distributed tracing capabilities including:
- OpenTelemetry instrumentation for FastAPI, SQLAlchemy, Redis, and HTTP clients
- Jaeger exporter for trace visualization
- Custom span creation and context management
- Performance monitoring and error tracking
- Correlation ID propagation across services

Based on OpenTelemetry best practices and enterprise monitoring requirements.
"""

import logging
import os
import uuid
from contextlib import contextmanager
from typing import Any, Dict, Optional, Union

try:
    from opentelemetry import trace
    from opentelemetry.exporter.jaeger.thrift import JaegerExporter
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    from opentelemetry.instrumentation.logging import LoggingInstrumentor
    from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
    from opentelemetry.instrumentation.redis import RedisInstrumentor
    from opentelemetry.instrumentation.requests import RequestsInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    from opentelemetry.propagate import inject, extract
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    from opentelemetry.trace import Status, StatusCode
    from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
    
    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    OPENTELEMETRY_AVAILABLE = False

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Global tracer instance
tracer: Optional[Any] = None
propagator = None

if OPENTELEMETRY_AVAILABLE:
    propagator = TraceContextTextMapPropagator()


class TracingManager:
    """
    Centralized tracing management for the FastAPI application.
    
    Handles OpenTelemetry setup, instrumentation, and trace context management.
    """
    
    def __init__(self):
        self.tracer_provider: Optional[Any] = None
        self.tracer: Optional[Any] = None
        self.is_initialized = False
        
    def initialize(self) -> None:
        """Initialize OpenTelemetry tracing with configured exporters."""
        if not OPENTELEMETRY_AVAILABLE:
            logger.warning("OpenTelemetry not available - tracing disabled")
            return
            
        if self.is_initialized:
            logger.warning("Tracing already initialized")
            return
            
        if not settings.TRACING_ENABLED:
            logger.info("Tracing disabled in configuration")
            return
            
        try:
            # Create resource with service information
            resource = Resource.create({
                "service.name": settings.OTEL_SERVICE_NAME,
                "service.version": settings.OTEL_SERVICE_VERSION,
                "service.environment": settings.OTEL_ENVIRONMENT,
                "service.instance.id": str(uuid.uuid4()),
            })
            
            # Create tracer provider
            self.tracer_provider = TracerProvider(resource=resource)
            trace.set_tracer_provider(self.tracer_provider)
            
            # Configure exporters
            self._setup_exporters()
            
            # Setup automatic instrumentation
            self._setup_instrumentation()
            
            # Create tracer instance
            self.tracer = trace.get_tracer(__name__)
            global tracer
            tracer = self.tracer
            
            self.is_initialized = True
            
            logger.info(
                "Distributed tracing initialized successfully",
                extra={
                    "service_name": settings.OTEL_SERVICE_NAME,
                    "service_version": settings.OTEL_SERVICE_VERSION,
                    "environment": settings.OTEL_ENVIRONMENT,
                    "jaeger_endpoint": settings.JAEGER_COLLECTOR_ENDPOINT,
                    "sampling_rate": settings.OTEL_TRACES_SAMPLER_ARG
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to initialize tracing: {e}", exc_info=True)
            
    def _setup_exporters(self) -> None:
        """Setup trace exporters (Jaeger, OTLP, Console)."""
        if not self.tracer_provider:
            return
            
        # Jaeger exporter
        try:
            jaeger_exporter = JaegerExporter(
                agent_host_name=settings.JAEGER_AGENT_HOST,
                agent_port=settings.JAEGER_AGENT_PORT,
                collector_endpoint=settings.JAEGER_COLLECTOR_ENDPOINT,
            )
            self.tracer_provider.add_span_processor(
                BatchSpanProcessor(jaeger_exporter)
            )
            logger.info("Jaeger exporter configured")
        except Exception as e:
            logger.warning(f"Failed to setup Jaeger exporter: {e}")
            
        # OTLP exporter (if configured)
        if settings.OTEL_EXPORTER_OTLP_ENDPOINT:
            try:
                otlp_exporter = OTLPSpanExporter(
                    endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
                    headers=self._parse_headers(settings.OTEL_EXPORTER_OTLP_HEADERS)
                )
                self.tracer_provider.add_span_processor(
                    BatchSpanProcessor(otlp_exporter)
                )
                logger.info("OTLP exporter configured")
            except Exception as e:
                logger.warning(f"Failed to setup OTLP exporter: {e}")
                
        # Console exporter for development
        if settings.ENVIRONMENT == "development":
            console_exporter = ConsoleSpanExporter()
            self.tracer_provider.add_span_processor(
                BatchSpanProcessor(console_exporter)
            )
            logger.info("Console exporter configured for development")
            
    def _setup_instrumentation(self) -> None:
        """Setup automatic instrumentation for common libraries."""
        try:
            # FastAPI instrumentation
            FastAPIInstrumentor.instrument()
            logger.debug("FastAPI instrumentation enabled")
            
            # HTTP client instrumentation
            RequestsInstrumentor().instrument()
            HTTPXClientInstrumentor().instrument()
            logger.debug("HTTP client instrumentation enabled")
            
            # Database instrumentation
            SQLAlchemyInstrumentor().instrument()
            Psycopg2Instrumentor().instrument()
            logger.debug("Database instrumentation enabled")
            
            # Redis instrumentation
            RedisInstrumentor().instrument()
            logger.debug("Redis instrumentation enabled")
            
            # Logging instrumentation
            LoggingInstrumentor().instrument()
            logger.debug("Logging instrumentation enabled")
            
        except Exception as e:
            logger.warning(f"Some instrumentations failed: {e}")
            
    def _parse_headers(self, headers_str: str) -> Dict[str, str]:
        """Parse OTLP headers from string format."""
        headers = {}
        if headers_str:
            for header in headers_str.split(","):
                if "=" in header:
                    key, value = header.split("=", 1)
                    headers[key.strip()] = value.strip()
        return headers
        
    def shutdown(self) -> None:
        """Shutdown tracing and flush remaining spans."""
        if self.tracer_provider:
            self.tracer_provider.shutdown()
            logger.info("Tracing shutdown completed")


# Global tracing manager instance
tracing_manager = TracingManager()


def initialize_tracing() -> None:
    """Initialize distributed tracing for the application."""
    tracing_manager.initialize()


def shutdown_tracing() -> None:
    """Shutdown distributed tracing."""
    tracing_manager.shutdown()


def get_tracer() -> Optional[Any]:
    """Get the current tracer instance."""
    return tracing_manager.tracer


@contextmanager
def trace_operation(
    operation_name: str,
    attributes: Optional[Dict[str, Any]] = None,
    set_status_on_exception: bool = True
):
    """
    Context manager for tracing operations.
    
    Args:
        operation_name: Name of the operation being traced
        attributes: Additional attributes to add to the span
        set_status_on_exception: Whether to set error status on exceptions
    
    Example:
        with trace_operation("database_query", {"table": "users"}):
            # Your operation here
            pass
    """
    if not tracer or not OPENTELEMETRY_AVAILABLE:
        yield None
        return
        
    with tracer.start_as_current_span(operation_name) as span:
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)
                
        try:
            yield span
        except Exception as e:
            if set_status_on_exception:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
            raise


def add_span_attributes(attributes: Dict[str, Any]) -> None:
    """Add attributes to the current span."""
    if not OPENTELEMETRY_AVAILABLE:
        return
        
    current_span = trace.get_current_span()
    if current_span and current_span.is_recording():
        for key, value in attributes.items():
            current_span.set_attribute(key, value)


def add_span_event(name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
    """Add an event to the current span."""
    if not OPENTELEMETRY_AVAILABLE:
        return
        
    current_span = trace.get_current_span()
    if current_span and current_span.is_recording():
        current_span.add_event(name, attributes or {})


def set_span_status(status_code: Any, description: Optional[str] = None) -> None:
    """Set the status of the current span."""
    if not OPENTELEMETRY_AVAILABLE:
        return
        
    current_span = trace.get_current_span()
    if current_span and current_span.is_recording():
        current_span.set_status(Status(status_code, description))


def record_exception(exception: Exception) -> None:
    """Record an exception in the current span."""
    if not OPENTELEMETRY_AVAILABLE:
        return
        
    current_span = trace.get_current_span()
    if current_span and current_span.is_recording():
        current_span.record_exception(exception)
        current_span.set_status(Status(StatusCode.ERROR, str(exception)))


def inject_trace_context(carrier: Dict[str, str]) -> None:
    """Inject trace context into a carrier (e.g., HTTP headers)."""
    if OPENTELEMETRY_AVAILABLE:
        inject(carrier)


def extract_trace_context(carrier: Dict[str, str]) -> Any:
    """Extract trace context from a carrier."""
    if OPENTELEMETRY_AVAILABLE:
        return extract(carrier)
    return None


class TracingMiddleware:
    """
    Middleware for enhanced tracing with correlation ID support.
    
    This middleware adds correlation IDs and additional context to traces.
    """
    
    def __init__(self, app):
        self.app = app
        
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
            
        if not OPENTELEMETRY_AVAILABLE or not tracer:
            await self.app(scope, receive, send)
            return
            
        # Extract or generate correlation ID
        headers = dict(scope.get("headers", []))
        correlation_id = self._get_correlation_id(headers)
        
        # Add correlation ID to span
        with tracer.start_as_current_span("http_request") as span:
            span.set_attribute("http.correlation_id", correlation_id)
            span.set_attribute("http.method", scope.get("method", ""))
            span.set_attribute("http.url", self._build_url(scope))
            
            # Store correlation ID in scope for other middleware
            scope["correlation_id"] = correlation_id
            
            await self.app(scope, receive, send)
            
    def _get_correlation_id(self, headers: Dict[bytes, bytes]) -> str:
        """Extract or generate correlation ID from headers."""
        # Try to get from headers
        for header_name in [b"x-correlation-id", b"x-request-id", b"correlation-id"]:
            if header_name in headers:
                return headers[header_name].decode("utf-8")
                
        # Generate new correlation ID
        return str(uuid.uuid4())
        
    def _build_url(self, scope: Dict[str, Any]) -> str:
        """Build URL from ASGI scope."""
        scheme = scope.get("scheme", "http")
        server = scope.get("server", ("localhost", 80))
        path = scope.get("path", "/")
        query_string = scope.get("query_string", b"").decode("utf-8")
        
        url = f"{scheme}://{server[0]}:{server[1]}{path}"
        if query_string:
            url += f"?{query_string}"
            
        return url


# Decorator for tracing functions
def trace_function(operation_name: Optional[str] = None, attributes: Optional[Dict[str, Any]] = None):
    """
    Decorator for tracing function calls.
    
    Args:
        operation_name: Custom operation name (defaults to function name)
        attributes: Additional attributes to add to the span
    
    Example:
        @trace_function("user_creation", {"component": "auth"})
        def create_user(user_data):
            # Function implementation
            pass
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            name = operation_name or f"{func.__module__}.{func.__name__}"
            with trace_operation(name, attributes):
                return func(*args, **kwargs)
        return wrapper
    return decorator


# Async decorator for tracing async functions
def trace_async_function(operation_name: Optional[str] = None, attributes: Optional[Dict[str, Any]] = None):
    """
    Decorator for tracing async function calls.
    
    Args:
        operation_name: Custom operation name (defaults to function name)
        attributes: Additional attributes to add to the span
    
    Example:
        @trace_async_function("async_user_creation", {"component": "auth"})
        async def create_user_async(user_data):
            # Async function implementation
            pass
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            name = operation_name or f"{func.__module__}.{func.__name__}"
            with trace_operation(name, attributes):
                return await func(*args, **kwargs)
        return wrapper
    return decorator


# Utility functions for common tracing patterns
def trace_database_operation(table_name: str, operation: str):
    """Create a span for database operations."""
    return trace_operation(
        f"db.{operation}",
        {
            "db.table": table_name,
            "db.operation": operation,
            "component": "database"
        }
    )


def trace_external_api_call(service_name: str, endpoint: str):
    """Create a span for external API calls."""
    return trace_operation(
        f"external_api.{service_name}",
        {
            "external.service": service_name,
            "external.endpoint": endpoint,
            "component": "external_api"
        }
    )


def trace_business_logic(operation_name: str, **attributes):
    """Create a span for business logic operations."""
    return trace_operation(
        f"business.{operation_name}",
        {
            "component": "business_logic",
            **attributes
        }
    ) 