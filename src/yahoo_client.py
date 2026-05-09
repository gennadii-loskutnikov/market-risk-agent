import yfinance as yf


def fetch_ticker_snapshot(ticker: str) -> dict:
    symbol = ticker.upper()
    t = yf.Ticker(symbol)
    info = t.info

    price = info.get("currentPrice") or info.get("regularMarketPrice")
    company_name = info.get("longName") or info.get("shortName")
    if not price and not company_name:
        raise ValueError(f"No quote data found for ticker: {symbol}")

    return {
        "ticker": symbol,
        "company_name": company_name,
        "price": price,
        "change_abs": info.get("regularMarketChange"),
        "change_pct": info.get("regularMarketChangePercent"),
        "previous_close": info.get("previousClose") or info.get("regularMarketPreviousClose"),
        "open_price": info.get("open") or info.get("regularMarketOpen"),
        "day_low": info.get("dayLow") or info.get("regularMarketDayLow"),
        "day_high": info.get("dayHigh") or info.get("regularMarketDayHigh"),
        "volume": info.get("volume") or info.get("regularMarketVolume"),
        "market_cap": _format_market_cap(info.get("marketCap")),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "source": "yfinance",
    }


def fetch_price_history(ticker: str, period: str = "5y") -> list[dict]:
    t = yf.Ticker(ticker.upper())
    hist = t.history(period=period)
    if hist.empty:
        return []
    rows = []
    for date, row in hist.iterrows():
        rows.append({
            "ticker": ticker.upper(),
            "date": date.strftime("%Y-%m-%d"),
            "open": float(row["Open"]),
            "high": float(row["High"]),
            "low": float(row["Low"]),
            "close": float(row["Close"]),
            "volume": int(row["Volume"]),
            "source": "yfinance",
        })
    return rows


def fetch_analyst_recommendations(ticker: str) -> dict | None:
    t = yf.Ticker(ticker.upper())
    try:
        recs = t.recommendations_summary
        if recs is None or recs.empty:
            return None
        current = recs[recs["period"] == "0m"]
        if current.empty:
            current = recs.iloc[0:1]
        if current.empty:
            return None
        row = current.iloc[0]
        sb = int(row.get("strongBuy", 0) or 0)
        b = int(row.get("buy", 0) or 0)
        h = int(row.get("hold", 0) or 0)
        s = int(row.get("sell", 0) or 0)
        ss = int(row.get("strongSell", 0) or 0)
        return {
            "ticker": ticker.upper(),
            "period": str(row.get("period", "")),
            "strong_buy": sb,
            "buy": b,
            "hold": h,
            "sell": s,
            "strong_sell": ss,
            "consensus": _calc_consensus(sb, b, h, s, ss),
            "source": "yfinance",
        }
    except Exception:
        return None


def fetch_analyst_firm_recommendations(ticker: str, limit: int = 15) -> list[dict]:
    t = yf.Ticker(ticker.upper())
    try:
        recs = t.upgrades_downgrades
        if recs is None or recs.empty:
            return []
        recent = recs.head(limit)
        result = []
        for date, row in recent.iterrows():
            result.append({
                "ticker": ticker.upper(),
                "date": date.strftime("%Y-%m-%d") if hasattr(date, "strftime") else str(date)[:10],
                "firm": str(row.get("Firm", "")).strip() or None,
                "to_grade": str(row.get("ToGrade", "")).strip() or None,
                "from_grade": str(row.get("FromGrade", "")).strip() or None,
                "action": str(row.get("Action", "")).strip() or None,
            })
        return result
    except Exception:
        return []


def fetch_related_companies(ticker: str) -> list[dict]:
    try:
        from finvizfinance.quote import finvizfinance
        stock = finvizfinance(ticker.upper())
        peers = stock.ticker_peer()
        if peers is None:
            return []
        if isinstance(peers, dict):
            peer_list = list(peers.values())
        elif hasattr(peers, "tolist"):
            peer_list = peers.tolist()
        else:
            peer_list = list(peers)
        result = []
        for p in peer_list:
            peer = str(p).strip().upper()
            if peer and peer != ticker.upper():
                result.append({
                    "related_ticker": peer,
                    "related_company_name": None,
                    "relation_type": "peer",
                    "source": "finviz",
                })
        return result
    except Exception:
        return []


def _format_market_cap(val) -> str | None:
    if val is None:
        return None
    if val >= 1e12:
        return f"${val / 1e12:.2f}T"
    if val >= 1e9:
        return f"${val / 1e9:.2f}B"
    if val >= 1e6:
        return f"${val / 1e6:.2f}M"
    return str(val)


def _calc_consensus(sb: int, b: int, h: int, s: int, ss: int) -> str:
    total = sb + b + h + s + ss
    if total == 0:
        return "N/A"
    bullish = sb + b
    bearish = s + ss
    if bullish / total >= 0.7:
        return "Strong Buy"
    if bullish / total >= 0.5:
        return "Buy"
    if bearish / total >= 0.5:
        return "Sell"
    return "Hold"
