from datetime import datetime, timedelta
from src.db import get_conn


def calculate_price_changes(ticker: str) -> dict:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT date, close FROM price_history WHERE ticker = ? ORDER BY date DESC",
            (ticker.upper(),),
        ).fetchall()

    if not rows:
        return {}

    dates = [(r["date"], r["close"]) for r in rows]
    current_date, current_close = dates[0]

    def closest_close(days_ago: int) -> float | None:
        target = (datetime.strptime(current_date, "%Y-%m-%d") - timedelta(days=days_ago)).strftime("%Y-%m-%d")
        for date, close in dates:
            if date <= target:
                return close
        return None

    def build_entry(start: float | None) -> dict | None:
        if start is None or current_close is None:
            return None
        change_abs = current_close - start
        change_pct = (change_abs / start * 100) if start != 0 else None
        return {
            "start": round(start, 4),
            "end": round(current_close, 4),
            "change_abs": round(change_abs, 4),
            "change_pct": round(change_pct, 2) if change_pct is not None else None,
        }

    return {
        "1d": build_entry(closest_close(1)),
        "5d": build_entry(closest_close(5)),
        "1mo": build_entry(closest_close(30)),
        "1y": build_entry(closest_close(365)),
        "5y": build_entry(closest_close(1825)),
    }


def build_rule_based_summary(
    snapshot: dict,
    price_changes: dict,
    recommendations: dict | None,
) -> dict:
    score = 0
    reasons = []

    if recommendations:
        consensus = recommendations.get("consensus", "N/A")
        if consensus in ("Strong Buy", "Buy"):
            score += 2
            reasons.append(f"Analyst consensus: {consensus}")
        elif consensus == "Hold":
            reasons.append("Analyst consensus: Hold")
        elif consensus in ("Sell", "Strong Sell"):
            score -= 1
            reasons.append(f"Analyst consensus: {consensus}")
    else:
        reasons.append("No analyst data available")

    change_1y = price_changes.get("1y")
    if change_1y and change_1y.get("change_pct") is not None:
        if change_1y["change_pct"] > 0:
            score += 1
            reasons.append(f"Positive 1Y return: +{change_1y['change_pct']:.1f}%")
        else:
            reasons.append(f"Negative 1Y return: {change_1y['change_pct']:.1f}%")

    change_5d = price_changes.get("5d")
    if change_5d and change_5d.get("change_pct") is not None:
        if change_5d["change_pct"] > 20:
            score -= 1
            reasons.append(f"Large 5D spike: +{change_5d['change_pct']:.1f}%")

    change_1d = price_changes.get("1d")
    if change_1d and change_1d.get("change_pct") is not None:
        if change_1d["change_pct"] > 30:
            score -= 1
            reasons.append(f"Very large 1D move: +{change_1d['change_pct']:.1f}%")

    market_cap = snapshot.get("market_cap") or ""
    if "M" in market_cap and "B" not in market_cap and "T" not in market_cap:
        try:
            cap_val = float(market_cap.replace("$", "").replace("M", ""))
            if cap_val < 300:
                score -= 1
                reasons.append(f"Very small market cap: {market_cap}")
        except ValueError:
            pass

    if score >= 3:
        label_code = "candidate_for_review"
    elif score >= 1:
        label_code = "watchlist"
    else:
        label_code = "avoid_for_now"

    return {"label_code": label_code, "score": score, "reasons": reasons}
