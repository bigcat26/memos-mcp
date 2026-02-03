"""Unit tests for MCP server resources (memo://, memos://list, memos://search/)."""

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


class TestMemoResource:
    def test_memo_resource_success(self, server, mock_client):
        mock_client.get_memo.return_value = {
            "data": {"id": 1, "content": "Memo content here"}
        }
        result = server.handle_resource_read("memo://1")
        text = result["contents"][0]["text"]
        assert text == "Memo content here"
        mock_client.get_memo.assert_called_once_with(1)

    def test_memo_resource_not_found(self, server, mock_client):
        mock_client.get_memo.return_value = {"data": {}}
        result = server.handle_resource_read("memo://999")
        assert "not found" in result["contents"][0]["text"]

    def test_memo_resource_invalid_id(self, server, mock_client):
        result = server.handle_resource_read("memo://abc")
        assert "Invalid memo ID" in result["contents"][0]["text"]
        mock_client.get_memo.assert_not_called()

    def test_memo_resource_api_error(self, server, mock_client):
        mock_client.get_memo.side_effect = MemosAPIError("Forbidden", 403)
        result = server.handle_resource_read("memo://1")
        text = result["contents"][0]["text"]
        assert "Error accessing memo" in text or "Forbidden" in text


class TestMemosListResource:
    def test_memos_list_success(self, server, mock_client):
        mock_client.list_memos.return_value = {
            "data": [
                {"id": 1, "content": "First memo", "createdTs": 100},
                {"id": 2, "content": "Second memo", "createdTs": 101},
            ]
        }
        result = server.handle_resource_read("memos://list")
        text = result["contents"][0]["text"]
        assert "Recent Memos" in text
        assert "#1" in text and "#2" in text
        assert "First memo" in text
        mock_client.list_memos.assert_called_once_with(page_size=50)

    def test_memos_list_empty(self, server, mock_client):
        mock_client.list_memos.return_value = {"data": []}
        result = server.handle_resource_read("memos://list")
        assert "No memos found" in result["contents"][0]["text"]

    def test_memos_list_api_error(self, server, mock_client):
        mock_client.list_memos.side_effect = MemosAPIError("Server error", 500)
        result = server.handle_resource_read("memos://list")
        text = result["contents"][0]["text"]
        assert "Error accessing memos" in text or "Server error" in text


class TestMemosSearchResource:
    def test_memos_search_success(self, server, mock_client):
        mock_client.search_memos.return_value = {
            "data": [
                {"id": 1, "content": "Match one", "createdTs": 100},
            ]
        }
        result = server.handle_resource_read("memos://search/hello")
        text = result["contents"][0]["text"]
        assert "Search Results for 'hello'" in text
        assert "#1" in text and "Match one" in text
        mock_client.search_memos.assert_called_once_with(query="hello", page_size=20)

    def test_memos_search_empty(self, server, mock_client):
        mock_client.search_memos.return_value = {"data": []}
        result = server.handle_resource_read("memos://search/nonexistent")
        assert "No memos found for query" in result["contents"][0]["text"]

    def test_memos_search_api_error(self, server, mock_client):
        mock_client.search_memos.side_effect = MemosAPIError("Timeout", 504)
        result = server.handle_resource_read("memos://search/q")
        text = result["contents"][0]["text"]
        assert "Error searching memos" in text or "Timeout" in text


class TestUnknownResource:
    def test_unknown_uri_returns_error(self, server):
        result = server.handle_resource_read("unknown://something")
        assert "Error reading resource" in result["contents"][0]["text"]
        assert "Unknown resource URI" in result["contents"][0]["text"]
