"""
Command-line interface for the dashboard scraper
"""

import argparse
import asyncio

from . import config
from .scraper import DashboardScraper


def create_parser() -> argparse.ArgumentParser:
    """
    Create and configure argument parser

    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(
        description='Comprehensive web scraper for JavaScript-rendered dashboards',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  python -m scraper.main

  # Run headless with CSV export
  python -m scraper.main --headless --export-csv

  # Custom output directory and timeout
  python -m scraper.main --output-dir ./my-output --timeout 60000

  # Debug mode
  python -m scraper.main --log-level DEBUG

  # Custom URL
  python -m scraper.main --url "https://example.com/dashboard"
        """
    )

    parser.add_argument(
        '--url',
        type=str,
        default=config.DEFAULT_URL,
        help='URL to scrape (default: configured dashboard URL)'
    )

    parser.add_argument(
        '--headless',
        action='store_true',
        help='Run browser in headless mode (no visible window)'
    )

    parser.add_argument(
        '--timeout',
        type=int,
        default=config.DEFAULT_TIMEOUT,
        help=f'Page load timeout in milliseconds (default: {config.DEFAULT_TIMEOUT})'
    )

    parser.add_argument(
        '--output-dir',
        type=str,
        default=config.DEFAULT_OUTPUT_DIR,
        help=f'Directory for output files (default: {config.DEFAULT_OUTPUT_DIR})'
    )

    parser.add_argument(
        '--export-csv',
        action='store_true',
        help='Export tables to CSV files in addition to JSON'
    )

    parser.add_argument(
        '--log-level',
        type=str,
        default=config.DEFAULT_LOG_LEVEL,
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help=f'Logging level (default: {config.DEFAULT_LOG_LEVEL})'
    )

    return parser


def main():
    """Main entry point for CLI"""
    parser = create_parser()
    args = parser.parse_args()

    # Create scraper instance
    scraper = DashboardScraper(
        url=args.url,
        output_dir=args.output_dir,
        headless=args.headless,
        timeout=args.timeout,
        export_csv=args.export_csv,
        log_level=args.log_level
    )

    # Run scraper
    asyncio.run(scraper.scrape())


if __name__ == '__main__':
    main()
