"""
Navigation module for detecting and handling page navigation elements
"""

import asyncio
import logging
from typing import Any, Dict, List, Set

from playwright.async_api import Page

from . import config
from .utils import retry


class NavigationDetector:
    """Detects all navigation elements on a page (tabs, pagination, expandables)"""

    def __init__(self, page: Page, logger: logging.Logger):
        """
        Initialize NavigationDetector

        Args:
            page: Playwright page instance
            logger: Logger instance
        """
        self.page = page
        self.logger = logger

    async def detect_tabs(self) -> List[Dict[str, Any]]:
        """
        Detect all tab elements on the page

        Returns:
            List of dictionaries containing tab information
        """
        tabs = []

        for selector in config.TAB_SELECTORS:
            try:
                elements = await self.page.query_selector_all(selector)
                for i, elem in enumerate(elements):
                    text = await elem.inner_text()
                    text = text.strip()

                    # Ignore very long text (likely not a tab)
                    if text and len(text) < 100:
                        is_visible = await elem.is_visible()
                        if is_visible:
                            tabs.append({
                                'type': 'tab',
                                'selector': selector,
                                'index': i,
                                'text': text,
                                'element': elem
                            })
            except Exception as e:
                self.logger.debug(f"No elements found for selector {selector}: {e}")

        # Deduplicate by text
        return self._deduplicate_tabs(tabs)

    def _deduplicate_tabs(self, tabs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate tabs based on text"""
        seen_texts = set()
        unique_tabs = []

        for tab in tabs:
            if tab['text'] not in seen_texts:
                seen_texts.add(tab['text'])
                unique_tabs.append(tab)

        return unique_tabs

    async def detect_pagination(self) -> Dict[str, Any]:
        """
        Detect pagination controls

        Returns:
            Dictionary with pagination information and elements
        """
        pagination = {
            'has_pagination': False,
            'next_button': None,
            'prev_button': None,
            'page_numbers': []
        }

        # Look for next button
        for selector in config.NEXT_BUTTON_SELECTORS:
            try:
                elem = await self.page.query_selector(selector)
                if elem and await elem.is_visible():
                    pagination['next_button'] = elem
                    pagination['has_pagination'] = True
                    break
            except:
                pass

        # Look for previous button
        for selector in config.PREV_BUTTON_SELECTORS:
            try:
                elem = await self.page.query_selector(selector)
                if elem and await elem.is_visible():
                    pagination['prev_button'] = elem
                    break
            except:
                pass

        # Look for page numbers
        try:
            page_num_elems = await self.page.query_selector_all(
                '.pagination button, .pagination a'
            )
            for elem in page_num_elems:
                text = await elem.inner_text()
                if text.strip().isdigit():
                    pagination['page_numbers'].append(elem)
        except:
            pass

        return pagination

    async def detect_expandable_sections(self) -> List[Dict[str, Any]]:
        """
        Detect expandable/collapsible sections

        Returns:
            List of dictionaries containing expandable section information
        """
        expandables = []

        # Look for elements with aria-expanded
        try:
            elements = await self.page.query_selector_all('[aria-expanded="false"]')
            for i, elem in enumerate(elements):
                if await elem.is_visible():
                    text = await elem.inner_text()
                    expandables.append({
                        'type': 'expandable',
                        'index': i,
                        'text': text[:50] if text else '',
                        'element': elem
                    })
        except Exception as e:
            self.logger.debug(f"Error detecting expandables: {e}")

        # Look for details/summary elements
        try:
            details = await self.page.query_selector_all('details:not([open])')
            for i, elem in enumerate(details):
                summary = await elem.query_selector('summary')
                if summary:
                    text = await summary.inner_text()
                    expandables.append({
                        'type': 'details',
                        'index': i,
                        'text': text,
                        'element': elem
                    })
        except Exception as e:
            self.logger.debug(f"Error detecting details: {e}")

        return expandables

    async def detect_dropdowns(self) -> List[Dict[str, Any]]:
        """
        Detect dropdown menus

        Returns:
            List of dictionaries containing dropdown information
        """
        dropdowns = []

        try:
            # Native select elements
            selects = await self.page.query_selector_all('select')
            for i, elem in enumerate(selects):
                if await elem.is_visible():
                    options = await elem.query_selector_all('option')
                    option_texts = []

                    for opt in options:
                        text = await opt.inner_text()
                        option_texts.append(text)

                    dropdowns.append({
                        'type': 'select',
                        'index': i,
                        'element': elem,
                        'options': option_texts
                    })
        except Exception as e:
            self.logger.debug(f"Error detecting dropdowns: {e}")

        return dropdowns

    async def get_all_navigation_elements(self) -> Dict[str, Any]:
        """
        Get all navigation elements in one call

        Returns:
            Dictionary containing all detected navigation elements
        """
        self.logger.info("Detecting navigation elements...")

        tabs = await self.detect_tabs()
        pagination = await self.detect_pagination()
        expandables = await self.detect_expandable_sections()
        dropdowns = await self.detect_dropdowns()

        self.logger.info(
            f"Detected: {len(tabs)} tabs, "
            f"pagination: {pagination['has_pagination']}, "
            f"{len(expandables)} expandable sections, "
            f"{len(dropdowns)} dropdowns"
        )

        return {
            'tabs': tabs,
            'pagination': pagination,
            'expandables': expandables,
            'dropdowns': dropdowns
        }


class PageNavigator:
    """Orchestrates systematic navigation through all page states"""

    def __init__(self, page: Page, logger: logging.Logger, timeout: int = config.DEFAULT_TIMEOUT):
        """
        Initialize PageNavigator

        Args:
            page: Playwright page instance
            logger: Logger instance
            timeout: Timeout for page operations in milliseconds
        """
        self.page = page
        self.logger = logger
        self.timeout = timeout
        self.visited_states: Set[str] = set()

    @retry(max_attempts=config.MAX_RETRY_ATTEMPTS, delay=config.RETRY_DELAY)
    async def wait_for_page_stability(self):
        """Wait for page to be fully loaded and stable"""
        try:
            # Wait for network to be idle
            await self.page.wait_for_load_state('networkidle', timeout=self.timeout)

            # Wait for common loading indicators to disappear
            for selector in config.LOADING_SELECTORS:
                try:
                    await self.page.wait_for_selector(
                        selector,
                        state='hidden',
                        timeout=config.ELEMENT_WAIT_TIMEOUT
                    )
                except:
                    pass  # Selector might not exist

            # Additional stabilization wait
            await asyncio.sleep(config.STABILIZATION_WAIT)

        except Exception as e:
            self.logger.warning(f"Page stability wait timed out: {e}")

    async def take_screenshot(self, filepath: str):
        """
        Take screenshot of current page state

        Args:
            filepath: Path where screenshot should be saved
        """
        try:
            await self.page.screenshot(path=filepath, full_page=True)
            self.logger.debug(f"Screenshot saved: {filepath}")
        except Exception as e:
            self.logger.error(f"Failed to take screenshot: {e}")

    async def expand_all_sections(self, expandables: List[Dict[str, Any]]):
        """
        Expand all collapsible sections

        Args:
            expandables: List of expandable section dictionaries
        """
        for expandable in expandables:
            try:
                elem = expandable['element']

                if expandable['type'] == 'expandable':
                    # Check if not already expanded
                    is_expanded = await elem.get_attribute('aria-expanded')
                    if is_expanded == 'false':
                        await elem.click()
                        await self.wait_for_page_stability()

                elif expandable['type'] == 'details':
                    # Check if not already open
                    is_open = await elem.get_attribute('open')
                    if not is_open:
                        summary = await elem.query_selector('summary')
                        if summary:
                            await summary.click()
                            await self.wait_for_page_stability()

                self.logger.debug(f"Expanded section: {expandable['text']}")

            except Exception as e:
                self.logger.warning(f"Failed to expand section: {e}")

    async def navigate_pagination(self, pagination: Dict[str, Any]) -> int:
        """
        Navigate through all pages

        Args:
            pagination: Pagination information dictionary

        Returns:
            Number of pages visited
        """
        if not pagination['has_pagination']:
            return 1

        pages_visited = 1

        while pages_visited < config.MAX_PAGINATION_PAGES:
            try:
                next_btn = pagination['next_button']

                # Check if next button is disabled
                is_disabled = await next_btn.get_attribute('disabled')
                if is_disabled:
                    break

                # Check if button has class indicating disabled state
                classes = await next_btn.get_attribute('class') or ''
                if 'disabled' in classes.lower():
                    break

                # Click next
                await next_btn.click()
                await self.wait_for_page_stability()
                pages_visited += 1

                self.logger.debug(f"Navigated to page {pages_visited}")

            except Exception as e:
                self.logger.debug(f"Pagination ended: {e}")
                break

        return pages_visited
