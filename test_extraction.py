output = """INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.autogenerate.compare] Detected added table 'products'
INFO  [alembic.autogenerate.compare] Detected added index ''ix_products_id'' on '('id',)'
INFO  [alembic.ddl.postgresql] Detected sequence named 'users_id_seq' as owned by integer column 'users(id)', assuming SERIAL and omitting
  Generating /Users/shantanubombatkar/Documents/code/codeSn/fastAPI_PostGres/alembic/versions/32bf4ac2c1ab_add_product_model.py ...  done"""

# Test the extraction logic
lines = output.strip().split("\n")
for line in lines:
    if "Generating" in line and ".py" in line and "..." in line:
        parts = line.split()
        for part in parts:
            if part.endswith(".py"):
                break
