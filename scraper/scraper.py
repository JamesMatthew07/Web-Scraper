"""
Main scraper module that coordinates all components
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from playwright.async_api import async_playwright, Browser, Page

from . import config
from .extraction import DataExtractor
from .interception import APIInterceptor
from .navigation import NavigationDetector, PageNavigator
from .utils import sanitize_filename, setup_directories, setup_logging, count_data_points


class DashboardScraper:
    """Main scraper class that coordinates all components"""

    def __init__(
        self,
        url: str,
        output_dir: str = config.DEFAULT_OUTPUT_DIR,
        headless: bool = config.DEFAULT_HEADLESS,
        timeout: int = config.DEFAULT_TIMEOUT,
        export_csv: bool = config.DEFAULT_EXPORT_CSV,
        log_level: str = config.DEFAULT_LOG_LEVEL
    ):
        """
        Initialize DashboardScraper

        Args:
            url: URL to scrape
            output_dir: Directory for output files
            headless: Whether to run browser in headless mode
            timeout: Page load timeout in milliseconds
            export_csv: Whether to export tables to CSV
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        """
        self.url = url
        self.output_dir = Path(output_dir)
        self.headless = headless
        self.timeout = timeout
        self.export_csv = export_csv

        # Setup directories
        self.data_dir = self.output_dir / 'data'
        self.screenshot_dir = self.output_dir / 'screenshots'
        self.log_dir = Path('logs')

        setup_directories(self.data_dir, self.screenshot_dir, self.log_dir)

        # Setup logging
        self.logger = setup_logging(self.log_dir, log_level)

        # Initialize stats
        self.stats = {
            'views_scraped': 0,
            'tables_extracted': 0,
            'data_points': 0,
            'files_generated': {
                'json': [],
                'csv': [],
                'screenshots': []
            },
            'errors': []
        }

        # Components (initialized later)
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.nav_detector: Optional[NavigationDetector] = None
        self.data_extractor: Optional[DataExtractor] = None
        self.api_interceptor: Optional[APIInterceptor] = None
        self.page_navigator: Optional[PageNavigator] = None

    async def initialize_browser(self):
        """Initialize Playwright browser and components"""
        self.logger.info("Initializing browser...")

        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=self.headless)
        self.page = await self.browser.new_page()

        # Set viewport size
        await self.page.set_viewport_size({
            'width': config.VIEWPORT_WIDTH,
            'height': config.VIEWPORT_HEIGHT
        })

        # Initialize components
        self.nav_detector = NavigationDetector(self.page, self.logger)
        self.data_extractor = DataExtractor(self.page, self.logger)
        self.api_interceptor = APIInterceptor(self.page, self.logger)
        self.page_navigator = PageNavigator(self.page, self.logger, self.timeout)

        # Setup API interception
        await self.api_interceptor.setup_request_interception()

    async def save_page_data(
        self,
        view_name: str,
        data: Dict[str, Any],
        screenshot_filename: str
    ):
        """
        Save extracted data to JSON and optionally CSV

        Args:
            view_name: Name of the current view
            data: Extracted data dictionary
            screenshot_filename: Name of the screenshot file
        """
        # Prepare data with metadata
        output_data = {
            'page_info': {
                'view_name': view_name,
                'url': self.page.url,
                'timestamp': datetime.now().isoformat(),
                'screenshot': screenshot_filename
            },
            **data
        }

        # Add API data
        api_data = self.api_interceptor.get_captured_data()
        if api_data:
            output_data['api_data'] = api_data

        # Save JSON
        json_filename = (
            f"page_{self.stats['views_scraped']}_"
            f"{sanitize_filename(view_name)}.json"
        )
        json_path = self.data_dir / json_filename

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        self.stats['files_generated']['json'].append(json_filename)
        self.logger.debug(f"Data saved to {json_filename}")

        # Save CSV if enabled
        if self.export_csv and data.get('tables'):
            self._save_tables_as_csv(data['tables'])

        # Update stats
        self.stats['tables_extracted'] += len(data.get('tables', []))
        self.stats['data_points'] += count_data_points(data.get('tables', []))

    def _save_tables_as_csv(self, tables: list):
        """Save tables to CSV files"""
        try:
            import pandas as pd
        except ImportError:
            self.logger.warning("pandas not available, skipping CSV export")
            return

        for i, table in enumerate(tables):
            if table['rows']:
                csv_filename = f"table_{self.stats['views_scraped']}_{i+1}.csv"
                csv_path = self.data_dir / csv_filename

                try:
                    df = pd.DataFrame(table['rows'], columns=table['headers'])
                    df.to_csv(csv_path, index=False)
                    self.stats['files_generated']['csv'].append(csv_filename)
                except Exception as e:
                    self.logger.error(f"Failed to save CSV: {e}")

    async def scrape_current_view(self, view_name: str):
        """
        Scrape data from current page state

        Args:
            view_name: Name of the current view being scraped
        """
        self.stats['views_scraped'] += 1

        self.logger.info(f"Scraping view {self.stats['views_scraped']}: \"{view_name}\"")

        # Wait for stability
        await self.page_navigator.wait_for_page_stability()

        # Extract data
        data = await self.data_extractor.extract_all_data()

        # Take screenshot
        screenshot_filename = (
            f"page_{self.stats['views_scraped']}_"
            f"{sanitize_filename(view_name)}.png"
        )
        screenshot_path = self.screenshot_dir / screenshot_filename
        await self.page_navigator.take_screenshot(str(screenshot_path))
        self.stats['files_generated']['screenshots'].append(screenshot_filename)

        self.logger.info(f"  └─ Screenshot saved: {screenshot_filename}")

        # Save data
        await self.save_page_data(view_name, data, screenshot_filename)

        # Clear API data for next view
        self.api_interceptor.clear_captured_data()

    async def scrape(self):
        """Main scraping workflow"""
        try:
            self.logger.info(f"Starting scrape of: {self.url}")
            self.logger.info("=" * 60)

            # Initialize browser
            await self.initialize_browser()

            # Load initial page
            self.logger.info(f"Loading page: {self.url}")
            await self.page.goto(self.url, wait_until='networkidle', timeout=self.timeout)
            await self.page_navigator.wait_for_page_stability()

            # Detect navigation elements
            nav_elements = await self.nav_detector.get_all_navigation_elements()

            tabs = nav_elements['tabs']
            expandables = nav_elements['expandables']

            # If no tabs, scrape current page
            if not tabs:
                await self._scrape_single_page(nav_elements)
            else:
                await self._scrape_tabbed_interface(tabs)

            # Generate summary
            await self.generate_summary()

            self._log_completion()

        except Exception as e:
            error_msg = f"Fatal error during scraping: {e}"
            self.logger.error(error_msg)
            self.stats['errors'].append(error_msg)
            raise

        finally:
            await self.cleanup()

    async def _scrape_single_page(self, nav_elements: Dict[str, Any]):
        """Scrape a page without tabs"""
        self.logger.info("No tabs detected, scraping single page view")

        # Expand all sections
        if nav_elements['expandables']:
            await self.page_navigator.expand_all_sections(nav_elements['expandables'])

        # Scrape
        await self.scrape_current_view("Main View")

        # Handle pagination if present
        pagination = nav_elements['pagination']
        if pagination['has_pagination']:
            total_pages = await self.page_navigator.navigate_pagination(pagination)
            self.logger.info(f"  └─ Pagination detected: {total_pages} pages")

            for page_num in range(2, total_pages + 1):
                await self.scrape_current_view(f"Page {page_num}")

    async def _scrape_tabbed_interface(self, tabs: list):
        """Scrape a page with tabs"""
        self.logger.info(f"Navigating through {len(tabs)} tabs")

        for i, tab in enumerate(tabs):
            try:
                tab_name = tab['text'] or f"Tab {i+1}"
                self.logger.info(f"\nTab {i+1}/{len(tabs)}: \"{tab_name}\"")

                # Click tab
                await tab['element'].click()
                await self.page_navigator.wait_for_page_stability()

                # Re-detect navigation elements for this tab
                nav_elements = await self.nav_detector.get_all_navigation_elements()

                # Expand sections
                if nav_elements['expandables']:
                    await self.page_navigator.expand_all_sections(
                        nav_elements['expandables']
                    )

                # Scrape tab
                await self.scrape_current_view(tab_name)

                # Handle pagination within tab
                if nav_elements['pagination']['has_pagination']:
                    total_pages = await self.page_navigator.navigate_pagination(
                        nav_elements['pagination']
                    )

                    if total_pages > 1:
                        self.logger.info(f"  └─ Pagination detected: {total_pages} pages")
                        for page_num in range(2, total_pages + 1):
                            await self.scrape_current_view(f"{tab_name} - Page {page_num}")

            except Exception as e:
                error_msg = f"Error scraping tab {tab_name}: {e}"
                self.logger.error(error_msg)
                self.stats['errors'].append(error_msg)

    async def generate_summary(self):
        """Generate summary report"""
        summary = {
            'scrape_timestamp': datetime.now().isoformat(),
            'target_url': self.url,
            'total_views_scraped': self.stats['views_scraped'],
            'total_tables': self.stats['tables_extracted'],
            'total_data_points': self.stats['data_points'],
            'files_generated': self.stats['files_generated'],
            'errors': self.stats['errors']
        }

        summary_path = self.output_dir / 'summary.json'
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        self.logger.info(f"\nSummary report saved to: {summary_path}")

    def _log_completion(self):
        """Log completion message"""
        self.logger.info("=" * 60)
        self.logger.info("Scraping complete!")
        self.logger.info(
            f"Summary: {self.stats['views_scraped']} views scraped, "
            f"{self.stats['tables_extracted']} tables extracted, "
            f"{self.stats['data_points']} data points"
        )

    async def cleanup(self):
        """Cleanup resources"""
        if self.browser:
            await self.browser.close()
            self.logger.info("Browser closed")
