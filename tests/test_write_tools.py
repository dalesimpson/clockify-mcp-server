import importlib
import json
import unittest

from clockify_client import ClockifyClient
from config import config
from timeutil import to_clockify_utc


def entry_payload(**overrides):
    payload = {
        "id": "entry-1",
        "description": "Weekly sync",
        "userId": "user-1",
        "billable": True,
        "projectId": "project-1",
        "taskId": "task-1",
        "tagIds": ["tag-1"],
        "timeInterval": {
            "start": "2026-09-15T13:00:00Z",
            "end": "2026-09-15T14:00:00Z",
            "duration": "PT1H",
        },
        "workspaceId": "workspace-id",
    }
    payload.update(overrides)
    return payload


class FakeClockifyClient(ClockifyClient):
    def __init__(self, get_responses=None, send_responses=None):
        self.base_url = "https://api.clockify.me/api/v1"
        self.headers = {"X-Api-Key": "test"}
        self.workspace_id = "workspace-id"
        self.get_responses = list(get_responses or [])
        self.send_responses = list(send_responses or [])
        self.get_calls = []
        self.send_calls = []

    async def _get_response(self, endpoint, params=None):
        self.get_calls.append((endpoint, params))
        return self.get_responses.pop(0)

    async def _send(self, method, endpoint, json_body=None):
        self.send_calls.append((method, endpoint, json_body))
        return self.send_responses.pop(0)


class TimezoneTests(unittest.TestCase):
    def test_naive_datetime_is_toronto_time(self):
        # September is EDT (UTC-4)
        self.assertEqual(to_clockify_utc("2026-09-15T09:00:00"), "2026-09-15T13:00:00Z")

    def test_winter_uses_est(self):
        self.assertEqual(to_clockify_utc("2026-01-15T09:00:00"), "2026-01-15T14:00:00Z")

    def test_explicit_offset_is_respected(self):
        self.assertEqual(to_clockify_utc("2026-09-15T09:00:00Z"), "2026-09-15T09:00:00Z")
        self.assertEqual(
            to_clockify_utc("2026-09-15T09:00:00-07:00"), "2026-09-15T16:00:00Z"
        )

    def test_date_only_start_and_inclusive_end(self):
        self.assertEqual(to_clockify_utc("2026-09-01"), "2026-09-01T04:00:00Z")
        self.assertEqual(
            to_clockify_utc("2026-09-30", end_of_day=True), "2026-10-01T04:00:00Z"
        )


class TimeEntryReadTests(unittest.IsolatedAsyncioTestCase):
    async def test_get_user_time_entries_paginates_and_converts_dates(self):
        client = FakeClockifyClient(
            get_responses=[
                ([entry_payload(id="e1")], {"Last-Page": "false"}),
                ([entry_payload(id="e2")], {"Last-Page": "true"}),
            ]
        )

        entries = await client.get_user_time_entries(
            "user-1", start_date="2026-09-01", end_date="2026-09-30", page_size=1
        )

        self.assertEqual([e.id for e in entries], ["e1", "e2"])
        endpoint, params = client.get_calls[0]
        self.assertEqual(endpoint, "/workspaces/workspace-id/user/user-1/time-entries")
        self.assertEqual(params["start"], "2026-09-01T04:00:00Z")
        self.assertEqual(params["end"], "2026-10-01T04:00:00Z")
        self.assertEqual(params["page"], 1)
        self.assertEqual(client.get_calls[1][1]["page"], 2)

    async def test_get_user_time_entries_stops_on_short_page(self):
        client = FakeClockifyClient(
            get_responses=[([entry_payload()], {})]
        )
        entries = await client.get_user_time_entries("user-1", page_size=50)
        self.assertEqual(len(entries), 1)
        self.assertEqual(len(client.get_calls), 1)


