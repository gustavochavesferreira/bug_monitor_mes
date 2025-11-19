# backend/models.py
import json
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = "sqlite:///bugs.db"

Base = declarative_base()
engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Issue(Base):
    __tablename__ = "issues"
    id = Column(Integer, primary_key=True)
    number = Column(Integer)
    title = Column(Text)
    body = Column(Text)
    state = Column(String(20))
    created_at = Column(DateTime)
    closed_at = Column(DateTime)
    closed_by = Column(String(200))
    creator = Column(String(200))
    comments_count = Column(Integer)
    labels = Column(Text)          # JSON list
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
    Base.metadata.create_all(bind=engine)

def upsert_issue(session, data):
    existing = session.query(Issue).filter(Issue.id == data["id"]).one_or_none()
    if existing:
        for k, v in data.items():
            if k == "labels":
                v = json.dumps(v)
            setattr(existing, k, v)
    else:
        session.add(Issue(
            **{k: (json.dumps(v) if k == "labels" else v) for k, v in data.items()}
        ))
