"""Client for interacting with the Clockify API."""

from datetime import datetime
from typing import Any, Optional

import httpx

from config import config
from models import ProjectSummary, Tag, TimeEntry, User, Workspace


class ClockifyClient:
    """Client for making requests to the Clockify API."""

    def __init__(self):
        """Initialize the Clockify client."""
        config.validate()
        self.base_url = config.base_url
        self.headers = config.headers
        self.workspace_id = config.workspace_id

    async def _get(self, endpoint: str, params: Optional[dict[str, Any]] = None) -> Any:
        """Make a GET request to the Clockify API."""
        url = f"{self.base_url}{endpoint}"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()

    async def get_workspace(self, workspace_id: Optional[str] = None) -> Workspace:
        """Get workspace information."""
        ws_id = workspace_id or self.workspace_id
        data = await self._get(f"/workspaces/{ws_id}")
        return Workspace.model_validate(data)

    async def get_users(self, workspace_id: Optional[str] = None) -> list[User]:
        """Get all users in the workspace."""
        ws_id = workspace_id or self.workspace_id
        data = await self._get(f"/workspaces/{ws_id}/users")
        return [User.model_validate(user) for user in data]

    async def get_projects(
        self,
        workspace_id: Optional[str] = None,
        archived: bool = False,
    ) -> list[ProjectSummary]:
        """Get all projects in the workspace."""
        ws_id = workspace_id or self.workspace_id
        params = {"archived": str(archived).lower()}
        data = await self._get(f"/workspaces/{ws_id}/projects", params=params)
        return [ProjectSummary.model_validate(project) for project in data]

    async def get_tags(self, workspace_id: Optional[str] = None) -> list[Tag]:
        """Get all tags in the workspace."""
        ws_id = workspace_id or self.workspace_id
        data = await self._get(f"/workspaces/{ws_id}/tags")
        return [Tag.model_validate(tag) for tag in data]

    async def get_time_entry(
        self,
        entry_id: str,
        workspace_id: Optional[str] = None,
        hydrated: bool = True,
    ) -> TimeEntry:
        """Get a specific time entry by ID."""
        ws_id = workspace_id or self.workspace_id
        params = {"hydrated": str(hydrated).lower()}
        data = await self._get(
            f"/workspaces/{ws_id}/time-entries/{entry_id}",
            params=params,
        )
        return TimeEntry.model_validate(data)

    async def get_user_time_entries(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        workspace_id: Optional[str] = None,
        project_id: Optional[str] = None,
        hydrated: bool = True,
        page_size: int = 50,
    ) -> list[TimeEntry]:
        """Get time entries for a specific user with optional filters."""
        ws_id = workspace_id or self.workspace_id
        params: dict[str, Any] = {
            "hydrated": str(hydrated).lower(),
            "page-size": page_size,
        }
        
        if start_date:
            params["start"] = start_date.isoformat()
        if end_date:
            params["end"] = end_date.isoformat()
        if project_id:
            params["project"] = project_id

        data = await self._get(
            f"/workspaces/{ws_id}/user/{user_id}/time-entries",
            params=params,
        )
        return [TimeEntry.model_validate(entry) for entry in data]

    async def get_in_progress_time_entries(
        self, workspace_id: Optional[str] = None
    ) -> list[TimeEntry]:
        """Get all currently running time entries in the workspace."""
        ws_id = workspace_id or self.workspace_id
        data = await self._get(
            f"/workspaces/{ws_id}/time-entries/in-progress"
        )
        return [TimeEntry.model_validate(entry) for entry in data]
