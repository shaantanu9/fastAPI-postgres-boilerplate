import sys
import os
import time
import requests
import sqlalchemy
from sqlalchemy import create_engine, inspect
from fastapi.testclient import TestClient
from urllib.parse import urljoin

# --- CONFIGURATION ---
MODEL_NAME = sys.argv[1] if len(sys.argv) > 1 else "Book"  # e.g. "Book"
MODEL_TABLE = sys.argv[2] if len(sys.argv) > 2 else None    # e.g. "books"
API_ROUTE = sys.argv[3] if len(sys.argv) > 3 else None      # e.g. "/api/v1/books/"
OPENAPI_URL = os.environ.get("OPENAPI_URL", "http://localhost:8000/openapi.json")
API_BASE = os.environ.get("API_BASE", "http://localhost:8000")
DB_URL = os.environ.get("DATABASE_URL", "postgresql://user:password@localhost:5432/dbname")

# --- FALLBACKS ---
def route_variants(model_name):
    base = model_name.lower()
    variants = [
        f"/api/v1/{base}/",
        f"/api/v1/{base}s/",
        f"/api/v1/{base.replace('_', '-')}/",
        f"/api/v1/{base.replace('_', '-') }s/",
        f"/api/v1/{base.replace('_', '')}/",
        f"/api/v1/{base.replace('_', '')}s/",
        f"/{base}/",
        f"/{base}s/",
    ]
    return list(dict.fromkeys(variants))  # Remove duplicates

def table_variants(model_name):
    base = model_name.lower()
    variants = [
        base,
        base + "s",
        base.replace('_', ''),
        base.replace('_', '') + "s",
        base.replace('_', '-'),
        base.replace('_', '-') + "s",
    ]
    return list(dict.fromkeys(variants))

# --- RETRY DECORATOR ---
def retry(times=5, delay=2):
    def decorator(fn):
        def wrapper(*args, **kwargs):
            for i in range(times):
                try:
                    return fn(*args, **kwargs)
                except Exception as e:
                    if i == times - 1:
                        raise
                    print(f"[Retry {i+1}/{times}] {fn.__name__} failed: {e}. Retrying in {delay}s...")
                    time.sleep(delay)
        return wrapper
    return decorator

# --- 1. Check OpenAPI docs for route ---
@retry()
def check_route_in_openapi():
    print(f"Checking OpenAPI docs at {OPENAPI_URL} for model '{MODEL_NAME}' ...")
    resp = requests.get(OPENAPI_URL)
    assert resp.status_code == 200, "OpenAPI docs not available"
    paths = resp.json().get("paths", {})
    found = False
    found_route = None
    candidates = [API_ROUTE] if API_ROUTE else route_variants(MODEL_NAME)
    for route in candidates:
        for p in paths:
            if route.rstrip("/") in p.rstrip("/"):
                found = True
                found_route = p
                break
        if found:
            break
    assert found, f"Route for model '{MODEL_NAME}' not found in OpenAPI docs. Tried: {candidates}"
    print(f"✅ Route found in OpenAPI docs: {found_route}")
    return found_route

# --- 2. Check route is registered and responds (GET, POST, PUT, DELETE) ---
@retry()
def check_route_responds(route):
    print(f"Checking API route {route} ...")
    url = urljoin(API_BASE, route)
    methods = ["get", "post", "put", "delete"]
    results = {}
    for method in methods:
        func = getattr(requests, method)
        try:
            if method == "post":
                resp = func(url, json={})
            elif method == "put":
                resp = func(url, json={"id": 1})
            else:
                resp = func(url)
            if resp.status_code in (200, 201, 204, 401, 403, 422, 405):
                print(f"✅ {method.upper()} {url}: {resp.status_code}")
                results[method] = True
            else:
                print(f"⚠️ {method.upper()} {url}: {resp.status_code}")
                results[method] = False
        except Exception as e:
            print(f"❌ {method.upper()} {url} failed: {e}")
            results[method] = False
    assert any(results.values()), f"No working HTTP methods found for {url}"
    return results

# --- 3. Check table exists in database ---
@retry()
def check_table_in_db():
    print(f"Checking database {DB_URL} for model '{MODEL_NAME}' table ...")
    engine = create_engine(DB_URL)
    insp = inspect(engine)
    tables = insp.get_table_names()
    candidates = [MODEL_TABLE] if MODEL_TABLE else table_variants(MODEL_NAME)
    found = False
    found_table = None
    for t in candidates:
        if t in tables:
            found = True
            found_table = t
            break
    assert found, f"Table for model '{MODEL_NAME}' not found in database. Tried: {candidates}"
    print(f"✅ Table exists in database: {found_table}")
    return found_table

if __name__ == "__main__":
    print("\n=== VERIFY SCAFFOLDED MODEL/PLUGIN ===")
    print(f"Model: {MODEL_NAME}")
    print(f"DB URL: {DB_URL}")
    print(f"API Base: {API_BASE}")
    print(f"OpenAPI URL: {OPENAPI_URL}")
    print("--------------------------------------")
    try:
        route = check_route_in_openapi()
        methods = check_route_responds(route)
        table = check_table_in_db()
        print("\n🎉 All checks passed for model/plugin:", MODEL_NAME)
        print(f"  - API route: {route}")
        print(f"  - Table: {table}")
        print(f"  - Working HTTP methods: {[m for m, ok in methods.items() if ok]}")
    except Exception as e:
        print(f"\n❌ Verification failed: {e}")
        print("Suggestions:")
        print("- Ensure the app is running and accessible at the API base URL.")
        print("- Ensure the database is up and the connection string is correct.")
        print("- Double-check the model name, table name, and route.")
        print("- If using authentication, some endpoints may require a token (401/403 is OK).")
        print("- If you just scaffolded, make sure migrations are applied and the app is restarted.")
        sys.exit(1) 