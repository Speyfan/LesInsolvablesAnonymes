from datetime import datetime
from typing import List, Dict
import re
from collections import Counter

from app.config import settings
from app.models.mongo_models import news_collection, sentiment_collection, SentimentDocument, MONGODB_AVAILABLE

# Try to import transformers and torch, but don't fail if not available
try:
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    print("Transformers/Torch not available, using fallback sentiment analysis")


class SentimentAnalyzer:
    """Service for analyzing sentiment of text using pretrained models"""
    
    def __init__(self):
        self.model_name = settings.SENTIMENT_MODEL
        self.tokenizer = None
        self.model = None
        if TRANSFORMERS_AVAILABLE:
            self._load_model()
    
    def _load_model(self):
        """Load the pretrained sentiment analysis model"""
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
            self.model.eval()
            print(f"Loaded sentiment model: {self.model_name}")
        except Exception as e:
            print(f"Error loading model: {e}")
            print("Will use fallback sentiment analysis")
    
    def analyze_sentiment(self, tickers: List[str] = None, limit: int = 100) -> Dict:
        """
        Analyze sentiment for news articles
        
        Args:
            tickers: List of ticker symbols to analyze (default: all)
            limit: Maximum number of articles to analyze per ticker
        
        Returns:
            Dictionary with analysis results
        """
        if tickers is None:
            tickers = settings.CAC40_TICKERS[:5]
        
        results = {
            "total_analyzed": 0,
            "sentiment_summary": {},
            "tickers_processed": []
        }
        
        for ticker in tickers:
            # Fetch unanalyzed news from MongoDB
            if not MONGODB_AVAILABLE:
                print(f"MongoDB not available, skipping {ticker}")
                continue
            
            query = {"ticker": ticker}
            articles = list(news_collection.find(query).limit(limit))
            
            if not articles:
                continue
            
            ticker_sentiments = []
            
            for article in articles:
                # Analyze sentiment
                text = f"{article.get('title', '')} {article.get('content', '')}"
                sentiment_result = self._analyze_text(text)
                
                # Extract keywords
                keywords = self._extract_keywords(text)
                
                # Create sentiment document
                sentiment_doc = SentimentDocument.create(
                    ticker=ticker,
                    text=text[:500],  # Store first 500 chars
                    sentiment_label=sentiment_result["label"],
                    sentiment_score=sentiment_result["score"],
                    source=article.get("source", "Unknown"),
                    date=article.get("published_at", datetime.utcnow()),
                    keywords=keywords
                )
                
                # Store in MongoDB
                sentiment_collection.insert_one(sentiment_doc)
                ticker_sentiments.append(sentiment_result["label"])
            
            # Summarize sentiments for this ticker
            sentiment_counts = Counter(ticker_sentiments)
            results["sentiment_summary"][ticker] = {
                "positive": sentiment_counts.get("positive", 0),
                "negative": sentiment_counts.get("negative", 0),
                "neutral": sentiment_counts.get("neutral", 0),
                "total": len(ticker_sentiments)
            }
            results["total_analyzed"] += len(ticker_sentiments)
            results["tickers_processed"].append(ticker)
        
        return results
    
    def _analyze_text(self, text: str) -> Dict:
        """Analyze sentiment of a single text"""
        if TRANSFORMERS_AVAILABLE and self.model and self.tokenizer:
            try:
                # Tokenize and analyze
                inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
                with torch.no_grad():
                    outputs = self.model(**inputs)
                    scores = torch.nn.functional.softmax(outputs.logits, dim=-1)
                
                # Get prediction
                predicted_class = torch.argmax(scores).item()
                confidence = scores[0][predicted_class].item()
                
                # Map to labels (depends on model)
                label_map = {0: "negative", 1: "neutral", 2: "positive"}
                label = label_map.get(predicted_class, "neutral")
                
                # Convert to score -1 to 1
                score = (predicted_class - 1) * confidence
                
                return {"label": label, "score": score}
            except Exception as e:
                print(f"Error in model inference: {e}")
        
        # Fallback: Simple keyword-based sentiment
        return self._fallback_sentiment(text)
    
    def _fallback_sentiment(self, text: str) -> Dict:
        """Simple keyword-based sentiment analysis as fallback"""
        text_lower = text.lower()
        
        positive_words = [
            "good", "great", "excellent", "strong", "growth", "profit", "gain",
            "success", "upgrade", "bullish", "exceed", "positive", "rise", "up"
        ]
        negative_words = [
            "bad", "poor", "weak", "decline", "loss", "fail", "downgrade",
            "bearish", "miss", "negative", "fall", "down", "concern", "risk"
        ]
        
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if positive_count > negative_count:
            return {"label": "positive", "score": 0.6}
        elif negative_count > positive_count:
            return {"label": "negative", "score": -0.6}
        else:
            return {"label": "neutral", "score": 0.0}
    
    def _extract_keywords(self, text: str, top_n: int = 5) -> List[str]:
        """Extract top keywords from text"""
        # Simple keyword extraction based on word frequency
        # Remove common words and extract meaningful terms
        stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
            "of", "with", "by", "from", "as", "is", "was", "are", "were", "be",
            "been", "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "can", "this", "that",
            "these", "those", "it", "its", "they", "them", "their"
        }
        
        # Extract words
        words = re.findall(r'\b[a-z]{4,}\b', text.lower())
        
        # Filter and count
        filtered_words = [w for w in words if w not in stop_words]
        word_counts = Counter(filtered_words)
        
        # Return top keywords
        return [word for word, count in word_counts.most_common(top_n)]
