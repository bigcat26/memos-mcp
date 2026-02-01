"""HTTP client for interacting with Memos API."""

import logging
from typing import Dict, List, Optional, Any
import urllib.request
import urllib.error
import json
from .config import settings


logger = logging.getLogger(__name__)


class MemosAPIError(Exception):
    """Custom exception for Memos API errors."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class MemosClient:
    """HTTP client for Memos API."""

    def __init__(self):
        """Initialize the Memos client."""
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
        """Make a request to the Memos API."""
        url = f"{self.base_url}{endpoint}"

        # Add query parameters
        if params:
            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
            url += f"?{query_string}"

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

    def get_memo(self, memo_id: int) -> Dict[str, Any]:
        """Get a specific memo by ID."""
        return self._make_request("GET", f"/memo/{memo_id}")

    def update_memo(
        self,
        memo_id: int,
        content: Optional[str] = None,
        visibility: Optional[str] = None,
        row_status: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update an existing memo."""
        data = {}
        if content is not None:
            data["content"] = content
        if visibility is not None:
            data["visibility"] = visibility
        if row_status is not None:
            data["rowStatus"] = row_status

        return self._make_request("PATCH", f"/memo/{memo_id}", data)

    def delete_memo(self, memo_id: int) -> Dict[str, Any]:
        """Delete a memo."""
        return self._make_request("DELETE", f"/memo/{memo_id}")

    def search_memos(
        self, query: str, page: int = 1, page_size: int = 20
    ) -> Dict[str, Any]:
        """Search memos by content."""
        params = {"filter": query, "page": str(page), "pageSize": str(page_size)}
        return self._make_request("GET", "/memos", params=params)

    def get_tags(self) -> List[str]:
        """Get all available tags."""
        response = self._make_request("GET", "/tags")
        return [tag["name"] for tag in response.get("data", [])]

    def get_user_info(self) -> Dict[str, Any]:
        """Get current user information."""
        return self._make_request("GET", "/user/me")


# Global client instance
memos_client = MemosClient()
