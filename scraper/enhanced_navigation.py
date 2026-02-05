"""
Enhanced navigation detection for custom buttons and navigation patterns
Use this when standard tab detection doesn't work
"""

import logging
from typing import Any, Dict, List

from playwright.async_api import Page

from . import config


class EnhancedNavigationDetector:
    """
    Enhanced detector for custom navigation patterns
    Detects buttons, links, and clickable elements that lead to different views
    """

    def __init__(self, page: Page, logger: logging.Logger):
        self.page = page
        self.logger = logger

    async def detect_custom_buttons(self) -> List[Dict[str, Any]]:
        """
        Detect custom navigation buttons that don't follow standard patterns
        Looks for:
        - Buttons with navigation-related text
        - Clickable elements with specific classes
        - Links that stay on same domain
        """
        custom_buttons = []

        # Navigation keywords (Italian + English)
        nav_keywords = [
            'visualizza',  # view
            'mostra',      # show
            'dettagli',    # details
            'analisi',     # analysis
            'report',      # report
            'più',         # more
            'view',
            'show',
            'details',
            'more',
            'analysis'
        ]

        # 1. Find all visible buttons
        self.logger.debug("Searching for custom navigation buttons...")

        all_buttons = await self.page.query_selector_all(
            'button, [role="button"], .btn, [class*="button"]'
        )

        for i, btn in enumerate(all_buttons):
            try:
                is_visible = await btn.is_visible()
                if not is_visible:
                    continue

                text = (await btn.inner_text()).strip()
                if not text or len(text) > 100:
                    continue

                classes = await btn.get_attribute('class') or ''

                # Check if text contains navigation keywords
                text_lower = text.lower()
                is_nav_button = any(keyword in text_lower for keyword in nav_keywords)

                if is_nav_button:
                    custom_buttons.append({
                        'type': 'custom_button',
                        'index': i,
                        'text': text,
                        'element': btn,
                        'classes': classes
                    })
                    self.logger.debug(f"Found custom button: '{text}'")

            except Exception as e:
                self.logger.debug(f"Error checking button {i}: {e}")

        # 2. Find clickable divs/spans with navigation text
        clickable_elements = await self.page.query_selector_all(
            '[onclick], div[class*="click"], span[class*="click"]'
        )

        for i, elem in enumerate(clickable_elements):
            try:
                is_visible = await elem.is_visible()
                if not is_visible:
                    continue

                text = (await elem.inner_text()).strip()
                if not text or len(text) > 100:
                    continue

                text_lower = text.lower()
                is_nav_element = any(keyword in text_lower for keyword in nav_keywords)

                if is_nav_element:
                    tag = await elem.evaluate('el => el.tagName')
                    classes = await elem.get_attribute('class') or ''

                    custom_buttons.append({
                        'type': 'clickable_element',
                        'index': i,
                        'text': text,
                        'element': elem,
                        'tag': tag,
                        'classes': classes
                    })
                    self.logger.debug(f"Found clickable element: '{text}'")

            except Exception as e:
                self.logger.debug(f"Error checking clickable element {i}: {e}")

        # 3. Find same-page links (not external)
        links = await self.page.query_selector_all('a')

        for i, link in enumerate(links):
            try:
                is_visible = await link.is_visible()
                if not is_visible:
                    continue

                href = await link.get_attribute('href')
                if not href or href.startswith('http'):
                    # Skip external links
                    continue

                text = (await link.inner_text()).strip()
                if not text or len(text) > 100:
                    continue

                custom_buttons.append({
                    'type': 'navigation_link',
                    'index': i,
                    'text': text,
                    'element': link,
                    'href': href
                })
                self.logger.debug(f"Found navigation link: '{text}' -> {href}")

            except Exception as e:
                self.logger.debug(f"Error checking link {i}: {e}")

        # Deduplicate by text
        seen_texts = set()
        unique_buttons = []
        for btn in custom_buttons:
            if btn['text'] not in seen_texts:
                seen_texts.add(btn['text'])
                unique_buttons.append(btn)

        return unique_buttons

    async def detect_all_clickable_navigation(self) -> List[Dict[str, Any]]:
        """
        Comprehensive detection of all possible navigation elements
        Combines multiple strategies
        """
        all_navigation = []

        # Strategy 1: Standard selectors with broader patterns
        broad_selectors = [
            # Standard tabs
            '[role="tab"]',
            '.tab',
            '.nav-item',

            # Vue.js / React common patterns
            '[class*="tab-"]',
            '[class*="nav-"]',
            '[class*="menu-"]',

            # Chinese/International frameworks
            '.el-tabs__item',      # Element UI
            '.ant-tabs-tab',       # Ant Design
            '.van-tab',            # Vant UI
            '.weui-navbar__item',  # WeUI

            # Generic clickable navigation
            'nav button',
            'nav a',
            '[class*="navigation"] button',
            '[class*="navigation"] a'
        ]

        for selector in broad_selectors:
            try:
                elements = await self.page.query_selector_all(selector)
                for i, elem in enumerate(elements):
                    is_visible = await elem.is_visible()
                    if not is_visible:
                        continue

                    text = (await elem.inner_text()).strip()
                    if text and len(text) < 100:
                        all_navigation.append({
                            'type': 'broad_selector',
                            'selector': selector,
                            'index': i,
                            'text': text,
                            'element': elem
                        })

            except Exception as e:
                self.logger.debug(f"Error with selector {selector}: {e}")

        # Strategy 2: Custom buttons
        custom_buttons = await self.detect_custom_buttons()
        all_navigation.extend(custom_buttons)

        # Deduplicate
        seen = set()
        unique = []
        for nav in all_navigation:
            key = nav['text']
            if key not in seen:
                seen.add(key)
                unique.append(nav)

        self.logger.info(f"Found {len(unique)} total navigation elements")
        return unique
