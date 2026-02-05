#!/usr/bin/env python3
"""
COMPLETE DASHBOARD SCRAPER - Extracts ALL data
Main page + Detail pages (Aging & Skin Analysis)
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright

TARGET_URL = 'https://eu-meicepro-api.meiquc.cn/meicepro-h5/pages/report/report?id=5111c64f-88bd-49de-81d2-700916ef7750&language=it'
OUTPUT_DIR = Path('./complete_data')
TIMEOUT = 60000

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


async def extract_section(page, section_name, section_num, output_dir):
    """Extract data from current page"""
    logger.info(f"\n📊 Extracting: {section_name}")

    await asyncio.sleep(3)
    try:
        await page.wait_for_load_state('networkidle', timeout=10000)
    except:
        pass

    body = await page.query_selector('body')
    text = await body.inner_text() if body else ""
    html = await page.content()

    data = {
        'section_name': section_name,
        'section_number': section_num,
        'url': page.url,
        'timestamp': datetime.now().isoformat(),
        'text_content': text,
        'text_length': len(text),
        'html_length': len(html)
    }

    safe_name = section_name.replace(' ', '_')
    json_file = output_dir / 'data' / f"{section_num}_{safe_name}.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    screenshot_file = output_dir / 'screenshots' / f"{section_num}_{safe_name}.png"
    await page.screenshot(path=str(screenshot_file), full_page=True)

    logger.info(f"  ✓ Text: {len(text):,} chars")
    logger.info(f"  ✓ URL: {page.url}")
    logger.info(f"  ✓ Saved: {json_file.name}")

    return data


async def find_and_click_all_buttons(page, output_dir, section_start_num, api_requests):
    """Find ALL 'Visualizza di più' buttons and click them one by one"""

    # Find ALL elements with this text
    all_elements = await page.query_selector_all('*:has-text("Visualizza di più")')

    clickable_buttons = []
    seen_positions = set()

    for elem in all_elements:
        try:
            is_visible = await elem.is_visible()
            if not is_visible:
                continue

            box = await elem.bounding_box()
            if not box:
                continue

            # Use position to deduplicate
            pos = (int(box['x']), int(box['y']))
            pos_key = f"{pos[0]//10}_{pos[1]//10}"  # Group nearby elements

            if pos_key in seen_positions:
                continue
            seen_positions.add(pos_key)

            # Get section name
            section_name = await elem.evaluate('''
                el => {
                    let parent = el.parentElement;
                    while (parent) {
                        const text = parent.textContent;
                        if (text.includes('Livello di Invecchiamento')) {
                            return 'Aging_Level';
                        }
                        if (text.includes('Analisi della Pelle')) {
                            return 'Skin_Analysis';
                        }
                        parent = parent.parentElement;
                    }
                    return 'Unknown';
                }
            ''')

            if section_name != 'Unknown':
                clickable_buttons.append({
                    'element': elem,
                    'section': section_name,
                    'position': pos
                })

        except:
            pass

    logger.info(f"\n✅ Found {len(clickable_buttons)} clickable 'Visualizza di più' elements")

    # Click each one
    section_num = section_start_num
    for i, btn in enumerate(clickable_buttons):
        try:
            logger.info(f"\n{'='*70}")
            logger.info(f"🖱️  Clicking [{i+1}/{len(clickable_buttons)}]: {btn['section']}")
            logger.info(f"{'='*70}")

            initial_url = page.url
            api_requests.clear()

            # Multiple click attempts
            await btn['element'].click(force=True)
            await asyncio.sleep(6)  # Wait longer

            # Check for navigation
            new_url = page.url
            if new_url != initial_url:
                logger.info(f"  ✓ NAVIGATED to: {new_url}")

                # Extract detail page
                await extract_section(page, btn['section'], section_num, output_dir)

                # Save API data
                for j, api in enumerate(api_requests):
                    api_file = output_dir / 'api_data' / f"{section_num}_{btn['section']}_api_{j+1}.json"
                    with open(api_file, 'w', encoding='utf-8') as f:
                        json.dump(api, f, indent=2, ensure_ascii=False)

                if api_requests:
                    logger.info(f"  ✓ Captured {len(api_requests)} API requests")

                section_num += 1

                # Go back
                await page.go_back(wait_until='networkidle', timeout=10000)
                await asyncio.sleep(3)

                # Re-find buttons after navigation
                all_elements = await page.query_selector_all('*:has-text("Visualizza di più")')
                clickable_buttons_new = []
                seen_positions_new = set()

                for elem in all_elements:
                    try:
                        if await elem.is_visible():
                            box = await elem.bounding_box()
                            if box:
                                pos = (int(box['x']), int(box['y']))
                                pos_key = f"{pos[0]//10}_{pos[1]//10}"
                                if pos_key not in seen_positions_new:
                                    seen_positions_new.add(pos_key)
                                    section_name = await elem.evaluate('''
                                        el => {
                                            let parent = el.parentElement;
                                            while (parent) {
                                                const text = parent.textContent;
                                                if (text.includes('Livello di Invecchiamento')) return 'Aging_Level';
                                                if (text.includes('Analisi della Pelle')) return 'Skin_Analysis';
                                                parent = parent.parentElement;
                                            }
                                            return 'Unknown';
                                        }
                                    ''')
                                    if section_name != 'Unknown':
                                        clickable_buttons_new.append({
                                            'element': elem,
                                            'section': section_name,
                                            'position': pos
                                        })
                    except:
                        pass

                clickable_buttons = clickable_buttons_new
                logger.info(f"  ✓ Re-found {len(clickable_buttons)} buttons")

            else:
                logger.info(f"  ! No navigation (modal?), same URL")

        except Exception as e:
            logger.error(f"❌ Error: {e}")
            try:
                await page.goto(TARGET_URL, wait_until='networkidle', timeout=TIMEOUT)
                await asyncio.sleep(2)
            except:
                pass

    return section_num


async def main():
    logger.info("=" * 80)
    logger.info("🎯 COMPLETE DASHBOARD SCRAPER")
    logger.info("=" * 80)

    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / 'data').mkdir(exist_ok=True)
    (OUTPUT_DIR / 'screenshots').mkdir(exist_ok=True)
    (OUTPUT_DIR / 'api_data').mkdir(exist_ok=True)

    api_requests = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.set_viewport_size({'width': 1920, 'height': 1080})

        async def capture_api(response):
            try:
                if 'json' in response.headers.get('content-type', '').lower():
                    try:
                        body = await response.json()
                    except:
                        body = await response.text()
                    api_requests.append({
                        'url': response.url,
                        'method': response.request.method,
                        'status': response.status,
                        'response': body,
                        'timestamp': datetime.now().isoformat()
                    })
            except:
                pass

        page.on('response', capture_api)

        # Load main page
        logger.info(f"\n📄 Loading: {TARGET_URL}")
        await page.goto(TARGET_URL, wait_until='networkidle', timeout=TIMEOUT)
        await asyncio.sleep(3)

        # Extract main page
        await extract_section(page, "Main_Page", 0, OUTPUT_DIR)

        # Save API data
        for i, api in enumerate(api_requests):
            api_file = OUTPUT_DIR / 'api_data' / f"0_main_page_api_{i+1}.json"
            with open(api_file, 'w', encoding='utf-8') as f:
                json.dump(api, f, indent=2, ensure_ascii=False)

        logger.info(f"  ✓ Captured {len(api_requests)} API requests from main page")

        # Find and click all buttons
        final_section_num = await find_and_click_all_buttons(page, OUTPUT_DIR, 1, api_requests)

        # Summary
        json_files = list((OUTPUT_DIR / 'data').glob('*.json'))
        screenshots = list((OUTPUT_DIR / 'screenshots').glob('*.png'))
        api_files = list((OUTPUT_DIR / 'api_data').glob('*.json'))

        summary = {
            'scrape_timestamp': datetime.now().isoformat(),
            'target_url': TARGET_URL,
            'total_sections': final_section_num,
            'files': {
                'data': sorted([f.name for f in json_files]),
                'screenshots': sorted([f.name for f in screenshots]),
                'api_data': sorted([f.name for f in api_files])
            }
        }

        with open(OUTPUT_DIR / 'summary.json', 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        logger.info("\n" + "=" * 80)
        logger.info("✅ SCRAPING COMPLETE!")
        logger.info("=" * 80)
        logger.info(f"📁 Output: {OUTPUT_DIR}")
        logger.info(f"📄 Data files: {len(json_files)}")
        logger.info(f"📸 Screenshots: {len(screenshots)}")
        logger.info(f"🌐 API files: {len(api_files)}")

        logger.info("\n⏸️  Browser stays open for 30 seconds...")
        await asyncio.sleep(30)

        await browser.close()


if __name__ == '__main__':
    asyncio.run(main())
