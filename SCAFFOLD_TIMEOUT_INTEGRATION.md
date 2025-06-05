# Scaffold v4 + Timeout System Integration Guide

## Overview

Scaffold v4 now seamlessly integrates with the enhanced timeout system, providing automatic timeout management for all generated endpoints. This integration ensures that scaffold-generated code is production-ready with robust timeout handling.

## ✅ **Automatic Benefits**

### **1. Middleware-Level Protection**

All scaffold-generated endpoints automatically inherit:

- **30-second global timeout** protection
- **Performance monitoring** and metrics collection
- **Enhanced error responses** with timeout details
- **Request duration tracking** in response headers

### **2. No Breaking Changes**

- All existing scaffold v4 code continues to work unchanged
- Plugin system compatibility maintained
- Database operations remain functional
- Authentication features unaffected

## 🚀 **Enhanced Features Available**

### **1. Enhanced Routes Template (Default)**

When generating plugins, scaffold v4 now uses enhanced routes by default:

```bash
# Generate plugin with timeout support (default)
python -m scaffold_generator_v4 add Product name:str price:float description:text

# Generate without timeout support (legacy mode)
python -m scaffold_generator_v4 add Product name:str price:float --no-timeouts
```

### **2. Smart Timeout Configuration**

The enhanced template automatically configures timeouts based on model complexity:

#### **Simple Models (< 10 fields)**

```python
timeouts = {
    'create': 10.0,    # Create operations
    'read': 5.0,       # Read operations
    'update': 10.0,    # Update operations
    'delete': 5.0,     # Delete operations
    'search': 15.0,    # Search operations
    'database': 8.0    # Database context
}
```

#### **Complex Models (> 20 fields, relations, text search)**

```python
timeouts = {
    'create': 15.0,    # Longer for complex data
    'read': 10.0,      # Relations need more time
    'update': 15.0,    # Complex updates
    'delete': 5.0,     # Deletes stay fast
    'search': 30.0,    # Text search slower
    'database': 15.0   # More complex queries
}
```

#### **Bulk Operations**

```python
timeouts = {
    'bulk_create': 60.0,   # Batch creates
    'bulk_update': 60.0,   # Batch updates
    'bulk_delete': 30.0    # Batch deletes
}
```

## 📝 **Generated Code Examples**

### **1. Enhanced Route with Timeouts**

Scaffold now generates routes like this:

```python
@router.post("/products/", response_model=ProductResponse, tags=["Product"])
@with_timeout(timeout_seconds=10.0)
async def create_product(item: ProductCreate, request: Request):
    """Create a new product"""
    try:
        # Use database timeout context for data operations
        async with database_timeout_context(8.0):
            result = await self.service.create(**item.dict())

        # Emit creation event
        self.emit_event("product_created",
                      id=result.id,
                      plugin="product_plugin")

        return result

    except TimeoutException as e:
        raise HTTPException(
            status_code=504,
            detail={
                "error": "operation_timeout",
                "message": "Create operation timed out",
                "timeout_seconds": 10.0,
                "operation": "create_product"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
```

### **2. Enhanced Error Responses**

Timeout errors now provide detailed information:

```json
{
  "error": "operation_timeout",
  "message": "Create operation timed out",
  "timeout_seconds": 10.0,
  "operation": "create_product",
  "timestamp": 1640995200.0
}
```

## 🔧 **Configuration Options**

### **1. Generate with Enhanced Timeouts (Default)**

```bash
# Enhanced routes with intelligent timeout management
python -m scaffold_generator_v4 add User name:str email:str profile:json
```

Features included:

- ✅ Automatic timeout decorators on all endpoints
- ✅ Database timeout contexts for data operations
- ✅ Smart timeout values based on model complexity
- ✅ Enhanced error handling with detailed responses
- ✅ Bulk operation timeout support

### **2. Generate with Standard Routes**

```bash
# Standard routes without timeout decorators (legacy mode)
python -m scaffold_generator_v4 add User name:str email:str --no-timeouts
```

Features included:

- ✅ Middleware-level timeout protection (still active)
- ❌ No endpoint-specific timeout decorators
- ❌ No database timeout contexts
- ❌ Basic error handling

### **3. Authentication + Timeouts**

```bash
# Enhanced routes with authentication AND timeouts
python -m scaffold_generator_v4 add Order user_id:int items:json --with-auth --with-bulk
```

Features included:

- ✅ All enhanced timeout features
- ✅ Enterprise authentication
- ✅ Bulk operations with extended timeouts
- ✅ Audit logging integration

## 📊 **Model Complexity Analysis**

The enhanced template analyzes your model and adjusts timeouts automatically:

### **Complexity Factors**

