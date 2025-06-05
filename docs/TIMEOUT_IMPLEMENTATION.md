# Request Timeout Implementation

This document outlines the implementation of request timeouts in our FastAPI application, following industry best practices for reliability and performance.

## Overview

We've implemented a multi-layered timeout strategy that includes:

1. **Global Request Timeout**: A default timeout applied to all requests
2. **Endpoint-Specific Timeouts**: Custom timeouts for specific routes
3. **Database Operation Timeouts**: Timeouts for database queries
4. **External Service Timeouts**: Timeouts for calls to external APIs

## Implementation Details

### 1. Global Request Timeout

- **Location**: `app/middleware/timeout_middleware.py`
- **Default**: 30 seconds
- **Purpose**: Ensures no request can run indefinitely

### 2. Endpoint-Specific Timeouts

Use the `@with_timeout` decorator to set custom timeouts:

```python
from app.core.timeouts import with_timeout, Timeouts

@app.get("/api/process-data")
@with_timeout(timeout_seconds=10.0)
async def process_data():
    # Your code here
    pass
```

### 3. Database Operation Timeouts

Use the `database_timeout_context` for database operations:

```python
from app.core.timeouts import database_timeout_context

async def get_data():
    async with database_timeout_context(5.0):  # 5 second timeout
        result = await db.execute(query)
        return result
```

## Configuration

### Timeout Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `GLOBAL_REQUEST_TIMEOUT` | 30.0s | Global request timeout |
| `DATABASE_TIMEOUT` | 10.0s | Database operations |
| `EXTERNAL_API_TIMEOUT` | 15.0s | External API calls |
| `HEAVY_COMPUTATION_TIMEOUT` | 60.0s | Heavy computations |

## Best Practices

1. **Be Specific**: Set appropriate timeouts for each operation type
2. **Fail Fast**: Use shorter timeouts for health checks
3. **Monitor**: Log timeout occurrences for analysis
4. **Document**: Document timeout expectations in your API docs

## Testing Timeouts

Test timeouts using the example endpoints:

```bash
# Test the global timeout (30s)
curl http://localhost:8000/api/process-data

# Test the slow operation (60s timeout)
curl http://localhost:8000/api/slow-operation
```

## Monitoring and Logging

Timeout events are logged with detailed context:

- Request path and method
- Timeout duration
- Process time
- Stack traces for debugging

## Performance Considerations

- **Resource Cleanup**: Timeouts ensure resources are released promptly
- **Circuit Breaking**: Works with rate limiting to prevent cascading failures
- **Graceful Degradation**: Fails gracefully when timeouts occur

## Troubleshooting

Common issues and solutions:

1. **Premature Timeouts**:
   - Check for blocking operations in async code
   - Verify database connection pool settings

2. **No Timeout Errors**:
   - Ensure middleware is properly registered
   - Check for exception handlers that might be swallowing errors

3. **Inconsistent Behavior**:
   - Verify timeout values are being set correctly
   - Check for conflicting middleware
