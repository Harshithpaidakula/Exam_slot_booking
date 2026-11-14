# This file connects the application to PostgreSQL.

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Change this URL to match your PostgreSQL database.
DATABASE_URL = "postgresql://postgres:password@localhost:5432/exam_guard"

# Create the database connection.
engine = create_engine(DATABASE_URL)

# Create a new database session when a route needs the database.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base is used by models.py to define database tables.
Base = declarative_base()


# Create all tables defined in models.py.
def create_tables():
    Base.metadata.create_all(bind=engine)


# Give a route a database session, then close it when the route finishes.
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
