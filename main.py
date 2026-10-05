"""Clockify MCP Server for querying time tracking data."""

import json
from typing import Optional

from fastmcp import FastMCP

from clockify_client import UNSET, ClockifyClient

# Initialize FastMCP server
mcp = FastMCP(
    name="Clockify Time Tracker",
    instructions="""
    This server provides access to Clockify time tracking data.
    Use the read tools to query time entries, projects, tasks, tags, users, and
    workspace information. Use create_time_entry, update_time_entry, and
    delete_time_entry to write time entries for the API key's user, and
    create_task to add a task to a project.
    Times without a UTC offset are interpreted in the configured local timezone
    (CLOCKIFY_TIMEZONE, default America/Toronto).
    """,
)

# Initialize Clockify client
client = ClockifyClient()


@mcp.tool
async def get_time_entries(
    user_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    project_id: Optional[str] = None,
) -> str:
    """
    Get time entries for a specific user within a date range.
    
    Args:
        user_id: The ID of the user whose time entries to retrieve
        start_date: Start date in ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS).
            Values without an offset are local time (default America/Toronto).
        end_date: End date in ISO format. A date-only value includes that whole day.
        project_id: Optional project ID to filter entries

    Returns all matching entries (pagination is handled automatically).

    Returns:
        JSON string containing list of time entries
    """
    entries = await client.get_user_time_entries(
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        project_id=project_id,
    )
    
    return "\n".join([entry.model_dump_json(indent=2) for entry in entries])


@mcp.tool
async def get_time_entry_by_id(entry_id: str) -> str:
    """
    Get a specific time entry by its ID.
    
    Args:
        entry_id: The ID of the time entry to retrieve
    
    Returns:
        JSON string containing the time entry details
    """
    entry = await client.get_time_entry(entry_id)
    return entry.model_dump_json(indent=2)


@mcp.tool
async def get_in_progress_entries() -> str:
    """
    Get all currently running time entries in the workspace.
    
    Returns:
        JSON string containing list of in-progress time entries
    """
    entries = await client.get_in_progress_time_entries()
    return "\n".join([entry.model_dump_json(indent=2) for entry in entries])


@mcp.tool
async def list_workspace_users() -> str:
    """
    Get all users in the workspace.
    
    Returns:
        JSON string containing list of users with their IDs, names, and emails
    """
    users = await client.get_users()
    return "\n".join([user.model_dump_json(indent=2) for user in users])


@mcp.tool
async def list_projects(include_archived: bool = False) -> str:
    """
    Get all projects in the workspace.
    
    Args:
        include_archived: Whether to include archived projects (default: False)
    
    Returns:
        JSON string containing list of projects
    """
    projects = await client.get_projects(archived=include_archived)
    return "\n".join([project.model_dump_json(indent=2) for project in projects])


@mcp.tool
async def list_active_project_tasks(project_id: str) -> str:
    """
    Get active tasks for a specific project.

    Args:
        project_id: The ID of the project whose active tasks to retrieve

    Returns:
        JSON array containing active task IDs, names, statuses, and project IDs
    """
    tasks = await client.get_active_project_tasks(project_id=project_id)
    return json.dumps(
        [task.model_dump(by_alias=False) for task in tasks],
        indent=2,
    )


@mcp.tool
async def list_tags() -> str:
    """
    Get all tags in the workspace.
    
    Returns:
        JSON string containing list of tags
    """
    tags = await client.get_tags()
    return "\n".join([tag.model_dump_json(indent=2) for tag in tags])


@mcp.tool
async def get_workspace_info() -> str:
    """
    Get information about the current workspace.
    
    Returns:
        JSON string containing workspace details
    """
    workspace = await client.get_workspace()
    return workspace.model_dump_json(indent=2)


@mcp.tool
async def get_current_user() -> str:
    """
    Get the Clockify user that owns the API key (the user time entries are created for).

    Returns:
        JSON string with the user's ID, name, and email
    """
    user = await client.get_current_user()
    return user.model_dump_json(indent=2)


@mcp.tool
async def create_time_entry(
    start: str,
    end: str,
    description: Optional[str] = None,
    project_id: Optional[str] = None,
    task_id: Optional[str] = None,
    billable: Optional[bool] = None,
    tag_ids: Optional[list[str]] = None,
) -> str:
    """
    Create a completed time entry for the API key's user.

    Args:
        start: Start time in ISO format, e.g. "2026-09-15T09:00:00". Values without
            an offset are local time (default America/Toronto).
        end: End time in ISO format, same rules as start.
        description: Entry description
        project_id: Project ID (see list_projects)
        task_id: Task ID within the project (see list_active_project_tasks)
        billable: Whether the entry is billable (omit to use the project default)
        tag_ids: Optional list of tag IDs (see list_tags)

    Returns:
        JSON string containing the created time entry
    """
    entry = await client.create_time_entry(
        start=start,
        end=end,
        description=description,
        project_id=project_id,
        task_id=task_id,
        billable=billable,
        tag_ids=tag_ids,
    )
    return entry.model_dump_json(indent=2)


@mcp.tool
async def update_time_entry(
    entry_id: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
    description: Optional[str] = None,
    project_id: Optional[str] = None,
    task_id: Optional[str] = None,
    billable: Optional[bool] = None,
    tag_ids: Optional[list[str]] = None,
) -> str:
    """
    Update an existing time entry. Only the fields you pass are changed.

    Args:
        entry_id: ID of the time entry to update
        start: New start time (ISO format; no offset means local time)
        end: New end time (ISO format; no offset means local time)
        description: New description
        project_id: New project ID. Changing the project without a task_id clears the task.
        task_id: New task ID
        billable: New billable flag
        tag_ids: Replacement list of tag IDs

    Returns:
        JSON string containing the updated time entry
    """
    def given(value):
        return UNSET if value is None else value

    entry = await client.update_time_entry(
        entry_id,
        start=given(start),
        end=given(end),
        description=given(description),
        project_id=given(project_id),
        task_id=given(task_id),
        billable=given(billable),
        tag_ids=given(tag_ids),
    )
    return entry.model_dump_json(indent=2)


@mcp.tool
async def delete_time_entry(entry_id: str) -> str:
    """
    Delete a single time entry by ID. This cannot be undone.

    Args:
        entry_id: ID of the time entry to delete

    Returns:
        Confirmation message
    """
    await client.delete_time_entry(entry_id)
    return json.dumps({"deleted": entry_id})


@mcp.tool
async def create_task(
    project_id: str,
    name: str,
    billable: Optional[bool] = None,
) -> str:
    """
    Create a new active task on a project.

    Fails if a task with the same name (case-insensitive) already exists on the
    project, including completed tasks.

    Args:
        project_id: Project ID (see list_projects)
        name: Task name
        billable: Whether the task is billable (omit to use the project default)

    Returns:
        JSON object with the new task's id, name, status, and project_id
    """
    task = await client.create_project_task(
        project_id=project_id, name=name, billable=billable
    )
    return json.dumps(task.model_dump(by_alias=False), indent=2)


if __name__ == "__main__":
    mcp.run()
