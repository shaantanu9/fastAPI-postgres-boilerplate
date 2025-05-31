# Technical Context: Technology Stack & Infrastructure

## Core Technology Stack

### Backend Framework

- **FastAPI**: 0.115.12+ (async, type hints, automatic OpenAPI)
- **Python**: 3.13+ (latest features, performance improvements)
- **Uvicorn**: ASGI server with standard extensions

### Database Stack

- **PostgreSQL**: Primary database (production-ready, ACID compliance)
- **SQLAlchemy**: 2.x async ORM with modern patterns
- **asyncpg**: High-performance async PostgreSQL driver
- **Alembic**: Database migrations and schema management

### Dependency Management

- **uv**: Ultra-fast Python package manager (Rust-based)
- **pyproject.toml**: Modern Python project configuration
- **uv.lock**: Reproducible dependency resolution

### Authentication & Security

- **PyJWT**: JSON Web Token implementation
- **passlib[bcrypt]**: Password hashing with bcrypt
- **FastAPI Security**: OAuth2, JWT bearer tokens

### Development Tools

- **loguru**: Structured logging with performance
- **python-dotenv**: Environment variable management
- **pydantic**: Data validation and settings management
- **pydantic-settings**: Configuration from environment

## Infrastructure Requirements

### Development Environment

- Python 3.13+
- PostgreSQL 14+
- Redis 6+ (for caching, sessions, queues)
- Docker & Docker Compose

### Production Environment

- **Container Runtime**: Docker/Kubernetes
- **Database**: Managed PostgreSQL (AWS RDS, Google Cloud SQL)
- **Cache**: Redis Cluster
- **Message Queue**: Redis/RabbitMQ/Apache Kafka
- **Monitoring**: Prometheus + Grafana
- **Logging**: ELK Stack or cloud logging

## Performance Considerations

### Current Performance Profile

- **Async I/O**: Full async/await implementation
- **Connection Pooling**: SQLAlchemy async engine
- **Memory Usage**: Moderate (no significant optimizations)
- **Response Times**: Good for simple CRUD operations

### Scaling Bottlenecks

1. **Database**: Single PostgreSQL instance
2. **Session State**: In-memory (not horizontally scalable)
3. **File Storage**: Local filesystem
4. **Background Tasks**: Simple in-memory queue

## Technical Debt & Issues

### Resolved Issues

- Alembic async/sync driver conflicts
- Pydantic v2 compatibility (`from_attributes`)
- Missing import statements in exception handlers

### Current Technical Debt

1. **No Containerization**: Missing Docker configuration
2. **Minimal Testing**: Basic test structure without fixtures
3. **No CI/CD**: Missing automated testing and deployment
4. **Basic Configuration**: No environment-specific configs
5. **Limited Observability**: No metrics, tracing, or health checks
6. **No Rate Limiting**: Missing API protection
7. **Simple Background Jobs**: No persistent task queue

## Integration Requirements

### External Services

- **Email**: SMTP/SendGrid for notifications
- **File Storage**: AWS S3/Google Cloud Storage
- **Search**: Elasticsearch for full-text search
- **Analytics**: Integration with analytics platforms
- **Payment**: Stripe/PayPal integration patterns

### API Integrations

- **REST API**: Client generation and documentation
- **GraphQL**: Optional GraphQL layer
- **WebSockets**: Real-time communication
- **Webhooks**: Incoming webhook handling

## Security Requirements

- **HTTPS**: TLS/SSL encryption
- **Authentication**: Multi-factor authentication support
- **Authorization**: Role-based access control (RBAC)
- **Data Protection**: Encryption at rest and in transit
- **Audit Logging**: User action tracking
- **Rate Limiting**: API abuse prevention