1. **Field Count**: More fields = longer timeouts
2. **Field Types**: Text/JSON fields = search timeouts increased
3. **Relationships**: Foreign keys = read/write timeouts increased
4. **Bulk Operations**: Enabled = special bulk timeouts

### **Example Analysis**

```python
# Simple model
class Product:
    id: int
    name: str
    price: float

# Timeout configuration: Standard (fast)
```

```python
# Complex model
class Article:
    id: int
    title: str
    content: text        # Text search = longer search timeout
    author_id: int       # Relationship = longer read timeout
    tags: json          # JSON field = longer timeouts
    categories: List[Category]  # Many-to-many = much longer timeouts

# Timeout configuration: Extended (slower but safer)
```

## 🧪 **Testing Integration**

### **1. Test Generated Endpoints**

```bash
# Start your FastAPI server
uvicorn app.main:app --reload

# Test timeout system
python test_timeout_system.py

# Test specific scaffold endpoints
curl "http://localhost:8000/api/v1/products/"
curl "http://localhost:8000/api/v1/products/1"
```

### **2. Test Timeout Behavior**

```bash
# Test with enhanced routes - should have timeout headers
curl -i "http://localhost:8000/api/v1/products/"

# Response headers include:
# X-Request-Duration: 0.123
# X-Timeout-Limit: 30
```

## 🔄 **Migration Guide**

### **Existing Scaffold v4 Projects**

Your existing scaffold-generated code will continue to work unchanged. To add timeout support:

#### **Option 1: Regenerate with Enhanced Templates**

```bash
# Backup existing plugin
cp -r app/plugins/product_plugin app/plugins/product_plugin.backup

# Regenerate with timeout support
python -m scaffold_generator_v4 add Product name:str price:float description:text

# Manually merge any custom changes from backup
```

#### **Option 2: Manual Enhancement**

Add timeout decorators to existing routes:

```python
# Add these imports to your existing routes.py
from app.core.timeouts import with_timeout, database_timeout_context, TimeoutException

# Add decorators to your endpoints
@router.post("/products/", response_model=ProductResponse)
@with_timeout(timeout_seconds=10.0)  # Add this line
async def create_product(item: ProductCreate, request: Request):
    try:
        # Wrap database operations
        async with database_timeout_context(8.0):  # Add this
            result = await self.service.create(**item.dict())
        return result
    except TimeoutException as e:  # Add timeout handling
        raise HTTPException(status_code=504, detail="Operation timed out")
```

## 📋 **Best Practices**

### **1. Use Enhanced Templates by Default**

- Enhanced routes provide better production readiness
- Automatic timeout management reduces operational issues
- Better error handling improves debugging

### **2. Customize Timeouts for Specific Use Cases**

```python
# For file upload endpoints
@with_timeout(timeout_seconds=120.0)  # Longer timeout

# For simple lookups
@with_timeout(timeout_seconds=3.0)    # Shorter timeout
```

### **3. Monitor Timeout Metrics**

```bash
# Check timeout metrics
curl http://localhost:8000/api/v1/test/timeout/metrics

# Monitor in production logs
grep "Request timed out" /var/log/fastapi/app.log
```

### **4. Test Timeout Scenarios**

```python
# Add to your test suite
def test_endpoint_timeout_handling():
    # Test with slow operations
    # Verify proper 504 responses
    # Check timeout headers
```

## 🚨 **Troubleshooting**

### **Common Issues**

#### **1. Import Errors**

```bash
# Error: Cannot import TimeoutException
# Solution: Ensure app/core/timeouts.py exists and is properly configured
```

#### **2. Middleware Not Working**

```bash
# Check middleware registration in app/main.py
# Should see: app.add_middleware(TimeoutMiddleware, ...)
```

#### **3. Timeout Values Too Short**

```python
# Increase timeouts for complex operations
@with_timeout(timeout_seconds=60.0)  # Increase as needed
```

### **Debug Commands**

```bash
# Check system health
python -m scaffold_generator_v4 health-check

# Test timeout system
python test_timeout_system.py

# Check middleware status
curl http://localhost:8000/api/v1/test/timeout/health
```

## ✨ **Summary**

The Scaffold v4 + Timeout System integration provides:

- ✅ **Zero Breaking Changes**: Existing code continues to work
- ✅ **Enhanced by Default**: New plugins get timeout support automatically
- ✅ **Smart Configuration**: Timeouts adjust based on model complexity
- ✅ **Production Ready**: Comprehensive error handling and monitoring
- ✅ **Easy Testing**: Built-in test endpoints and validation
- ✅ **Flexible Options**: Can disable if needed for special cases

Your scaffold-generated code is now more robust, production-ready, and provides better operational visibility! 🎉
