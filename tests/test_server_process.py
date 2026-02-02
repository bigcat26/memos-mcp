"""MCP 进程级测试：通过 subprocess 调用 main.py，验证 initialize / tools/list / resources/list / prompts/list / tools/call。"""

import json
import os
import subprocess
import sys
import time

import pytest


pytestmark = pytest.mark.integration


def send_message(server_process, message):
    message_json = json.dumps(message)
    server_process.stdin.write(message_json + "\n")
    server_process.stdin.flush()
    time.sleep(0.1)
    response_lines = []
    while True:
        line = server_process.stdout.readline()
        if not line:
            break
        if line.strip():
            response_lines.append(line.strip())
    return [json.loads(line) for line in response_lines] if response_lines else []


@pytest.fixture
def server_process():
    env = os.environ.copy()
    env.update({
        "MEMOS_BASE_URL": "https://demo.usememos.com",
        "MEMOS_ACCESS_TOKEN": "test_token",
        "LOG_LEVEL": "INFO",
    })
    # 从项目根目录启动，main.py 在根目录
    proc = subprocess.Popen(
        [sys.executable, "main.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    )
    yield proc
    proc.terminate()
    proc.wait(timeout=5)


def test_initialize(server_process):
    init_message = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "clientInfo": {"name": "test", "version": "1.0.0"},
        },
    }
    responses = send_message(server_process, init_message)
    assert responses
    init_response = responses[0]
    assert "result" in init_response
    server_info = init_response["result"]["serverInfo"]
    assert "name" in server_info
    assert "version" in server_info


def test_tools_list(server_process):
    tools_message = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
    responses = send_message(server_process, tools_message)
    assert responses
    tools_response = responses[0]
    assert "result" in tools_response
    tools = tools_response["result"]["tools"]
    assert len(tools) >= 6
    names = {t["name"] for t in tools}
    assert "create_memo" in names
    assert "list_memos" in names
    assert "get_memo" in names
    assert "update_memo" in names
    assert "delete_memo" in names
    assert "search_memos" in names


def test_resources_list(server_process):
    resources_message = {"jsonrpc": "2.0", "id": 3, "method": "resources/list"}
    responses = send_message(server_process, resources_message)
    assert responses
    resources_response = responses[0]
    assert "result" in resources_response
    resources = resources_response["result"]["resources"]
    assert len(resources) >= 1


def test_prompts_list(server_process):
    prompts_message = {"jsonrpc": "2.0", "id": 4, "method": "prompts/list"}
    responses = send_message(server_process, prompts_message)
    assert responses
    prompts_response = responses[0]
    assert "result" in prompts_response
    prompts = prompts_response["result"]["prompts"]
    assert isinstance(prompts, list)


def test_tools_call_list_memos(server_process):
    tool_call_message = {
        "jsonrpc": "2.0",
        "id": 5,
        "method": "tools/call",
        "params": {"name": "list_memos", "arguments": {"page": 1, "page_size": 5}},
    }
    responses = send_message(server_process, tool_call_message)
    assert responses
    tool_response = responses[0]
    assert "result" in tool_response
    content = tool_response["result"]["content"][0]["text"]
    assert isinstance(content, str)
