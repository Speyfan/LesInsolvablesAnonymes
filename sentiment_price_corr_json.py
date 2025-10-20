#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sentiment ↔ Price backend (JSON + FastAPI) — Local DB + JSON files
-------------------------------------------------------------------
- Prix : SQLite local ./cac40_open_prices.db (table avec colonnes: date, symbol, open_price, high_price, low_price, volume)
- Sentiment : JSON local ./articles_epures_groupes.json (objets: ticker, published_date, sentiment_score_mean, nb_articles)
- Sorties : corrélations ΔSent_t ↔ Return_{t+k}, prévisions multi-horizons (rendements + chemin de prix)
- API : /api/health, /api/correlation, /api/forecast

Dépendances :
  pip install fastapi uvicorn sqlalchemy pandas numpy statsmodels

Lancer :
  uvicorn sentiment_price_corr_json:app --host 0.0.0.0 --port 8000 --reload
"""

from __future__ import annotations
import os
import json
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import statsmodels.api as sm
from sqlalchemy import create_engine, text

# ============================ CONFIG ============================

HERE = Path(__file__).resolve().parent

class Config:
    # Fichiers locaux (même dossier que ce script)
    PRICES_DB_PATH: Path = HERE / "cac40_open_prices.db"
    SENTI_JSON_PATH: Path = HERE / "sentiments_cac40_daily_fixed.json"

    # SQLite URI construite depuis le chemin ci-dessus
    DB_URI: str = f"sqlite:///{PRICES_DB_PATH.as_posix()}"

    # Table SQLite des prix (d’après la capture)
    PRICES_TABLE: str = "cac40_open_prices"

CFG = Config()

# ============================ DATA ACCESS ============================

def get_engine():
    """Crée l'engine SQLAlchemy vers le SQLite local."""
    return create_engine(CFG.DB_URI, future=True)

def fetch_prices(engine, ticker: str, start: str, end: str) -> pd.DataFrame:
    """
    Lit les prix depuis SQLite (table 'cac40_open_prices').
    Mappe: symbol->ticker, open_price->open, etc.
    Utilise 'open' pour calculer les rendements (close indisponible ici).
    """
    q = text(f"""
        SELECT
            date,
            symbol      AS ticker,
            open_price  AS open
        FROM {CFG.PRICES_TABLE}
        WHERE symbol = :ticker
          AND date BETWEEN :start AND :end
        ORDER BY date ASC
    """)
    with engine.connect() as conn:
        df = pd.read_sql(q, conn, params={"ticker": ticker, "start": start, "end": end}, parse_dates=["date"])
    if df.empty:
        return df
    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
    # Nettoyage minimal
    if "open" in df.columns:
        df["open"] = pd.to_numeric(df["open"], errors="coerce")
    df = df.dropna(subset=["open"]).sort_values("date").reset_index(drop=True)
    return df

def fetch_sentiment_from_json(ticker: str, start: str, end: str) -> pd.DataFrame:
    """
    Lit le fichier JSON local 'articles_epures_groupes.json' qui contient
      { "ticker": "ACA.PA", "published_date": "2025-09-17",
        "sentiment_score_mean": 0.6701, "nb_articles": 14 }
    Renvoie un DataFrame (date, ticker, sentiment, mentions), agrégé par jour si doublons.
    """
    p = CFG.SENTI_JSON_PATH
    if not p.exists():
        return pd.DataFrame(columns=["date", "ticker", "sentiment"])

    # Charge JSON : liste d'objets ou dict {"data": [...]}
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
        items = payload.get("data", payload) if isinstance(payload, dict) else payload
        if isinstance(items, dict):
            items = [items]
    except Exception:
        return pd.DataFrame(columns=["date", "ticker", "sentiment"])

    if not items:
        return pd.DataFrame(columns=["date", "ticker", "sentiment"])

    rows: List[dict] = []
    for rec in items:
        try:
            tck = rec.get("ticker") or rec.get("symbol")
            dte = rec.get("published_date") or rec.get("date")
            sc  = rec.get("sentiment_score_mean") or rec.get("sentiment_mean") or rec.get("sentiment") or rec.get("score")
            n   = rec.get("nb_articles") or rec.get("mentions")
            if tck is None or dte is None or sc is None:
                continue
            rows.append({"ticker": tck, "date": dte, "sentiment": sc, "mentions": n})
        except Exception:
            continue

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.tz_localize(None)
    df = df.dropna(subset=["date"])
    df["sentiment"] = pd.to_numeric(df["sentiment"], errors="coerce")
    if "mentions" in df.columns:
        df["mentions"] = pd.to_numeric(df["mentions"], errors="coerce")

    # Filtre ticker/période
    mask = (df["ticker"] == ticker) & \
           (df["date"] >= pd.to_datetime(start)) & \
           (df["date"] <= pd.to_datetime(end))
    df = df.loc[mask]
    if df.empty:
        return pd.DataFrame(columns=["date", "ticker", "sentiment"])

    # Agrégation quotidienne (moyenne du score, somme des mentions)
    agg = {"sentiment": "mean"}
    if "mentions" in df.columns:
        agg["mentions"] = "sum"
    df = (df.groupby(["date", "ticker"], as_index=False)
            .agg(agg)
            .sort_values("date")
            .reset_index(drop=True))
    return df


