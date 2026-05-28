from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr
import uuid


class UserPublic(BaseModel):
    id: uuid.UUID
    username: str
    name: Optional[str]
    college: Optional[str]
    avatar_url: Optional[str]
    github_login: Optional[str]
    lc_username: Optional[str]
    cf_handle: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class UserMe(UserPublic):
    email: str
    gh_username: Optional[str]
    last_synced: Optional[datetime]


class UserUpdate(BaseModel):
    lc_username: Optional[str] = None
    cf_handle: Optional[str] = None
    gh_username: Optional[str] = None
    name: Optional[str] = None
    college: Optional[str] = None


class TopicScoreOut(BaseModel):
    topic: str
    attempted: int
    solved: int
    accuracy: Optional[float]
    weakness_score: Optional[float]
    computed_at: datetime

    model_config = {"from_attributes": True}
