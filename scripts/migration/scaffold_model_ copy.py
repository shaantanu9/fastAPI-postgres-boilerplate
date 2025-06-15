import json
import os
import sys

BASE_PATH = "app"
TRACK_FILE = "scaffolded_models.json"
API_FILE = os.path.join(BASE_PATH, "api/v1/api.py")


# --- Utility functions ---
def snake_case(name):
    return "".join(["_" + c.lower() if c.isupper() else c for c in name]).lstrip("_")


def pascal_case(name):
    return "".join(word.capitalize() for word in name.split("_"))


def ensure_init(path) -> None:
    dirs = path.split(os.sep)
    for i in range(1, len(dirs)):
        d = os.sep.join(dirs[:i])
        if d and not os.path.exists(os.path.join(d, "__init__.py")):
            with open(os.path.join(d, "__init__.py"), "a"):
                pass


def prompt_fields():
    fields = []
    while True:
        field = input("Field: ")
        if field.lower() == "done":
            break
        if ":" in field:
            name, typ = field.split(":", 1)
            fields.append((name.strip(), typ.strip()))
    return fields


def load_track():
    if os.path.exists(TRACK_FILE):
        with open(TRACK_FILE) as f:
            return json.load(f)
    return {}


def save_track(data) -> None:
    with open(TRACK_FILE, "w") as f:
        json.dump(data, f, indent=2)


# --- File generation and removal ---
def write_file(path, content) -> None:
    ensure_init(os.path.dirname(path))
    with open(path, "w") as f:
        f.write(content)


def remove_file(path) -> None:
    if os.path.exists(path):
        os.remove(path)
        # Remove empty parent dirs up to BASE_PATH
        d = os.path.dirname(path)
        while d.startswith(BASE_PATH) and d != BASE_PATH:
            if not os.listdir(d):
                os.rmdir(d)
                d = os.path.dirname(d)
            else:
                break


def update_api_py(model, action) -> None:
    """Add or remove import/include_router for the model in api.py."""
    snake = snake_case(model)
    router_line = f"from app.api.v1.endpoints import {snake}"
    include_line = f'api_router.include_router({snake}.router, prefix="/{snake}s", tags=["{snake}s"])'
    with open(API_FILE) as f:
        lines = f.readlines()
    if action == "add":
        if router_line + "\n" not in lines:
            # Insert after last import
            last_import = max(i for i, l in enumerate(lines) if l.startswith("from"))
            lines.insert(last_import + 1, router_line + "\n")
        if include_line + "\n" not in lines:
            # Insert after last include_router
            last_include = max(i for i, l in enumerate(lines) if "include_router" in l)
            lines.insert(last_include + 1, include_line + "\n")
    elif action == "remove":
        lines = [
            l for l in lines if l.strip() != router_line and l.strip() != include_line
        ]
    with open(API_FILE, "w") as f:
        f.writelines(lines)


