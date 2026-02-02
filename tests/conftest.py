"""pytest 共享 fixtures，供 tests 下各 test_*.py 使用。"""

import os

import pytest

# 加载项目根目录的 .env（pytest 不会自动加载 .env，这里显式加载便于 live 测试等使用）
try:
    from dotenv import load_dotenv
    _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    load_dotenv(os.path.join(_root, ".env"))
except ImportError:
    pass


def _live_configured():
    """是否已配置真实服务器：MEMOS_TEST_LIVE=1 且 URL/Token 已设置。"""
    if os.environ.get("MEMOS_TEST_LIVE", "").strip() != "1":
        return False
    base = os.environ.get("MEMOS_BASE_URL", "").strip()
    token = os.environ.get("MEMOS_ACCESS_TOKEN", "").strip()
    return bool(base and token)


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
