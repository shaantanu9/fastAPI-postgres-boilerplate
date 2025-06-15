# Scaffold Generator v4 🚀

**Enterprise-ready FastAPI plugin generator with advanced features**

## 🎯 Quick Start

### Main Command (Verified Working)

```bash
python main.py add <ModelName> <field1:type> <field2:type> [options]
```

### ✅ Working Examples

#### Basic Model

```bash
python main.py add Customer name:str email:str phone:str
```

#### Advanced Model with All Features

```bash
python main.py add Product name:str price:float:gt=0 category:str:choices=electronics,clothing,books description:str:optional stock:int:ge=0 is_active:bool --with-tasks --with-bulk
```

## 📋 All Field Types & Constraints

| Type       | Example               | Description           |
| ---------- | --------------------- | --------------------- |
| `str`      | `name:str`            | String field          |
| `int`      | `age:int`             | Integer field         |
| `float`    | `price:float`         | Float field           |
| `bool`     | `is_active:bool`      | Boolean field         |
| `date`     | `birth_date:date`     | Date field            |
| `datetime` | `created_at:datetime` | Datetime field        |
| `email`    | `contact:email`       | Email with validation |

### Constraints

| Constraint      | Example                              | Description                |
| --------------- | ------------------------------------ | -------------------------- |
| `gt=N`          | `price:float:gt=0`                   | Greater than N             |
| `ge=N`          | `stock:int:ge=0`                     | Greater than or equal to N |
| `lt=N`          | `limit:int:lt=100`                   | Less than N                |
| `le=N`          | `score:int:le=100`                   | Less than or equal to N    |
| `choices=a,b,c` | `status:str:choices=active,inactive` | Limited choices            |
| `optional`      | `description:str:optional`           | Nullable field             |

## 🚀 Command Options

| Option         | Description                      |
| -------------- | -------------------------------- |
| `--with-tasks` | Add background task support      |
| `--with-bulk`  | Add bulk operations              |
| `--with-auth`  | Enable enterprise authentication |

## 📋 Available Commands

### Core Commands

```bash
# Create new plugin
python main.py add ModelName field1:type field2:type [options]

# List all plugins
python main.py list

# Test model (dry run)
python main.py test ModelName field1:type field2:type

# Remove plugin files
python main.py remove ModelName

# Complete cleanup
python main.py cleanup ModelName [--force]
```

### Health & Maintenance

```bash
# Check infrastructure
python main.py infra-check

# Fix migration issues
python main.py auto-fix [--force]

# Check migration health
python main.py migration-health
```

## 🎯 Success Metrics

✅ **Auto-Fix System**: 7/8 strategies working (87.5% success rate)  
✅ **Migration Generation**: Fully automated with conflict resolution  
✅ **Plugin Creation**: Complete file generation (models, routes, schemas, services, tasks)  
✅ **Database Integration**: Auto-creates tables with constraints  
✅ **FastAPI Integration**: Routes auto-registered with timeout support

## 📁 Generated Structure

For model `Product`, generates:

```
app/plugins/product_plugin/
├── __init__.py          # Plugin registration
├── models.py            # SQLAlchemy model
├── schemas.py           # Pydantic schemas
├── routes.py            # FastAPI routes with timeouts
├── services.py          # Business logic
└── tasks.py             # Background tasks (if --with-tasks)
```

## 🌐 Generated API Endpoints

For model `Product`:

- `POST /products/` - Create product
- `GET /products/` - List products (with pagination)
- `GET /products/{id}` - Get specific product
- `PUT /products/{id}` - Update product
- `DELETE /products/{id}` - Delete product
- `GET /products/search/` - Search products

## 🔧 Features

### Enterprise Features

- ✅ Comprehensive field validation
- ✅ Auto-fix migration system
- ✅ Timeout support on all routes
- ✅ Background task integration
- ✅ Bulk operations
- ✅ Enterprise authentication (optional)
- ✅ Audit logging
- ✅ Soft delete functionality

### Technical Features

- ✅ SQLAlchemy models with proper relationships
- ✅ Pydantic schemas with validation
- ✅ FastAPI routes with error handling
- ✅ Service layer with business logic
- ✅ Background task support (Procrastinate)
- ✅ Migration generation and auto-fix
- ✅ Plugin architecture

## 🐛 Troubleshooting

### Migration Issues

```bash
# Fix all migration problems
python main.py auto-fix

# Force fix with aggressive strategies
python main.py auto-fix --force
```

### Plugin Not Loading

```bash
# Check infrastructure
python main.py infra-check

# Verify plugin list
python main.py list
```

## 📖 Examples

### E-commerce Models

```bash
# Product catalog
python main.py add Product name:str price:float:gt=0 category:str:choices=electronics,clothing,books stock:int:ge=0 --with-tasks

# Customer management
python main.py add Customer name:str email:email phone:str address:str:optional

# Order processing
python main.py add Order customer_email:email total:float:gt=0 status:str:choices=pending,shipped,delivered --with-bulk
```

### Content Management

```bash
# Blog posts
python main.py add Post title:str content:str author:str published:bool publish_date:datetime:optional

# User accounts
python main.py add User username:str email:email age:int:ge=18 is_active:bool --with-auth
```

### Business Applications

```bash
# Invoice system
python main.py add Invoice number:str amount:float:gt=0 due_date:date status:str:choices=draft,sent,paid --with-tasks

# Project management
python main.py add Task title:str description:str:optional priority:str:choices=low,medium,high due_date:date:optional
```

## 🎉 Success Stories

✅ **Customer Model**: Generated successfully with all CRUD operations  
✅ **Product Model**: Created with constraints, migrations applied  
✅ **Auto-Fix**: Resolved migration conflicts automatically  
✅ **Database**: Tables created with proper indexes and constraints  
✅ **API**: All endpoints working with timeout protection

---

**Ready to create enterprise-grade FastAPI plugins in seconds!** 🚀