class TimeEntryWriteTests(unittest.IsolatedAsyncioTestCase):
    async def test_create_time_entry_sends_utc_body(self):
        client = FakeClockifyClient(send_responses=[entry_payload()])

        entry = await client.create_time_entry(
            start="2026-09-15T09:00:00",
            end="2026-09-15T10:00:00",
            description="Weekly sync",
            project_id="project-1",
            task_id="task-1",
            billable=True,
        )

        self.assertEqual(entry.id, "entry-1")
        method, endpoint, body = client.send_calls[0]
        self.assertEqual(method, "POST")
        self.assertEqual(endpoint, "/workspaces/workspace-id/time-entries")
        self.assertEqual(
            body,
            {
                "start": "2026-09-15T13:00:00Z",
                "end": "2026-09-15T14:00:00Z",
                "description": "Weekly sync",
                "projectId": "project-1",
                "taskId": "task-1",
                "billable": True,
            },
        )

    async def test_update_merges_with_existing_entry(self):
        client = FakeClockifyClient(
            get_responses=[(entry_payload(), {})],
            send_responses=[entry_payload(taskId="task-2")],
        )

        await client.update_time_entry("entry-1", task_id="task-2")

        method, endpoint, body = client.send_calls[0]
        self.assertEqual(method, "PUT")
        self.assertEqual(endpoint, "/workspaces/workspace-id/time-entries/entry-1")
        self.assertEqual(
            body,
            {
                "start": "2026-09-15T13:00:00Z",
                "end": "2026-09-15T14:00:00Z",
                "description": "Weekly sync",
                "billable": True,
                "projectId": "project-1",
                "taskId": "task-2",
                "tagIds": ["tag-1"],
            },
        )

    async def test_update_project_without_task_clears_task(self):
        client = FakeClockifyClient(
            get_responses=[(entry_payload(), {})],
            send_responses=[entry_payload(projectId="project-2", taskId=None)],
        )

        await client.update_time_entry("entry-1", project_id="project-2")

        body = client.send_calls[0][2]
        self.assertEqual(body["projectId"], "project-2")
        self.assertNotIn("taskId", body)

    async def test_delete_time_entry(self):
        client = FakeClockifyClient(send_responses=[None])
        await client.delete_time_entry("entry-1")
        self.assertEqual(
            client.send_calls[0],
            ("DELETE", "/workspaces/workspace-id/time-entries/entry-1", None),
        )


class CreateTaskTests(unittest.IsolatedAsyncioTestCase):
    async def test_create_task_posts_after_duplicate_check(self):
        client = FakeClockifyClient(
            get_responses=[
                ([{"id": "t1", "name": "Delivery", "status": "ACTIVE"}], {"Last-Page": "true"}),
                ([{"id": "t2", "name": "Old", "status": "DONE"}], {"Last-Page": "true"}),
            ],
            send_responses=[
                {"id": "t3", "name": "DevOps", "status": "ACTIVE", "projectId": "project-1"}
            ],
        )

        task = await client.create_project_task("project-1", "  DevOps ")

        self.assertEqual(task.id, "t3")
        self.assertEqual(client.get_calls[0][1]["is-active"], "true")
        self.assertEqual(client.get_calls[1][1]["is-active"], "false")
        self.assertEqual(
            client.send_calls[0],
            (
                "POST",
                "/workspaces/workspace-id/projects/project-1/tasks",
                {"name": "DevOps", "status": "ACTIVE"},
            ),
        )

    async def test_create_task_rejects_duplicate_name(self):
        client = FakeClockifyClient(
            get_responses=[
                ([], {"Last-Page": "true"}),
                ([{"id": "t2", "name": "devops", "status": "DONE"}], {"Last-Page": "true"}),
            ]
        )

        with self.assertRaises(ValueError):
            await client.create_project_task("project-1", "DevOps")
        self.assertEqual(client.send_calls, [])

    async def test_create_task_rejects_empty_name(self):
        client = FakeClockifyClient()
        with self.assertRaises(ValueError):
            await client.create_project_task("project-1", "   ")


class McpToolTests(unittest.IsolatedAsyncioTestCase):
    async def test_update_tool_only_passes_given_fields(self):
        config.api_key = "test"
        config.workspace_id = "workspace-id"
        main = importlib.import_module("main")
        from clockify_client import UNSET
        from models import TimeEntry

        captured = {}

        class FakeMcpClient:
            async def update_time_entry(self, entry_id, **kwargs):
                captured.update(kwargs)
                return TimeEntry.model_validate(entry_payload())

        original = main.client
        main.client = FakeMcpClient()
        try:
            result = await main.update_time_entry.fn("entry-1", description="New")
        finally:
            main.client = original

        self.assertEqual(captured["description"], "New")
        self.assertIs(captured["task_id"], UNSET)
        self.assertIs(captured["start"], UNSET)
        self.assertEqual(json.loads(result)["id"], "entry-1")

    async def test_delete_tool_returns_confirmation(self):
        config.api_key = "test"
        config.workspace_id = "workspace-id"
        main = importlib.import_module("main")

        class FakeMcpClient:
            async def delete_time_entry(self, entry_id):
                return None

        original = main.client
        main.client = FakeMcpClient()
        try:
            result = await main.delete_time_entry.fn("entry-1")
        finally:
            main.client = original

        self.assertEqual(json.loads(result), {"deleted": "entry-1"})


if __name__ == "__main__":
    unittest.main()
