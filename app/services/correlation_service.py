from datetime import datetime, timedelta
from typing import List, Dict
from sqlalchemy.orm import Session
from sqlalchemy import func
import numpy as np
from collections import defaultdict
import json

from app.config import settings
from app.models.sql_models import StockPrice, CorrelationMetric
from app.models.mongo_models import sentiment_collection, MONGODB_AVAILABLE


class CorrelationService:
    """Service for computing correlations between sentiment and price changes"""
    
    def compute_correlations(self, db: Session, tickers: List[str] = None, days_back: int = 30) -> Dict:
        """
        Compute correlations between sentiment and price variations
        
        Args:
            db: Database session
            tickers: List of ticker symbols (default: all CAC40 tickers)
            days_back: Number of days to analyze
        
        Returns:
            Dictionary with correlation results
        """
        if tickers is None:
            tickers = settings.CAC40_TICKERS[:5]
        
        results = {
            "correlations": {},
            "tickers_processed": []
        }
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        for ticker in tickers:
            try:
                correlation_data = self._compute_ticker_correlation(
                    db, ticker, start_date, end_date
                )
                
                if correlation_data:
                    results["correlations"][ticker] = correlation_data
                    results["tickers_processed"].append(ticker)
            except Exception as e:
                print(f"Error computing correlation for {ticker}: {e}")
                continue
        
        return results
    
    def _compute_ticker_correlation(self, db: Session, ticker: str, 
                                   start_date: datetime, end_date: datetime) -> Dict:
        """Compute correlation for a single ticker"""
        # Get price data with daily returns
        prices = db.query(StockPrice).filter(
            StockPrice.ticker == ticker,
            StockPrice.date >= start_date.date(),
            StockPrice.date <= end_date.date(),
            StockPrice.daily_return.isnot(None)
        ).order_by(StockPrice.date).all()
        
        if not prices:
            return None
        
        # Get sentiment data aggregated by day
        daily_sentiments = self._aggregate_daily_sentiment(ticker, start_date, end_date)
        
        if not daily_sentiments:
            return None
        
        # Align data by date
        aligned_data = []
        all_keywords = []
        
        for price in prices:
            date_key = price.date.strftime("%Y-%m-%d")
            if date_key in daily_sentiments:
                sentiment_data = daily_sentiments[date_key]
                aligned_data.append({
                    "date": price.date,
                    "sentiment": sentiment_data["avg_sentiment"],
                    "return": price.daily_return,
                    "keywords": sentiment_data["keywords"]
                })
                all_keywords.extend(sentiment_data["keywords"])
        
        if len(aligned_data) < 2:
            return None
        
        # Calculate correlation
        sentiments = [d["sentiment"] for d in aligned_data]
        returns = [d["return"] for d in aligned_data]
        
        correlation = np.corrcoef(sentiments, returns)[0, 1]
        
        # Get top keywords
        from collections import Counter
        keyword_counts = Counter(all_keywords)
        top_keywords = [kw for kw, count in keyword_counts.most_common(10)]
        
        # Calculate summary statistics
        avg_sentiment = np.mean(sentiments)
        avg_return = np.mean(returns)
        
        # Store correlation metrics for each day
        for data_point in aligned_data:
            existing = db.query(CorrelationMetric).filter(
                CorrelationMetric.ticker == ticker,
                CorrelationMetric.date == data_point["date"]
            ).first()
            
            if not existing:
                metric = CorrelationMetric(
                    ticker=ticker,
                    date=data_point["date"],
                    avg_sentiment=data_point["sentiment"],
                    daily_return=data_point["return"],
                    correlation_coefficient=correlation,
                    recent_keywords=json.dumps(top_keywords)
                )
                db.add(metric)
        
        db.commit()
        
        return {
            "correlation_coefficient": float(correlation) if not np.isnan(correlation) else 0.0,
            "avg_daily_sentiment": float(avg_sentiment),
            "avg_daily_return": float(avg_return),
            "data_points": len(aligned_data),
            "top_keywords": top_keywords
        }
    
    def _aggregate_daily_sentiment(self, ticker: str, start_date: datetime, 
                                   end_date: datetime) -> Dict:
        """Aggregate sentiment scores by day"""
        if not MONGODB_AVAILABLE:
            return {}
        
        # Query sentiment data from MongoDB
        query = {
            "ticker": ticker,
            "date": {
                "$gte": start_date,
                "$lte": end_date
            }
        }
        
        sentiments = list(sentiment_collection.find(query))
        
        if not sentiments:
            return {}
        
        # Group by day
        daily_data = defaultdict(lambda: {"scores": [], "keywords": []})
        
        for sentiment in sentiments:
            date_key = sentiment["date"].strftime("%Y-%m-%d")
            daily_data[date_key]["scores"].append(sentiment["sentiment_score"])
            daily_data[date_key]["keywords"].extend(sentiment.get("keywords", []))
        
        # Calculate averages
        result = {}
        for date_key, data in daily_data.items():
            result[date_key] = {
                "avg_sentiment": np.mean(data["scores"]),
                "keywords": data["keywords"]
            }
        
        return result
