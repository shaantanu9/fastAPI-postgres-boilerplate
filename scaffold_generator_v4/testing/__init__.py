"""Advanced Testing Suite Generator for FastAPI Scaffold Generator v4.0.

This module provides comprehensive testing capabilities:
- Unit test generation for models, services, and routes
- Integration test generation for plugin interactions
- End-to-end test generation for complete workflows
- Load testing scripts with realistic scenarios
- Contract testing for API validation
- Mock data generation with realistic test data
"""

from .test_generator import TestConfig, TestGenerator

__all__ = ["TestConfig", "TestGenerator"]
