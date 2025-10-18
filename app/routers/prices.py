from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from sqlalchemy.orm import Session

from app.services.price_scraper import PriceScraper
from app.models.sql_models import get_db
from app.config import settings

router = APIRouter(prefix="/prices", tags=["prices"])

# Initialize service
price_scraper = PriceScraper()


@router.post("/scrape")
async def scrape_prices(
    tickers: Optional[List[str]] = Query(None, description="List of tickers to scrape (default: top 5 CAC40)"),
    days_back: int = Query(30, description="Number of days to look back"),
    db: Session = Depends(get_db)
):
    """
    Scrape daily stock price data from Yahoo Finance
    
    - **tickers**: List of ticker symbols (e.g., ['AIR.PA', 'BNP.PA'])
    - **days_back**: Number of days to look back (default: 30)
    """
    try:
        if tickers is None:
            tickers = settings.CAC40_TICKERS[:5]
        
        results = price_scraper.scrape_prices(db=db, tickers=tickers, days_back=days_back)
        
        return {
            "status": "success",
            "message": f"Scraped prices for {len(results['tickers_processed'])} tickers",
            "data": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error scraping prices: {str(e)}")
