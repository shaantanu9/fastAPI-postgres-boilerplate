# Rate Limiting Configuration and Debugging Guide

## Overview

Our FastAPI application implements robust rate limiting with Redis backend and in-memory fallback. This guide covers configuration, debugging, and troubleshooting.

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI       │    │  Enhanced       │    │     Redis       │
│   Request       │───▶│  Rate Limiter   │───▶│   (Primary)     │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   In-Memory     │
                       │   Fallback      │
                       │   (Secondary)   │
                       └─────────────────┘
```

## Environment Configuration

### Core Settings

```bash
# Redis Configuration
REDIS_URL=redis://localhost:6379/0                    # Redis connection URL
RATE_LIMIT_REDIS_TIMEOUT=5                           # Redis operation timeout (seconds)
RATE_LIMIT_REDIS_RETRY_ATTEMPTS=3                    # Number of retry attempts
RATE_LIMIT_REDIS_RETRY_DELAY=0.5                     # Delay between retries (seconds)

# Rate Limiting Configuration
RATE_LIMIT_DEFAULT=100/minute                        # Default rate limit
RATE_LIMIT_ENABLE_FALLBACK=true                      # Enable in-memory fallback
RATE_LIMIT_FALLBACK_LIMIT=50                         # Fallback limit per minute
RATE_LIMIT_KEY_PREFIX=rate_limit                     # Redis key prefix
RATE_LIMIT_CLEANUP_INTERVAL=3600                     # Cleanup interval (seconds)
RATE_LIMIT_ENABLE_METRICS=true                       # Enable metrics collection

# Endpoint-Specific Limits
RATE_LIMIT_AUTH_LOGIN=10/minute                      # Login endpoint limit
RATE_LIMIT_AUTH_REGISTER=5/minute                    # Registration limit
RATE_LIMIT_AUTH_FORGOT=3/minute                      # Forgot password limit
RATE_LIMIT_AUTH_RESET=3/minute                       # Reset password limit
RATE_LIMIT_AUTH_REFRESH=20/minute                    # Token refresh limit
RATE_LIMIT_USERS=50/minute                           # User endpoints limit
RATE_LIMIT_ORGS=30/minute                            # Organization endpoints limit
RATE_LIMIT_PUBLIC=200/minute                         # Public endpoints limit
```

### Production Configuration

```bash
# Production Redis (with authentication)
REDIS_URL=redis://username:password@redis-host:6379/0

# Stricter Production Limits
RATE_LIMIT_DEFAULT=50/minute
RATE_LIMIT_AUTH_LOGIN=5/minute
RATE_LIMIT_AUTH_REGISTER=3/minute
RATE_LIMIT_FALLBACK_LIMIT=25

# Production Security
RATE_LIMIT_ENABLE_FALLBACK=false                     # Disable fallback in production
RATE_LIMIT_REDIS_TIMEOUT=3                           # Shorter timeout for production
```

## Rate Limit Formats

### Supported Time Units

- `second` - Per second limits
- `minute` - Per minute limits
- `hour` - Per hour limits
- `day` - Per day limits

### Examples

```bash
# Very strict
RATE_LIMIT_CRITICAL_ENDPOINT=1/second

# Moderate
RATE_LIMIT_API_ENDPOINT=100/minute

# Generous
RATE_LIMIT_PUBLIC_ENDPOINT=1000/hour

# Daily limits
RATE_LIMIT_BULK_OPERATION=100/day
```

## Debugging and Monitoring

### Test Endpoints

The application provides several test endpoints for debugging:

```bash
# Basic rate limiting test (5/minute)
GET /api/v1/test/rate-limit/basic-test

# Enhanced rate limiter test
GET /api/v1/test/rate-limit/enhanced-test

# Strict test (2/minute)
GET /api/v1/test/rate-limit/strict-test

# System status and metrics
GET /api/v1/test/rate-limit/status

# Health check
GET /api/v1/test/rate-limit/health

# Reset rate limits (for testing)
POST /api/v1/test/rate-limit/reset
```

### Status Response Example

```json
{
  "status": "operational",
  "metrics": {
    "total_requests": 150,
    "redis_requests": 145,
    "fallback_requests": 5,
    "errors": 2,
    "rate_limited": 8,
    "redis_healthy": true,
    "fallback_enabled": true,
    "timestamp": 1703123456.789
  },
  "config": {
    "redis_url": "redis://***:***@localhost:6379/0",
    "default_limit": "100/minute",
    "enable_fallback": true,
    "fallback_limit": 50,
    "redis_timeout": 5,
    "enable_metrics": true
  }
}
```

### Rate Limit Response Headers

When rate limited, responses include:

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 45
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1703123501
X-RateLimit-Window: 60

{
  "detail": "Rate limit exceeded",
  "error": "rate_limit_exceeded",
  "error_code": "RATE_LIMIT_EXCEEDED",
  "retry_after": 45,
  "limit": 100,
  "window": 60,
  "endpoint": "/api/v1/auth/login",
  "timestamp": "2023-12-21T10:30:00.000Z",
  "suggestion": "Please wait 45 seconds before making another request to this endpoint"
}
```

## Logging and Monitoring

### Log Levels

