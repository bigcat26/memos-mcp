"""Main MCP server for Memos integration."""

import sys
import os
import json
import logging
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.config import settings
from utils.client import memos_client, MemosAPIError

def _api_error_json(e: Exception) -> str:
    """将 API 异常转为 JSON 字符串，含 error 与 status_code，便于上层/单测感知 4xx/5xx。"""
    payload: Dict[str, Any] = {"error": str(e)}
    if isinstance(e, MemosAPIError) and getattr(e, "status_code", None) is not None:
        payload["status_code"] = e.status_code
    return json.dumps(payload)


logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def _memo_id(memo: Dict[str, Any]) -> str:
    """从 memo 中取展示用 ID，兼容 name（新 API）与 id（旧 API）。"""
    return memo.get("name") or str(memo.get("id", "unknown"))


def _memo_created(memo: Dict[str, Any]) -> str:
    """从 memo 中取创建时间，兼容 createTime（新 API）与 createdTs（旧 API）。"""
    return memo.get("createTime") or memo.get("createdTs", "")


def _memo_updated(memo: Dict[str, Any]) -> str:
    """从 memo 中取更新时间，兼容 updateTime（新 API）与 updatedTs（旧 API）。"""
    return memo.get("updateTime") or memo.get("updatedTs", "")


def _memo_creator(memo: Dict[str, Any]) -> str:
    """从 memo 中取创建者，兼容 creator 为字符串（新 API）或对象（旧 API）。"""
    c = memo.get("creator")
    if isinstance(c, dict):
        return c.get("nickname", "Unknown")
    return str(c) if c else "Unknown"


def _result_memos(result: Dict[str, Any]) -> List[Any]:
    """从 API 响应中取 memo 列表，兼容 memos（新 API）与 data（旧 API）。"""
    return result.get("memos", result.get("data", []))


def _result_memo(result: Dict[str, Any]) -> Dict[str, Any]:
    """从 API 响应中取单条 memo，兼容 memo（新 API）与 data（旧 API）。"""
    return result.get("memo", result.get("data", {}))


def _create_memo_response(memo: Dict[str, Any]) -> Dict[str, Any]:
    """create_memo 精简返回：仅 name, createTime, content（name 为 memo 标识，格式 memos/xxxxx）。"""
    return {
        "name": memo.get("name") or str(memo.get("id", "")),
        "createTime": _memo_created(memo),
        "content": memo.get("content", ""),
    }


def _memo_to_json_obj(memo: Dict[str, Any]) -> Dict[str, Any]:
    """将原始 memo 转为 MCP 工具约定字段：name, id(若有), createTime, updateTime, content, tags。"""
    raw_tags = memo.get("tags", [])
    if raw_tags and isinstance(raw_tags[0], dict):
        tags = [t.get("name", "") for t in raw_tags if t.get("name")]
    else:
        tags = [str(t) for t in raw_tags] if raw_tags else []
    return {
        "name": memo.get("name") or str(memo.get("id", "")),
        "createTime": _memo_created(memo),
        "updateTime": _memo_updated(memo),
        "content": memo.get("content", ""),
        "tags": tags,
    }


# 工具名称列表，供单元测试等 import 使用
TOOL_NAMES = [
    "create_memo",
    "list_memos",
    "get_memo",
    "update_memo",
    "delete_memo",
    "search_memos",
]


