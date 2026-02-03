"""pytest 共享 fixtures，供 tests 下各 test_*.py 使用。"""

import os
import sys

import pytest
from unittest.mock import patch

# 加载项目根目录的 .env（pytest 不会自动加载 .env，这里显式加载便于 live 测试等使用）
try:
    from dotenv import load_dotenv
    _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    load_dotenv(os.path.join(_root, ".env"))
except ImportError:
    pass

# 确保以项目根为 path，便于测试时导入
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


def _live_configured():
    """是否已配置真实服务器：MEMOS_TEST_LIVE=1 且 URL/Token 已设置。"""
    if os.environ.get("MEMOS_TEST_LIVE", "").strip() != "1":
        return False
    base = os.environ.get("MEMOS_BASE_URL", "").strip()
    token = os.environ.get("MEMOS_ACCESS_TOKEN", "").strip()
    return bool(base and token)


@pytest.fixture(autouse=True)
def env_config():
    """设置最小 env，避免 server 初始化时 config 报错（可选）。"""
    with patch.dict(
        os.environ,
        {
            "MEMOS_BASE_URL": "https://test.memos.local",
            "MEMOS_ACCESS_TOKEN": "test-token",
        },
        clear=False,
    ):
        yield


@pytest.fixture
def mock_memos_client():
    """Mock Memos API 客户端，避免真实 HTTP 请求。"""
    with patch("memos_mcp.server.memos_client") as client:
        yield client


@pytest.fixture
def server(mock_memos_client):
    """带 mock 客户端的 MCP server 实例。"""
    from memos_mcp.server import SimpleMCPServer
    return SimpleMCPServer()


@pytest.fixture
def server_instance():
    """创建 SimpleMCPServer 实例，供工具接口测试使用。"""
    from memos_mcp import SimpleMCPServer
    return SimpleMCPServer()


# 供 live 测试使用的 skip 条件：未配置真实服务器时跳过
live_skip = pytest.mark.skipif(
    not _live_configured(),
    reason="真实服务器测试需设置 MEMOS_TEST_LIVE=1 且 MEMOS_BASE_URL、MEMOS_ACCESS_TOKEN",
)
