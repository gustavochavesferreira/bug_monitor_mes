import os
import json
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import (
    Column, Integer, BigInteger, String, Text, DateTime, create_engine
)
from sqlalchemy.orm import declarative_base, sessionmaker

# Load .env from project root
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set. Check your .env or docker-compose.")

Base = declarative_base()

# SQLAlchemy engine for PostgreSQL
engine = create_engine(
    DATABASE_URL,
    echo=False,
    future=True
)

# Session factory
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False
)

class Issue(Base):
    __tablename__ = "issues"

    id = Column(BigInteger, primary_key=True)
    number = Column(Integer)
    title = Column(Text)
    body = Column(Text)
    state = Column(String(20))
    created_at = Column(DateTime)
    closed_at = Column(DateTime)
    closed_by = Column(String(200))
    creator = Column(String(200))
    comments_count = Column(Integer)
    labels = Column(Text)  # JSON list
    html_url = Column(String(400))
    repository = Column(String(200))

    def to_dict(self):
        return {
            "id": self.id,
            "number": self.number,
            "title": self.title,
            "body": self.body,
            "state": self.state,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
            "closed_by": self.closed_by,
            "creator": self.creator,
            "comments_count": self.comments_count,
            "labels": json.loads(self.labels) if self.labels else [],
            "html_url": self.html_url,
            "repository": self.repository,
        }

def init_db():
    """Create all tables in PostgreSQL."""
    Base.metadata.create_all(bind=engine)

def upsert_issue(session, data):
    """Insert or update issue."""
    existing = session.query(Issue).filter(Issue.id == data["id"]).one_or_none()

    # Normalize JSON field
    if "labels" in data:
        data["labels"] = json.dumps(data["labels"])

    if existing:
        for k, v in data.items():
            setattr(existing, k, v)
    else:
        session.add(Issue(**data))
