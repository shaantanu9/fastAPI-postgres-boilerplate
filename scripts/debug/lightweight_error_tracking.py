#!/usr/bin/env python3
"""
Lightweight Error Tracking System
Alternative to Sentry for performance-critical applications

This provides:
- Minimal overhead error tracking
- Local file-based error storage
- Optional webhook notifications
- Performance metrics
- Zero external dependencies
"""

import asyncio
import json
import traceback
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
import hashlib
import logging
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ErrorEvent:
    """Lightweight error event structure"""
    timestamp: str
    error_type: str
    error_message: str
    error_hash: str
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None
    status_code: Optional[int] = None
    execution_time_ms: Optional[float] = None
    stack_trace: Optional[str] = None
    environment: str = "production"
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class LightweightErrorTracker:
    """
    Ultra-lightweight error tracker with minimal overhead
    
    Features:
    - File-based storage (no network calls during error)
    - Asynchronous processing
    - Error deduplication
    - Configurable sampling
    - Performance metrics
    """
    
    def __init__(
        self,
        error_log_path: str = "logs/errors.jsonl",
        sample_rate: float = 1.0,  # Track 100% of errors by default
        max_stack_trace_lines: int = 20,
        enable_webhook: bool = False,
        webhook_url: Optional[str] = None,
        webhook_timeout: float = 2.0
    ):
        self.error_log_path = Path(error_log_path)
        self.sample_rate = sample_rate
        self.max_stack_trace_lines = max_stack_trace_lines
        self.enable_webhook = enable_webhook
        self.webhook_url = webhook_url
        self.webhook_timeout = webhook_timeout
        
        # Create logs directory
        self.error_log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Performance metrics
        self.total_errors = 0
        self.errors_tracked = 0
        self.avg_processing_time = 0.0
        
        # Error deduplication cache
        self.error_cache: Dict[str, int] = {}
        self.cache_max_size = 1000
        
    def _generate_error_hash(self, error_type: str, error_message: str, endpoint: str = "") -> str:
        """Generate hash for error deduplication"""
        content = f"{error_type}:{error_message}:{endpoint}"
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def _should_sample(self) -> bool:
        """Determine if this error should be tracked based on sample rate"""
        import random
        return random.random() < self.sample_rate
    
    def _truncate_stack_trace(self, stack_trace: str) -> str:
        """Truncate stack trace to reduce overhead"""
        lines = stack_trace.split('\n')
        if len(lines) <= self.max_stack_trace_lines:
            return stack_trace
        return '\n'.join(lines[:self.max_stack_trace_lines]) + f"\n... truncated ({len(lines) - self.max_stack_trace_lines} more lines)"
    
    async def track_error(
        self,
        error: Exception,
        request_id: Optional[str] = None,
        user_id: Optional[str] = None,
        endpoint: Optional[str] = None,
        method: Optional[str] = None,
        status_code: Optional[int] = None,
        execution_time_ms: Optional[float] = None,
        extra_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Track an error with minimal overhead
        
        This method is designed to be fast and non-blocking
        """
        start_time = time.perf_counter()
        
        try:
            self.total_errors += 1
            
            # Sample check - skip if not selected
            if not self._should_sample():
                return
            
            # Generate error details
            error_type = type(error).__name__
            error_message = str(error)
            error_hash = self._generate_error_hash(error_type, error_message, endpoint or "")
            
            # Check for duplicate errors (simple deduplication)
            if error_hash in self.error_cache:
                self.error_cache[error_hash] += 1
                # Only log every 10th occurrence of the same error
                if self.error_cache[error_hash] % 10 != 0:
                    return
            else:
                self.error_cache[error_hash] = 1
                # Clean cache if it gets too large
                if len(self.error_cache) > self.cache_max_size:
                    # Remove oldest entries (simple LRU-like behavior)
                    keys_to_remove = list(self.error_cache.keys())[:100]
                    for key in keys_to_remove:
                        del self.error_cache[key]
            
            # Create error event
            error_event = ErrorEvent(
                timestamp=datetime.utcnow().isoformat(),
                error_type=error_type,
                error_message=error_message,
                error_hash=error_hash,
                request_id=request_id,
                user_id=user_id,
                endpoint=endpoint,
                method=method,
                status_code=status_code,
                execution_time_ms=execution_time_ms,
                stack_trace=self._truncate_stack_trace(traceback.format_exc())
            )
            
            # Write to file (fast, non-blocking)
            await self._write_error_to_file(error_event)
            
            # Optional webhook notification (async, non-blocking)
            if self.enable_webhook and self.webhook_url:
                asyncio.create_task(self._send_webhook_notification(error_event))
            
            self.errors_tracked += 1
            
        except Exception as tracking_error:
            # Never let error tracking break the application
            logger.error(f"Error in error tracking: {tracking_error}")
        
        finally:
            # Update performance metrics
            processing_time = (time.perf_counter() - start_time) * 1000
            self.avg_processing_time = (
                (self.avg_processing_time * (self.errors_tracked - 1) + processing_time) / 
                self.errors_tracked if self.errors_tracked > 0 else processing_time
            )
    
    async def _write_error_to_file(self, error_event: ErrorEvent) -> None:
        """Write error to file asynchronously"""
        try:
            error_json = json.dumps(error_event.to_dict(), separators=(',', ':'))
            
            # Use async file writing for better performance
            import aiofiles
            async with aiofiles.open(self.error_log_path, 'a') as f:
                await f.write(error_json + '\n')
                
        except Exception as e:
            # Fallback to synchronous writing
            with open(self.error_log_path, 'a') as f:
                f.write(json.dumps(error_event.to_dict()) + '\n')
    
    async def _send_webhook_notification(self, error_event: ErrorEvent) -> None:
        """Send webhook notification (async, fire-and-forget)"""
        try:
            import aiohttp
            
            payload = {
                "error_type": error_event.error_type,
                "error_message": error_event.error_message,
                "timestamp": error_event.timestamp,
                "endpoint": error_event.endpoint,
                "error_hash": error_event.error_hash,
                "occurrence_count": self.error_cache.get(error_event.error_hash, 1)
            }
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.webhook_timeout)) as session:
                await session.post(self.webhook_url, json=payload)
                
        except Exception as e:
            logger.error(f"Webhook notification failed: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get error tracking statistics"""
        return {
            "total_errors": self.total_errors,
            "errors_tracked": self.errors_tracked,
            "sampling_rate": self.sample_rate,
            "avg_processing_time_ms": round(self.avg_processing_time, 2),
            "unique_errors": len(self.error_cache),
            "most_common_errors": sorted(
                [(k, v) for k, v in self.error_cache.items()], 
                key=lambda x: x[1], 
                reverse=True
            )[:10]
        }

# Global error tracker instance
error_tracker: Optional[LightweightErrorTracker] = None

def initialize_error_tracking(
    error_log_path: str = "logs/errors.jsonl",
    sample_rate: float = 1.0,
    enable_webhook: bool = False,
    webhook_url: Optional[str] = None
) -> None:
    """Initialize global error tracker"""
    global error_tracker
    error_tracker = LightweightErrorTracker(
        error_log_path=error_log_path,
        sample_rate=sample_rate,
        enable_webhook=enable_webhook,
        webhook_url=webhook_url
    )

async def track_error(
    error: Exception,
    request_id: Optional[str] = None,
    user_id: Optional[str] = None,
    endpoint: Optional[str] = None,
    method: Optional[str] = None,
    status_code: Optional[int] = None,
    execution_time_ms: Optional[float] = None
) -> None:
    """Global error tracking function"""
    if error_tracker:
        await error_tracker.track_error(
            error=error,
            request_id=request_id,
            user_id=user_id,
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            execution_time_ms=execution_time_ms
        )

@asynccontextmanager
async def error_tracking_context(
    request_id: Optional[str] = None,
    user_id: Optional[str] = None,
    endpoint: Optional[str] = None,
    method: Optional[str] = None
):
    """Context manager for automatic error tracking"""
    start_time = time.perf_counter()
    try:
        yield
    except Exception as e:
        execution_time = (time.perf_counter() - start_time) * 1000
        await track_error(
            error=e,
            request_id=request_id,
            user_id=user_id,
            endpoint=endpoint,
            method=method,
            execution_time_ms=execution_time
        )
        raise

# FastAPI middleware integration
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import uuid

class LightweightErrorMiddleware(BaseHTTPMiddleware):
    """Ultra-lightweight error tracking middleware for FastAPI"""
    
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        start_time = time.perf_counter()
        
        try:
            response = await call_next(request)
            return response
            
        except Exception as e:
            execution_time = (time.perf_counter() - start_time) * 1000
            
            # Extract user ID if available
            user_id = getattr(request.state, 'user_id', None)
            
            await track_error(
                error=e,
                request_id=request_id,
                user_id=user_id,
                endpoint=str(request.url.path),
                method=request.method,
                execution_time_ms=execution_time
            )
            
            raise

# Usage example for FastAPI
"""
from fastapi import FastAPI
from lightweight_error_tracking import initialize_error_tracking, LightweightErrorMiddleware

app = FastAPI()

# Initialize lightweight error tracking
initialize_error_tracking(
    error_log_path="logs/errors.jsonl",
    sample_rate=1.0,  # Track all errors
    enable_webhook=True,
    webhook_url="https://your-slack-webhook.com/webhook"
)

# Add middleware
app.add_middleware(LightweightErrorMiddleware)

@app.get("/health")
async def health_check():
    if error_tracker:
        stats = error_tracker.get_stats()
        return {"status": "healthy", "error_tracking": stats}
    return {"status": "healthy"}
"""

if __name__ == "__main__":
    # Example usage
    async def main():
        initialize_error_tracking(sample_rate=0.1)  # Sample 10% of errors
        
        try:
            raise ValueError("Test error")
        except Exception as e:
            await track_error(e, endpoint="/test", method="GET")
        
        print("Error tracking stats:", error_tracker.get_stats())
    
    asyncio.run(main()) 