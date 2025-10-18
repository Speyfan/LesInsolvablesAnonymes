from datetime import datetime, timedelta
from typing import Dict, List
from sqlalchemy.orm import Session
from sqlalchemy import func
from collections import Counter
import json

from app.config import settings
from app.models.sql_models import CorrelationMetric
from app.models.mongo_models import sentiment_collection, MONGODB_AVAILABLE


class DashboardService:
    """Service for generating dashboard data"""
    
    def get_dashboard_data(self, db: Session, tickers: List[str] = None, days_back: int = 30) -> Dict:
        """
        Generate dashboard summary data
        
        Args:
            db: Database session
            tickers: List of ticker symbols (default: all CAC40 tickers)
            days_back: Number of days to analyze
        
        Returns:
            Dictionary with dashboard data
        """
        if tickers is None:
            tickers = settings.CAC40_TICKERS[:5]
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        dashboard = {
            "generated_at": datetime.utcnow().isoformat(),
            "period": {
                "start": start_date.strftime("%Y-%m-%d"),
                "end": end_date.strftime("%Y-%m-%d"),
                "days": days_back
            },
            "sentiment_trends": [],
            "bullish_bearish_ratio": {},
            "top_keywords": [],
            "correlations": [],
            "stock_summary": []
        }
        
        # Aggregate data for each ticker
        for ticker in tickers:
            ticker_data = self._get_ticker_dashboard_data(db, ticker, start_date, end_date)
            if ticker_data:
                dashboard["sentiment_trends"].append({
                    "ticker": ticker,
                    "trend": ticker_data["sentiment_trend"]
                })
                
                dashboard["bullish_bearish_ratio"][ticker] = ticker_data["bullish_bearish"]
                
                dashboard["correlations"].append({
                    "ticker": ticker,
                    "correlation": ticker_data["correlation"]
                })
                
                dashboard["stock_summary"].append({
                    "ticker": ticker,
                    "avg_sentiment": ticker_data["avg_sentiment"],
                    "avg_return": ticker_data["avg_return"],
                    "correlation": ticker_data["correlation"],
                    "keywords": ticker_data["keywords"][:5]
                })
        
        # Get overall top keywords
        all_keywords = []
        for stock in dashboard["stock_summary"]:
            all_keywords.extend(stock["keywords"])
        
        keyword_counts = Counter(all_keywords)
        dashboard["top_keywords"] = [
            {"keyword": kw, "count": count} 
            for kw, count in keyword_counts.most_common(15)
        ]
        
        return dashboard
    
    def _get_ticker_dashboard_data(self, db: Session, ticker: str, 
                                   start_date: datetime, end_date: datetime) -> Dict:
        """Get dashboard data for a single ticker"""
        # Get correlation metrics from SQL
        metrics = db.query(CorrelationMetric).filter(
            CorrelationMetric.ticker == ticker,
            CorrelationMetric.date >= start_date.date(),
            CorrelationMetric.date <= end_date.date()
        ).order_by(CorrelationMetric.date).all()
        
        if not metrics:
            return None
        
        # Calculate sentiment trend (time series)
        sentiment_trend = [
            {
                "date": m.date.strftime("%Y-%m-%d"),
                "sentiment": float(m.avg_sentiment) if m.avg_sentiment else 0.0
            }
            for m in metrics
        ]
        
        # Get sentiment counts from MongoDB
        sentiments = []
        if MONGODB_AVAILABLE:
            query = {
                "ticker": ticker,
                "date": {
                    "$gte": start_date,
                    "$lte": end_date
                }
            }
            sentiments = list(sentiment_collection.find(query))
        
        # Count bullish vs bearish
        bullish = sum(1 for s in sentiments if s["sentiment_score"] > 0.2)
        bearish = sum(1 for s in sentiments if s["sentiment_score"] < -0.2)
        neutral = len(sentiments) - bullish - bearish
        
        bullish_bearish = {
            "bullish": bullish,
            "bearish": bearish,
            "neutral": neutral,
            "ratio": bullish / bearish if bearish > 0 else float('inf')
        }
        
        # Aggregate statistics
        avg_sentiment = sum(m.avg_sentiment for m in metrics if m.avg_sentiment) / len(metrics)
        avg_return = sum(m.daily_return for m in metrics if m.daily_return) / len(metrics)
        correlation = metrics[-1].correlation_coefficient if metrics else 0.0
        
        # Get keywords
        all_keywords = []
        for m in metrics:
            if m.recent_keywords:
                try:
                    keywords = json.loads(m.recent_keywords)
                    all_keywords.extend(keywords)
                except:
                    pass
        
        keyword_counts = Counter(all_keywords)
        top_keywords = [kw for kw, count in keyword_counts.most_common(10)]
        
        return {
            "sentiment_trend": sentiment_trend,
            "bullish_bearish": bullish_bearish,
            "avg_sentiment": float(avg_sentiment),
            "avg_return": float(avg_return),
            "correlation": float(correlation) if correlation else 0.0,
            "keywords": top_keywords
        }
