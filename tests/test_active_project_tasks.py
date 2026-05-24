import importlib
import json
import unittest

from clockify_client import ClockifyClient
from config import config
from models import TaskSummary


class FakeClockifyClient(ClockifyClient):
    def __init__(self, responses):
        self.base_url = "https://api.clockify.me/api/v1"
        self.headers = {"X-Api-Key": "test"}
        self.workspace_id = "workspace-id"
        self.responses = responses
        self.calls = []

    async def _get_response(self, endpoint, params=None):
        self.calls.append((endpoint, params))
        return self.responses.pop(0)


class ActiveProjectTaskTests(unittest.IsolatedAsyncioTestCase):
    async def test_get_project_tasks_sends_active_filter_and_endpoint(self):
        client = FakeClockifyClient(
            [
                (
                    [
                        {
                            "id": "task-1",
                            "name": "Build",
                            "status": "ACTIVE",
                            "projectId": "project-1",
                        }
                    ],
                    {"Last-Page": "true"},
                )
            ]
        )

        tasks = await client.get_project_tasks("project-1")

        self.assertEqual(len(tasks), 1)
        self.assertEqual(
            client.calls[0][0],
            "/workspaces/workspace-id/projects/project-1/tasks",
        )
        self.assertEqual(client.calls[0][1]["is-active"], "true")
        self.assertEqual(client.calls[0][1]["sort-column"], "NAME")
        self.assertEqual(client.calls[0][1]["sort-order"], "ASCENDING")

    async def test_get_project_tasks_combines_paginated_results(self):
        client = FakeClockifyClient(
            [
                (
                    [
                        {
                            "id": "task-1",
                            "name": "Build",
                            "status": "ACTIVE",
                            "projectId": "project-1",
                        }
                    ],
                    {"Last-Page": "false"},
                ),
                (
                    [
                        {
                            "id": "task-2",
                            "name": "Test",
                            "status": "ACTIVE",
                            "projectId": "project-1",
                        }
                    ],
                    {"Last-Page": "true"},
                ),
            ]
        )

        tasks = await client.get_project_tasks("project-1", page_size=1)

        self.assertEqual([task.id for task in tasks], ["task-1", "task-2"])
        self.assertEqual(client.calls[0][1]["page"], 1)
        self.assertEqual(client.calls[1][1]["page"], 2)

    async def test_get_active_project_tasks_filters_and_normalizes_status(self):
        client = FakeClockifyClient(
            [
                (
                    [
                        {
                            "id": "task-1",
                            "name": "Build",
                            "status": "ACTIVE",
                            "projectId": "project-1",
                        },
                        {
                            "id": "task-2",
                            "name": "Closed",
                            "status": "DONE",
                            "projectId": "project-1",
                        },
                        {
                            "id": "task-3",
                            "name": "No Status",
                            "projectId": "project-1",
                        },
                    ],
                    {"Last-Page": "true"},
                )
            ]
        )

        tasks = await client.get_active_project_tasks("project-1")

        self.assertEqual([task.id for task in tasks], ["task-1", "task-3"])
        self.assertEqual([task.status for task in tasks], ["ACTIVE", "ACTIVE"])

    async def test_mcp_tool_returns_expected_json_shape(self):
        config.api_key = "test"
        config.workspace_id = "workspace-id"
        main = importlib.import_module("main")

        class FakeMcpClient:
            async def get_active_project_tasks(self, project_id):
                return [
                    TaskSummary(
                        id="task-1",
                        name="Build",
                        status="ACTIVE",
                        project_id=project_id,
                    )
                ]

        original_client = main.client
        main.client = FakeMcpClient()
        try:
            result = await main.list_active_project_tasks.fn("project-1")
        finally:
            main.client = original_client

        self.assertEqual(
            json.loads(result),
            [
                {
                    "id": "task-1",
                    "name": "Build",
                    "status": "ACTIVE",
                    "project_id": "project-1",
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()
