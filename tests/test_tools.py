"""单元测试：create_memo / list_memos / get_memo / update_memo / delete_memo / search_memos 工具接口。官方 API 无 get_tags 接口。

所有工具返回 MCP 约定的 JSON 字符串（含 name/createTime/updateTime/content/tags 或 error）。

切换真实服务器 vs Mock：
- 默认（Mock）：直接运行 pytest，所有带 @patch 的用例使用 mock 返回值，不请求真实 Memos。
- 真实服务器：设置环境变量 MEMOS_TEST_LIVE=1，并配置 MEMOS_BASE_URL、MEMOS_ACCESS_TOKEN（或 .env），
  然后运行带 live 标记的用例，会请求真实服务器并断言返回结构。

  运行仅 Mock 测试：  pytest tests/test_tools.py
  运行真实服务器测试： pytest tests/test_tools.py -m live
  运行全部（含 live）： pytest tests/test_tools.py -m ""  或  pytest tests/test_tools.py
  （未配置时 live 用例会被 skip）
"""

import json
from unittest.mock import patch

import pytest

from memos_mcp import SimpleMCPServer, TOOL_NAMES

try:
    from tests.conftest import live_skip
except ImportError:
    from conftest import live_skip


def _assert_tool_result_ok(result: dict) -> dict:
    """解析工具返回的 JSON，若含 error 则断言失败，使单测能感知底层 API 错误（如 400/404）。"""
    assert "content" in result and len(result["content"]) == 1, "Missing content"
    assert result["content"][0]["type"] == "text", "Expected text content"
    text = result["content"][0]["text"]
    assert isinstance(text, str), "Content text must be string"
    data = json.loads(text)
    assert "error" not in data, f"Tool returned API error: {data.get('error', text)}"
    return data


def test_tool_names_import():
    """确保 TOOL_NAMES 可从 memos_mcp import，且包含所有工具名。"""
    expected = [
        "create_memo",
        "list_memos",
        "get_memo",
        "update_memo",
        "delete_memo",
        "search_memos",
    ]
    assert TOOL_NAMES == expected


def test_server_has_all_tools():
    """确保 SimpleMCPServer 注册了所有 TOOL_NAMES 中的工具。"""
    server = SimpleMCPServer()
    for name in TOOL_NAMES:
        assert name in server.tools, f"工具 {name} 未注册"


@patch("memos_mcp.server.memos_client")
def test_create_memo(mock_client):
    """create_memo：返回 JSON，含 success 与 memo 精简字段（name/createTime/content，及 id 若有）。"""
    # API 直接返回 memo 对象（顶层）
    mock_client.create_memo.return_value = {
        "name": "memos/abc",
        "createTime": "2026-01-31T07:04:05Z",
        "content": "hello",
    }
    server = SimpleMCPServer()
    result = server.handle_tool_call(
        "create_memo",
        {"content": "hello", "visibility": "PRIVATE"},
    )
    mock_client.create_memo.assert_called_once_with("hello", "PRIVATE")
    assert result["content"][0]["type"] == "text"
    data = json.loads(result["content"][0]["text"])
    assert data.get("success") is True
    assert "memo" in data
    assert data["memo"].get("name") == "memos/abc"
    assert data["memo"].get("content") == "hello"
    assert data["memo"].get("createTime") == "2026-01-31T07:04:05Z"
    # 精简返回仅 name, createTime, content
    assert set(data["memo"].keys()) <= {"name", "createTime", "content"}


@patch("memos_mcp.server.memos_client")
def test_list_memos(mock_client):
    """list_memos：返回 JSON，含 memos 数组与 count，每项含 name/createTime/updateTime/content/tags。"""
    mock_client.list_memos.return_value = {
        "memos": [
            {"name": "memos/1", "createTime": "2026-01-31T07:04:05Z", "updateTime": "2026-01-31T07:04:05Z", "content": "a", "tags": []},
        ]
    }
    server = SimpleMCPServer()
    result = server.handle_tool_call(
        "list_memos",
        {"page": 1, "page_size": 20},
    )
    mock_client.list_memos.assert_called_once_with(
        page=1, page_size=20, visibility=None, tag=None
    )
    assert result["content"][0]["type"] == "text"
    data = json.loads(result["content"][0]["text"])
    assert "memos" in data and "count" in data
    assert len(data["memos"]) == 1
    assert data["memos"][0].get("name") == "memos/1"
    assert data["memos"][0].get("content") == "a"


@patch("memos_mcp.server.memos_client")
def test_get_memo(mock_client):
    """get_memo：按 name（memos/xxxxx）返回 JSON 单条 memo。"""
    mock_client.get_memo.return_value = {
        "memo": {
            "name": "memos/abc1",
            "createTime": "2026-01-31T07:04:05Z",
            "updateTime": "2026-01-31T07:04:05Z",
            "content": "memo body",
            "tags": [],
        }
    }
    server = SimpleMCPServer()
    result = server.handle_tool_call("get_memo", {"name": "memos/abc1"})
    mock_client.get_memo.assert_called_once_with("memos/abc1")
    assert result["content"][0]["type"] == "text"
    data = json.loads(result["content"][0]["text"])
    assert data.get("name") == "memos/abc1"
    assert data.get("content") == "memo body"
    assert "createTime" in data and "updateTime" in data and "tags" in data


