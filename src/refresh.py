from datetime import datetime, timezone
from src.config import FRESHNESS_RULES
from src.db import get_conn
from src.finviz_client import fetch_market_signal, fetch_related_companies
from src.yahoo_client import (
    fetch_ticker_snapshot,
    fetch_price_history,
    fetch_analyst_recommendations,
    fetch_analyst_firm_recommendations,
)


def refresh_signal(signal_type: str) -> dict:
    now = _now()
    try:
        rows = fetch_market_signal(signal_type, limit=20)
        if not rows:
            return {"ok": False, "count": 0, "error": f"No rows returned for {signal_type}"}
        _store_signals(signal_type, rows, now)
        return {"ok": True, "count": len(rows), "captured_at": now}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def refresh_market_signals() -> dict:
    return {s: refresh_signal(s) for s in ("top_gainers", "new_highs")}


def refresh_ticker(ticker: str) -> dict:
    ticker = ticker.upper()
    now = _now()
    result = {
        "ticker": ticker,
        "snapshot_ok": False,
        "history_ok": False,
        "recommendations_ok": False,
        "related_ok": False,
    }

    try:
        snapshot = fetch_ticker_snapshot(ticker)
        _store_snapshot(snapshot, now)
        result["snapshot_ok"] = True
    except Exception as e:
        result["snapshot_error"] = str(e)

    try:
        history = fetch_price_history(ticker)
        _store_history(history)
        result["history_ok"] = bool(history)
        result["history_rows"] = len(history)
    except Exception as e:
        result["history_error"] = str(e)

    try:
        recs = fetch_analyst_recommendations(ticker)
        if recs:
            _store_recommendations(recs, now)
            result["recommendations_ok"] = True
        else:
            result["recommendations_note"] = "No recommendations available"
    except Exception as e:
        result["recs_error"] = str(e)

    try:
        firm_recs = fetch_analyst_firm_recommendations(ticker)
        if firm_recs:
            _store_firm_recommendations(ticker, firm_recs, now)
            result["firm_recs_ok"] = True
            result["firm_recs_count"] = len(firm_recs)
        else:
            result["firm_recs_note"] = "No firm recommendations available"
    except Exception as e:
        result["firm_recs_error"] = str(e)

    try:
        related = fetch_related_companies(ticker)
        if related:
            _store_related(ticker, related, now)
            result["related_ok"] = True
            result["related_count"] = len(related)
        else:
            result["related_note"] = "No related companies found"
    except Exception as e:
        result["related_error"] = str(e)

    result["ok"] = result["snapshot_ok"] or result["history_ok"]
    return result


def ensure_ticker_fresh(ticker: str) -> dict:
    ticker = ticker.upper()
    snapshot_age = _get_snapshot_age(ticker)

    if snapshot_age is None:
        result = refresh_ticker(ticker)
        return {"ticker": ticker, "refreshed": True, "reason": "missing", "refresh_result": result}

    if not _has_price_history(ticker):
        result = refresh_ticker(ticker)
        return {"ticker": ticker, "refreshed": True, "reason": "missing_history", "refresh_result": result}

    if snapshot_age > FRESHNESS_RULES["ticker_snapshot"]:
        result = refresh_ticker(ticker)
        return {"ticker": ticker, "refreshed": True, "reason": "stale", "refresh_result": result}

    return {"ticker": ticker, "refreshed": False, "reason": "fresh"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _has_price_history(ticker: str) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM price_history WHERE ticker = ?",
            (ticker,),
        ).fetchone()
    return row["cnt"] > 0


def _get_snapshot_age(ticker: str) -> float | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT captured_at FROM ticker_snapshots WHERE ticker = ? ORDER BY id DESC LIMIT 1",
            (ticker,),
        ).fetchone()
    if not row:
        return None
    captured = datetime.fromisoformat(row["captured_at"])
    if captured.tzinfo is None:
        captured = captured.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - captured).total_seconds()


