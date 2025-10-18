# à installer : pip install yfinance fastapi uvicorn pandas --quiet

import yfinance as yf
import pandas as pd
import json
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import os

app = FastAPI(title="CAC40 Open Prices API")

# Configuration CORS pour permettre les requêtes depuis le navigateur
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En production, spécifiez les domaines autorisés
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Liste des symboles CAC40 ---
cac40_symbols = {
    "Air Liquide": "AI.PA",  # Pas dans le JSON
    "Airbus": "AIR.PA",      # Correspond à AIR.PA dans le JSON
    "ArcelorMittal": "MT.AS", # Pas dans le JSON
    "AXA": "CS.PA",          # Correspond à CS.PA dans le JSON
    "BNP Paribas": "BNP.PA",
    "Bouygues": "EN.PA",
    "Capgemini": "CAP.PA",
    "Carrefour": "CA.PA",
    "Crédit Agricole": "ACA.PA",
    "Danone": "BN.PA",
    "Dassault Systèmes": "DSY.PA",
    "Engie": "ENGI.PA",
    "EssilorLuxottica": "EL.PA",
    "Eurofins Scientific": "ERF.PA",
    "Hermès": "RMS.PA",
    "Kering": "KER.PA",
    "Legrand": "LR.PA",
    "L'Oréal": "OR.PA",
    "LVMH": "MC.PA",
    "Michelin": "ML.PA",
    "Orange": "ORA.PA",
    "Pernod Ricard": "RI.PA",
    "Renault": "RNO.PA",
    "Safran": "SAF.PA",
    "Saint-Gobain": "SGO.PA",
    "Sanofi": "SAN.PA",
    "Schneider Electric": "SU.PA",
    "Société Générale": "GLE.PA",
    "STMicroelectronics": "STMPA.PA",
    "Teleperformance": "TEP.PA",
    "Thales": "HO.PA",
    "TotalEnergies": "TTE.PA",
    "Unibail-Rodamco-Westfield": "URW.AS",
    "Veolia": "VIE.PA",
    "Vinci": "DG.PA",
    "Vivendi": "VIV.PA"
}

