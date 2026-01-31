"""Database connection and session management."""

import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from src.db.models import Base


class Database:
    """Database connection manager."""

    def __init__(self, database_url: str = None):
        """Initialize database connection.

        Args:
            database_url: SQLAlchemy database URL. If None, uses SQLite in current directory.
        """
        if database_url is None:
            database_url = "sqlite:///briefbot.db"

        # SQLite-specific settings for better concurrency
        connect_args = {}
        poolclass = None
        if database_url.startswith("sqlite"):
            connect_args = {"check_same_thread": False}
            # Use StaticPool for in-memory databases
            if ":memory:" in database_url:
                poolclass = StaticPool

        self.engine = create_engine(
            database_url,
            connect_args=connect_args,
            poolclass=poolclass,
            echo=os.getenv("SQL_DEBUG", "false").lower() == "true",
        )
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )

    def create_tables(self):
        """Create all tables in the database."""
        Base.metadata.create_all(bind=self.engine)

    def get_session(self) -> Generator[Session, None, None]:
        """Get a database session.

        Yields:
            SQLAlchemy Session object
        """
        session = self.SessionLocal()
        try:
            yield session
        finally:
            session.close()

    def get_sync_session(self) -> Session:
        """Get a synchronous database session (for non-async contexts).

        Returns:
            SQLAlchemy Session object (must be closed manually)
        """
        return self.SessionLocal()


# Global database instance
db = Database()


def init_db(database_url: str = None):
    """Initialize database with tables.

    Args:
        database_url: SQLAlchemy database URL
    """
    global db
    db = Database(database_url)
    db.create_tables()


def get_db_session() -> Generator[Session, None, None]:
    """Dependency to get database session.

    Yields:
        SQLAlchemy Session object
    """
    return db.get_session()
