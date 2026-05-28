from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func
from sqlalchemy import TIMESTAMP
from ..database import Base
import uuid


class User(Base):
    __tablename__ = "users"
    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email         = Column(Text, unique=True, nullable=False)
    name          = Column(Text)
    username      = Column(Text, unique=True, nullable=False)
    college       = Column(Text, default="VJTI")
    avatar_url    = Column(Text)
    github_login  = Column(Text, unique=True)
    lc_username   = Column(Text)
    cf_handle     = Column(Text)
    gh_username   = Column(Text)
    created_at    = Column(TIMESTAMP(timezone=True), server_default=func.now())
    last_synced   = Column(TIMESTAMP(timezone=True))


class PlatformSnapshot(Base):
    __tablename__ = "platform_snapshots"
    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id    = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    platform   = Column(Text, nullable=False)
    raw_data   = Column(JSONB, nullable=False)
    fetched_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


class TopicScore(Base):
    __tablename__ = "topic_scores"
    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id        = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    topic          = Column(Text, nullable=False)
    attempted      = Column(Integer, default=0)
    solved         = Column(Integer, default=0)
    accuracy       = Column(Float)
    weakness_score = Column(Float)
    computed_at    = Column(TIMESTAMP(timezone=True), server_default=func.now())
