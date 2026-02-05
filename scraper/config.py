"""
Configuration constants and default values
"""

# Default values
DEFAULT_TIMEOUT = 30000  # milliseconds
DEFAULT_OUTPUT_DIR = './output'
DEFAULT_LOG_LEVEL = 'INFO'
DEFAULT_HEADLESS = False
DEFAULT_EXPORT_CSV = False

# Browser settings
VIEWPORT_WIDTH = 1920
VIEWPORT_HEIGHT = 1080

# Retry settings
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAY = 2.0  # seconds

# Wait settings
STABILIZATION_WAIT = 1.0  # seconds after network idle
ELEMENT_WAIT_TIMEOUT = 2000  # milliseconds

# Pagination limits
MAX_PAGINATION_PAGES = 50  # Safety limit to prevent infinite loops

# File naming
MAX_FILENAME_LENGTH = 50

# Tab detection selectors
TAB_SELECTORS = [
    '[role="tab"]',
    '.tab',
    '.nav-item',
    '.tab-item',
    '[aria-selected]',
    '.tabs button',
    '.nav-tabs a',
    'ul[role="tablist"] > *'
]

# Pagination selectors
NEXT_BUTTON_SELECTORS = [
    'button:has-text("Next")',
    'a:has-text("Next")',
    '[aria-label*="next" i]',
    '.pagination .next',
    'button:has-text(">")',
    '[class*="next" i]'
]

PREV_BUTTON_SELECTORS = [
    'button:has-text("Previous")',
    'a:has-text("Previous")',
    '[aria-label*="prev" i]',
    '.pagination .prev',
    'button:has-text("<")',
    '[class*="prev" i]'
]

# Loading indicator selectors
LOADING_SELECTORS = [
    '.loading',
    '.spinner',
    '[class*="loading"]',
    '[class*="spinner"]',
    '[aria-busy="true"]'
]

# Metric/KPI selectors
METRIC_SELECTORS = [
    '.metric',
    '.stat',
    '.kpi',
    '.card-value',
    '[class*="metric"]',
    '[class*="stat"]',
    '[class*="value"]',
    '[class*="count"]'
]

# Section/container selectors
SECTION_TAGS = ['section', 'article', 'div[class*="section"]', 'div[class*="panel"]']

# Default target URL
DEFAULT_URL = 'https://eu-meicepro-api.meiquc.cn/meicepro-h5/pages/report/report?id=5111c64f-88bd-49de-81d2-700916ef7750&language=it'
