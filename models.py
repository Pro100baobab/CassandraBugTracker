from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from uuid import UUID
from datetime import datetime
from enum import Enum


class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Status(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"
    REOPENED = "reopened"


class UserRole(str, Enum):
    ADMIN = "admin"
    DEVELOPER = "developer"
    TESTER = "tester"
    PROJECT_MANAGER = "project_manager"


# Модели для запросов
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    role: UserRole = UserRole.DEVELOPER


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


class IssueCreate(BaseModel):
    project_id: UUID
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1)
    status: Status = Status.OPEN
    priority: Priority = Priority.MEDIUM
    assignee_id: Optional[UUID] = None
    reporter_id: UUID
    component: Optional[str] = Field(None, max_length=100)


class IssueUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, min_length=1)
    status: Optional[Status] = None
    priority: Optional[Priority] = None
    assignee_id: Optional[UUID] = None
    component: Optional[str] = Field(None, max_length=100)


class CommentCreate(BaseModel):
    user_id: UUID
    content: str = Field(..., min_length=1, max_length=1000)


# Модели для ответов
class UserResponse(BaseModel):
    user_id: UUID
    username: str
    email: str
    role: UserRole
    created_at: datetime


class ProjectResponse(BaseModel):
    project_id: UUID
    name: str
    description: Optional[str]
    created_at: datetime


class IssueResponse(BaseModel):
    issue_id: UUID
    project_id: UUID
    title: str
    description: str
    status: Status
    priority: Priority
    assignee_id: Optional[UUID]
    reporter_id: UUID
    component: Optional[str]
    created_at: datetime
    updated_at: datetime


class CommentResponse(BaseModel):
    comment_id: UUID
    issue_id: UUID
    project_id: UUID
    user_id: UUID
    content: str
    created_at: datetime


class HistoryEventResponse(BaseModel):
    event_id: UUID
    issue_id: UUID
    project_id: UUID
    field_changed: str
    old_value: Optional[str]
    new_value: Optional[str]
    changed_by: UUID
    changed_at: datetime


class ProjectStatistics(BaseModel):
    project_id: UUID
    total_issues: int
    issues_by_status: dict
    issues_by_priority: dict
    issues_by_component: dict