# --- Main scaffold logic ---
def make_model_files(model, fields):
    snake = snake_case(model)
    files = {}
    # Model
    model_path = f"{BASE_PATH}/db/models/{snake}.py"
    model_code = f'''"""
SQLAlchemy model for {model}.
"""
from app.db.base import Base
from sqlalchemy import Column, Integer, String

class {model}(Base):
    __tablename__ = "{snake}s"
    id = Column(Integer, primary_key=True, index=True)
'''
    for name, typ in fields:
        sqlatype = "String" if typ == "str" else "Integer" if typ == "int" else "String"
        model_code += f"    {name} = Column({sqlatype}, nullable=False)\n"
    files[model_path] = model_code
    # Schema
    schema_path = f"{BASE_PATH}/db/schemas/{snake}.py"
    schema_code = f'''"""
Pydantic schemas for {model}.
"""
from pydantic import BaseModel

class {model}Create(BaseModel):
'''
    for name, typ in fields:
        pytyp = "str" if typ == "str" else "int" if typ == "int" else "str"
        schema_code += f"    {name}: {pytyp}\n"
    schema_code += f"""

class {model}Read({model}Create):
    id: int
    class Config:
        orm_mode = True
"""
    files[schema_path] = schema_code
    # Service
    service_path = f"{BASE_PATH}/services/{snake}_service.py"
    service_code = f'''"""
Service for {model} business logic and CRUD operations.
"""
from app.services.base_service import BaseService
from app.db.models.{snake} import {model}

class {model}Service(BaseService[{model}]):
    def __init__(self):
        super().__init__({model})
'''
    files[service_path] = service_code
    # Endpoint
    endpoint_path = f"{BASE_PATH}/api/v1/endpoints/{snake}.py"
    endpoint_code = f'''"""
Auto-generated CRUD endpoints for {model}.
"""
from app.api.v1.endpoints.base import get_crud_router
from app.services.{snake}_service import {model}Service
from app.db.schemas.{snake} import {model}Read, {model}Create
from app.db.session import get_db

router = get_crud_router(
    service={model}Service(),
    schema_read={model}Read,
    schema_create={model}Create,
    prefix="/{snake}s",
    get_db=get_db,
    tags=["{model}s"]
)
'''
    files[endpoint_path] = endpoint_code
    return files


def add_model(model, fields) -> None:
    track = load_track()
    if model in track:
        return
    files = make_model_files(model, fields)
    created = []
    try:
        for path, content in files.items():
            write_file(path, content)
            created.append(path)
        # Update __init__.py for imports
        for subdir, imp in [
            (
                f"{BASE_PATH}/db/models/__init__.py",
                f"from .{snake_case(model)} import {model}\n",
            ),
            (
                f"{BASE_PATH}/db/schemas/__init__.py",
                f"from .{snake_case(model)} import {model}Create, {model}Read\n",
            ),
            (
                f"{BASE_PATH}/services/__init__.py",
                f"from .{snake_case(model)}_service import {model}Service\n",
            ),
            (
                f"{BASE_PATH}/api/v1/endpoints/__init__.py",
                f"from .{snake_case(model)} import router as {snake_case(model)}_router\n",
            ),
        ]:
            with open(subdir, "a") as f:
                f.write(imp)
        # Update API router
        update_api_py(model, "add")
        # Track
        track[model] = list(files.keys())
        save_track(track)
    except Exception:
        for path in created:
            remove_file(path)
        update_api_py(model, "remove")
        if model in track:
            del track[model]
            save_track(track)
        raise


def remove_model(model) -> None:
    track = load_track()
    if model not in track:
        return
    for path in track[model]:
        remove_file(path)
    # Remove imports from __init__.py
    for subdir, imp in [
        (
            f"{BASE_PATH}/db/models/__init__.py",
            f"from .{snake_case(model)} import {model}\n",
        ),
        (
            f"{BASE_PATH}/db/schemas/__init__.py",
            f"from .{snake_case(model)} import {model}Create, {model}Read\n",
        ),
        (
            f"{BASE_PATH}/services/__init__.py",
            f"from .{snake_case(model)}_service import {model}Service\n",
        ),
        (
            f"{BASE_PATH}/api/v1/endpoints/__init__.py",
            f"from .{snake_case(model)} import router as {snake_case(model)}_router\n",
        ),
    ]:
        if os.path.exists(subdir):
            with open(subdir) as f:
                lines = f.readlines()
            with open(subdir, "w") as f:
                for l in lines:
                    if l != imp:
                        f.write(l)
    update_api_py(model, "remove")
    del track[model]
    save_track(track)


def list_models() -> None:
    track = load_track()
    if not track:
        return
    for _model, _files in track.items():
        pass


# --- Extra features ---
SUPPORTED_FIELD_TYPES = {
    "str": "String",
    "int": "Integer",
    "float": "Float",
    "bool": "Boolean",
}