# --- Route pour récupérer les dernières valeurs de toutes les actions CAC40 ---
@app.get("/get_latest_cac40_prices")
def get_latest_cac40_prices(period_days: int = Query(2, description="Nombre de jours pour calculer la performance")):
    try:
        # Récupérer tous les symboles CAC40
        all_symbols = list(cac40_symbols.values())
        
        # Télécharger les données sur la période demandée pour calculer la performance
        from datetime import datetime, timedelta
        end_date = datetime.now()
        start_date = end_date - timedelta(days=period_days)
        
        print(f"Téléchargement des dernières valeurs pour {len(all_symbols)} actions...")
        data = yf.download(all_symbols, start=start_date.strftime('%Y-%m-%d'), 
                          end=end_date.strftime('%Y-%m-%d'), group_by='ticker')
        
        if data.empty:
            raise HTTPException(status_code=404, detail="Aucune donnée trouvée")

        results = {}
        
        # Traiter chaque action
        for stock_name, symbol in cac40_symbols.items():
            try:
                # Accéder aux données par symbole
                if (symbol, 'Open') in data.columns:
                    stock_data = data[(symbol, 'Open')].dropna()
                    stock_data = stock_data.to_frame()
                    stock_data.columns = ['Open']
                else:
                    print(f"Aucune donnée pour {stock_name} ({symbol})")
                    continue
                
                if len(stock_data) == 0:
                    continue
                
                # Récupérer la dernière valeur et la précédente
                last_price = float(stock_data.iloc[-1]['Open'])
                first_price = float(stock_data.iloc[0]['Open'])
                
                # Calculer le changement de prix
                change_percent = ((last_price - first_price) / first_price) * 100
                
                results[stock_name] = {
                    "symbol": symbol,
                    "last_price": round(last_price, 2),
                    "price_change": round(change_percent, 2),
                    "last_update": str(stock_data.index[-1].date())
                }
                
            except Exception as e:
                print(f"Erreur pour {stock_name} ({symbol}): {e}")
                continue
        
        json_result = {
            "total_stocks": len(results),
            "stocks": results,
            "last_update": datetime.now().isoformat()
        }

        return JSONResponse(content=json_result)

    except Exception as e:
        print(f"Erreur générale: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- Route pour récupérer l'historique d'une action spécifique (30 derniers jours) ---
@app.get("/get_stock_history")
def get_stock_history(
    stock: str = Query(..., description="Nom de l'action CAC40"),
    days: int = Query(30, description="Nombre de jours d'historique")
):
    symbol = cac40_symbols.get(stock)
    if not symbol:
        raise HTTPException(status_code=404, detail="Action non trouvée")

    try:
        # Calculer les dates pour les X derniers jours
        from datetime import datetime, timedelta
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Télécharger les données
        data = yf.download(symbol, start=start_date.strftime('%Y-%m-%d'), 
                          end=end_date.strftime('%Y-%m-%d'))
        
        if data.empty:
            raise HTTPException(status_code=404, detail="Aucune donnée trouvée pour cette période")

        results = [{"date": str(date.date()), "open_price": round(float(row.iloc[0] if len(row) == 1 else row["Open"]), 2)}
                   for date, row in data.iterrows()]

        json_result = {
            "symbol": stock,
            "start_date": start_date.strftime('%Y-%m-%d'),
            "end_date": end_date.strftime('%Y-%m-%d'),
            "days_requested": days,
            "days_available": len(results),
            "open_prices": results
        }

        return JSONResponse(content=json_result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Route pour récupérer une action spécifique (gardée pour compatibilité) ---
@app.get("/get_open_prices")
def get_open_prices(
    stock: str = Query(..., description="Nom de l'action CAC40"),
    start: str = Query(..., description="Date de début AAAA-MM-JJ"),
    end: str = Query(..., description="Date de fin AAAA-MM-JJ")
):
    symbol = cac40_symbols.get(stock)
    if not symbol:
        raise HTTPException(status_code=404, detail="Action non trouvée")

    try:
        # Télécharger les données
        data = yf.download(symbol, start=start, end=end)
        if data.empty:
            raise HTTPException(status_code=404, detail="Aucune donnée trouvée pour cette période")

        results = [{"date": str(date.date()), "open_price": round(float(row.iloc[0] if len(row) == 1 else row["Open"]), 2)}
                   for date, row in data.iterrows()]

        json_result = {
            "symbol": stock,
            "start_date": start,
            "end_date": end,
            "open_prices": results
        }

        # Retourner directement le JSON au lieu d'un fichier
        return JSONResponse(content=json_result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/get_articles_data")
def get_articles_data(stock_name: str = Query(..., description="Nom de l'action")):
    """Récupère les données d'articles pour une action depuis synthese_cac40_mensuelle.json"""
    try:
        # Trouver le ticker correspondant
        if stock_name not in cac40_symbols:
            raise HTTPException(status_code=404, detail=f"Action '{stock_name}' non trouvée")
        
        ticker = cac40_symbols[stock_name]
        
        # Charger les données d'articles
        try:
            with open('synthese_cac40_mensuelle.json', 'r', encoding='utf-8') as f:
                articles_data = json.load(f)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="Fichier de données d'articles non trouvé")
        
        # Chercher les données pour ce ticker
        ticker_articles = None
        for item in articles_data:
            if item['ticker'] == ticker:
                ticker_articles = item
                break
        
        if not ticker_articles:
            raise HTTPException(status_code=404, detail=f"Aucune donnée d'articles trouvée pour {ticker}")
        
        # Retourner les articles formatés
        return JSONResponse(content={
            "stock_name": stock_name,
            "ticker": ticker,
            "articles": {
                "positive": {
                    "title": ticker_articles['article_plus_positif']['title'],
                    "description": ticker_articles['article_plus_positif']['description'],
                    "sentiment": ticker_articles['article_plus_positif']['sentiment']
                },
                "negative": {
                    "title": ticker_articles['article_plus_negatif']['title'],
                    "description": ticker_articles['article_plus_negatif']['description'],
                    "sentiment": ticker_articles['article_plus_negatif']['sentiment']
                },
                "random": {
                    "title": ticker_articles['article_random']['title'],
                    "description": ticker_articles['article_random']['description'],
                    "sentiment": ticker_articles['article_random']['sentiment']
                }
            },
            "monthly_sentiment": ticker_articles['sentiment_moyen'],
            "nb_articles": ticker_articles['nb_articles'],
            "keywords": ticker_articles['mots_cles_frequents']
        })
        
    except Exception as e:
        print(f"Erreur lors de la récupération des articles: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/get_correlation_data")
def get_correlation_data(stock_name: str = Query(..., description="Nom de l'action")):
    """Récupère les données de corrélation et projection depuis batch_corr_2025-09.json"""
    try:
        # Trouver le ticker correspondant
        if stock_name not in cac40_symbols:
            raise HTTPException(status_code=404, detail=f"Action '{stock_name}' non trouvée")
        
        ticker = cac40_symbols[stock_name]
        
        # Charger les données de corrélation
        try:
            with open('batch_corr_2025-09.json', 'r', encoding='utf-8') as f:
                correlation_data = json.load(f)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="Fichier de données de corrélation non trouvé")
        
        # Chercher les données pour ce ticker
        if ticker not in correlation_data:
            raise HTTPException(status_code=404, detail=f"Aucune donnée de corrélation trouvée pour {ticker}")
        
        ticker_correlation = correlation_data[ticker]
        
        # Retourner les données formatées
        return JSONResponse(content={
            "stock_name": stock_name,
            "ticker": ticker,
            "correlation": {
                "mean_correlation": ticker_correlation['mean_corr_return'],
                "period": ticker_correlation['period'],
                "last_date": ticker_correlation['last_date']
            },
            "forecast": ticker_correlation['forecast'],
            "last_sentiment_delta": ticker_correlation.get('last_sentiment_delta', 0)
        })
        
    except Exception as e:
        print(f"Erreur lors de la récupération des données de corrélation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/get_sentiment_data")
def get_sentiment_data(stock_name: str = Query(..., description="Nom de l'action"), days: int = Query(30, description="Nombre de jours d'historique")):
    """Récupère les données de sentiment pour une action sur une période donnée"""
    try:
        # Trouver le ticker correspondant
        if stock_name not in cac40_symbols:
            raise HTTPException(status_code=404, detail=f"Action '{stock_name}' non trouvée")
        
        ticker = cac40_symbols[stock_name]
        
        # Charger les données de sentiment
        try:
            with open('articles_epures_groupes.json', 'r', encoding='utf-8') as f:
                sentiment_data = json.load(f)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="Fichier de données de sentiment non trouvé")
        
        # Filtrer les données pour ce ticker
        ticker_data = [item for item in sentiment_data if item['ticker'] == ticker]
        
        # Créer un dictionnaire pour un accès rapide par date
        sentiment_by_date = {}
        for item in ticker_data:
            sentiment_by_date[item['published_date']] = {
                'sentiment': item['sentiment_score_mean'],
                'nb_articles': item['nb_articles']
            }
        
        # Utiliser les vraies dates des données au lieu de dates récentes
        # Trouver la date la plus récente dans les données
        if not ticker_data:
            raise HTTPException(status_code=404, detail=f"Aucune donnée de sentiment trouvée pour {ticker}")
        
        # Extraire toutes les dates et trouver la plus récente
        all_dates = [item['published_date'] for item in ticker_data]
        all_dates.sort()
        latest_date_str = all_dates[-1]
        
        # Utiliser la date la plus récente comme point de départ
        from datetime import datetime, timedelta
        end_date = datetime.strptime(latest_date_str, '%Y-%m-%d')
        start_date = end_date - timedelta(days=days)
        
        result = []
        current_date = start_date
        
        while current_date <= end_date:
            date_str = current_date.strftime('%Y-%m-%d')
            
            # Chercher le sentiment pour cette date
            sentiment_value = None
            
            # 1. Chercher la date exacte
            if date_str in sentiment_by_date:
                sentiment_value = sentiment_by_date[date_str]['sentiment']
            else:
                # 2. Chercher la veille
                yesterday = current_date - timedelta(days=1)
                yesterday_str = yesterday.strftime('%Y-%m-%d')
                
                if yesterday_str in sentiment_by_date:
                    sentiment_value = sentiment_by_date[yesterday_str]['sentiment']
                else:
                    # 3. Chercher dans toutes les dates disponibles (jusqu'à 30 jours)
                    found = False
                    for i in range(2, 31):
                        past_date = current_date - timedelta(days=i)
                        past_date_str = past_date.strftime('%Y-%m-%d')
                        
                        if past_date_str in sentiment_by_date:
                            sentiment_value = sentiment_by_date[past_date_str]['sentiment']
                            found = True
                            break
                    
                    # 4. Si toujours rien trouvé, utiliser le sentiment le plus récent disponible
                    if not found:
                        # Trouver le sentiment le plus récent disponible pour ce ticker
                        available_dates = list(sentiment_by_date.keys())
                        available_dates.sort()
                        if available_dates:
                            latest_available_date = available_dates[-1]
                            sentiment_value = sentiment_by_date[latest_available_date]['sentiment']
                        else:
                            sentiment_value = 0.0
            
            result.append({
                'date': date_str,
                'sentiment': sentiment_value,
                'ticker': ticker
            })
            
            current_date += timedelta(days=1)
        
        return JSONResponse(content={
            "stock_name": stock_name,
            "ticker": ticker,
            "sentiment_data": result,
            "total_days": len(result),
            "period": f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
        })
        
    except Exception as e:
        print(f"Erreur lors de la récupération des sentiments: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- Routes pour servir les fichiers statiques ---
@app.get("/{filename}")
async def serve_static_file(filename: str):
    """Serve static files like HTML, CSS, JS, JSON"""
    if filename in ["index.html", "styles.css", "script.js", "fake_data.json", 
                   "articles_epures_groupes.json", "synthese_cac40_mensuelle.json", "logo.png"]:
        if os.path.exists(filename):
            return FileResponse(filename)
    raise HTTPException(status_code=404, detail="File not found")

@app.get("/")
async def serve_index():
    """Serve the main HTML file"""
    return FileResponse("index.html")

# --- Pour lancer le serveur ---
# en ligne de commande : uvicorn main:app --reload --host 0.0.0.0 --port 8000
# en URL : http://127.0.0.1:8000/get_open_prices?stock=LVMH&start=2024-01-01&end=2024-01-10
