from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from sqlalchemy.orm import Session

from app.services.dashboard_service import DashboardService
from app.models.sql_models import get_db
from app.config import settings

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

# Initialize service
dashboard_service = DashboardService()


@router.get("")
async def get_dashboard(
    tickers: Optional[List[str]] = Query(None, description="List of tickers to include (default: top 5 CAC40)"),
    days_back: int = Query(30, description="Number of days to analyze"),
    db: Session = Depends(get_db)
):
    """
    Get dashboard summary data
    
    - **tickers**: List of ticker symbols (e.g., ['AIR.PA', 'BNP.PA'])
    - **days_back**: Number of days to analyze (default: 30)
    
    Returns:
    - Sentiment trends over time
    - Bullish/bearish ratios
    - Top keywords
    - Correlation coefficients
    - Stock summaries with average sentiment, daily return, and keywords
    """
    try:
        if tickers is None:
            tickers = settings.CAC40_TICKERS[:5]
        
        dashboard_data = dashboard_service.get_dashboard_data(
            db=db,
            tickers=tickers,
            days_back=days_back
        )
        
        return {
            "status": "success",
            "data": dashboard_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating dashboard: {str(e)}")