HELP_TEXT = """
FastAPI Scaffold Tool - Enhanced

Usage:
  python scaffold_model.py add        # Add a new model (with prompts)
  python scaffold_model.py remove     # Remove a model and all related files/imports
  python scaffold_model.py list       # List all scaffolded models
  python scaffold_model.py help       # Show this help message

Options:
  --dry-run   Preview changes without writing files
  --verbose   Show detailed output
  --quiet     Suppress most output

Features:
- Test file generation for each model
- Field type validation and warning
- Basic relationship support (ForeignKey)
- Docstrings/examples in schemas
- Customizable CRUD endpoints (disable/enable)
- Dry run/preview mode
- Verbose/quiet modes
- Help/usage command
"""


def validate_fields(fields):
    valid = True
    for _name, typ in fields:
        if typ not in SUPPORTED_FIELD_TYPES and not typ.startswith("FK:"):
            valid = False
    return valid


def prompt_relationships():
    rels = []
    while True:
        rel = input("Relationship: ")
        if rel.lower() == "done":
            break
        if ":" in rel and rel.count(":") == 2:
            name, fk, target = rel.split(":")
            if fk == "FK":
                rels.append((name.strip(), target.strip()))
    return rels


def prompt_crud():
    crud = {}
    for op in ["create", "read", "update", "delete", "list"]:
        val = input(f"  {op}? [y/n]: ").strip().lower()
        crud[op] = val == "y"
    return crud


def make_test_file(model, fields):
    snake = snake_case(model)
    test_path = f"app/tests/test_{snake}.py"
    test_code = f'''"""
Basic tests for {model} endpoints and service.
"""
def test_{snake}_crud(client):
    # TODO: Implement real tests
    resp = client.get(f"/{snake}s")
    assert resp.status_code in (200, 401, 403)
'''
    return test_path, test_code


def make_model_files_enhanced(
    model, fields, relationships, crud, examples, dry_run=False, verbose=True,
):
    snake = snake_case(model)
    files = {}
    # Model
    model_path = f"{BASE_PATH}/db/models/{snake}.py"
    model_code = f'''"""
SQLAlchemy model for {model}.
"""
from app.db.base import Base
from sqlalchemy import Column, Integer, String, ForeignKey

class {model}(Base):
    """SQLAlchemy ORM model for {model}."""
    __tablename__ = "{snake}s"
    id = Column(Integer, primary_key=True, index=True)
'''
    for name, typ in fields:
        if typ.startswith("FK:"):
            target = typ.split(":")[1]
            model_code += f"    {name} = Column(Integer, ForeignKey('{snake_case(target)}s.id'))\n"
        else:
            sqlatype = SUPPORTED_FIELD_TYPES.get(typ, "String")
            model_code += f"    {name} = Column({sqlatype}, nullable=False)\n"
    for name, target in relationships:
        model_code += (
            f"    {name} = Column(Integer, ForeignKey('{snake_case(target)}s.id'))\n"
        )
    files[model_path] = model_code
    # Schema
    schema_path = f"{BASE_PATH}/db/schemas/{snake}.py"
    schema_code = f'''"""
Pydantic schemas for {model}.
"""
from pydantic import BaseModel, Field

class {model}Create(BaseModel):
'''
    for name, typ in fields:
        pytyp = (
            "str"
            if typ == "str"
            else "int"
            if typ == "int"
            else "float"
            if typ == "float"
            else "bool"
            if typ == "bool"
            else "str"
        )
        example = examples.get(name, "example")
        schema_code += f"    {name}: {pytyp} = Field(..., example={example!r})\n"
    schema_code += f"""

class {model}Read({model}Create):
    id: int
    class Config:
        orm_mode = True
"""
    files[schema_path] = schema_code
    # Service
    service_path = f"{BASE_PATH}/services/{snake}_service.py"
    service_code = f'''"""
Service for {model} business logic and CRUD operations.
"""
from app.services.base_service import BaseService
from app.db.models.{snake} import {model}

class {model}Service(BaseService[{model}]):
    def __init__(self):
        super().__init__({model})
'''
    files[service_path] = service_code
    # Endpoint
    endpoint_path = f"{BASE_PATH}/api/v1/endpoints/{snake}.py"
    endpoint_code = f'''"""
Auto-generated CRUD endpoints for {model}.
"""
from app.api.v1.endpoints.base import get_crud_router
from app.services.{snake}_service import {model}Service
from app.db.schemas.{snake} import {model}Read, {model}Create
from app.db.session import get_db

router = get_crud_router(
    service={model}Service(),
    schema_read={model}Read,
    schema_create={model}Create,
    prefix="/{snake}s",
    get_db=get_db,
    tags=["{model}s"],
    crud_ops={crud}
)
'''
    files[endpoint_path] = endpoint_code
    # Test
    test_path, test_code = make_test_file(model, fields)
    files[test_path] = test_code
    if not dry_run:
        for path, code in files.items():
            write_file(path, code)
        if verbose:
            pass
    return files


