"""
API interception module for capturing network requests and responses
"""

import logging
from datetime import datetime
from typing import Any, Dict, List

from playwright.async_api import Page, Response


class APIInterceptor:
    """Captures API requests and responses"""

    def __init__(self, page: Page, logger: logging.Logger):
        """
        Initialize APIInterceptor

        Args:
            page: Playwright page instance
            logger: Logger instance
        """
        self.page = page
        self.logger = logger
        self.captured_requests: List[Dict[str, Any]] = []
        self.api_counter = 0

    async def setup_request_interception(self):
        """Set up listeners for network requests"""

        async def handle_response(response: Response):
            """Handle each response and capture JSON responses"""
            try:
                # Only capture JSON responses
                content_type = response.headers.get('content-type', '')
                if 'json' in content_type.lower():
                    url = response.url
                    method = response.request.method

                    # Try to get response body
                    try:
                        body = await response.json()
                    except:
                        body = await response.text()

                    self.captured_requests.append({
                        'url': url,
                        'method': method,
                        'status': response.status,
                        'response': body,
                        'timestamp': datetime.now().isoformat()
                    })

                    self.logger.debug(f"Captured API response: {method} {url}")

            except Exception as e:
                self.logger.debug(f"Error capturing response: {e}")

        self.page.on('response', handle_response)

    def get_captured_data(self) -> List[Dict[str, Any]]:
        """
        Get all captured API data

        Returns:
            List of captured API requests with responses
        """
        return self.captured_requests

    def clear_captured_data(self):
        """Clear captured data for next view"""
        self.captured_requests = []

    def get_capture_count(self) -> int:
        """
        Get count of captured requests

        Returns:
            Number of captured API requests
        """
        return len(self.captured_requests)
