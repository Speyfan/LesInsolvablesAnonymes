import requests
from datetime import datetime, timedelta
from typing import List, Dict
import re

from app.config import settings
from app.models.mongo_models import news_collection, NewsDocument, MONGODB_AVAILABLE


class NewsScraper:
    """Service for scraping news about CAC40 stocks"""
    
    def __init__(self):
        self.api_key = settings.NEWS_API_KEY
    
    def scrape_news(self, tickers: List[str] = None, days_back: int = 7) -> Dict:
        """
        Scrape news for specified tickers
        
        Args:
            tickers: List of ticker symbols (default: all CAC40 tickers)
            days_back: Number of days to look back for news
        
        Returns:
            Dictionary with scraping results
        """
        if tickers is None:
            tickers = settings.CAC40_TICKERS[:5]  # Limit to 5 for MVP
        
        results = {
            "total_articles": 0,
            "tickers_processed": [],
            "articles_by_ticker": {}
        }
        
        from_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        
        for ticker in tickers:
            # Extract company name from ticker (simplified)
            company_name = self._ticker_to_company_name(ticker)
            articles = self._fetch_news_for_company(company_name, ticker, from_date)
            
            results["articles_by_ticker"][ticker] = len(articles)
            results["total_articles"] += len(articles)
            results["tickers_processed"].append(ticker)
            
            # Store articles in MongoDB
            if articles and MONGODB_AVAILABLE:
                news_collection.insert_many(articles)
        
        return results
    
    def _ticker_to_company_name(self, ticker: str) -> str:
        """Convert ticker to company name for search"""
        # Simplified mapping for major CAC40 companies
        ticker_map = {
            "AIR.PA": "Airbus",
            "BNP.PA": "BNP Paribas",
            "MC.PA": "LVMH",
            "OR.PA": "L'Oréal",
            "SAN.PA": "Sanofi",
            "TTE.PA": "TotalEnergies",
            "CA.PA": "Carrefour",
            "RNO.PA": "Renault",
            "CS.PA": "AXA"
        }
        return ticker_map.get(ticker, ticker.replace(".PA", "").replace(".AS", ""))
    
    def _fetch_news_for_company(self, company_name: str, ticker: str, from_date: str) -> List[Dict]:
        """Fetch news from NewsAPI or use mock data"""
        articles = []
        
        if self.api_key and self.api_key != "your_news_api_key_here":
            # Use NewsAPI if key is available
            try:
                url = "https://newsapi.org/v2/everything"
                params = {
                    "q": company_name,
                    "from": from_date,
                    "sortBy": "publishedAt",
                    "language": "en",
                    "apiKey": self.api_key,
                    "pageSize": 10
                }
                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    for article in data.get("articles", []):
                        articles.append(NewsDocument.create(
                            ticker=ticker,
                            title=article.get("title", ""),
                            content=article.get("description", "") or article.get("content", ""),
                            source=article.get("source", {}).get("name", "Unknown"),
                            url=article.get("url", ""),
                            published_at=datetime.fromisoformat(article["publishedAt"].replace("Z", "+00:00"))
                        ))
            except Exception as e:
                print(f"Error fetching from NewsAPI: {e}")
        
        # Fallback: Generate mock news data
        if not articles:
            articles = self._generate_mock_news(ticker, company_name)
        
        return articles
    
    def _generate_mock_news(self, ticker: str, company_name: str) -> List[Dict]:
        """Generate mock news data for testing"""
        mock_articles = [
            {
                "title": f"{company_name} Reports Strong Q4 Earnings",
                "content": f"{company_name} exceeded market expectations with strong quarterly results.",
            },
            {
                "title": f"{company_name} Announces New Strategic Initiative",
                "content": f"{company_name} unveiled plans for expansion in emerging markets.",
            },
            {
                "title": f"Analysts Upgrade {company_name} Stock Rating",
                "content": f"Major investment banks raised their price targets for {company_name}.",
            }
        ]
        
        articles = []
        for i, mock in enumerate(mock_articles):
            articles.append(NewsDocument.create(
                ticker=ticker,
                title=mock["title"],
                content=mock["content"],
                source="Mock News Source",
                url=f"https://example.com/news/{ticker.lower()}/{i}",
                published_at=datetime.now() - timedelta(days=i)
            ))
        
        return articles
