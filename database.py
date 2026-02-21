# database.py
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

# Get DB URL from environment variables, with a fallback for local development
DATABASE_URL = os.getenv("DB_URL", "sqlite:///./app.db")

# Create the SQLAlchemy engine
# The `connect_args` is needed only for SQLite to allow multi-threaded access
engine_args = {}
if DATABASE_URL.startswith("sqlite"):
    engine_args["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **engine_args)

# Create a SessionLocal class, which will be a factory for new Session objects
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create a Base class for our models to inherit from
Base = declarative_base()

# --- Dependency for getting a DB session ---
def get_db():
    """
    FastAPI dependency to provide a database session per request.
    Ensures the session is always closed after the request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