def list_price_tickers(engine, start: str, end: str) -> set:
    """
    Renvoie l'ensemble des tickers présents dans la base PRICES entre start et end.
    """
    q = text(f"""
        SELECT DISTINCT symbol AS ticker
        FROM {CFG.PRICES_TABLE}
        WHERE date BETWEEN :start AND :end
    """)
    with engine.connect() as conn:
        df = pd.read_sql(q, conn, params={"start": start, "end": end})
    if df.empty:
        return set()
    return set(df["ticker"].dropna().astype(str).unique())


def list_sentiment_tickers(start: str, end: str) -> set:
    """
    Renvoie l'ensemble des tickers présents dans le JSON de sentiments entre start et end.
    """
    p = CFG.SENTI_JSON_PATH
    if not p.exists():
        return set()

    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
        items = payload.get("data", payload) if isinstance(payload, dict) else payload
        if isinstance(items, dict):
            items = [items]
    except Exception:
        return set()

    if not items:
        return set()

    rows = []
    for rec in items:
        tck = rec.get("ticker") or rec.get("symbol")
        dte = rec.get("published_date") or rec.get("date")
        if not tck or not dte:
            continue
        rows.append({"ticker": tck, "date": dte})

    if not rows:
        return set()

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    mask = (df["date"] >= pd.to_datetime(start)) & (df["date"] <= pd.to_datetime(end))
    df = df.loc[mask]
    if df.empty:
        return set()

    return set(df["ticker"].dropna().astype(str).unique())


# ============================ FEATURE ENGINEERING ============================

def prep_features(prices: pd.DataFrame, senti: pd.DataFrame) -> pd.DataFrame:
    """
    Aligne prix & sentiments et calcule:
      - return (log) basé sur 'open'
      - dsent (diff 1j du sentiment)
    """
    prices = prices.copy()
    senti = senti.copy()

    prices["return"] = np.log(prices["open"] / prices["open"].shift(1))
    senti["dsent"] = senti["sentiment"].diff(1)

    df = pd.merge(prices, senti, on=["date", "ticker"], how="inner")
    df = df.dropna(subset=["return", "dsent"]).reset_index(drop=True)
    return df

# ============================ CORRELATIONS ============================

def corr_with_leads(df: pd.DataFrame, max_lead: int = 5) -> pd.DataFrame:
    """Corrélation ΔSent_t vs Return_{t+k} pour k=0..max_lead."""
    out: List[Dict] = []
    for k in range(max_lead + 1):
        r_lead = df["return"].shift(-k)
        corr_r = df["dsent"].corr(r_lead)
        out.append({"lead_days": k, "corr_return": None if pd.isna(corr_r) else float(corr_r)})
    return pd.DataFrame(out)

# ============================ PREDICTION ============================

def fit_linear_prediction(df: pd.DataFrame, target: str = "return", lead: int = 1):
    """OLS: Y_{t+lead} ~ α + β * ΔSent_t (renvoie un modèle statsmodels)."""
    y = df[target].shift(-lead)
    X = df[["dsent"]].copy()
    mask = X["dsent"].notna() & y.notna()
    X = sm.add_constant(X.loc[mask], has_constant="add")
    y = y.loc[mask]
    model = sm.OLS(y, X).fit()
    return model

