#!/usr/bin/env python3

import json
import subprocess
import sys
import time
import os


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


def test_server():
    print("Testing Memos MCP Server...")

    env = os.environ.copy()
    env.update(
        {
            "MEMOS_BASE_URL": "https://demo.usememos.com",
            "MEMOS_ACCESS_TOKEN": "test_token",
            "LOG_LEVEL": "INFO",
        }
    )

    try:
        server_process = subprocess.Popen(
            [sys.executable, "main.py"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            cwd=".",
        )

        print("\n1. Testing initialize...")
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
        if responses:
            init_response = responses[0]
            if "result" in init_response:
                print("✓ Initialize successful")
                server_info = init_response["result"]["serverInfo"]
                print(f"  Server: {server_info['name']} v{server_info['version']}")
            else:
                print("✗ Initialize failed")
                print(f"  Error: {init_response.get('error', 'Unknown')}")

        print("\n2. Testing tools/list...")
        tools_message = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}

        responses = send_message(server_process, tools_message)
        if responses:
            tools_response = responses[0]
            if "result" in tools_response:
                tools = tools_response["result"]["tools"]
                print(f"✓ Found {len(tools)} tools:")
                for tool in tools:
                    print(f"  - {tool['name']}: {tool['description']}")
            else:
                print("✗ Tools list failed")
                print(f"  Error: {tools_response.get('error', 'Unknown')}")

        print("\n3. Testing resources/list...")
        resources_message = {"jsonrpc": "2.0", "id": 3, "method": "resources/list"}

        responses = send_message(server_process, resources_message)
        if responses:
            resources_response = responses[0]
            if "result" in resources_response:
                resources = resources_response["result"]["resources"]
                print(f"✓ Found {len(resources)} resources:")
                for resource in resources:
                    print(f"  - {resource['uri']}: {resource['name']}")
            else:
                print("✗ Resources list failed")
                print(f"  Error: {resources_response.get('error', 'Unknown')}")

        print("\n4. Testing prompts/list...")
        prompts_message = {"jsonrpc": "2.0", "id": 4, "method": "prompts/list"}

        responses = send_message(server_process, prompts_message)
        if responses:
            prompts_response = responses[0]
            if "result" in prompts_response:
                prompts = prompts_response["result"]["prompts"]
                print(f"✓ Found {len(prompts)} prompts:")
                for prompt in prompts:
                    print(f"  - {prompt['name']}: {prompt['description']}")
            else:
                print("✗ Prompts list failed")
                print(f"  Error: {prompts_response.get('error', 'Unknown')}")

        print("\n5. Testing tools/call (get_tags)...")
        tool_call_message = {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {"name": "get_tags", "arguments": {}},
        }

        responses = send_message(server_process, tool_call_message)
        if responses:
            tool_response = responses[0]
            if "result" in tool_response:
                content = tool_response["result"]["content"][0]["text"]
                print(f"✓ Tool call successful")
                print(f"  Response: {content[:100]}...")
            else:
                print("✗ Tool call failed")
                print(f"  Error: {tool_response.get('error', 'Unknown')}")

        print("\n✓ All basic MCP protocol tests completed!")
        print("Note: Actual API calls require valid Memos instance and access token")

    except Exception as e:
        print(f"✗ Test failed with error: {str(e)}")

    finally:
        if "server_process" in locals():
            server_process.terminate()
            server_process.wait()


if __name__ == "__main__":
    test_server()
