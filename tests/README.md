# FastAPI PostgreSQL Test Suite

This directory contains a comprehensive test suite organized by functionality and purpose. All tests have been moved from the root directory and properly documented with clear purposes, usage instructions, and expected outcomes.

## 📁 Directory Structure

```
tests/
├── auth/                    # Authentication & Authorization Tests
├── plugins/                 # Plugin System Tests
├── system/                  # Core System Tests
├── production/              # Production Environment Tests
├── enterprise/              # Enterprise Feature Tests
├── integration/             # Integration Tests
├── user_journey/            # End-to-End User Journey Tests
├── production_checks/       # Production Readiness Checks
├── timeout_middleware/      # Timeout System Tests (from previous debugging)
└── README.md               # This file
```

## 🔐 Authentication Tests (`auth/`)

Tests for user authentication, authorization, and security features.

| Test File                    | Purpose                       | When to Use                          |
| ---------------------------- | ----------------------------- | ------------------------------------ |
| `test_auth_comprehensive.py` | Complete auth flow testing    | Testing full authentication system   |
| `test_auth_debug.py`         | Debug auth endpoint issues    | When auth endpoints are failing      |
| `test_jwt_debug.py`          | Debug JWT token functionality | When JWT tokens aren't working       |
| `test_login_debug.py`        | Debug login process           | When login endpoint fails            |
| `test_password_reset.py`     | Test password reset flow      | Testing password reset functionality |
| `test_user_creation.py`      | Test user registration        | Testing user creation process        |

### Running Auth Tests

```bash
# Run all auth tests
python3 -m pytest tests/auth/ -v

# Run specific auth test
python3 tests/auth/test_auth_comprehensive.py
```

## 🔌 Plugin Tests (`plugins/`)

Tests for the plugin system, plugin discovery, and individual plugin functionality.

| Test File                            | Purpose                         | When to Use                     |
| ------------------------------------ | ------------------------------- | ------------------------------- |
| `test_plugin_discovery.py`           | Debug plugin discovery system   | When plugins aren't loading     |
| `test_book_plugin.py`                | Test book plugin functionality  | Testing book plugin features    |
| `test_book_integration.py`           | Test book plugin integration    | Testing book plugin integration |
| `test_plugin_init.py`                | Test plugin initialization      | When plugins don't initialize   |
| `test_plugin_base_conflict.py`       | Test plugin inheritance issues  | When plugin conflicts occur     |
| `test_v4_discovery.py`               | Test v4 plugin discovery        | Testing new plugin system       |
| `test_manual_plugin_registration.py` | Test manual plugin registration | When auto-discovery fails       |
| `test_manual_registration.py`        | Test manual registration flows  | Testing manual processes        |
| `test_manual_inclusion.py`           | Test manual plugin inclusion    | Testing inclusion methods       |

### Running Plugin Tests

```bash
# Run all plugin tests
python3 -m pytest tests/plugins/ -v

# Debug plugin discovery
python3 tests/plugins/test_plugin_discovery.py
```

## ⚙️ System Tests (`system/`)

Tests for core system functionality, routing, and infrastructure.

| Test File                | Purpose                       | When to Use                    |
| ------------------------ | ----------------------------- | ------------------------------ |
| `test_timeout_system.py` | Comprehensive timeout testing | Testing timeout functionality  |
| `test_lifespan.py`       | Test app lifecycle events     | Testing startup/shutdown       |
| `test_routes.py`         | Test route registration       | Testing API route availability |
| `test_server_routes.py`  | Test server route config      | Testing server setup           |
| `test_rate_limiting.py`  | Test rate limiting            | Testing rate limiting features |
| `test_redis_async.py`    | Test Redis integration        | Testing Redis functionality    |

### Running System Tests

```bash
# Run all system tests
python3 -m pytest tests/system/ -v

# Test timeout system specifically
python3 tests/system/test_timeout_system.py
```

## 🏭 Production Tests (`production/`)

Tests for production-specific features and background processing.

| Test File                             | Purpose                  | When to Use             |
| ------------------------------------- | ------------------------ | ----------------------- |
| `test_procrastinate_comprehensive.py` | Test job queue system    | Testing background jobs |
| `test_auto_fix_comprehensive.py`      | Test auto-fix mechanisms | Testing error recovery  |

### Running Production Tests

```bash
# Run production tests
python3 -m pytest tests/production/ -v
```

## 🏢 Enterprise Tests (`enterprise/`)

Tests for enterprise-level features and advanced functionality.

| Test File                     | Purpose                       | When to Use                 |
| ----------------------------- | ----------------------------- | --------------------------- |
| `test_enterprise_features.py` | Test enterprise functionality | Testing enterprise features |
| `test_16_codes.py`            | Test code generation system   | Testing code generation     |

### Running Enterprise Tests

```bash
# Run enterprise tests
python3 -m pytest tests/enterprise/ -v
```

## 🔗 Integration Tests (`integration/`)

Tests for system integration and data processing.

| Test File              | Purpose                     | When to Use                      |
| ---------------------- | --------------------------- | -------------------------------- |
| `test_final_system.py` | Complete system integration | Final testing before deployment  |
| `test_extraction.py`   | Test data extraction        | Testing data extraction features |
| `test_fresh_import.py` | Test import functionality   | Testing import processes         |

### Running Integration Tests

