#!/usr/bin/env python3
"""
API server for the dashboard scraper.
Run with: python api.py
"""

import asyncio

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
import uvicorn

from scrape_dashboard import run_scraper, TARGET_URL

app = FastAPI(
    title="Dashboard Scraper API",
    description="API to trigger the MeicePro dashboard scraper and retrieve extracted data.",
)

# Only one scrape can run at a time (browser + shared output directory)
_scrape_lock = asyncio.Lock()


class ScrapeRequest(BaseModel):
    url: Optional[str] = Field(
        default=None,
        description="Target URL to scrape. Defaults to the MeicePro dashboard URL."
    )
    output_dir: Optional[str] = Field(
        default=None,
        description="Output directory for scraped files. Defaults to ./complete_data"
    )
    headless: bool = Field(
        default=True,
        description="Run browser in headless mode (no visible window)."
    )


class ScrapeResponse(BaseModel):
    status: str
    summary: dict
    sections: list
    api_responses: list


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/scrape", response_model=ScrapeResponse)
async def scrape(request: ScrapeRequest = ScrapeRequest()):
    """
    Trigger a scrape of the target dashboard.

    Launches a headless browser, navigates the dashboard, extracts data from
    all pages, captures API responses, and returns the collected data as JSON.
    """
    if _scrape_lock.locked():
        raise HTTPException(status_code=429, detail="A scrape is already in progress. Try again later.")

    async with _scrape_lock:
        try:
            result = await run_scraper(
                url=request.url,
                output_dir=request.output_dir,
                headless=request.headless,
            )
            return ScrapeResponse(
                status="success",
                summary=result["summary"],
                sections=result["sections"],
                api_responses=result["api_responses"],
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
