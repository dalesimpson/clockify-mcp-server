"""Data models for Clockify API responses."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class TimeInterval(BaseModel):
    """Time interval with start and end times."""

    start: datetime
    end: Optional[datetime] = None
    duration: Optional[str] = None


class Project(BaseModel):
    """Project information."""

    id: str
    name: str
    color: Optional[str] = None
    client_id: Optional[str] = Field(None, alias="clientId")
    client_name: Optional[str] = Field(None, alias="clientName")


class Task(BaseModel):
    """Task information."""

    id: str
    name: str
    project_id: Optional[str] = Field(None, alias="projectId")


class Tag(BaseModel):
    """Tag information."""

    id: str
    name: str
    workspace_id: Optional[str] = Field(None, alias="workspaceId")


class User(BaseModel):
    """User information."""

    id: str
    name: str
    email: Optional[str] = None
    status: Optional[str] = None


class TimeEntry(BaseModel):
    """Time entry information."""

    id: str
    description: Optional[str] = None
    user_id: str = Field(alias="userId")
    billable: bool = False
    project_id: Optional[str] = Field(None, alias="projectId")
    task_id: Optional[str] = Field(None, alias="taskId")
    time_interval: TimeInterval = Field(alias="timeInterval")
    workspace_id: str = Field(alias="workspaceId")
    tags: list[Tag] = Field(default_factory=list)
    project: Optional[Project] = None
    task: Optional[Task] = None
    type: Optional[str] = None
    
    class Config:
        populate_by_name = True


class Workspace(BaseModel):
    """Workspace information."""

    id: str
    name: str
    image_url: Optional[str] = Field(None, alias="imageUrl")
    
    class Config:
        populate_by_name = True


class ProjectSummary(BaseModel):
    """Summary information for a project."""

    id: str
    name: str
    client_id: Optional[str] = Field(None, alias="clientId")
    client_name: Optional[str] = Field(None, alias="clientName")
    color: Optional[str] = None
    archived: bool = False
    
    class Config:
        populate_by_name = True