def multi_horizon_forecast(df: pd.DataFrame, H: int = 5) -> Tuple[float, List[float], List[float]]:
    """
    Prévoit R̂_{t+1..t+H} et reconstruit un chemin de prix à partir du dernier 'open'.
    Retourne (last_dsent, [rendements], [prix]).
    """
    last_price = float(df["open"].iloc[-1])
    last_dsent = float(df["dsent"].iloc[-1])

    preds: List[float] = []
    for h in range(1, H + 1):
        m_h = fit_linear_prediction(df, target="return", lead=h)
        X_pred = sm.add_constant(pd.DataFrame({"dsent": [last_dsent]}), has_constant="add")
        r_hat = float(m_h.predict(X_pred).iloc[0])
        preds.append(r_hat)

    cumu = np.cumsum(preds)
    price_path = last_price * np.exp(cumu)
    return last_dsent, list(preds), list(map(float, price_path))

# ============================ CORE (DICT / JSON) ============================

def run_dict(ticker: str, start: str, end: str, max_lead: int = 5) -> Dict:
    engine = get_engine()

    # Vérifie que le ticker existe dans les DEUX sources sur la période
    price_tks = list_price_tickers(engine, start, end)
    senti_tks = list_sentiment_tickers(start, end)
    common_tks = sorted(price_tks & senti_tks)

    if ticker not in common_tks:
        return {
            "error": "Ticker indisponible dans les deux sources pour la période demandée.",
            "ticker": ticker,
            "period": {"start": start, "end": end},
            "available_in_prices": sorted(price_tks)[:50],
            "available_in_sentiments": sorted(senti_tks)[:50],
            "suggestions_common": common_tks[:50]  # intersection
        }

    prices = fetch_prices(engine, ticker, start, end)
    senti   = fetch_sentiment_from_json(ticker, start, end)

    if prices.empty or senti.empty:
        return {
            "error": "Pas de données pour ce ticker/période.",
            "ticker": ticker, "period": {"start": start, "end": end}
        }

    df = prep_features(prices, senti)
    if df.empty:
        return {
            "error": "Données insuffisantes après alignement/NaN.",
            "ticker": ticker, "period": {"start": start, "end": end}
        }

    # Corrélations
    cdf = corr_with_leads(df, max_lead=max_lead)
    vals = [x for x in cdf["corr_return"] if x is not None]
    mean_corr = float(pd.Series(vals).mean()) if vals else None

    # Prévisions multi-horizons
    last_dsent, preds, prices_f = multi_horizon_forecast(df, H=max_lead)

    payload = {
        "ticker": ticker,
        "period": {"start": start, "end": end},
        "last_date": str(pd.to_datetime(df["date"].iloc[-1]).date()),
        "mean_corr_return": mean_corr,
        "lead_corrs": cdf.to_dict(orient="records"),
        "last_sentiment_delta": last_dsent,
        "forecast": [
            {"horizon": h+1, "predicted_return": float(preds[h]), "predicted_price": float(prices_f[h])}
            for h in range(len(preds))
        ],
    }
    return payload

def run_json(ticker: str, start: str, end: str, max_lead: int = 5) -> str:
    return json.dumps(run_dict(ticker, start, end, max_lead), indent=2, ensure_ascii=False)

def run_batch_dict(tickers: List[str], start: str, end: str, max_lead: int = 5) -> Dict[str, Dict]:
    """
    Exécute run_dict pour une liste de tickers.
    Retourne un dict {ticker: payload_ou_error}.
    """
    out = {}
    for t in tickers:
        try:
            out[t] = run_dict(t, start, end, max_lead)
        except Exception as e:
            out[t] = {"error": f"Exception: {e}", "ticker": t, "period": {"start": start, "end": end}}
    return out


def discover_common_tickers(start: str, end: str) -> List[str]:
    """
    Renvoie la liste triée des tickers présents dans la DB prix ET dans le JSON sentiments
    sur la période demandée.
    """
    engine = get_engine()
    price_tks = list_price_tickers(engine, start, end)
    senti_tks = list_sentiment_tickers(start, end)
    return sorted(price_tks & senti_tks)


# ============================ FASTAPI ROUTES ============================

