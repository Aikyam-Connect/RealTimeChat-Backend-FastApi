from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

# Use the property logic we defined
DATABASE_URL = settings.sqlalchemy_database_url

# For TiDB (MySQL) we might need pool_recycle
connect_args = {}
if "mysql" in DATABASE_URL:
    connect_args = {"ssl": {"ssl_mode": "VERIFY_IDENTITY"}}

# Create Engine
# Note: For TiDB/MySQL sometimes we need specific connect_args for SSL.
# PyMySQL usually handles ssl=True in query param or connect_args.
# We added ?ssl_verify_cert=true in the URL construction for pymysql which might handle it.
# Let's keep it simple.

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()