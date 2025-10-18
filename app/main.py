from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import sentiment, prices, correlation, dashboard
from app.models.sql_models import init_db
from app.models.mongo_models import init_mongodb

# Initialize FastAPI app
app = FastAPI(
    title="CAC40 Sentiment-Price Correlation API",
    description="API for analyzing correlations between sentiment and price variations for CAC40 stocks",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(sentiment.router)
app.include_router(prices.router)
app.include_router(correlation.router)
app.include_router(dashboard.router)


@app.on_event("startup")
async def startup_event():
    """Initialize databases on startup"""
    print("Initializing databases...")
    init_db()
    init_mongodb()
    print("Databases initialized successfully")


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "CAC40 Sentiment-Price Correlation API",
        "version": "1.0.0",
        "endpoints": {
            "sentiment_scrape": "/sentiment/scrape",
            "sentiment_analyze": "/sentiment/analyze",
            "prices_scrape": "/prices/scrape",
            "correlation_run": "/correlation/run",
            "dashboard": "/dashboard"
        },
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
