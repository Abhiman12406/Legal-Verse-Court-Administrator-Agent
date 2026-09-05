import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

logger = logging.getLogger("lexis_ops.db")

DEFAULT_PG_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+psycopg://temporal:temporal_password@localhost:5432/lexisops"
)
SQLITE_FALLBACK_URL = "sqlite:///./lexisops.db"

# Create engine with fallback resilience
engine = None
try:
    # Test primary engine
    test_engine = create_engine(
        DEFAULT_PG_URL,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 2} if "postgres" in DEFAULT_PG_URL else {},
    )
    # Quick connectivity test
    with test_engine.connect() as conn:
        pass
    engine = test_engine
    logger.info("Connected to primary PostgreSQL database engine.")
except Exception as e:
    logger.warning(
        f"PostgreSQL connection to '{DEFAULT_PG_URL}' unavailable ({e}). "
        f"Falling back to local ACID SQLite storage: {SQLITE_FALLBACK_URL}"
    )
    engine = create_engine(
        SQLITE_FALLBACK_URL,
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """
    FastAPI dependency that yields an ACID database session.
    Automatically closes session after request handling.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initializes database tables defined in SQLAlchemy models.
    """
    from lexis_ops.db import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
