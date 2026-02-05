#!/usr/bin/env python3
"""
Backward compatibility wrapper for the refactored scraper
This file maintains the same interface as before, now using the modular package
"""

from scraper.main import main

if __name__ == '__main__':
    main()
