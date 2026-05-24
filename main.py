"""Clockify MCP Server for querying time tracking data."""

import json
from datetime import datetime
from typing import Optional

from fastmcp import FastMCP

from clockify_client import ClockifyClient

# Initialize FastMCP server
mcp = FastMCP(
    name="Clockify Time Tracker",
    instructions="""
    This server provides read-only access to Clockify time tracking data.
    Use these tools to query time entries, projects, users, and workspace information.
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
        start_date: Start date in ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)
        end_date: End date in ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)
        project_id: Optional project ID to filter entries
    
    Returns:
        JSON string containing list of time entries
    """
    start = datetime.fromisoformat(start_date) if start_date else None
    end = datetime.fromisoformat(end_date) if end_date else None
    
    entries = await client.get_user_time_entries(
        user_id=user_id,
        start_date=start,
        end_date=end,
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


if __name__ == "__main__":
    mcp.run()
