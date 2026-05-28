from __future__ import annotations
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel


class CompanyOut(BaseModel):
    name: str
    frequency: Optional[int]
    timeframe: Optional[str]


class QuestionOut(BaseModel):
    id: str
    platform: str
    number: Optional[str]
    title: str
    slug: Optional[str]
    url: str
    difficulty: Optional[str]
    difficulty_rating: Optional[int]
    statement_html: Optional[str]
    is_premium: bool
    acceptance_rate: Optional[float]
    solved_count: Optional[int]
    topics: list[str] = []
    companies: list[CompanyOut] = []

    model_config = {"from_attributes": True}


class QuestionProgressUpdate(BaseModel):
    status: str  # 'todo' | 'attempted' | 'done'
    notes: Optional[str] = None


class RoadmapTopicOut(BaseModel):
    topic: str
    ordinal: int
    display_name: str
    prerequisite_topics: Optional[list[str]]
    summary: Optional[str]
    core_patterns: Optional[list[str]]
    starter_problems: Optional[list[str]]
    milestone_problems: Optional[list[str]]
    # runtime-computed
    user_solved: int = 0
    user_attempted: int = 0
    weakness_score: Optional[float] = None

    model_config = {"from_attributes": True}


class CuratedProblemOut(BaseModel):
    question_id: str
    topic: str
    ordinal: int
    cross_sheet_count: Optional[int]
    source_sheets: Optional[list[str]]
    score: Optional[float]
    title: str
    url: str
    difficulty: Optional[str]
    platform: str
    status: str = "todo"  # user progress


class SheetSourceOut(BaseModel):
    id: str
    name: str
    url: Optional[str]
    problem_count: Optional[int]
    weight: float
