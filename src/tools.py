from src.db import get_conn
from src.refresh import ensure_ticker_fresh, refresh_ticker
from src.analysis import calculate_price_changes, build_rule_based_summary


def list_market_signals(signal_type: str, limit: int = 10) -> dict:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT * FROM market_signals
            WHERE signal_type = ?
              AND captured_at = (
                  SELECT MAX(captured_at) FROM market_signals WHERE signal_type = ?
              )
            ORDER BY rank ASC
            LIMIT ?
            """,
            (signal_type, signal_type, limit),
        ).fetchall()

    if not rows:
        return {"ok": False, "error": f"No data for signal: {signal_type}"}

    return {
        "ok": True,
        "signal_type": signal_type,
        "captured_at": rows[0]["captured_at"],
        "rows": [dict(r) for r in rows],
    }


def analyze_ticker(ticker: str) -> dict:
    ticker = ticker.upper()
    freshness = ensure_ticker_fresh(ticker)

    with get_conn() as conn:
        snapshot = conn.execute(
            "SELECT * FROM ticker_snapshots WHERE ticker = ? ORDER BY id DESC LIMIT 1",
            (ticker,),
        ).fetchone()
        recs = conn.execute(
            "SELECT * FROM analyst_recommendations WHERE ticker = ? ORDER BY id DESC LIMIT 1",
            (ticker,),
        ).fetchone()

    if not snapshot:
        return {"ok": False, "error": f"No data for ticker: {ticker}"}

    with get_conn() as conn:
        firm_recs = conn.execute(
            """
            SELECT date, firm, to_grade, from_grade, action
            FROM analyst_firm_recommendations
            WHERE ticker = ?
            ORDER BY date DESC
            LIMIT 15
            """,
            (ticker,),
        ).fetchall()

    snapshot_dict = dict(snapshot)
    recs_dict = dict(recs) if recs else None
    firm_recs_list = [dict(r) for r in firm_recs] if firm_recs else []
    price_changes = calculate_price_changes(ticker)
    summary = build_rule_based_summary(snapshot_dict, price_changes, recs_dict)

    freshness_clean = {k: v for k, v in freshness.items() if k != "refresh_result"}

    return {
        "ok": True,
        "ticker": ticker,
        "freshness": freshness_clean,
        "snapshot": snapshot_dict,
        "price_changes": price_changes,
        "recommendations": recs_dict,
        "firm_recommendations": firm_recs_list,
        "summary": summary,
    }


def _get_related_tickers(ticker: str) -> list[str]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT DISTINCT related_ticker FROM related_companies WHERE ticker = ? LIMIT 5",
            (ticker,),
        ).fetchall()
    return [r["related_ticker"] for r in rows][:3]


def compare_ticker(ticker: str) -> dict:
    ticker = ticker.upper()
    ensure_ticker_fresh(ticker)

    peer_tickers = _get_related_tickers(ticker)

    if not peer_tickers:
        refresh_ticker(ticker)
        peer_tickers = _get_related_tickers(ticker)

    if not peer_tickers:
        return {
            "ok": True,
            "ticker": ticker,
            "note": "No related companies found after refresh.",
            "comparisons": [analyze_ticker(ticker)],
        }

    comparisons = [analyze_ticker(ticker)]
    for peer in peer_tickers:
        try:
            comparisons.append(analyze_ticker(peer))
        except Exception as e:
            comparisons.append({"ok": False, "ticker": peer, "error": str(e)})

    return {"ok": True, "ticker": ticker, "comparisons": comparisons}


def refresh_ticker_tool(ticker: str) -> dict:
    ticker = ticker.upper()
    result = refresh_ticker(ticker)
    return {"ok": bool(result.get("ok")), "ticker": ticker, "result": result}


_TABLE_TIMESTAMP_COL = {
    "market_signals": "captured_at",
    "ticker_snapshots": "captured_at",
    "price_history": "date",
    "analyst_recommendations": "captured_at",
    "analyst_firm_recommendations": "captured_at",
    "related_companies": "captured_at",
}


def get_database_status() -> dict:
    tables = {}
    with get_conn() as conn:
        for table, ts_col in _TABLE_TIMESTAMP_COL.items():
            row = conn.execute(
                f"SELECT COUNT(*) as cnt, MAX({ts_col}) as latest FROM {table}"
            ).fetchone()
            tables[table] = {"count": row["cnt"], "latest": row["latest"]}
    return {"ok": True, "tables": tables}
