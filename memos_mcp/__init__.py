"""Memos MCP Server

A Model Context Protocol (MCP) server that provides integration with the Memos API.
This package allows AI assistants to interact with Memos instances for managing
notes, memos, and knowledge bases.
"""

from memos_mcp.server import SimpleMCPServer, TOOL_NAMES

__version__ = "1.0.0"
__author__ = "MCP Server Developer"
__all__ = ["SimpleMCPServer", "TOOL_NAMES"]