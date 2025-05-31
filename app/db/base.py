from sqlalchemy.orm import declarative_base

Base = declarative_base()

# Import all models here so Alembic's autogenerate can see them
from app.db.models.user import User






from app.db.models.product import Product
