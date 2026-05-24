# Clockify MCP Server

A FastMCP server that provides read-only access to Clockify time tracking data. Query time entries, projects, users, and workspace information through an AI agent.

## Features

- 🔍 Query time entries by user, date range, and project
- 📊 Get detailed time entry information
- 👥 List workspace users
- 📁 List projects, active project tasks, and tags
- ⏱️ Get currently running time entries
- 🏢 Access workspace information

## Setup

### 1. Install Dependencies

```bash
uv sync
```

### 2. Configure Environment Variables

Copy the example environment file and add your Clockify credentials:

```bash
cp .env.example .env
```

Edit `.env` and add:

- **CLOCKIFY_API_KEY**: Get from [Clockify Settings](https://app.clockify.me/user/settings) (API section)
- **CLOCKIFY_WORKSPACE_ID**: Find in your Clockify workspace settings or URL

### 3. Run the Server

```bash
uv run main.py
```

## Available Tools

### Time Entry Queries

#### `get_time_entries`
Get time entries for a specific user with optional filters.

**Parameters:**
- `user_id` (required): User ID
- `start_date` (optional): Start date in ISO format (e.g., "2024-01-01" or "2024-01-01T00:00:00")
- `end_date` (optional): End date in ISO format
- `project_id` (optional): Filter by project ID

**Example:**
```python
get_time_entries(
    user_id="64c777ddd3fcab07cfbb210c",
    start_date="2024-01-01",
    end_date="2024-01-31"
)
```

#### `get_time_entry_by_id`
Get a specific time entry by its ID.

**Parameters:**
- `entry_id` (required): Time entry ID

#### `get_in_progress_entries`
Get all currently running time entries in the workspace.

**Parameters:** None

### Supporting Queries

#### `list_workspace_users`
Get all users in the workspace with their IDs, names, and emails.

**Parameters:** None

#### `list_projects`
Get all projects in the workspace.

**Parameters:**
- `include_archived` (optional): Include archived projects (default: False)

#### `list_active_project_tasks`
Get active tasks for a specific project.

**Parameters:**
- `project_id` (required): Project ID

**Returns:**
JSON array of active task objects with `id`, `name`, `status`, and `project_id`.

**Example:**
```python
list_active_project_tasks(
    project_id="25b687e29ae1f428e7ebe123"
)
```

#### `list_tags`
Get all tags in the workspace.

**Parameters:** None

#### `get_workspace_info`
Get information about the current workspace.

**Parameters:** None

## Usage with AI Agents

This MCP server is designed to be used with AI agents. Example queries:

- "Show me all time entries for the last week"
- "What projects am I tracking time on?"
- "Show me the active task IDs for project X"
- "How many hours did I work on project X in January?"
- "Who is currently tracking time?"

## API Reference

This server uses the [Clockify API v1](https://docs.clockify.me/). All tools are read-only and do not modify any data.

## Project Structure

```
clockify-mcp-server/
├── main.py              # FastMCP server with tool definitions
├── clockify_client.py   # Clockify API client
├── models.py            # Pydantic data models
├── config.py            # Configuration management
├── .env.example         # Environment variables template
└── README.md            # This file
```

## License

MIT
