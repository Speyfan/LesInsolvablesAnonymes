import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings"""
    
    # MongoDB settings
    MONGODB_URL: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017/")
    MONGODB_DB: str = os.getenv("MONGODB_DB", "cac40_sentiment")
    
    # SQLite settings
    SQLITE_DB_PATH: str = os.getenv("SQLITE_DB_PATH", "./cac40_prices.db")
    
    # API Keys
    NEWS_API_KEY: str = os.getenv("NEWS_API_KEY", "")
    REDDIT_CLIENT_ID: str = os.getenv("REDDIT_CLIENT_ID", "")
    REDDIT_CLIENT_SECRET: str = os.getenv("REDDIT_CLIENT_SECRET", "")
    REDDIT_USER_AGENT: str = os.getenv("REDDIT_USER_AGENT", "CAC40SentimentBot/1.0")
    
    # CAC40 tickers (major stocks)
    CAC40_TICKERS = [
        "AIR.PA", "ALO.PA", "MT.AS", "CS.PA", "BNP.PA", "EN.PA", "CAP.PA",
        "CA.PA", "ACA.PA", "BN.PA", "DSY.PA", "ENGI.PA", "EL.PA", "ERF.PA",
        "RMS.PA", "KER.PA", "LR.PA", "OR.PA", "MC.PA", "ML.PA", "ORA.PA",
        "RI.PA", "PUB.PA", "RNO.PA", "SAF.PA", "SGO.PA", "SAN.PA", "SU.PA",
        "GLE.PA", "STLAP.PA", "STMPA.PA", "TEP.PA", "HO.PA", "FP.PA", "URW.AS",
        "VIE.PA", "DG.PA", "VIV.PA", "WLN.PA"
    ]
    
    # Sentiment model
    SENTIMENT_MODEL = "cardiffnlp/twitter-xlm-roberta-base-sentiment"


settings = Settings()
