import logging

_log = logging.getLogger(__name__)

_SIGNAL_MAP = {
    "top_gainers": ("Top Gainers", "ta_topgainers"),
    "new_highs": ("New High", "ta_newhigh"),
}


def fetch_market_signal(signal_type: str, limit: int = 20) -> list[dict]:
    if signal_type not in _SIGNAL_MAP:
        raise ValueError(f"Unknown signal_type: {signal_type}")
    try:
        rows = _fetch_via_finvizfinance(signal_type, limit)
        rows = [r for r in rows if _is_valid_ticker(r.get("ticker", ""))]
        if rows:
            return rows
    except Exception as e:
        _log.warning(f"finvizfinance failed for {signal_type}, falling back to pyfinviz: {e}")
    rows = _fetch_via_pyfinviz(signal_type, limit)
    return [r for r in rows if _is_valid_ticker(r.get("ticker", ""))]


def _is_valid_ticker(ticker: str) -> bool:
    return bool(ticker) and " " not in ticker and len(ticker) <= 10


def _fetch_via_finvizfinance(signal_type: str, limit: int) -> list[dict]:
    from finvizfinance.screener.overview import Overview

    label, _ = _SIGNAL_MAP[signal_type]
    foverview = Overview()
    foverview.set_filter(signal=label)
    df = foverview.screener_view()
    if df is None or df.empty:
        return []

    rows = []
    for i, (_, row) in enumerate(df.head(limit).iterrows()):
        rows.append({
            "ticker": str(row.get("Ticker", "")).strip(),
            "company_name": str(row.get("Company", "")).strip() or None,
            "price": _safe_float(row.get("Price")),
            "change_pct": _safe_float(row.get("Change"), multiply=100),
            "volume": _safe_int(row.get("Volume")),
            "rank": i + 1,
            "source": "finvizfinance",
        })
    return [r for r in rows if r["ticker"]]


def _fetch_via_pyfinviz(signal_type: str, limit: int) -> list[dict]:
    from pyfinviz.screener import Screener

    label, _ = _SIGNAL_MAP[signal_type]
    signal_opt = getattr(Screener.SignalOption, label.upper().replace(" ", "_"), None)
    if signal_opt is None:
        return []

    pages_needed = max(1, (limit + 19) // 20)
    s = Screener(signal_option=signal_opt, pages=list(range(1, pages_needed + 1)))
    if not s.data_frames:
        return []

    rows = []
    rank = 0
    for page_df in s.data_frames.values():
        for _, row in page_df.iterrows():
            if rank >= limit:
                break
            rank += 1
            rows.append({
                "ticker": str(row.get("Ticker", "")).strip(),
                "company_name": str(row.get("Company", "")).strip() or None,
                "price": _safe_float(row.get("Price")),
                "change_pct": _safe_float(row.get("Change")),
                "volume": _safe_int(row.get("Volume")),
                "rank": rank,
                "source": "pyfinviz",
            })
    return rows


def _safe_float(val, multiply: float = 1) -> float | None:
    if val is None:
        return None
    try:
        result = float(str(val).replace("%", "").replace(",", "").strip())
        return result * multiply
    except (ValueError, TypeError):
        return None


def _safe_int(val) -> int | None:
    if val is None:
        return None
    try:
        s = str(val).replace(",", "").strip()
        if s.endswith("M"):
            return int(float(s[:-1]) * 1_000_000)
        if s.endswith("K"):
            return int(float(s[:-1]) * 1_000)
        return int(float(s))
    except (ValueError, TypeError):
        return None
