"""
Database configuration and connection setup for Smart Factory (Async Version)
"""

import os
import logging

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text

logger = logging.getLogger(__name__)

# Database configuration from environment variables
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://smartfactory:password123@localhost:5432/smartfactory",
)

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=True,  # Set to False in production
    pool_pre_ping=True,  # Validate connections before use
    pool_recycle=3600,  # Recycle connections every hour
    future=True,
)

# Create async sessionmaker
SessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
    class_=AsyncSession,
)

# Create base class for declarative models
Base = declarative_base()


async def get_db():
    """
    Async dependency to get the database session.
    Usage in FastAPI:
        async def endpoint(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with SessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def init_database() -> AsyncSession:
    """Initialize database - create all tables (async version)"""
    try:
        # Import all models so SQLAlchemy registers them
        from app.models import acl_models, ss_models, mqtt_models

        logger.info("Creating database tables...")

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        logger.info("Database tables created successfully!")

        # Initialize default data
        try:
            from app.database.init_data import create_default_data

            async with get_db as db:
                await create_default_data(db)
                return db
        except Exception as e:
            logger.error(f"Error creating default data: {e}")

    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise


async def test_connection():
    """Test database connection (async)"""
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        logger.info("Database connection successful!")
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False
