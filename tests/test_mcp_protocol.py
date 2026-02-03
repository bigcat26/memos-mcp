"""Unit tests for MCP protocol handlers (initialize, tools/list, resources/list, etc.)."""

import pytest
from unittest.mock import patch

from memos_mcp.server import SimpleMCPServer


@pytest.fixture
def mock_client():
    with patch("memos_mcp.server.memos_client") as m:
        yield m


@pytest.fixture
def server(mock_client):
    return SimpleMCPServer()


class TestInitialize:
    def test_initialize_returns_capabilities(self, server):
        msg = {
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "test", "version": "1.0.0"},
            },
        }
        resp = server._handle_message(msg)
        assert resp["jsonrpc"] == "2.0"
        assert resp["id"] == 1
        assert "result" in resp
        r = resp["result"]
        assert r["protocolVersion"] == "2024-11-05"
        assert "capabilities" in r
        assert r["capabilities"]["tools"]["listChanged"] is True
        assert r["serverInfo"]["name"] == "memos-mcp-server"
        assert r["serverInfo"]["version"] == "1.0.0"


class TestToolsList:
    def test_tools_list_returns_all_tools(self, server):
        msg = {"id": 2, "method": "tools/list"}
        resp = server._handle_message(msg)
        assert resp["jsonrpc"] == "2.0"
        assert "result" in resp
        tools = resp["result"]["tools"]
        names = [t["name"] for t in tools]
        assert "create_memo" in names
        assert "list_memos" in names
        assert "get_memo" in names
        assert "update_memo" in names
        assert "delete_memo" in names
        assert "search_memos" in names
        assert "get_tags" in names
        assert len(tools) == 7


class TestToolsCall:
    def test_tools_call_get_tags(self, server, mock_client):
        mock_client.get_tags.return_value = ["a", "b"]
        msg = {
            "id": 3,
            "method": "tools/call",
            "params": {"name": "get_tags", "arguments": {}},
        }
        resp = server._handle_message(msg)
        assert "result" in resp
        content = resp["result"]["content"][0]["text"]
        assert "Available tags" in content
        assert "a" in content and "b" in content

    def test_tools_call_create_memo(self, server, mock_client):
        mock_client.create_memo.return_value = {"data": {"id": 10}}
        msg = {
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "create_memo",
                "arguments": {"content": "Test", "visibility": "PRIVATE"},
            },
        }
        resp = server._handle_message(msg)
        assert "result" in resp
        assert "Successfully created memo #10" in resp["result"]["content"][0]["text"]


class TestResourcesList:
    def test_resources_list_returns_all_resources(self, server):
        msg = {"id": 5, "method": "resources/list"}
        resp = server._handle_message(msg)
        assert "result" in resp
        resources = resp["result"]["resources"]
        uris = [r["uri"] for r in resources]
        assert "memo://{memo_id}" in uris
        assert "memos://list" in uris
        assert "memos://search/{query}" in uris
        assert len(resources) == 3


class TestResourcesRead:
    def test_resources_read_memo(self, server, mock_client):
        mock_client.get_memo.return_value = {"data": {"id": 1, "content": "Body"}}
        msg = {
            "id": 6,
            "method": "resources/read",
            "params": {"uri": "memo://1"},
        }
        resp = server._handle_message(msg)
        assert resp["result"]["contents"][0]["text"] == "Body"

    def test_resources_read_memos_list(self, server, mock_client):
        mock_client.list_memos.return_value = {"data": []}
        msg = {
            "id": 7,
            "method": "resources/read",
            "params": {"uri": "memos://list"},
        }
        resp = server._handle_message(msg)
        assert "No memos found" in resp["result"]["contents"][0]["text"]


class TestPromptsList:
    def test_prompts_list_returns_all_prompts(self, server):
        msg = {"id": 8, "method": "prompts/list"}
        resp = server._handle_message(msg)
        assert "result" in resp
        prompts = resp["result"]["prompts"]
        names = [p["name"] for p in prompts]
        assert "memo_summary" in names
        assert "memo_organization" in names
        assert len(prompts) == 2


class TestPromptsGet:
    def test_prompts_get_memo_summary(self, server):
        msg = {
            "id": 9,
            "method": "prompts/get",
            "params": {"name": "memo_summary", "arguments": {"memo_count": 10}},
        }
        resp = server._handle_message(msg)
        assert "result" in resp
        messages = resp["result"]["messages"]
        assert len(messages) == 1
        text = messages[0]["content"]["text"]
        assert "10" in text
        assert "summarize" in text.lower()

    def test_prompts_get_memo_organization_with_tag(self, server):
        msg = {
            "id": 10,
            "method": "prompts/get",
            "params": {"name": "memo_organization", "arguments": {"tag": "work"}},
        }
        resp = server._handle_message(msg)
        text = resp["result"]["messages"][0]["content"]["text"]
        assert "work" in text
        assert "organize" in text.lower()

    def test_prompts_get_memo_organization_no_tag(self, server):
        msg = {
            "id": 11,
            "method": "prompts/get",
            "params": {"name": "memo_organization", "arguments": {}},
        }
        resp = server._handle_message(msg)
        text = resp["result"]["messages"][0]["content"]["text"]
        assert "organize" in text.lower()
        assert "get_tags" in text or "list_memos" in text


class TestMethodNotFound:
    def test_unknown_method_returns_error(self, server):
        msg = {"id": 99, "method": "unknown/method"}
        resp = server._handle_message(msg)
        assert "error" in resp
        assert resp["error"]["code"] == -32601
        assert "Method not found" in resp["error"]["message"]
