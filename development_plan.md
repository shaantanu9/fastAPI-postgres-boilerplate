# SaaS Enhancement Plan: Real-Time Features & Subscription Billing

This document outlines the implementation plan for adding scalable real-time features and subscription billing capabilities to our FastAPI PostgreSQL boilerplate.

## Table of Contents

1. [Real-Time Features](#real-time-features)
   - [WebSocket Integration](#websocket-integration)
   - [Event Broadcasting](#event-broadcasting)
   - [Notification System](#notification-system)
2. [Subscription & Billing](#subscription--billing)
   - [Stripe Integration](#stripe-integration)
   - [Usage-Based Billing](#usage-based-billing)
   - [Plan & Feature Management](#plan--feature-management)
   - [Subscription Lifecycle](#subscription-lifecycle)
3. [Implementation Timeline](#implementation-timeline)
4. [Integration Points](#integration-points)
5. [Testing Strategy](#testing-strategy)

## Real-Time Features

### WebSocket Integration

#### Architecture Overview

We will implement a scalable, tenant-aware WebSocket system using Redis as the pub/sub backbone. This architecture enables:

- Horizontal scaling across multiple server instances
- Tenant isolation for security and performance
- Room/channel-based communication
- High availability with no single point of failure

#### Key Components

1. **WebSocketManager**: Core class managing connections, room membership, and message distribution
2. **RedisPubSubManager**: Handles Redis pub/sub operations for cross-server communication
3. **ConnectionTracker**: Monitors active connections with heartbeat mechanism
4. **TenantIsolation**: Ensures proper tenant data segregation

#### Data Flow

1. Client connects to any server instance with tenant context
2. Server adds client to appropriate tenant-specific room
3. Messages published to Redis channels based on tenant+room
4. All server instances subscribe to relevant channels
5. Messages delivered to appropriate clients across all instances

### Event Broadcasting

We'll build a flexible event broadcasting system on top of the WebSocket infrastructure:

#### Key Features

1. **Event Types**: Structured event taxonomy (system, user, tenant, global)
2. **Event Filtering**: Allow clients to subscribe to specific event types
3. **Event Persistence**: Optional event storage for replay/history
4. **Backpressure Handling**: Protect system from event flooding
5. **Dead Letter Channel**: Handle undeliverable events

#### Implementation Components

- `EventEmitter` class for application-wide event publishing
- Event schema validation with Pydantic
- Topic-based subscription model
- Integration with existing background task systems

### Notification System

Building on both WebSockets and event broadcasting, we'll create a unified notification system:

#### Delivery Channels

1. **In-App**: Real-time via WebSockets
2. **Email**: Async delivery through existing email service
3. **Push**: Mobile push notifications via Firebase Cloud Messaging
4. **SMS**: Optional text messaging for critical alerts

#### Notification Features

- Template-based content generation
- Priority levels with delivery guarantees
- User preference management
- Read/unread status tracking
- Notification grouping and summarization
- Rate limiting to prevent notification spam

## Subscription & Billing

### Stripe Integration

#### Core Components

1. **Stripe Client**: Wrapper around Stripe SDK with error handling
2. **Webhook Handler**: Process Stripe events securely
3. **Customer Management**: Map application users to Stripe customers
4. **Payment Method Manager**: Securely handle payment instruments
5. **Invoice & Receipt Manager**: Generate and deliver transaction documents

#### Webhook Events

We'll implement handlers for these crucial Stripe events:

- `customer.subscription.created`
- `customer.subscription.updated`
- `customer.subscription.deleted`
- `invoice.paid`
- `invoice.payment_failed`
- `charge.succeeded`
- `charge.failed`

#### Security Considerations

- Webhook signature verification
- Idempotency keys for all Stripe operations
- Secure handling of payment details (no storage)
- Proper error handling and recovery

### Usage-Based Billing

#### Metering Infrastructure

1. **Usage Collectors**: Distributed counters for various billable metrics
2. **Aggregation Service**: Consolidate usage data across services
3. **Redis-Based Counters**: Fast, atomic increments with persistence
4. **Reporting API**: Expose current usage to customers

#### Billable Metrics

Template metrics we'll implement:

- API call volume
- Storage consumption
- Processing time
- User seats
- Custom metrics based on tenant actions

#### Integration with Stripe

- Create metered billing products in Stripe
- Automatically report usage via Stripe API
- Support for tiered pricing models

### Plan & Feature Management

#### Feature Flag System

1. **Dynamic Configuration**: Runtime-updatable feature flags
2. **Multi-Level Control**: Global, tenant, and user-level flags
3. **Percentage Rollouts**: Gradual feature introduction
4. **A/B Testing**: Compare feature variations
5. **Tenant-Aware Evaluation**: Context-based feature decisions

#### Subscription Tiers

Core components of our tier system:

- `SubscriptionPlan` model with clear capabilities
- Feature matrix mapped to subscription levels
- PostgreSQL-based feature entitlement storage
- In-memory cache for high-performance checks
- Upgrade/downgrade workflows

#### Access Control Integration

- Feature middleware for HTTP endpoints
- WebSocket connection filtering
- Background task permission evaluation
- API usage throttling based on tier

### Subscription Lifecycle

#### State Machine

Implement a robust state machine for subscription lifecycle:

```
Trial → Active → Past Due → Canceled/Unpaid
   ↑         ↑        |         ↓
   |         |        ↓         |
   +--------------------→ Reactivated
```

#### Key Transitions

Automated handling for:

- Trial expiration
- Payment success/failure
- Manual cancellation
- Plan changes
- Reactivation
- Grace periods

#### Customer Communication

- Lifecycle event notifications
- Upcoming payment reminders
- Dunning management
- Winback campaigns for canceled accounts

## Implementation Timeline

1. **Phase 1 (Weeks 1-2)**:
   - WebSocket infrastructure with Redis pub/sub
   - Basic Stripe integration with webhook handling
   
2. **Phase 2 (Weeks 3-4)**:
   - Event broadcasting system
   - Subscription plans and feature flags
   
3. **Phase 3 (Weeks 5-6)**:
   - Unified notification system
   - Usage-based metering and billing
   
4. **Phase 4 (Weeks 7-8)**:
   - Subscription lifecycle management
   - Integration testing and optimization

## Integration Points

- User authentication system
- Tenant management system
- PostgreSQL database
- Redis cache and pub/sub
- Email delivery service
- Background task processor (Procrastinate)
- Monitoring and metrics collection

## Testing Strategy

1. **Unit Tests**: Core components and business logic
2. **Integration Tests**: Service interactions and data flow
3. **Load Tests**: Performance under scale with simulated users
4. **Failure Tests**: System resilience during outages
5. **Security Tests**: Vulnerability assessment
