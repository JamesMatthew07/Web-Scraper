# Dashboard Scraper

Extracts ALL data from your MeicePro dashboard including main page and detail pages.

## ✅ What It Extracts

1. **Main Page** (218 chars) - Basic customer info + **3 API requests with raw JSON data**
2. **Aging Level** (9,326 chars) - Complete aging analysis
3. **Skin Analysis** (8,570 chars) - Complete skin symptoms analysis

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Run the scraper
python3 scrape_dashboard.py
```

## 📁 Output

```
complete_data/
├── data/
│   ├── 0_Main_Page.json          # Main dashboard
│   ├── 1_Aging_Level.json        # Aging analysis detail page
│   └── 2_Skin_Analysis.json      # Skin analysis detail page
│
├── screenshots/
│   ├── 0_Main_Page.png
│   ├── 1_Aging_Level.png
│   └── 2_Skin_Analysis.png
│
├── api_data/
│   ├── 0_main_page_api_1.json    # Raw API response (63KB - diagnosis data)
│   ├── 0_main_page_api_2.json    # Language settings
│   └── 0_main_page_api_3.json    # Additional diagnosis data (27KB)
│
└── summary.json                   # Overview of scraping session
```

## 📊 Data Captured

### Main Page API Data (Most Valuable!)
- **API 1**: 63KB - Complete diagnosis data with scores, metrics, analysis
- **API 3**: 27KB - Additional diagnosis details

### Detail Pages
- **Aging Level**: Full aging analysis with multiple metrics
- **Skin Analysis**: Complete skin symptom analysis including:
  - Pori (Pores) - Score: 52
  - Porfirina - Score: 68
  - Macchie Superficiali - Score: 74
  - Texture - Score: 57
  - Macchie Marroni - Score: 75
  - Macchie Solari - Score: 65
  - Zone Reattive - Score: 40

## 🔧 For Different Dashboards

To scrape a different dashboard URL, edit `scrape_dashboard.py`:

```python
TARGET_URL = 'your-new-url-here'
```

## 📖 How It Works

1. Loads main page and captures API responses
2. Finds "Visualizza di più" buttons
3. Clicks each button to navigate to detail pages
4. Extracts all text content
5. Takes screenshots
6. Saves everything to JSON

## ✨ Features

- ✅ Automatic button detection
- ✅ API response capture
- ✅ Full-page screenshots
- ✅ Clean JSON output
- ✅ Error handling with retries
- ✅ Progress logging

## That's It!

Just run `python3 scrape_dashboard.py` and all data will be in `complete_data/`
