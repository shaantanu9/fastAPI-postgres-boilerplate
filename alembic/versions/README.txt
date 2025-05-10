This directory stores Alembic migration scripts. Each migration tracks changes to the database schema, such as creating or altering tables and columns. Migrations are auto-generated or manually written using Alembic commands.

- To create a new migration: alembic revision --autogenerate -m "describe change"
- To apply migrations: alembic upgrade head
- To view migration history: alembic history

For more info, see: https://alembic.sqlalchemy.org/en/latest/