try:
    from fastapi import FastAPI, HTTPException, Query
    from fastapi.middleware.cors import CORSMiddleware

    app = FastAPI(title="Sentiment-Price Corr API (Local DB + JSON)", version="1.0.0")

    origins = os.getenv("FRONTEND_ORIGINS", "*").split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins if origins != ["*"] else ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    @app.get("/api/correlation")
    def correlation(
        ticker: str = Query(..., min_length=1),
        start: str = Query(..., regex=r"^\d{4}-\d{2}-\d{2}$"),
        end:   str = Query(..., regex=r"^\d{4}-\d{2}-\d{2}$"),
        max_lead: int = Query(5, ge=0, le=60),
    ):
        try:
            payload = run_dict(ticker=ticker, start=start, end=end, max_lead=max_lead)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Computation error: {e}")
        if "error" in payload:
            raise HTTPException(status_code=404, detail=payload["error"])
        return {
            "ticker": payload["ticker"],
            "period": payload["period"],
            "mean_corr_return": payload["mean_corr_return"],
            "lead_corrs": payload["lead_corrs"],
        }

    @app.get("/api/forecast")
    def forecast(
        ticker: str = Query(..., min_length=1),
        start: str = Query(..., regex=r"^\d{4}-\d{2}-\d{2}$"),
        end:   str = Query(..., regex=r"^\d{4}-\d{2}-\d{2}$"),
        h: int = Query(5, ge=1, le=60),
    ):
        try:
            payload = run_dict(ticker=ticker, start=start, end=end, max_lead=h)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Computation error: {e}")
        if "error" in payload:
            raise HTTPException(status_code=404, detail=payload["error"])
        return {
            "ticker": payload["ticker"],
            "last_date": payload["last_date"],
            "last_sentiment_delta": payload["last_sentiment_delta"],
            "forecast": payload["forecast"],
        }
    
    @app.get("/api/common-tickers")
    def common_tickers(
        start: str = Query(..., regex=r"^\d{4}-\d{2}-\d{2}$"),
        end:   str = Query(..., regex=r"^\d{4}-\d{2}-\d{2}$"),
    ):
        try:
            engine = get_engine()
            price_tks = list_price_tickers(engine, start, end)
            senti_tks = list_sentiment_tickers(start, end)
            common_tks = sorted(price_tks & senti_tks)
            return {
                "period": {"start": start, "end": end},
                "count": len(common_tks),
                "tickers": common_tks
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Computation error: {e}")

except Exception:
    app = None  # FastAPI non installé : utilisation CLI uniquement

# ============================ CLI ============================

if __name__ == "__main__":
    import argparse, sys

    ap = argparse.ArgumentParser(description="Sentiment ↔ Price JSON backend (Local DB + JSON)")
    ap.add_argument("--ticker", help="Un ticker unique (ex: BNP.PA)")
    ap.add_argument("--tickers", help="Liste de tickers séparés par des virgules (ex: BNP.PA,ACA.PA,STLAM.MI)")
    ap.add_argument("--all-common", action="store_true",
                    help="Ignorer --ticker/--tickers et utiliser l'intersection des tickers disponibles dans les deux sources sur la période")
    ap.add_argument("--start",  required=True)
    ap.add_argument("--end",    required=True)
    ap.add_argument("--max-lead", type=int, default=5)
    ap.add_argument("--out", help="Chemin de sortie JSON (ex: out.json). Si omis, imprime sur stdout.")
    ap.add_argument("--as-json", action="store_true",
                    help="[mode single] imprime la charge utile JSON complète (sinon résumé)")

    args = ap.parse_args()

    # Détermination de la/les cibles
    tickers = []
    if args.all_common:
        tickers = discover_common_tickers(args.start, args.end)
        if not tickers:
            print(json.dumps({
                "error": "Aucun ticker commun trouvé sur la période demandée.",
                "period": {"start": args.start, "end": args.end}
            }, ensure_ascii=False))
            sys.exit(1)
    elif args.tickers:
        tickers = [t.strip() for t in args.tickers.split(",") if t.strip()]
    elif args.ticker:
        # Mode single-ticker (historique)
        payload = run_dict(ticker=args.ticker, start=args.start, end=args.end, max_lead=args.max_lead)
        if args.out:
            Path(args.out).write_text(json.dumps(payload if args.as_json else {
                k: payload.get(k) for k in ["ticker","period","mean_corr_return","last_date","last_sentiment_delta"]
            }, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"✔ Écrit: {args.out}")
        else:
            print(json.dumps(payload if args.as_json else {
                k: payload.get(k) for k in ["ticker","period","mean_corr_return","last_date","last_sentiment_delta"]
            }, indent=2, ensure_ascii=False))
        sys.exit(0)
    else:
        ap.error("Spécifie --ticker, ou --tickers, ou --all-common")

    # Mode batch (plusieurs tickers)
    batch = run_batch_dict(tickers, start=args.start, end=args.end, max_lead=args.max_lead)

    if args.out:
        Path(args.out).write_text(json.dumps(batch, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"✔ Écrit: {args.out}  ({len(tickers)} tickers)")
    else:
        print(json.dumps(batch, indent=2, ensure_ascii=False))
