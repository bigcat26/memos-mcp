"""验证 Memos MCP Server 模块导入、初始化及工具/资源/提示注册。"""

def test_module_imports():
    """确保 memos_mcp 相关模块可被 import。"""
    import memos_mcp.server
    import memos_mcp.utils.config
    import memos_mcp.utils.client
    assert memos_mcp.server.SimpleMCPServer is not None
    assert memos_mcp.server.TOOL_NAMES is not None


def test_server_initialization():
    """确保 SimpleMCPServer 可初始化且工具/资源/提示数量正确。"""
    from memos_mcp import SimpleMCPServer
    server = SimpleMCPServer()
    assert len(server.tools) >= 6
    assert len(server.resources) >= 1
    assert len(server.prompts) >= 1


def test_tool_names_export():
    """确保 TOOL_NAMES 可从 memos_mcp import 并与 server.tools 一致。"""
    from memos_mcp import SimpleMCPServer, TOOL_NAMES
    server = SimpleMCPServer()
    for name in TOOL_NAMES:
        assert name in server.tools


def test_handle_tool_call_list_memos():
    """list_memos 调用返回 content 结构（可能为 API 错误，但接口正常）。"""
    from memos_mcp import SimpleMCPServer
    server = SimpleMCPServer()
    result = server.handle_tool_call("list_memos", {"page": 1, "page_size": 5})
    assert "content" in result
    assert len(result["content"]) == 1
    assert "text" in result["content"][0]
    assert isinstance(result["content"][0]["text"], str)


def test_handle_tool_call_create_memo_interface():
    """create_memo 接口接受 content/visibility，返回 content 结构。"""
    from memos_mcp import SimpleMCPServer
    server = SimpleMCPServer()
    result = server.handle_tool_call(
        "create_memo",
        {"content": "Test memo", "visibility": "PRIVATE"},
    )
    assert "content" in result
    assert len(result["content"]) == 1
    assert "text" in result["content"][0]
    assert isinstance(result["content"][0]["text"], str)


def test_handle_resource_read():
    """资源读取返回 contents 结构。"""
    from memos_mcp import SimpleMCPServer
    server = SimpleMCPServer()
    for uri, _ in [
        ("memo://memos/verify-test", "memo resource"),
        ("memos://list", "memos list"),
        ("memos://search/test", "memos search"),
    ]:
        result = server.handle_resource_read(uri)
        assert "contents" in result
        assert len(result["contents"]) == 1
        assert "text" in result["contents"][0]
        assert isinstance(result["contents"][0]["text"], str)
