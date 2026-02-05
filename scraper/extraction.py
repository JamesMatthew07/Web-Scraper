"""
Data extraction module for extracting tables, text, and metrics from pages
"""

import logging
import re
from typing import Dict, List, Any

from bs4 import BeautifulSoup
from playwright.async_api import Page

from . import config


class DataExtractor:
    """Extracts all data from the current page state"""

    def __init__(self, page: Page, logger: logging.Logger):
        """
        Initialize DataExtractor

        Args:
            page: Playwright page instance
            logger: Logger instance
        """
        self.page = page
        self.logger = logger

    async def extract_tables(self) -> List[Dict[str, Any]]:
        """
        Extract all tables from the page

        Returns:
            List of dictionaries containing table data with headers and rows
        """
        tables = []

        try:
            html = await self.page.content()
            soup = BeautifulSoup(html, 'html.parser')

            table_elements = soup.find_all('table')
            self.logger.debug(f"Found {len(table_elements)} table elements")

            for i, table in enumerate(table_elements):
                try:
                    headers = self._extract_table_headers(table)
                    rows = self._extract_table_rows(table, has_thead=bool(table.find('thead')))

                    if rows or headers:
                        tables.append({
                            'table_id': i + 1,
                            'headers': headers,
                            'rows': rows,
                            'row_count': len(rows),
                            'column_count': len(headers) if headers else (
                                len(rows[0]) if rows else 0
                            )
                        })

                except Exception as e:
                    self.logger.error(f"Error extracting table {i}: {e}")

        except Exception as e:
            self.logger.error(f"Error in extract_tables: {e}")

        return tables

    def _extract_table_headers(self, table) -> List[str]:
        """Extract headers from a table element"""
        headers = []

        # Try to find headers in thead
        thead = table.find('thead')
        if thead:
            header_rows = thead.find_all('tr')
            if header_rows:
                header_cells = header_rows[0].find_all(['th', 'td'])
                headers = [cell.get_text(strip=True) for cell in header_cells]

        # If no thead, try first row
        if not headers:
            first_row = table.find('tr')
            if first_row:
                cells = first_row.find_all(['th', 'td'])
                headers = [cell.get_text(strip=True) for cell in cells]

        return headers

    def _extract_table_rows(self, table, has_thead: bool = False) -> List[List[str]]:
        """Extract rows from a table element"""
        rows = []

        tbody = table.find('tbody')
        row_elements = tbody.find_all('tr') if tbody else table.find_all('tr')

        # Skip first row if it was used as header and there's no thead
        start_idx = 1 if not has_thead and self._extract_table_headers(table) else 0

        for row in row_elements[start_idx:]:
            cells = row.find_all(['td', 'th'])
            row_data = [cell.get_text(strip=True) for cell in cells]
            if any(row_data):  # Only add non-empty rows
                rows.append(row_data)

        return rows

    async def extract_text_sections(self) -> Dict[str, str]:
        """
        Extract text content organized by sections

        Returns:
            Dictionary mapping section names to text content
        """
        sections = {}

        try:
            html = await self.page.content()
            soup = BeautifulSoup(html, 'html.parser')

            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()

            # Try to find semantic sections
            section_count = 0
            for tag in config.SECTION_TAGS:
                elements = soup.select(tag)
                for elem in elements:
                    section_name = self._get_section_name(elem, section_count)
                    text = elem.get_text(separator=' ', strip=True)

                    if text and len(text) > 20:  # Ignore very short sections
                        sections[section_name] = text
                        section_count += 1

            # If no sections found, get main content
            if not sections:
                main = soup.find('main') or soup.find('body')
                if main:
                    sections['main_content'] = main.get_text(separator=' ', strip=True)

        except Exception as e:
            self.logger.error(f"Error extracting text sections: {e}")

        return sections

    def _get_section_name(self, element, default_index: int) -> str:
        """Get a name for a section element"""
        # Try to find a heading
        heading = element.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        if heading:
            return heading.get_text(strip=True)
        return f"section_{default_index}"

    async def extract_metrics(self) -> Dict[str, Any]:
        """
        Extract numeric values and metrics/KPIs

        Returns:
            Dictionary mapping metric names to values
        """
        metrics = {}

        try:
            html = await self.page.content()
            soup = BeautifulSoup(html, 'html.parser')

            metric_count = 0
            for selector in config.METRIC_SELECTORS:
                elements = soup.select(selector)
                for elem in elements:
                    text = elem.get_text(strip=True)

                    # Try to extract numbers
                    numbers = re.findall(r'[\d,\.]+%?', text)
                    if numbers:
                        label = self._find_metric_label(elem)
                        key = label if label else f"metric_{metric_count}"
                        metrics[key] = text
                        metric_count += 1

        except Exception as e:
            self.logger.error(f"Error extracting metrics: {e}")

        return metrics

    def _find_metric_label(self, element) -> str:
        """Try to find a label for a metric element"""
        parent = element.parent
        if parent:
            siblings = parent.find_all(['span', 'div', 'p', 'label'])
            for sib in siblings:
                sib_text = sib.get_text(strip=True)
                elem_text = element.get_text(strip=True)
                if sib_text and sib_text != elem_text:
                    return sib_text
        return None

    async def extract_all_data(self) -> Dict[str, Any]:
        """
        Extract all data from current page state

        Returns:
            Dictionary containing tables, text_sections, and metrics
        """
        self.logger.debug("Extracting all data...")

        tables = await self.extract_tables()
        text_sections = await self.extract_text_sections()
        metrics = await self.extract_metrics()

        self.logger.info(
            f"  └─ Extracted {len(tables)} tables, "
            f"{len(text_sections)} text sections, "
            f"{len(metrics)} metrics"
        )

        return {
            'tables': tables,
            'text_sections': text_sections,
            'metrics': metrics
        }