```bash
# Run integration tests
python3 -m pytest tests/integration/ -v
```

## 👤 User Journey Tests (`user_journey/`)

End-to-end tests that simulate complete user workflows.

| Test File                            | Purpose                       | When to Use                  |
| ------------------------------------ | ----------------------------- | ---------------------------- |
| `user_journey_comprehensive.py`      | Complete user journey testing | End-to-end system validation |
| `comprehensive_user_journey_test.py` | Comprehensive user flow       | Full user experience testing |
| `user_journey_test.py`               | Basic user journey            | Standard user flow testing   |

### Running User Journey Tests

```bash
# Run user journey tests
python3 tests/user_journey/user_journey_comprehensive.py
```

## 🏥 Production Checks (`production_checks/`)

Production readiness and health check scripts.

| Test File                           | Purpose                       | When to Use                    |
| ----------------------------------- | ----------------------------- | ------------------------------ |
| `comprehensive_check.py`            | Comprehensive system check    | Before production deployment   |
| `comprehensive_production_fixes.py` | Production issue fixes        | Fixing production issues       |
| `quick_production_check.py`         | Quick production health check | Rapid production validation    |
| `production_readiness_check.py`     | Full production readiness     | Complete production assessment |

### Running Production Checks

```bash
# Quick production check
python3 tests/production_checks/quick_production_check.py

# Comprehensive check
python3 tests/production_checks/comprehensive_check.py
```

## ⏱️ Timeout Middleware Tests (`timeout_middleware/`)

Tests specifically for the timeout middleware system (from previous debugging session).

| Test File                   | Purpose                            | Historical Context              |
| --------------------------- | ---------------------------------- | ------------------------------- |
| `debug_timeout_issue.py`    | Test asyncio.wait() behavior       | Ruled out Python version issues |
| `debug_middleware_logic.py` | Test middleware logic isolation    | Confirmed logic was correct     |
| `fix_timeout_middleware.py` | Enhanced middleware error handling | Revealed the real NameError     |

These tests were created during the 2025-06-14 timeout middleware debugging session and helped identify the missing `security_service` import issue.

## 🚀 Quick Start Guide

### Prerequisites

1. **Server Running**: `uvicorn app.main:app --reload`
2. **Database**: PostgreSQL accessible with migrations applied
3. **Environment Variables**: Set DATABASE_URL, JWT_SECRET_TOKEN
4. **Test User**: Create test user with credentials for auth tests

### Running All Tests

```bash
# Run all tests with pytest
python3 -m pytest tests/ -v

# Run tests by category
python3 -m pytest tests/auth/ -v
python3 -m pytest tests/plugins/ -v
python3 -m pytest tests/system/ -v
```

### Running Individual Tests

```bash
# Authentication flow
python3 tests/auth/test_auth_comprehensive.py

# Plugin discovery debugging
python3 tests/plugins/test_plugin_discovery.py

# Timeout system testing
python3 tests/system/test_timeout_system.py

# User journey testing
python3 tests/user_journey/user_journey_comprehensive.py
```

## 📊 Test Documentation Format

Each test file includes comprehensive documentation:

```python
"""
TEST NAME

PURPOSE:
    What this test does and why it exists

WHEN TO USE:
    Specific scenarios when you should run this test

WHAT IT TESTS:
    Detailed breakdown of test coverage

CREATED: Date and context information
DEPENDENCIES: What needs to be running/configured
RESULT: What the test validates

HOW TO RUN:
    Step-by-step instructions

EXPECTED OUTPUT:
    What success looks like

NOTES:
    Additional context and troubleshooting tips
"""
```

## 🔧 Troubleshooting

### Common Issues

1. **Server Not Running**

   ```bash
   uvicorn app.main:app --reload
   ```

2. **Database Connection Issues**

   - Check DATABASE_URL environment variable
   - Ensure PostgreSQL is running
   - Verify database exists and is accessible

3. **Plugin Tests Failing**

   - Check that plugins are in `app/plugins/` directory
   - Verify plugin `__init__.py` files exist
   - Check plugin metadata and registration functions

4. **Authentication Tests Failing**
   - Ensure test user exists with correct credentials
   - Check JWT_SECRET_TOKEN is set
   - Verify auth endpoints are accessible

### Getting Help

1. **Check Test Documentation**: Each test file has detailed documentation
2. **Review Server Logs**: Check uvicorn output for errors
3. **Run Health Checks**: Use production check scripts
4. **Debug Step by Step**: Use individual debug tests

## 📈 Test Organization Benefits

This organized structure provides:

- ✅ **Clear Purpose**: Each test has documented purpose and usage
- ✅ **Easy Discovery**: Tests are categorized by functionality
- ✅ **Better Maintenance**: Related tests are grouped together
- ✅ **Historical Context**: Legacy tests preserve debugging history
- ✅ **Comprehensive Coverage**: All aspects of the system are tested
- ✅ **Production Ready**: Production checks ensure deployment readiness

## 🎯 Next Steps

1. **Add More Tests**: Expand coverage in each category
2. **Automate Testing**: Set up CI/CD pipeline with these tests
3. **Performance Testing**: Add load testing to system tests
4. **Monitoring Integration**: Connect tests to monitoring systems
5. **Documentation Updates**: Keep test documentation current

---

_This test suite was organized on 2025-06-14 to improve maintainability and provide clear documentation for all testing scenarios._
