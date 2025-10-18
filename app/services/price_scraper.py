import yfinance as yf
from datetime import datetime, timedelta
from typing import List, Dict
from sqlalchemy.orm import Session

from app.config import settings
from app.models.sql_models import StockPrice


class PriceScraper:
    """Service for scraping stock price data"""
    
    def scrape_prices(self, db: Session, tickers: List[str] = None, days_back: int = 30) -> Dict:
        """
        Scrape price data for specified tickers
        
        Args:
            db: Database session
            tickers: List of ticker symbols (default: all CAC40 tickers)
            days_back: Number of days to look back
        
        Returns:
            Dictionary with scraping results
        """
        if tickers is None:
            tickers = settings.CAC40_TICKERS[:5]  # Limit to 5 for MVP
        
        results = {
            "total_records": 0,
            "tickers_processed": [],
            "records_by_ticker": {}
        }
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        for ticker in tickers:
            try:
                # Fetch data from Yahoo Finance
                stock = yf.Ticker(ticker)
                hist = stock.history(start=start_date, end=end_date)
                
                if hist.empty:
                    print(f"No data found for {ticker}")
                    continue
                
                records_added = 0
                
                for date, row in hist.iterrows():
                    # Check if record already exists
                    existing = db.query(StockPrice).filter(
                        StockPrice.ticker == ticker,
                        StockPrice.date == date.date()
                    ).first()
                    
                    if existing:
                        continue
                    
                    # Create new record
                    price_record = StockPrice(
                        ticker=ticker,
                        date=date.date(),
                        open_price=float(row['Open']),
                        high_price=float(row['High']),
                        low_price=float(row['Low']),
                        close_price=float(row['Close']),
                        volume=float(row['Volume']),
                        daily_return=None  # Will be calculated later
                    )
                    
                    db.add(price_record)
                    records_added += 1
                
                db.commit()
                
                # Calculate daily returns
                self._calculate_daily_returns(db, ticker)
                
                results["records_by_ticker"][ticker] = records_added
                results["total_records"] += records_added
                results["tickers_processed"].append(ticker)
                
            except Exception as e:
                print(f"Error scraping {ticker}: {e}")
                db.rollback()
                continue
        
        return results
    
    def _calculate_daily_returns(self, db: Session, ticker: str):
        """Calculate daily returns for a ticker"""
        # Get all prices for this ticker, ordered by date
        prices = db.query(StockPrice).filter(
            StockPrice.ticker == ticker
        ).order_by(StockPrice.date).all()
        
        # Calculate returns
        for i in range(1, len(prices)):
            prev_price = prices[i-1].close_price
            curr_price = prices[i].close_price
            
            if prev_price and prev_price > 0:
                daily_return = ((curr_price - prev_price) / prev_price) * 100
                prices[i].daily_return = daily_return
        
        db.commit()
