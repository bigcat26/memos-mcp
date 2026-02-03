"""Unit tests for MCP server tools (create/list/get/update/delete/search/get_tags)."""

import pytest
from unittest.mock import patch

from memos_mcp.server import SimpleMCPServer
from memos_mcp.utils.client import MemosAPIError


@pytest.fixture
def mock_client():
    with patch("memos_mcp.server.memos_client") as m:
        yield m


@pytest.fixture
def server(mock_client):
    return SimpleMCPServer()


class TestCreateMemo:
    def test_create_memo_success(self, server, mock_client):
        mock_client.create_memo.return_value = {"data": {"id": 42}}
        result = server.handle_tool_call(
            "create_memo", {"content": "Hello", "visibility": "PRIVATE"}
        )
        text = result["content"][0]["text"]
        assert "Successfully created memo #42" in text
        assert "Hello" in text
        mock_client.create_memo.assert_called_once_with("Hello", "PRIVATE")

    def test_create_memo_default_visibility(self, server, mock_client):
        mock_client.create_memo.return_value = {"data": {"id": 1}}
        server.handle_tool_call("create_memo", {"content": "Only content"})
        mock_client.create_memo.assert_called_once_with("Only content", "PRIVATE")

    def test_create_memo_api_error(self, server, mock_client):
        mock_client.create_memo.side_effect = MemosAPIError("Unauthorized", 401)
        result = server.handle_tool_call(
            "create_memo", {"content": "Fail", "visibility": "PUBLIC"}
        )
        text = result["content"][0]["text"]
        assert "Error creating memo" in text or "Unauthorized" in text


class TestListMemos:
    def test_list_memos_success(self, server, mock_client):
        mock_client.list_memos.return_value = {
            "data": [
                {"id": 1, "content": "First", "createdTs": 123, "visibility": "PRIVATE"},
                {"id": 2, "content": "Second", "createdTs": 124, "visibility": "PUBLIC"},
            ]
        }
        result = server.handle_tool_call(
            "list_memos", {"page": 1, "page_size": 20}
        )
        text = result["content"][0]["text"]
        assert "Found 2 memos" in text
        assert "#1" in text and "#2" in text
        mock_client.list_memos.assert_called_once_with(
            page=1, page_size=20, visibility=None, tag=None
        )

    def test_list_memos_empty(self, server, mock_client):
        mock_client.list_memos.return_value = {"data": []}
        result = server.handle_tool_call("list_memos", {})
        assert "No memos found" in result["content"][0]["text"]

    def test_list_memos_with_filters(self, server, mock_client):
        mock_client.list_memos.return_value = {"data": []}
        server.handle_tool_call(
            "list_memos",
            {"page": 2, "page_size": 10, "visibility": "PUBLIC", "tag": "work"},
        )
        mock_client.list_memos.assert_called_once_with(
            page=2, page_size=10, visibility="PUBLIC", tag="work"
        )


class TestGetMemo:
    def test_get_memo_success(self, server, mock_client):
        mock_client.get_memo.return_value = {
            "data": {
                "id": 10,
                "content": "Memo body",
                "createdTs": 1000,
                "updatedTs": 1001,
                "visibility": "PRIVATE",
                "creator": {"nickname": "Alice"},
            }
        }
        result = server.handle_tool_call("get_memo", {"memo_id": 10})
        text = result["content"][0]["text"]
        assert "Memo #10" in text
        assert "Memo body" in text
        assert "Alice" in text
        mock_client.get_memo.assert_called_once_with(10)

    def test_get_memo_not_found(self, server, mock_client):
        mock_client.get_memo.return_value = {"data": {}}
        result = server.handle_tool_call("get_memo", {"memo_id": 999})
        assert "not found" in result["content"][0]["text"]

    def test_get_memo_api_error(self, server, mock_client):
        mock_client.get_memo.side_effect = MemosAPIError("Not found", 404)
        result = server.handle_tool_call("get_memo", {"memo_id": 1})
        text = result["content"][0]["text"]
        assert "Error getting memo" in text or "Not found" in text


class TestUpdateMemo:
    def test_update_memo_success(self, server, mock_client):
        mock_client.update_memo.return_value = {}
        result = server.handle_tool_call(
            "update_memo",
            {"memo_id": 5, "content": "Updated", "visibility": "PUBLIC"},
        )
        assert "Successfully updated memo #5" in result["content"][0]["text"]
        mock_client.update_memo.assert_called_once_with(
            memo_id=5, content="Updated", visibility="PUBLIC", row_status=None
        )

    def test_update_memo_api_error(self, server, mock_client):
        mock_client.update_memo.side_effect = MemosAPIError("Forbidden", 403)
        result = server.handle_tool_call("update_memo", {"memo_id": 1})
        text = result["content"][0]["text"]
        assert "Error updating memo" in text or "Forbidden" in text


class TestDeleteMemo:
    def test_delete_memo_success(self, server, mock_client):
        mock_client.delete_memo.return_value = None
        result = server.handle_tool_call("delete_memo", {"memo_id": 3})
        assert "Successfully deleted memo #3" in result["content"][0]["text"]
        mock_client.delete_memo.assert_called_once_with(3)

    def test_delete_memo_api_error(self, server, mock_client):
        mock_client.delete_memo.side_effect = MemosAPIError("Not found", 404)
        result = server.handle_tool_call("delete_memo", {"memo_id": 99})
        text = result["content"][0]["text"]
        assert "Error deleting memo" in text or "Not found" in text


class TestSearchMemos:
    def test_search_memos_success(self, server, mock_client):
        mock_client.search_memos.return_value = {
            "data": [
                {"id": 1, "content": "Meeting notes", "createdTs": 100},
            ]
        }
        result = server.handle_tool_call(
            "search_memos", {"query": "meeting", "page": 1, "page_size": 20}
        )
        text = result["content"][0]["text"]
        assert "Found 1 memos matching 'meeting'" in text
        mock_client.search_memos.assert_called_once_with(
            query="meeting", page=1, page_size=20
        )

    def test_search_memos_empty(self, server, mock_client):
        mock_client.search_memos.return_value = {"data": []}
        result = server.handle_tool_call("search_memos", {"query": "nonexistent"})
        assert "No memos found for query" in result["content"][0]["text"]

    def test_search_memos_api_error(self, server, mock_client):
        mock_client.search_memos.side_effect = MemosAPIError("Server error", 500)
        result = server.handle_tool_call("search_memos", {"query": "x"})
        text = result["content"][0]["text"]
        assert "Error searching memos" in text or "Server error" in text


class TestGetTags:
    def test_get_tags_success(self, server, mock_client):
        mock_client.get_tags.return_value = ["work", "personal", "ideas"]
        result = server.handle_tool_call("get_tags", {})
        text = result["content"][0]["text"]
        assert "Available tags" in text
        assert "work" in text and "personal" in text

    def test_get_tags_empty(self, server, mock_client):
        mock_client.get_tags.return_value = []
        result = server.handle_tool_call("get_tags", {})
        assert "No tags found" in result["content"][0]["text"]

    def test_get_tags_api_error(self, server, mock_client):
        mock_client.get_tags.side_effect = MemosAPIError("Unauthorized", 401)
        result = server.handle_tool_call("get_tags", {})
        text = result["content"][0]["text"]
        assert "Error getting tags" in text or "Unauthorized" in text


class TestUnknownTool:
    def test_unknown_tool_returns_error_message(self, server):
        result = server.handle_tool_call("unknown_tool", {})
        assert "Error executing" in result["content"][0]["text"]
        assert "Unknown tool" in result["content"][0]["text"]
