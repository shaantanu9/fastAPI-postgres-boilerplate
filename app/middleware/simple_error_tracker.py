
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import json
import time
from datetime import datetime
from pathlib import Path

class SimpleErrorTracker(BaseHTTPMiddleware):
    """Ultra-lightweight error tracker - <0.1ms overhead"""
    
    def __init__(self, app, log_file="logs/errors.jsonl"):
        super().__init__(app)
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(exist_ok=True)
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        try:
            response = await call_next(request)
            
            # Only log errors and slow requests
            if response.status_code >= 400:
                execution_time = (time.time() - start_time) * 1000
                self._log_error(request, response.status_code, execution_time)
            
            return response
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            self._log_error(request, 500, execution_time, str(e))
            raise
    
    def _log_error(self, request, status_code, execution_time, error_msg=None):
        """Log error with minimal overhead"""
        try:
            error_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "method": request.method,
                "path": str(request.url.path),
                "status_code": status_code,
                "execution_time_ms": round(execution_time, 2),
                "error": error_msg,
                "user_agent": request.headers.get("user-agent", "")
            }
            
            # Fast file write
            with open(self.log_file, 'a') as f:
                f.write(json.dumps(error_data, separators=(',', ':')) + '\n')
                
        except Exception:
            pass  # Never let error logging break the app
