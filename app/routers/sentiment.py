from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional

from app.services.news_scraper import NewsScraper
from app.services.sentiment_analyzer import SentimentAnalyzer
from app.config import settings

router = APIRouter(prefix="/sentiment", tags=["sentiment"])

# Initialize services
news_scraper = NewsScraper()
sentiment_analyzer = SentimentAnalyzer()


@router.post("/scrape")
async def scrape_news(
    tickers: Optional[List[str]] = Query(None, description="List of tickers to scrape (default: top 5 CAC40)"),
    days_back: int = Query(7, description="Number of days to look back for news")
):
    """
    Scrape recent news articles for CAC40 stocks
    
    - **tickers**: List of ticker symbols (e.g., ['AIR.PA', 'BNP.PA'])
    - **days_back**: Number of days to look back (default: 7)
    """
    try:
        if tickers is None:
            tickers = settings.CAC40_TICKERS[:5]
        
        results = news_scraper.scrape_news(tickers=tickers, days_back=days_back)
        
        return {
            "status": "success",
            "message": f"Scraped news for {len(results['tickers_processed'])} tickers",
            "data": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error scraping news: {str(e)}")


@router.post("/analyze")
async def analyze_sentiment(
    tickers: Optional[List[str]] = Query(None, description="List of tickers to analyze (default: top 5 CAC40)"),
    limit: int = Query(100, description="Maximum articles to analyze per ticker")
):
    """
    Run sentiment analysis on collected news articles
    
    - **tickers**: List of ticker symbols (e.g., ['AIR.PA', 'BNP.PA'])
    - **limit**: Maximum number of articles to analyze per ticker (default: 100)
    """
    try:
        if tickers is None:
            tickers = settings.CAC40_TICKERS[:5]
        
        results = sentiment_analyzer.analyze_sentiment(tickers=tickers, limit=limit)
        
        return {
            "status": "success",
            "message": f"Analyzed sentiment for {results['total_analyzed']} articles",
            "data": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing sentiment: {str(e)}")