def add_model_enhanced(
    model, fields, relationships, crud, examples, dry_run=False, verbose=True,
) -> None:
    track = load_track()
    if model in track:
        return
    files = make_model_files_enhanced(
        model, fields, relationships, crud, examples, dry_run, verbose,
    )
    if not dry_run:
        # Update __init__.py for imports
        for subdir, imp in [
            (
                f"{BASE_PATH}/db/models/__init__.py",
                f"from .{snake_case(model)} import {model}\n",
            ),
            (
                f"{BASE_PATH}/db/schemas/__init__.py",
                f"from .{snake_case(model)} import {model}Create, {model}Read\n",
            ),
            (
                f"{BASE_PATH}/services/__init__.py",
                f"from .{snake_case(model)}_service import {model}Service\n",
            ),
            (
                f"{BASE_PATH}/api/v1/endpoints/__init__.py",
                f"from .{snake_case(model)} import router as {snake_case(model)}_router\n",
            ),
        ]:
            with open(subdir, "a") as f:
                f.write(imp)
        update_api_py(model, "add")
        track[model] = list(files.keys())
        save_track(track)
    else:
        pass


# --- CLI ---
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="FastAPI Scaffold Tool", add_help=False,
    )
    parser.add_argument(
        "cmd", nargs="?", default="help", choices=["add", "remove", "list", "help"],
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    if args.cmd == "help":
        sys.exit(0)
    if args.cmd == "list":
        list_models()
        sys.exit(0)
    if args.cmd == "add":
        model = input("Enter model name (CamelCase, e.g., Book): ").strip()
        fields = prompt_fields()
        validate_fields(fields)
        relationships = prompt_relationships()
        crud = prompt_crud()
        examples = {name: input(f"Example for {name}: ") for name, _ in fields}
        add_model_enhanced(
            model,
            fields,
            relationships,
            crud,
            examples,
            dry_run=args.dry_run,
            verbose=args.verbose and not args.quiet,
        )
    elif args.cmd == "remove":
        model = input("Enter model name (CamelCase, e.g., Book): ").strip()
        remove_model(model)


def make_model(model_name, fields) -> None:
    fname = f"{BASE_PATH}/db/models/{snake_case(model_name)}.py"
    ensure_init(os.path.dirname(fname))
    if os.path.exists(fname):
        return
    with open(fname, "w") as f:
        f.write(f'''"""
SQLAlchemy model for {model_name}.
"""
from app.db.base import Base
from sqlalchemy import Column, Integer, String

class {model_name}(Base):
    \"\"\"SQLAlchemy ORM model for {model_name}.\"\"\"
    __tablename__ = "{snake_case(model_name)}s"
    id = Column(Integer, primary_key=True, index=True)
''')
        for name, typ in fields:
            sqlatype = (
                "String" if typ == "str" else "Integer" if typ == "int" else "String"
            )
            f.write(f"    {name} = Column({sqlatype}, nullable=False)\n")
    # Add to __init__.py for Alembic
    init_file = f"{BASE_PATH}/db/models/__init__.py"
    ensure_init(os.path.dirname(init_file))
    with open(init_file, "a") as f:
        f.write(f"from .{snake_case(model_name)} import {model_name}\n")


def make_schema(model_name, fields) -> None:
    fname = f"{BASE_PATH}/db/schemas/{snake_case(model_name)}.py"
    ensure_init(os.path.dirname(fname))
    if os.path.exists(fname):
        return
    with open(fname, "w") as f:
        f.write(f'''"""
Pydantic schemas for {model_name}.
"""
from pydantic import BaseModel

class {model_name}Create(BaseModel):
    """Schema for creating a {model_name}."""
''')
        for name, typ in fields:
            pytyp = "str" if typ == "str" else "int" if typ == "int" else "str"
            f.write(f"    {name}: {pytyp}\n")
        f.write(f"""\n
class {model_name}Read({model_name}Create):
    \"\"\"Schema for reading a {model_name}.\"\"\"
    id: int

    class Config:
        orm_mode = True
""")
    # Add to __init__.py for import convenience
    init_file = f"{BASE_PATH}/db/schemas/__init__.py"
    ensure_init(os.path.dirname(init_file))
    with open(init_file, "a") as f:
        f.write(
            f"from .{snake_case(model_name)} import {model_name}Create, {model_name}Read\n",
        )


def make_service(model_name) -> None:
    fname = f"{BASE_PATH}/services/{snake_case(model_name)}_service.py"
    ensure_init(os.path.dirname(fname))
    if os.path.exists(fname):
        return
    with open(fname, "w") as f:
        f.write(f'''"""
Service for {model_name} business logic and CRUD operations.
"""
from app.services.base_service import BaseService
from app.db.models.{snake_case(model_name)} import {model_name}

class {model_name}Service(BaseService[{model_name}]):
    \"\"\"Service class for {model_name}. Inherit and extend for custom business logic.\"\"\"
    def __init__(self):
        super().__init__({model_name})
''')
    # Add to __init__.py for import convenience
    init_file = f"{BASE_PATH}/services/__init__.py"
    ensure_init(os.path.dirname(init_file))
    with open(init_file, "a") as f:
        f.write(f"from .{snake_case(model_name)}_service import {model_name}Service\n")


def make_endpoint(model_name) -> None:
    fname = f"{BASE_PATH}/api/v1/endpoints/{snake_case(model_name)}.py"
    ensure_init(os.path.dirname(fname))
    if os.path.exists(fname):
        return
    with open(fname, "w") as f:
        f.write(f'''"""
Auto-generated CRUD endpoints for {model_name}.
"""
from app.api.v1.endpoints.base import get_crud_router
from app.services.{snake_case(model_name)}_service import {model_name}Service
from app.db.schemas.{snake_case(model_name)} import {model_name}Read, {model_name}Create
from app.db.session import get_db

router = get_crud_router(
    service={model_name}Service(),
    schema_read={model_name}Read,
    schema_create={model_name}Create,
    prefix="/{snake_case(model_name)}s",
    get_db=get_db,
    tags=["{model_name}s"]
)

# Example custom endpoint (extend as needed)
# from fastapi import Depends, HTTPException
# @router.get("/{snake_case(model_name)}s/by_field/{{value}}", tags=["{model_name}s"], description="Get a {model_name} by field value.")
# async def get_by_field(value: str, db=Depends(get_db)):
#     ...
''')
    # Add to __init__.py for import convenience
    init_file = f"{BASE_PATH}/api/v1/endpoints/__init__.py"
    ensure_init(os.path.dirname(init_file))
    with open(init_file, "a") as f:
        f.write(
            f"from .{snake_case(model_name)} import router as {snake_case(model_name)}_router\n",
        )


def main() -> None:
    model_name = input("Enter model name (CamelCase, e.g., Book): ").strip()
    fields = prompt_fields()
    make_model(model_name, fields)
    make_schema(model_name, fields)
    make_service(model_name)
    make_endpoint(model_name)


if __name__ == "__main__":
    main()
