"""Client for interacting with the Clockify API."""

from datetime import datetime
from typing import Any, Optional

import httpx

from config import config
from models import ProjectSummary, Tag, TaskSummary, TimeEntry, User, Workspace
from timeutil import DateLike, to_clockify_utc

# Sentinel so update_time_entry can tell "not provided" apart from an explicit None.
UNSET: Any = object()


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
        data, _ = await self._get_response(endpoint, params=params)
        return data

    async def _get_response(
        self, endpoint: str, params: Optional[dict[str, Any]] = None
    ) -> tuple[Any, httpx.Headers]:
        """Make a GET request to the Clockify API and return data with headers."""
        url = f"{self.base_url}{endpoint}"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json(), response.headers

    async def _send(
        self,
        method: str,
        endpoint: str,
        json_body: Optional[dict[str, Any]] = None,
    ) -> Any:
        """Make a write request (POST/PUT/DELETE) to the Clockify API."""
        url = f"{self.base_url}{endpoint}"
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method, url, headers=self.headers, json=json_body
            )
            if response.is_error:
                raise RuntimeError(
                    f"Clockify API {method} {endpoint} failed "
                    f"({response.status_code}): {response.text}"
                )
            if response.status_code == 204 or not response.content:
                return None
            return response.json()

    async def get_current_user(self) -> User:
        """Get the user that owns the API key."""
        data = await self._get("/user")
        return User.model_validate(data)

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

    async def get_project_tasks(
        self,
        project_id: str,
        workspace_id: Optional[str] = None,
        is_active: bool = True,
        page_size: int = 50,
    ) -> list[TaskSummary]:
        """Get tasks for a specific project."""
        ws_id = workspace_id or self.workspace_id
        tasks: list[TaskSummary] = []
        page = 1

        while True:
            params: dict[str, Any] = {
                "is-active": str(is_active).lower(),
                "page": page,
                "page-size": page_size,
                "sort-column": "NAME",
                "sort-order": "ASCENDING",
            }
            data, headers = await self._get_response(
                f"/workspaces/{ws_id}/projects/{project_id}/tasks",
                params=params,
            )
            page_tasks = [TaskSummary.model_validate(task) for task in data]
            tasks.extend(page_tasks)

            last_page = headers.get("Last-Page", "").lower() == "true"
            if last_page or len(page_tasks) < page_size:
                break

            page += 1

        return tasks

    async def create_project_task(
        self,
        project_id: str,
        name: str,
        billable: Optional[bool] = None,
        workspace_id: Optional[str] = None,
    ) -> TaskSummary:
        """
        Create a task on a project.

        Raises ValueError if a task with the same name (case-insensitive) already
        exists on the project, whether active or done.
        """
        ws_id = workspace_id or self.workspace_id
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Task name must not be empty")

        existing = await self.get_project_tasks(project_id, workspace_id=ws_id, is_active=True)
        existing += await self.get_project_tasks(project_id, workspace_id=ws_id, is_active=False)
        for task in existing:
            if task.name.strip().lower() == clean_name.lower():
                raise ValueError(
                    f"Task '{task.name}' already exists on this project (id {task.id})"
                )

        body: dict[str, Any] = {"name": clean_name, "status": "ACTIVE"}
        if billable is not None:
            body["billable"] = billable
        data = await self._send(
            "POST", f"/workspaces/{ws_id}/projects/{project_id}/tasks", body
        )
        task = TaskSummary.model_validate(data)
        if not task.project_id:
            task.project_id = project_id
        return task

    async def get_active_project_tasks(
        self,
        project_id: str,
        workspace_id: Optional[str] = None,
        page_size: int = 50,
    ) -> list[TaskSummary]:
        """Get active tasks for a specific project."""
        tasks = await self.get_project_tasks(
            project_id=project_id,
            workspace_id=workspace_id,
            is_active=True,
            page_size=page_size,
        )
        active_tasks: list[TaskSummary] = []

        for task in tasks:
            if task.status and task.status.upper() != "ACTIVE":
                continue
            active_tasks.append(
                TaskSummary(
                    id=task.id,
                    name=task.name,
                    status="ACTIVE",
                    project_id=task.project_id or project_id,
                )
            )

        return active_tasks

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
        start_date: Optional[DateLike] = None,
        end_date: Optional[DateLike] = None,
        workspace_id: Optional[str] = None,
        project_id: Optional[str] = None,
        hydrated: bool = True,
        page_size: int = 200,
    ) -> list[TimeEntry]:
        """
        Get all time entries for a user with optional filters, following pagination.

        Dates without an offset are interpreted in the configured local timezone.
        A date-only end_date includes that whole day.
        """
        ws_id = workspace_id or self.workspace_id
        base_params: dict[str, Any] = {
            "hydrated": str(hydrated).lower(),
            "page-size": page_size,
        }
        if start_date:
            base_params["start"] = to_clockify_utc(start_date)
        if end_date:
            base_params["end"] = to_clockify_utc(end_date, end_of_day=True)
        if project_id:
            base_params["project"] = project_id

        entries: list[TimeEntry] = []
        page = 1
        while True:
            params = {**base_params, "page": page}
            data, headers = await self._get_response(
                f"/workspaces/{ws_id}/user/{user_id}/time-entries",
                params=params,
            )
            page_entries = [TimeEntry.model_validate(entry) for entry in data]
            entries.extend(page_entries)

            last_page = str(headers.get("Last-Page", "")).lower() == "true"
            if last_page or len(page_entries) < page_size:
                break
            page += 1

        return entries

    async def create_time_entry(
        self,
        start: DateLike,
        end: DateLike,
        description: Optional[str] = None,
        project_id: Optional[str] = None,
        task_id: Optional[str] = None,
        billable: Optional[bool] = None,
        tag_ids: Optional[list[str]] = None,
        workspace_id: Optional[str] = None,
    ) -> TimeEntry:
        """Create a completed time entry for the API key's user."""
        ws_id = workspace_id or self.workspace_id
        body: dict[str, Any] = {
            "start": to_clockify_utc(start),
            "end": to_clockify_utc(end),
        }
        if description is not None:
            body["description"] = description
        if project_id:
            body["projectId"] = project_id
        if task_id:
            body["taskId"] = task_id
        if billable is not None:
            body["billable"] = billable
        if tag_ids:
            body["tagIds"] = tag_ids

        data = await self._send("POST", f"/workspaces/{ws_id}/time-entries", body)
        return TimeEntry.model_validate(data)

    async def update_time_entry(
        self,
        entry_id: str,
        start: Any = UNSET,
        end: Any = UNSET,
        description: Any = UNSET,
        project_id: Any = UNSET,
        task_id: Any = UNSET,
        billable: Any = UNSET,
        tag_ids: Any = UNSET,
        workspace_id: Optional[str] = None,
    ) -> TimeEntry:
        """
        Update a time entry. Only provided fields change; the rest are kept.

        Clockify's PUT replaces the whole entry, so the current entry is fetched and
        merged first. Changing the project without giving a task clears the task.
        """
        ws_id = workspace_id or self.workspace_id
        current = await self.get_time_entry(entry_id, workspace_id=ws_id, hydrated=False)

        body: dict[str, Any] = {
            "start": to_clockify_utc(current.time_interval.start),
            "description": current.description or "",
            "billable": current.billable,
        }
        if current.time_interval.end is not None:
            body["end"] = to_clockify_utc(current.time_interval.end)
        if current.project_id:
            body["projectId"] = current.project_id
        if current.task_id:
            body["taskId"] = current.task_id
        if current.tag_ids:
            body["tagIds"] = current.tag_ids

        if start is not UNSET:
            body["start"] = to_clockify_utc(start)
        if end is not UNSET:
            body["end"] = to_clockify_utc(end)
        if description is not UNSET:
            body["description"] = description or ""
        if billable is not UNSET:
            body["billable"] = bool(billable)
        if tag_ids is not UNSET:
            body["tagIds"] = tag_ids or []
        if project_id is not UNSET:
            if project_id:
                body["projectId"] = project_id
            else:
                body.pop("projectId", None)
            if task_id is UNSET and project_id != current.project_id:
                body.pop("taskId", None)
        if task_id is not UNSET:
            if task_id:
                body["taskId"] = task_id
            else:
                body.pop("taskId", None)

        data = await self._send(
            "PUT", f"/workspaces/{ws_id}/time-entries/{entry_id}", body
        )
        return TimeEntry.model_validate(data)

    async def delete_time_entry(
        self, entry_id: str, workspace_id: Optional[str] = None
    ) -> None:
        """Delete a single time entry by ID."""
        ws_id = workspace_id or self.workspace_id
        await self._send("DELETE", f"/workspaces/{ws_id}/time-entries/{entry_id}")

    async def get_in_progress_time_entries(
        self, workspace_id: Optional[str] = None
    ) -> list[TimeEntry]:
        """Get all currently running time entries in the workspace."""
        ws_id = workspace_id or self.workspace_id
        data = await self._get(
            f"/workspaces/{ws_id}/time-entries/in-progress"
        )
        return [TimeEntry.model_validate(entry) for entry in data]
