# Project Brief: FastAPI PostgreSQL Scalable Boilerplate

## Project Overview

This is a FastAPI + PostgreSQL async boilerplate designed to be a minimal, production-ready foundation for rapid backend development. The project currently provides basic CRUD operations, async SQLAlchemy ORM, authentication, and database migrations through Alembic.

## Core Requirements

1. **Scalability**: Transform from basic boilerplate to enterprise-ready template
2. **Large Codebase Support**: Architecture that handles complex applications with many models, services, and endpoints
3. **Project Agnostic**: Reusable template that can be adapted for any project domain
4. **Production Ready**: Comprehensive features for deployment, monitoring, testing, and maintenance

## Current Features

- Async SQLAlchemy ORM with PostgreSQL
- FastAPI app structure with versioned APIs
- Environment variable support via `.env`
- Basic authentication and authorization (JWT, OAuth2)
- Alembic migrations
- Model scaffolding system
- Service layer architecture
- Basic middleware and exception handling
- Task queue implementation
- Docker support

## Key Technologies

- **Framework**: FastAPI (async)
- **Database**: PostgreSQL with asyncpg
- **ORM**: SQLAlchemy (async)
- **Migrations**: Alembic
- **Dependency Management**: uv (fast, modern)
- **Authentication**: JWT with passlib
- **Logging**: loguru
- **Testing**: pytest (basic structure)

## Success Metrics

- Handles projects with 100+ models efficiently
- Code generation and scaffolding for rapid development
- Clean separation of concerns
- Comprehensive testing suite
- Production deployment readiness
- Clear documentation and onboarding
- Plugin/extension system for modularity