class SimpleMCPServer:
    """Simple MCP server implementation for Memos."""

    def __init__(self):
        self.tools = self._register_tools()
        self.resources = self._register_resources()
        self.prompts = self._register_prompts()

    def _register_tools(self) -> Dict[str, Any]:
        tools = {
            "create_memo": {
                "name": "create_memo",
                "description": "Create a new memo in Memos",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "The content of the memo",
                        },
                        "visibility": {
                            "type": "string",
                            "enum": ["PUBLIC", "PRIVATE", "PROTECTED"],
                            "default": "PRIVATE",
                            "description": "Visibility level",
                        },
                    },
                    "required": ["content"],
                },
            },
            "list_memos": {
                "name": "list_memos",
                "description": "List memos from Memos with optional filters",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "page": {"type": "integer", "default": 1},
                        "page_size": {"type": "integer", "default": 20},
                        "visibility": {"type": "string"},
                        "tag": {"type": "string"},
                    },
                },
            },
            "get_memo": {
                "name": "get_memo",
                "description": "Get a specific memo by name (e.g. memos/xxxxx)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "The memo name (e.g. memos/xxxxx)",
                        }
                    },
                    "required": ["name"],
                },
            },
            "update_memo": {
                "name": "update_memo",
                "description": "Update an existing memo by name (e.g. memos/xxxxx)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "The memo name (e.g. memos/xxxxx)"},
                        "content": {"type": "string"},
                        "visibility": {"type": "string"},
                        "row_status": {"type": "string"},
                    },
                    "required": ["name"],
                },
            },
            "delete_memo": {
                "name": "delete_memo",
                "description": "Delete a memo by name (e.g. memos/xxxxx)",
                "inputSchema": {
                    "type": "object",
                    "properties": {"name": {"type": "string", "description": "The memo name (e.g. memos/xxxxx)"}},
                    "required": ["name"],
                },
            },
            "search_memos": {
                "name": "search_memos",
                "description": "Search memos by content",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "page": {"type": "integer", "default": 1},
                        "page_size": {"type": "integer", "default": 20},
                    },
                    "required": ["query"],
                },
            },
        }
        return tools

    def _register_resources(self) -> Dict[str, Any]:
        resources = {
            "memo": {
                "uriTemplate": "memo://{memo_name}",
                "name": "Individual memo",
                "description": "Access individual memo content (memo_name e.g. memos/xxxxx)",
            },
            "memos_list": {
                "uri": "memos://list",
                "name": "Recent memos list",
                "description": "Access list of recent memos",
            },
            "memos_search": {
                "uriTemplate": "memos://search/{query}",
                "name": "Memos search",
                "description": "Access search results",
            },
        }
        return resources

    def _register_prompts(self) -> Dict[str, Any]:
        prompts = {
            "memo_summary": {
                "name": "memo_summary",
                "description": "Generate a prompt for summarizing recent memos",
                "arguments": [
                    {
                        "name": "memo_count",
                        "description": "Number of recent memos to summarize",
                        "type": "integer",
                        "default": 5,
                    }
                ],
            },
            "memo_organization": {
                "name": "memo_organization",
                "description": "Generate a prompt for helping organize memos",
                "arguments": [
                    {
                        "name": "tag",
                        "description": "Specific tag to focus on (optional)",
                        "type": "string",
                    }
                ],
            },
        }
        return prompts

    def handle_tool_call(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        try:
            if tool_name == "create_memo":
                result = self._create_memo(
                    content=arguments["content"],
                    visibility=arguments.get("visibility", "PRIVATE"),
                )
                return {"content": [{"type": "text", "text": result}]}

            elif tool_name == "list_memos":
                result = self._list_memos(
                    page=arguments.get("page", 1),
                    page_size=arguments.get("page_size", 20),
                    visibility=arguments.get("visibility"),
                    tag=arguments.get("tag"),
                )
                return {"content": [{"type": "text", "text": result}]}

            elif tool_name == "get_memo":
                result = self._get_memo(arguments["name"])
                return {"content": [{"type": "text", "text": result}]}

            elif tool_name == "update_memo":
                result = self._update_memo(
                    memo_name=arguments["name"],
                    content=arguments.get("content"),
                    visibility=arguments.get("visibility"),
                    row_status=arguments.get("row_status"),
                )
                return {"content": [{"type": "text", "text": result}]}

            elif tool_name == "delete_memo":
                result = self._delete_memo(arguments["name"])
                return {"content": [{"type": "text", "text": result}]}

            elif tool_name == "search_memos":
                result = self._search_memos(
                    query=arguments["query"],
                    page=arguments.get("page", 1),
                    page_size=arguments.get("page_size", 20),
                )
                return {"content": [{"type": "text", "text": result}]}

            else:
                raise ValueError(f"Unknown tool: {tool_name}")

        except Exception as e:
            error_message = f"Error executing {tool_name}: {str(e)}"
            logger.error(error_message)
            return {"content": [{"type": "text", "text": json.dumps({"error": error_message})}]}

    def handle_resource_read(self, uri: str) -> Dict[str, Any]:
        try:
            if uri.startswith("memo://"):
                memo_name = uri.replace("memo://", "")
                result = self._get_memo_resource(memo_name)
                return {"contents": [{"type": "text", "text": result}]}

            elif uri == "memos://list":
                result = self._get_memos_list_resource()
                return {"contents": [{"type": "text", "text": result}]}

            elif uri.startswith("memos://search/"):
                query = uri.replace("memos://search/", "")
                result = self._search_memos_resource(query)
                return {"contents": [{"type": "text", "text": result}]}

            else:
                raise ValueError(f"Unknown resource URI: {uri}")

        except Exception as e:
            error_message = f"Error reading resource {uri}: {str(e)}"
            logger.error(error_message)
            return {"contents": [{"type": "text", "text": json.dumps({"error": error_message})}]}

    def _create_memo(self, content: str, visibility: str = "PRIVATE") -> str:
        try:
            result = memos_client.create_memo(content, visibility)
            # create_memo API 直接返回 memo 对象（顶层），无 memo/data 包装；兼容旧格式用 _result_memo
            if not isinstance(result, dict):
                return json.dumps({"success": False, "error": "No memo in response"})
            if result.get("name") is not None or result.get("content") is not None:
                memo = result
            else:
                memo = _result_memo(result)
            if memo:
                return json.dumps({"success": True, "memo": _create_memo_response(memo)})
            return json.dumps({"success": False, "error": "No memo in response"})
        except MemosAPIError as e:
            return _api_error_json(e)
        except Exception as e:
            return json.dumps({"error": str(e)})

    def _list_memos(
        self,
        page: int = 1,
        page_size: int = 20,
        visibility: Optional[str] = None,
        tag: Optional[str] = None,
    ) -> str:
        try:
            result = memos_client.list_memos(
                page=page, page_size=page_size, visibility=visibility, tag=tag
            )
            memos = _result_memos(result)

            if not memos:
                return json.dumps({"memos": [], "count": 0})

            items = [_memo_to_json_obj(m) for m in memos]
            return json.dumps({"memos": items, "count": len(items)})
        except MemosAPIError as e:
            return _api_error_json(e)
        except Exception as e:
            return json.dumps({"error": str(e)})

    def _get_memo(self, memo_name: str) -> str:
        try:
            result = memos_client.get_memo(memo_name)
            memo = _result_memo(result)

            if not memo:
                return json.dumps({"error": f"Memo {memo_name!r} not found."})

            return json.dumps(_memo_to_json_obj(memo))
        except MemosAPIError as e:
            return _api_error_json(e)
        except Exception as e:
            return json.dumps({"error": str(e)})

    def _update_memo(
        self,
        memo_name: str,
        content: Optional[str] = None,
        visibility: Optional[str] = None,
        row_status: Optional[str] = None,
    ) -> str:
        try:
            result = memos_client.update_memo(
                memo_name=memo_name,
                content=content,
                visibility=visibility,
                row_status=row_status,
            )
            return json.dumps({"success": True, "memo_name": memo_name})
        except MemosAPIError as e:
            return _api_error_json(e)
        except Exception as e:
            return json.dumps({"error": str(e)})

    def _delete_memo(self, memo_name: str) -> str:
        try:
            memos_client.delete_memo(memo_name)
            return json.dumps({"success": True, "memo_name": memo_name})
        except MemosAPIError as e:
            return _api_error_json(e)
        except Exception as e:
            return json.dumps({"error": str(e)})

    def _search_memos(self, query: str, page: int = 1, page_size: int = 20) -> str:
        try:
            result = memos_client.search_memos(
                query=query, page=page, page_size=page_size
            )
            memos = _result_memos(result)

            if not memos:
                return json.dumps({"memos": [], "count": 0, "query": query})

            items = [_memo_to_json_obj(m) for m in memos]
            return json.dumps({"memos": items, "count": len(items), "query": query})
        except MemosAPIError as e:
            return _api_error_json(e)
        except Exception as e:
            return json.dumps({"error": str(e)})

    def _get_memo_resource(self, memo_name: str) -> str:
        try:
            result = memos_client.get_memo(memo_name)
            memo = _result_memo(result)

            if not memo:
                return json.dumps({"error": f"Memo {memo_name!r} not found."})

            return json.dumps(_memo_to_json_obj(memo))
        except MemosAPIError as e:
            return _api_error_json(e)
        except Exception as e:
            return json.dumps({"error": str(e)})

    def _get_memos_list_resource(self) -> str:
        try:
            result = memos_client.list_memos(page_size=50)
            memos = _result_memos(result)

            if not memos:
                return json.dumps({"memos": [], "count": 0})

            items = [_memo_to_json_obj(m) for m in memos]
            return json.dumps({"memos": items, "count": len(items)})
        except MemosAPIError as e:
            return _api_error_json(e)
        except Exception as e:
            return json.dumps({"error": str(e)})

    def _search_memos_resource(self, query: str) -> str:
        try:
            result = memos_client.search_memos(query=query, page_size=20)
            memos = _result_memos(result)

            if not memos:
                return json.dumps({"memos": [], "count": 0, "query": query})

            items = [_memo_to_json_obj(m) for m in memos]
            return json.dumps({"memos": items, "count": len(items), "query": query})
        except MemosAPIError as e:
            return _api_error_json(e)
        except Exception as e:
            return json.dumps({"error": str(e)})

    def run_stdio(self):
        logger.info("Starting Memos MCP server with stdio transport...")

        while True:
            try:
                line = input()
                if not line:
                    continue

                try:
                    message = json.loads(line)
                    response = self._handle_message(message)
                    print(json.dumps(response))
                    sys.stdout.flush()
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON: {line}")
                except Exception as e:
                    logger.error(f"Error handling message: {str(e)}")

            except EOFError:
                logger.info("Server connection closed")
                break
            except KeyboardInterrupt:
                logger.info("Server stopped by user")
                break

    def _handle_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        message_id = message.get("id")
        method = message.get("method")
        params = message.get("params", {})

        try:
            if method == "initialize":
                return {
                    "jsonrpc": "2.0",
                    "id": message_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "tools": {"listChanged": True},
                            "resources": {"subscribe": False, "listChanged": True},
                            "prompts": {"listChanged": True},
                        },
                        "serverInfo": {"name": "memos-mcp-server", "version": "1.0.0"},
                    },
                }

            elif method == "tools/list":
                return {
                    "jsonrpc": "2.0",
                    "id": message_id,
                    "result": {"tools": list(self.tools.values())},
                }

            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                result = self.handle_tool_call(tool_name, arguments)
                return {"jsonrpc": "2.0", "id": message_id, "result": result}

            elif method == "resources/list":
                resources = []
                for resource in self.resources.values():
                    if "uriTemplate" in resource:
                        resources.append(
                            {
                                "uri": resource["uriTemplate"],
                                "name": resource["name"],
                                "description": resource["description"],
                            }
                        )
                    else:
                        resources.append(
                            {
                                "uri": resource["uri"],
                                "name": resource["name"],
                                "description": resource["description"],
                            }
                        )
                return {
                    "jsonrpc": "2.0",
                    "id": message_id,
                    "result": {"resources": resources},
                }

            elif method == "resources/read":
                uri = params.get("uri")
                result = self.handle_resource_read(uri)
                return {"jsonrpc": "2.0", "id": message_id, "result": result}

            elif method == "prompts/list":
                return {
                    "jsonrpc": "2.0",
                    "id": message_id,
                    "result": {"prompts": list(self.prompts.values())},
                }

            elif method == "prompts/get":
                name = params.get("name")
                arguments = params.get("arguments", {})
                prompt = self._get_prompt_content(name, arguments)
                return {
                    "jsonrpc": "2.0",
                    "id": message_id,
                    "result": {
                        "description": self.prompts[name]["description"],
                        "messages": [
                            {
                                "role": "user",
                                "content": {"type": "text", "text": prompt},
                            }
                        ],
                    },
                }

            else:
                return {
                    "jsonrpc": "2.0",
                    "id": message_id,
                    "error": {"code": -32601, "message": f"Method not found: {method}"},
                }

        except Exception as e:
            logger.error(f"Error handling {method}: {str(e)}")
            return {
                "jsonrpc": "2.0",
                "id": message_id,
                "error": {"code": -32603, "message": f"Internal error: {str(e)}"},
            }

    def _get_prompt_content(self, name: str, arguments: Dict[str, Any]) -> str:
        if name == "memo_summary":
            memo_count = arguments.get("memo_count", 5)
            return f"""Please summarize the most recent {memo_count} memos from my Memos instance.

Focus on:
1. Key themes and topics
2. Action items or tasks mentioned
3. Important insights or decisions
4. Any patterns or trends

Use the list_memos tool to retrieve the recent memos, then provide a comprehensive summary."""

        elif name == "memo_organization":
            tag = arguments.get("tag")
            if tag:
                return f"""Help me organize and analyze my memos tagged with '{tag}'.

Please:
1. Retrieve all memos with this tag using the list_memos tool
2. Identify common themes and patterns
3. Suggest better organization or additional tags
4. Highlight any important action items or follow-ups"""
            else:
                return """Help me organize my memos.

Please:
1. Retrieve recent memos using list_memos (each memo has a tags field)
2. Analyze the current organization and tags used
3. Suggest improvements to tagging and structure
4. Identify any memos that need better organization"""

        else:
            return f"Unknown prompt: {name}"


def main():
    try:
        settings.validate_config()
        logger.info("Starting Memos MCP server...")
        logger.info(f"Connected to Memos instance: {settings.memos_base_url}")

        server = SimpleMCPServer()
        server.run_stdio()

    except ValueError as e:
        logger.error(f"Configuration error: {str(e)}")
        print(f"Configuration error: {str(e)}")
        print("Please check your .env file or environment variables.")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {str(e)}")
        print(f"Server error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
