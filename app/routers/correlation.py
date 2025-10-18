from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from sqlalchemy.orm import Session

from app.services.correlation_service import CorrelationService
from app.models.sql_models import get_db
from app.config import settings

router = APIRouter(prefix="/correlation", tags=["correlation"])

# Initialize service
correlation_service = CorrelationService()


@router.post("/run")
async def compute_correlations(
    tickers: Optional[List[str]] = Query(None, description="List of tickers to analyze (default: top 5 CAC40)"),
    days_back: int = Query(30, description="Number of days to analyze"),
    db: Session = Depends(get_db)
):
    """
    Compute correlations between sentiment and price variations
    
    - **tickers**: List of ticker symbols (e.g., ['AIR.PA', 'BNP.PA'])
    - **days_back**: Number of days to analyze (default: 30)
    
    Returns correlation coefficients and statistics for each ticker
    """
    try:
        if tickers is None:
            tickers = settings.CAC40_TICKERS[:5]
        
        results = correlation_service.compute_correlations(
            db=db, 
            tickers=tickers, 
            days_back=days_back
        )
        
        return {
            "status": "success",
            "message": f"Computed correlations for {len(results['tickers_processed'])} tickers",
            "data": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error computing correlations: {str(e)}")
