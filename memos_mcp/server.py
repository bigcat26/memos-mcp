"""Main MCP server for Memos integration."""

import sys
import os
import json
import logging
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.config import settings
from utils.client import memos_client, MemosAPIError

logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


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
                "description": "Get a specific memo by ID",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "memo_id": {
                            "type": "integer",
                            "description": "The ID of the memo to retrieve",
                        }
                    },
                    "required": ["memo_id"],
                },
            },
            "update_memo": {
                "name": "update_memo",
                "description": "Update an existing memo",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "memo_id": {"type": "integer"},
                        "content": {"type": "string"},
                        "visibility": {"type": "string"},
                        "row_status": {"type": "string"},
                    },
                    "required": ["memo_id"],
                },
            },
            "delete_memo": {
                "name": "delete_memo",
                "description": "Delete a memo",
                "inputSchema": {
                    "type": "object",
                    "properties": {"memo_id": {"type": "integer"}},
                    "required": ["memo_id"],
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
            "get_tags": {
                "name": "get_tags",
                "description": "Get all available tags from Memos",
                "inputSchema": {"type": "object"},
            },
        }
        return tools

    def _register_resources(self) -> Dict[str, Any]:
        resources = {
            "memo": {
                "uriTemplate": "memo://{memo_id}",
                "name": "Individual memo",
                "description": "Access individual memo content",
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
                result = self._get_memo(arguments["memo_id"])
                return {"content": [{"type": "text", "text": result}]}

            elif tool_name == "update_memo":
                result = self._update_memo(
                    memo_id=arguments["memo_id"],
                    content=arguments.get("content"),
                    visibility=arguments.get("visibility"),
                    row_status=arguments.get("row_status"),
                )
                return {"content": [{"type": "text", "text": result}]}

            elif tool_name == "delete_memo":
                result = self._delete_memo(arguments["memo_id"])
                return {"content": [{"type": "text", "text": result}]}

            elif tool_name == "search_memos":
                result = self._search_memos(
                    query=arguments["query"],
                    page=arguments.get("page", 1),
                    page_size=arguments.get("page_size", 20),
                )
                return {"content": [{"type": "text", "text": result}]}

            elif tool_name == "get_tags":
                result = self._get_tags()
                return {"content": [{"type": "text", "text": result}]}

            else:
                raise ValueError(f"Unknown tool: {tool_name}")

        except Exception as e:
            error_message = f"Error executing {tool_name}: {str(e)}"
            logger.error(error_message)
            return {"content": [{"type": "text", "text": error_message}]}

    def handle_resource_read(self, uri: str) -> Dict[str, Any]:
        try:
            if uri.startswith("memo://"):
                memo_id = uri.replace("memo://", "")
                result = self._get_memo_resource(memo_id)
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
            return {"contents": [{"type": "text", "text": error_message}]}

    def _create_memo(self, content: str, visibility: str = "PRIVATE") -> str:
        try:
            result = memos_client.create_memo(content, visibility)
            memo_id = result.get("data", {}).get("id", "unknown")
            return f"Successfully created memo #{memo_id}: {content[:50]}..."
        except MemosAPIError as e:
            return f"Error creating memo: {str(e)}"
        except Exception as e:
            return f"Unexpected error: {str(e)}"

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
            memos = result.get("data", [])

            if not memos:
                return "No memos found."

            output = f"Found {len(memos)} memos:\n\n"
            for memo in memos:
                memo_id = memo.get("id", "unknown")
                content = memo.get("content", "")[:100]
                created_at = memo.get("createdTs", "")
                visibility = memo.get("visibility", "unknown")

                output += f"#{memo_id} [{visibility}] {content}...\n"

            return output
        except MemosAPIError as e:
            return f"Error listing memos: {str(e)}"
        except Exception as e:
            return f"Unexpected error: {str(e)}"

    def _get_memo(self, memo_id: int) -> str:
        try:
            result = memos_client.get_memo(memo_id)
            memo = result.get("data", {})

            if not memo:
                return f"Memo #{memo_id} not found."

            content = memo.get("content", "")
            created_at = memo.get("createdTs", "")
            updated_at = memo.get("updatedTs", "")
            visibility = memo.get("visibility", "")
            creator = memo.get("creator", {}).get("nickname", "Unknown")

            output = f"""Memo #{memo_id}
Creator: {creator}
Visibility: {visibility}
Created: {created_at}
Updated: {updated_at}

Content:
{content}"""

            return output
        except MemosAPIError as e:
            return f"Error getting memo: {str(e)}"
        except Exception as e:
            return f"Unexpected error: {str(e)}"

    def _update_memo(
        self,
        memo_id: int,
        content: Optional[str] = None,
        visibility: Optional[str] = None,
        row_status: Optional[str] = None,
    ) -> str:
        try:
            result = memos_client.update_memo(
                memo_id=memo_id,
                content=content,
                visibility=visibility,
                row_status=row_status,
            )
            return f"Successfully updated memo #{memo_id}"
        except MemosAPIError as e:
            return f"Error updating memo: {str(e)}"
        except Exception as e:
            return f"Unexpected error: {str(e)}"

    def _delete_memo(self, memo_id: int) -> str:
        try:
            memos_client.delete_memo(memo_id)
            return f"Successfully deleted memo #{memo_id}"
        except MemosAPIError as e:
            return f"Error deleting memo: {str(e)}"
        except Exception as e:
            return f"Unexpected error: {str(e)}"

    def _search_memos(self, query: str, page: int = 1, page_size: int = 20) -> str:
        try:
            result = memos_client.search_memos(
                query=query, page=page, page_size=page_size
            )
            memos = result.get("data", [])

            if not memos:
                return f"No memos found for query: '{query}'"

            output = f"Found {len(memos)} memos matching '{query}':\n\n"
            for memo in memos:
                memo_id = memo.get("id", "unknown")
                content = memo.get("content", "")[:100]
                created_at = memo.get("createdTs", "")

                output += f"#{memo_id} {content}...\n"

            return output
        except MemosAPIError as e:
            return f"Error searching memos: {str(e)}"
        except Exception as e:
            return f"Unexpected error: {str(e)}"

    def _get_tags(self) -> str:
        try:
            tags = memos_client.get_tags()
            if not tags:
                return "No tags found."
            return f"Available tags: {', '.join(tags)}"
        except MemosAPIError as e:
            return f"Error getting tags: {str(e)}"
        except Exception as e:
            return f"Unexpected error: {str(e)}"

    def _get_memo_resource(self, memo_id: str) -> str:
        try:
            memo_id_int = int(memo_id)
            result = memos_client.get_memo(memo_id_int)
            memo = result.get("data", {})

            if not memo:
                return f"Memo #{memo_id} not found."

            return memo.get("content", "")
        except ValueError:
            return f"Invalid memo ID: {memo_id}"
        except MemosAPIError as e:
            return f"Error accessing memo: {str(e)}"
        except Exception as e:
            return f"Unexpected error: {str(e)}"

    def _get_memos_list_resource(self) -> str:
        try:
            result = memos_client.list_memos(page_size=50)
            memos = result.get("data", [])

            if not memos:
                return "No memos found."

            output = "Recent Memos:\n\n"
            for memo in memos:
                memo_id = memo.get("id", "unknown")
                content = memo.get("content", "")
                created_at = memo.get("createdTs", "")

                output += f"#{memo_id} [{created_at}]\n{content}\n\n"

            return output
        except MemosAPIError as e:
            return f"Error accessing memos: {str(e)}"
        except Exception as e:
            return f"Unexpected error: {str(e)}"

    def _search_memos_resource(self, query: str) -> str:
        try:
            result = memos_client.search_memos(query=query, page_size=20)
            memos = result.get("data", [])

            if not memos:
                return f"No memos found for query: '{query}'"

            output = f"Search Results for '{query}':\n\n"
            for memo in memos:
                memo_id = memo.get("id", "unknown")
                content = memo.get("content", "")
                created_at = memo.get("createdTs", "")

                output += f"#{memo_id} [{created_at}]\n{content}\n\n"

            return output
        except MemosAPIError as e:
            return f"Error searching memos: {str(e)}"
        except Exception as e:
            return f"Unexpected error: {str(e)}"

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
1. Get all available tags using get_tags
2. Retrieve recent memos using list_memos
3. Analyze the current organization
4. Suggest improvements to tagging and structure
5. Identify any memos that need better organization"""

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
