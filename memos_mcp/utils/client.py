"""HTTP client for interacting with Memos API."""

import json
import logging
from typing import Any, Dict, Optional
import urllib.error
import urllib.request
from urllib.parse import urlencode, quote

from .config import settings


logger = logging.getLogger(__name__)

# memo name 可能带 "memos/" 前缀，拼 URL 时统一去掉避免 /memos/memos/xxx
MEMOS_NAME_PREFIX = "memos/"


def _memo_path_segment(memo_name: str) -> str:
    """规范化 memo name 为路径段：若含 memos/ 前缀则去掉，再 URL 编码。"""
    name = (memo_name or "").strip()
    if name.startswith(MEMOS_NAME_PREFIX):
        name = name[len(MEMOS_NAME_PREFIX) :].lstrip("/")
    return quote(name, safe="")


class MemosAPIError(Exception):
    """Custom exception for Memos API errors."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class MemosClient:
    """HTTP client for Memos API."""

    def __init__(self):
        """Initialize Memos client."""
        self.base_url = settings.memos_api_url
        self.access_token = settings.memos_access_token
        self.timeout = settings.memos_timeout

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make a request to Memos API."""
        url = f"{self.base_url}{endpoint}"

        # Add query parameters (URL-encode for CEL filter etc.)
        if params:
            url += "?" + urlencode(params)

        try:
            # Prepare request
            req = urllib.request.Request(url)
            req.method = method

            # Add headers
            req.add_header("Authorization", f"Bearer {self.access_token}")
            req.add_header("Content-Type", "application/json")
            req.add_header("Accept", "application/json")

            # Add data if present
            if data:
                req.data = json.dumps(data).encode("utf-8")

            # Make request
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                response_data = response.read().decode("utf-8")
                return json.loads(response_data)

        except urllib.error.HTTPError as e:
            error_message = e.read().decode("utf-8")
            logger.error(f"HTTP error: {e.code} - {error_message}")
            raise MemosAPIError(f"Memos API error: {e.code} - {error_message}", e.code)
        except urllib.error.URLError as e:
            logger.error(f"Request error: {str(e)}")
            raise MemosAPIError(f"Failed to connect to Memos: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise MemosAPIError(f"Unexpected error: {str(e)}")

    def create_memo(self, content: str, visibility: str = "PRIVATE") -> Dict[str, Any]:
        """Create a new memo."""
        data = {"content": content, "visibility": visibility}
        return self._make_request("POST", "/memos", data)

    def list_memos(
        self,
        page: int = 1,
        page_size: int = 20,
        visibility: Optional[str] = None,
        creator_id: Optional[int] = None,
        row_status: Optional[str] = None,
        tag: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List memos with optional filters."""
        params = {"page": str(page), "pageSize": str(page_size)}

        if visibility:
            params["visibility"] = visibility
        if creator_id:
            params["creatorId"] = str(creator_id)
        if row_status:
            params["rowStatus"] = row_status
        if tag:
            params["tag"] = tag

        return self._make_request("GET", "/memos", params=params)

    def get_memo(self, memo_name: str) -> Dict[str, Any]:
        """Get a specific memo by name (e.g. memos/xxxxx 或 xxxxx)。"""
        path = _memo_path_segment(memo_name)
        return self._make_request("GET", f"/memos/{path}")

    def update_memo(
        self,
        memo_name: str,
        content: Optional[str] = None,
        visibility: Optional[str] = None,
        row_status: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update an existing memo by name (e.g. memos/xxxxx 或 xxxxx)。"""
        data = {}
        if content is not None:
            data["content"] = content
        if visibility is not None:
            data["visibility"] = visibility
        if row_status is not None:
            data["rowStatus"] = row_status
        path = _memo_path_segment(memo_name)
        return self._make_request("PATCH", f"/memos/{path}", data)

    def delete_memo(self, memo_name: str) -> Dict[str, Any]:
        """Delete a memo by name (e.g. memos/xxxxx 或 xxxxx)。"""
        path = _memo_path_segment(memo_name)
        return self._make_request("DELETE", f"/memos/{path}")

    def search_memos(
        self,
        query: str,
        page: int = 1,
        page_size: int = 20,
        page_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Search memos by content. Filter uses CEL: content.contains(\"keyword\")."""
        # ListMemos expects CEL filter; plain keyword -> content.contains("keyword")
        escaped = (query or "").replace("\\", "\\\\").replace('"', '\\"')
        cel_filter = f'content.contains("{escaped}")'
        params: Dict[str, Any] = {"pageSize": str(page_size), "filter": cel_filter}
        if page_token:
            params["pageToken"] = page_token
        return self._make_request("GET", "/memos", params=params)

    def get_user_info(self) -> Dict[str, Any]:
        """Get current user information."""
        return self._make_request("GET", "/user/me")


# Global client instance
memos_client = MemosClient()
