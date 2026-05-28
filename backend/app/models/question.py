from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, String, Text, ARRAY
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func
from sqlalchemy import TIMESTAMP
from ..database import Base
import uuid


class Question(Base):
    __tablename__ = "questions"
    id                = Column(Text, primary_key=True)
    platform          = Column(Text, nullable=False)
    number            = Column(Text)
    title             = Column(Text, nullable=False)
    slug              = Column(Text)
    url               = Column(Text, nullable=False)
    difficulty        = Column(Text)
    difficulty_rating = Column(Integer)
    statement_html    = Column(Text)
    statement_text    = Column(Text)
    constraints       = Column(JSONB)
    examples          = Column(JSONB)
    hints             = Column(JSONB)
    is_premium        = Column(Boolean, default=False)
    acceptance_rate   = Column(Float)
    solved_count      = Column(Integer)
    raw               = Column(JSONB)
    fetched_at        = Column(TIMESTAMP(timezone=True), server_default=func.now())


class QuestionTopic(Base):
    __tablename__ = "question_topics"
    question_id = Column(Text, ForeignKey("questions.id", ondelete="CASCADE"), primary_key=True)
    topic       = Column(Text, primary_key=True)


class QuestionCompany(Base):
    __tablename__ = "question_companies"
    question_id = Column(Text, ForeignKey("questions.id", ondelete="CASCADE"), primary_key=True)
    company     = Column(Text, primary_key=True)
    frequency   = Column(Integer)
    timeframe   = Column(Text, primary_key=True)


class RoadmapTopic(Base):
    __tablename__ = "roadmap_topics"
    topic               = Column(Text, primary_key=True)
    ordinal             = Column(Integer, unique=True, nullable=False)
    display_name        = Column(Text, nullable=False)
    prerequisite_topics = Column(ARRAY(Text))
    summary             = Column(Text)
    core_patterns       = Column(ARRAY(Text))
    starter_problems    = Column(ARRAY(Text))
    milestone_problems  = Column(ARRAY(Text))


class SheetSource(Base):
    __tablename__ = "sheet_sources"
    id            = Column(Text, primary_key=True)
    name          = Column(Text, nullable=False)
    url           = Column(Text)
    problem_count = Column(Integer)
    weight        = Column(Float, default=1.0)
    fetched_at    = Column(TIMESTAMP(timezone=True), server_default=func.now())


class CuratedSheetProblem(Base):
    __tablename__ = "curated_sheet_problems"
    sheet_id          = Column(Text, ForeignKey("curated_sheet.id", ondelete="CASCADE"), primary_key=True)
    question_id       = Column(Text, ForeignKey("questions.id", ondelete="CASCADE"), primary_key=True)
    topic             = Column(Text, nullable=False)
    ordinal           = Column(Integer, nullable=False)
    cross_sheet_count = Column(Integer)
    source_sheets     = Column(ARRAY(Text))
    score             = Column(Float)


class QuestionProgress(Base):
    __tablename__ = "question_progress"
    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id     = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    question_id = Column(Text, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False)
    status      = Column(Text, default="todo")
    notes       = Column(Text)
    updated_at  = Column(TIMESTAMP(timezone=True), server_default=func.now())


class SheetProgress(Base):
    __tablename__ = "sheet_progress"
    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id    = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    problem_id = Column(Text, nullable=False)
    status     = Column(Text, default="todo")
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