```python
# Rate limiting logs at different levels
logger.info("Successfully connected to Redis for rate limiting")
logger.warning("Redis health check failed: Connection timeout")
logger.error("Redis rate limit check failed: RedisConnectionError")
logger.debug("Using fallback rate limiting for key: rate_limit:192.168.1.100:GET:/api/v1/users")
```

### Key Log Messages

```bash
# Successful initialization
✅ Enhanced rate limiting initialized successfully

# Redis connection issues
⚠️ Failed to connect to Redis (attempt 1/3): Connection timeout
❌ Redis health check failed: Connection refused

# Rate limit events
⚠️ Rate limit exceeded - IP: 192.168.1.100, Endpoint: POST /api/v1/auth/login, Retry after: 45s

# Fallback usage
⚠️ Using fallback rate limiting for key: rate_limit:192.168.1.100:GET:/api/v1/users
```

## Troubleshooting

### Common Issues

#### 1. Redis Connection Failed

**Symptoms:**

- All requests use fallback rate limiting
- Logs show Redis connection errors

**Solutions:**

```bash
# Check Redis is running
redis-cli ping

# Check Redis URL
echo $REDIS_URL

# Test Redis connection
redis-cli -u $REDIS_URL ping

# Check firewall/network
telnet redis-host 6379
```

#### 2. Rate Limits Too Strict

**Symptoms:**

- Legitimate users getting rate limited
- Many 429 responses in logs

**Solutions:**

```bash
# Increase limits temporarily
export RATE_LIMIT_DEFAULT=200/minute
export RATE_LIMIT_AUTH_LOGIN=20/minute

# Reset specific IP (testing only)
curl -X POST http://localhost:8000/api/v1/test/rate-limit/reset
```

#### 3. Memory Usage Growing (Fallback Mode)

**Symptoms:**

- Application memory usage increasing
- Running without Redis for extended periods

**Solutions:**

```bash
# Enable Redis to reduce memory usage
# Or adjust cleanup interval
export RATE_LIMIT_CLEANUP_INTERVAL=1800  # 30 minutes

# Monitor fallback metrics
curl http://localhost:8000/api/v1/test/rate-limit/status
```

#### 4. Inconsistent Rate Limiting

**Symptoms:**

- Some requests not rate limited
- Inconsistent behavior across instances

**Solutions:**

```bash
# Ensure all instances use same Redis
export REDIS_URL=redis://shared-redis:6379/0

# Check Redis key consistency
redis-cli keys "rate_limit:*"

# Verify configuration consistency
curl http://localhost:8000/api/v1/test/rate-limit/status
```

### Debug Mode

Enable debug logging for detailed rate limiting information:

```bash
export LOG_LEVEL=DEBUG

# Or in Python
import logging
logging.getLogger('app.core.rate_limiting').setLevel(logging.DEBUG)
```

### Production Monitoring

#### Metrics to Monitor

1. **Rate Limiting Metrics:**

   - `total_requests` - Total rate limit checks
   - `redis_requests` - Requests handled by Redis
   - `fallback_requests` - Requests handled by fallback
   - `errors` - Rate limiting errors
   - `rate_limited` - Number of rate limited requests

2. **Redis Health:**

   - `redis_healthy` - Redis connection status
   - Redis connection latency
   - Redis memory usage

3. **Application Health:**
   - 429 response rate
   - Response time impact
   - Memory usage (when using fallback)

#### Alerting Rules

```yaml
# High rate limit usage
- alert: HighRateLimitUsage
  expr: rate_limit_exceeded_total > 100
  for: 5m

# Redis connectivity issues
- alert: RedisConnectionFailed
  expr: redis_healthy == 0
  for: 1m

# High fallback usage
- alert: HighFallbackUsage
  expr: fallback_requests_ratio > 0.5
  for: 10m
```

## Security Considerations

### IP Spoofing Protection

The rate limiter handles `X-Forwarded-For` headers properly:

```python
# Handles proxy chains
client_ip = request.headers.get("x-forwarded-for")
if client_ip:
    client_ip = client_ip.split(",")[0].strip()  # Take first IP
```

### Rate Limit Bypass Prevention

1. **Key Generation:** Includes IP, method, and endpoint
2. **Atomic Operations:** Uses Redis pipelines for consistency
3. **Fallback Security:** In-memory fallback has same limits
4. **Error Handling:** Fails open but logs security events

### DDoS Protection

1. **Multiple Layers:** Different limits for different endpoints
2. **Progressive Limits:** Stricter limits for sensitive endpoints
3. **Automatic Cleanup:** Removes old entries to prevent memory attacks
4. **Health Monitoring:** Alerts on unusual patterns

## Performance Optimization

### Redis Optimization

```bash
# Redis configuration for rate limiting
maxmemory 256mb
maxmemory-policy allkeys-lru
tcp-keepalive 60
timeout 300
```

### Application Optimization

1. **Connection Pooling:** Reuse Redis connections
2. **Health Check Caching:** Avoid frequent Redis pings
3. **Pipeline Operations:** Batch Redis operations
4. **Efficient Cleanup:** Regular but not frequent cleanup

This comprehensive rate limiting system provides robust protection with excellent debugging capabilities and graceful fallback mechanisms.