@patch("memos_mcp.server.memos_client")
def test_update_memo(mock_client):
    """update_memo：按 name 返回 JSON，含 success 与 memo_name。"""
    mock_client.update_memo.return_value = {}
    server = SimpleMCPServer()
    result = server.handle_tool_call(
        "update_memo",
        {"name": "memos/abc2", "content": "updated"},
    )
    mock_client.update_memo.assert_called_once_with(
        memo_name="memos/abc2",
        content="updated",
        visibility=None,
        row_status=None,
    )
    assert result["content"][0]["type"] == "text"
    data = json.loads(result["content"][0]["text"])
    assert data.get("success") is True
    assert data.get("memo_name") == "memos/abc2"


@patch("memos_mcp.server.memos_client")
def test_delete_memo(mock_client):
    """delete_memo：按 name 返回 JSON，含 success 与 memo_name。"""
    mock_client.delete_memo.return_value = None
    server = SimpleMCPServer()
    result = server.handle_tool_call("delete_memo", {"name": "memos/abc3"})
    mock_client.delete_memo.assert_called_once_with("memos/abc3")
    assert result["content"][0]["type"] == "text"
    data = json.loads(result["content"][0]["text"])
    assert data.get("success") is True
    assert data.get("memo_name") == "memos/abc3"


@patch("memos_mcp.server.memos_client")
def test_search_memos(mock_client):
    """search_memos：返回 JSON，含 memos、count、query。"""
    mock_client.search_memos.return_value = {"memos": []}
    server = SimpleMCPServer()
    result = server.handle_tool_call(
        "search_memos",
        {"query": "test", "page": 1, "page_size": 10},
    )
    mock_client.search_memos.assert_called_once_with(
        query="test", page=1, page_size=10
    )
    assert result["content"][0]["type"] == "text"
    data = json.loads(result["content"][0]["text"])
    assert "memos" in data and data["memos"] == []
    assert data.get("query") == "test"
    assert data.get("count") == 0


@patch("memos_mcp.server.memos_client")
def test_create_memo_api_error(mock_client):
    """create_memo：API 异常时返回 JSON，含 error。"""
    from memos_mcp.utils.client import MemosAPIError
    mock_client.create_memo.side_effect = MemosAPIError("bad request")
    server = SimpleMCPServer()
    result = server.handle_tool_call(
        "create_memo",
        {"content": "x", "visibility": "PRIVATE"},
    )
    assert result["content"][0]["type"] == "text"
    data = json.loads(result["content"][0]["text"])
    assert "error" in data
    assert "bad request" in data["error"]


# ---------- 真实服务器测试（需 MEMOS_TEST_LIVE=1 且配置 MEMOS_BASE_URL、MEMOS_ACCESS_TOKEN） ----------


@live_skip
@pytest.mark.live
def test_list_memos_live():
    """list_memos：请求真实服务器，断言返回结构且无 API 错误。"""
    server = SimpleMCPServer()
    result = server.handle_tool_call("list_memos", {"page": 1, "page_size": 5})
    data = _assert_tool_result_ok(result)
    assert "memos" in data and "count" in data
    assert isinstance(data["memos"], list)


@live_skip
@pytest.mark.live
def test_search_memos_live():
    """search_memos：请求真实服务器，断言返回结构且无 API 错误。"""
    server = SimpleMCPServer()
    result = server.handle_tool_call("search_memos", {"query": "test", "page": 1, "page_size": 5})
    data = _assert_tool_result_ok(result)
    assert "memos" in data and "count" in data and "query" in data
    assert isinstance(data["memos"], list)


def _memo_name_for_delete(memo: dict) -> str:
    """从 create 返回的 memo 中取 name（memos/xxxxx），用于 delete。"""
    name = memo.get("name")
    if name and isinstance(name, str):
        return name
    raise ValueError(f"Cannot get memo name for delete from memo: {memo}")


@live_skip
@pytest.mark.live
def test_create_and_delete_memo_live():
    """Live：先 create 一条 memo，再按 name（memos/xxxxx）删除该 memo。"""
    import time
    server = SimpleMCPServer()
    content = f"[MCP live test] create then delete at {time.time()}"
    create_result = server.handle_tool_call(
        "create_memo",
        {"content": content, "visibility": "PRIVATE"},
    )
    data = _assert_tool_result_ok(create_result)
    assert data.get("success") is True, data.get("error", "create failed")
    assert "memo" in data
    memo = data["memo"]
    memo_name = _memo_name_for_delete(memo)

    delete_result = server.handle_tool_call("delete_memo", {"name": memo_name})
    delete_data = _assert_tool_result_ok(delete_result)
    assert delete_data.get("success") is True, delete_data.get("error", "delete failed")
    assert delete_data.get("memo_name") == memo_name