def get_top_tickers(limit: int) -> list[str]:
    result = []
    seen = set()
    with get_conn() as conn:
        for signal_type in ("top_gainers", "new_highs"):
            latest = conn.execute(
                "SELECT MAX(captured_at) AS latest FROM market_signals WHERE signal_type = ?",
                (signal_type,),
            ).fetchone()["latest"]
            if not latest:
                continue
            rows = conn.execute(
                """
                SELECT ticker FROM market_signals
                WHERE signal_type = ? AND captured_at = ?
                ORDER BY rank ASC
                LIMIT ?
                """,
                (signal_type, latest, limit),
            ).fetchall()
            for row in rows:
                ticker = row["ticker"]
                if ticker not in seen:
                    result.append(ticker)
                    seen.add(ticker)
                if len(result) >= limit:
                    return result
    return result


def _store_signals(signal_type: str, rows: list[dict], now: str):
    with get_conn() as conn:
        conn.execute("DELETE FROM market_signals WHERE signal_type = ?", (signal_type,))
        for row in rows:
            conn.execute(
                """
                INSERT INTO market_signals
                    (signal_type, ticker, company_name, price, change_pct, volume, rank, source, captured_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    signal_type,
                    row["ticker"],
                    row.get("company_name"),
                    row.get("price"),
                    row.get("change_pct"),
                    row.get("volume"),
                    row.get("rank"),
                    row.get("source", "finviz"),
                    now,
                ),
            )


def _store_snapshot(snapshot: dict, now: str):
    with get_conn() as conn:
        conn.execute("DELETE FROM ticker_snapshots WHERE ticker = ?", (snapshot["ticker"],))
        conn.execute(
            """
            INSERT INTO ticker_snapshots
                (ticker, company_name, price, change_abs, change_pct, previous_close,
                 open_price, day_low, day_high, volume, market_cap, sector, industry, source, captured_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot["ticker"],
                snapshot.get("company_name"),
                snapshot.get("price"),
                snapshot.get("change_abs"),
                snapshot.get("change_pct"),
                snapshot.get("previous_close"),
                snapshot.get("open_price"),
                snapshot.get("day_low"),
                snapshot.get("day_high"),
                snapshot.get("volume"),
                snapshot.get("market_cap"),
                snapshot.get("sector"),
                snapshot.get("industry"),
                snapshot.get("source", "yfinance"),
                now,
            ),
        )


def _store_history(rows: list[dict]):
    with get_conn() as conn:
        for row in rows:
            conn.execute(
                """
                INSERT OR REPLACE INTO price_history
                    (ticker, date, open, high, low, close, volume, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["ticker"],
                    row["date"],
                    row.get("open"),
                    row.get("high"),
                    row.get("low"),
                    row.get("close"),
                    row.get("volume"),
                    row.get("source", "yfinance"),
                ),
            )


def _store_recommendations(recs: dict, now: str):
    with get_conn() as conn:
        conn.execute("DELETE FROM analyst_recommendations WHERE ticker = ?", (recs["ticker"],))
        conn.execute(
            """
            INSERT INTO analyst_recommendations
                (ticker, period, strong_buy, buy, hold, sell, strong_sell, consensus, source, captured_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                recs["ticker"],
                recs.get("period"),
                recs.get("strong_buy"),
                recs.get("buy"),
                recs.get("hold"),
                recs.get("sell"),
                recs.get("strong_sell"),
                recs.get("consensus"),
                recs.get("source", "yfinance"),
                now,
            ),
        )


def _store_firm_recommendations(ticker: str, recs: list[dict], now: str):
    with get_conn() as conn:
        conn.execute("DELETE FROM analyst_firm_recommendations WHERE ticker = ?", (ticker,))
        for r in recs:
            conn.execute(
                """
                INSERT INTO analyst_firm_recommendations
                    (ticker, date, firm, to_grade, from_grade, action, captured_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (ticker, r["date"], r.get("firm"), r.get("to_grade"),
                 r.get("from_grade"), r.get("action"), now),
            )


def _store_related(ticker: str, related: list[dict], now: str):
    with get_conn() as conn:
        conn.execute("DELETE FROM related_companies WHERE ticker = ?", (ticker,))
        for r in related:
            conn.execute(
                """
                INSERT INTO related_companies
                    (ticker, related_ticker, related_company_name, relation_type, source, captured_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    ticker,
                    r["related_ticker"],
                    r.get("related_company_name"),
                    r.get("relation_type", "peer"),
                    r.get("source", "finviz"),
                    now,
                ),
            )
