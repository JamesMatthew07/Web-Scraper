# Dashboard Scraper API Documentation

## Overview

A FastAPI-based REST API that wraps a Playwright browser scraper targeting the MeicePro dashboard. It navigates the dashboard, extracts skin analysis and aging data from all pages, captures backend API responses, and returns the collected data as JSON.

---

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. Start the Server

```bash
python api.py
```

The server starts on **http://localhost:8000**.

### 3. Verify It's Running

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{ "status": "ok" }
```

---

## Endpoints

### `GET /health`

Simple health check.

**Response**

```json
{ "status": "ok" }
```

---

### `POST /scrape`

Triggers a full scrape of the MeicePro dashboard. Launches a headless browser, navigates all pages (main, aging level, skin analysis), extracts text/screenshots, and captures API responses.

> Only one scrape can run at a time. Concurrent requests return `429`.

**Request Body** (all fields optional)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `url` | `string \| null` | MeicePro dashboard URL | Target URL to scrape |
| `output_dir` | `string \| null` | `./complete_data` | Directory for scraped files (JSON, screenshots) |
| `headless` | `boolean` | `true` | Run browser without a visible window |

**Example Request**

```bash
curl -X POST http://localhost:8000/scrape \
  -H "Content-Type: application/json" \
  -d '{"headless": true}'
```

With custom options:

```bash
curl -X POST http://localhost:8000/scrape \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://eu-meicepro-api.meiquc.cn/meicepro-h5/pages/report/report?id=YOUR_ID&language=it",
    "output_dir": "./my_output",
    "headless": true
  }'
```

**Success Response** (`200 OK`)

```json
{
  "status": "success",
  "summary": {
    "scrape_timestamp": "2026-02-09T12:00:00.000000",
    "target_url": "https://...",
    "total_sections": 3,
    "files": {
      "data": ["0_Main_Page.json", "1_Aging_Level.json", "2_Skin_Analysis.json"],
      "screenshots": ["0_Main_Page.png", "1_Aging_Level.png", "2_Skin_Analysis.png"],
      "api_data": ["0_main_page_api_1.json", "..."]
    }
  },
  "sections": [
    {
      "section_name": "Main_Page",
      "section_number": 0,
      "url": "https://...",
      "timestamp": "2026-02-09T12:00:00.000000",
      "data": {
        "algorithm_version": "...",
        "date": "...",
        "customer_name": "..."
      },
      "raw_text_length": 1234,
      "html_length": 5678
    },
    {
      "section_name": "Aging_Level",
      "section_number": 1,
      "url": "https://...",
      "timestamp": "...",
      "data": {
        "total_categories": 6,
        "categories": [
          {
            "category": "Rughe della Fronte",
            "score": "3",
            "severity": null,
            "metrics": {
              "Rughe Sottili": { "Quantità": "12", "Area": "8.7mm²" }
            },
            "causes": ["UV exposure", "..."],
            "care_suggestions": ["Use sunscreen", "..."]
          }
        ]
      },
      "raw_text_length": 4321,
      "html_length": 9876
    }
  ],
  "api_responses": [
    {
      "url": "https://eu-meicepro-api.meiquc.cn/...",
      "method": "GET",
      "status": 200,
      "response": { "...": "..." },
      "timestamp": "2026-02-09T12:00:00.000000"
    }
  ]
}
```

**Error Responses**

| Status | Meaning | Body |
|--------|---------|------|
| `429` | A scrape is already in progress | `{"detail": "A scrape is already in progress. Try again later."}` |
| `500` | Scraper encountered an error | `{"detail": "<error message>"}` |

---

## Interactive Docs

FastAPI auto-generates interactive documentation:

| URL | Description |
|-----|-------------|
| `http://localhost:8000/docs` | Swagger UI — try endpoints directly in the browser |
| `http://localhost:8000/redoc` | ReDoc — clean, readable API reference |

---

## Integration Examples

### Python (requests)

```python
import requests

# Health check
r = requests.get("http://localhost:8000/health")
print(r.json())  # {"status": "ok"}

# Trigger scrape
r = requests.post("http://localhost:8000/scrape", json={"headless": True})
data = r.json()

print(f"Status: {data['status']}")
print(f"Sections scraped: {data['summary']['total_sections']}")

for section in data["sections"]:
    print(f"  - {section['section_name']}: {section['raw_text_length']} chars")
```

### Python (async with httpx)

```python
import httpx
import asyncio

async def scrape():
    async with httpx.AsyncClient(timeout=300) as client:
        r = await client.post("http://localhost:8000/scrape", json={"headless": True})
        return r.json()

result = asyncio.run(scrape())
print(result["summary"])
```

### JavaScript (fetch)

```javascript
const response = await fetch("http://localhost:8000/scrape", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ headless: true }),
});

const data = await response.json();
console.log(`Scraped ${data.summary.total_sections} sections`);

data.sections.forEach((s) => {
  console.log(`${s.section_name}: ${s.raw_text_length} chars`);
});
```

### cURL

```bash
# Default scrape
curl -X POST http://localhost:8000/scrape

# Custom URL
curl -X POST http://localhost:8000/scrape \
  -H "Content-Type: application/json" \
  -d '{"url": "https://your-url-here", "headless": true}'
```

---

## Output Structure

When a scrape completes, the following files are written to the output directory (`./complete_data` by default):

```
complete_data/
├── summary.json                    # Scrape metadata and file listing
├── data/
│   ├── 0_Main_Page.json            # Main page extracted data
│   ├── 1_Aging_Level.json          # Aging detail page data
│   └── 2_Skin_Analysis.json        # Skin analysis detail page data
├── screenshots/
│   ├── 0_Main_Page.png             # Full-page screenshot of main page
│   ├── 1_Aging_Level.png           # Full-page screenshot of aging page
│   └── 2_Skin_Analysis.png         # Full-page screenshot of skin page
└── api_data/
    ├── 0_main_page_api_1.json      # API responses captured on main page
    ├── 1_Aging_Level_api_1.json    # API responses from aging page
    └── 2_Skin_Analysis_api_1.json  # API responses from skin page
```

---

## Data Categories

The scraper extracts detailed metrics for the following skin analysis categories (in Italian):

| Category | Translation |
|----------|-------------|
| Rughe della Fronte | Forehead Wrinkles |
| Rughe Glabellari | Glabellar Wrinkles |
| Rughe Interoculari | Interocular Wrinkles |
| Pieghe Nasolabiali | Nasolabial Folds |
| Rughe della Marionetta | Marionette Wrinkles |
| Rughe Periorbitali | Periorbital Wrinkles |
| Macchie Marroni | Brown Spots |
| Pori | Pores |
| Porfirina | Porphyrin |
| Macchie Superficiali | Surface Spots |
| Texture | Texture |
| Macchie Solari | Sun Spots |
| Zone Reattive | Reactive Zones |

Each category includes: **score**, **severity**, **metrics** (quantity/area), **causes**, and **care suggestions**.

---

## Notes

- The scrape takes **30-90 seconds** depending on network speed and page load times.
- Set a generous HTTP timeout (e.g., 5 minutes) in your client — the browser has to fully load and navigate multiple pages.
- Only **one scrape runs at a time**. The lock prevents concurrent browser sessions from conflicting.
- Logs are written to `./logs/scraper.log`.
