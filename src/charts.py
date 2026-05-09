import plotly.graph_objects as go
from datetime import datetime, timedelta
from src.db import get_conn

_COLORS = ["#00d4aa", "#ff6b6b", "#ffd93d", "#6bcbff", "#c77dff"]


def build_price_chart(ticker: str) -> go.Figure | None:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT date, open, high, low, close, volume
            FROM price_history
            WHERE ticker = ?
            ORDER BY date ASC
            """,
            (ticker.upper(),),
        ).fetchall()

    if not rows:
        return None

    dates = [r["date"] for r in rows]
    closes = [r["close"] for r in rows]
    opens = [r["open"] for r in rows]
    highs = [r["high"] for r in rows]
    lows = [r["low"] for r in rows]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=dates,
        y=closes,
        mode="lines",
        name="Close",
        line=dict(color="#00d4aa", width=1.5),
        fill="tozeroy",
        fillcolor="rgba(0, 212, 170, 0.08)",
        hovertemplate="<b>%{x}</b><br>Close: $%{y:.2f}<extra></extra>",
    ))

    fig.update_layout(
        xaxis=dict(
            rangeselector=dict(
                buttons=[
                    dict(count=5, label="5D", step="day", stepmode="backward"),
                    dict(count=1, label="1M", step="month", stepmode="backward"),
                    dict(count=6, label="6M", step="month", stepmode="backward"),
                    dict(count=1, label="1Y", step="year", stepmode="backward"),
                    dict(count=5, label="5Y", step="year", stepmode="backward"),
                    dict(label="All", step="all"),
                ],
                bgcolor="#1e1e1e",
                activecolor="#00d4aa",
            ),
            rangeslider=dict(visible=False),
            type="date",
            showgrid=True,
            gridcolor="#2a2a2a",
        ),
        yaxis=dict(
            title="Price (USD)",
            showgrid=True,
            gridcolor="#2a2a2a",
            tickprefix="$",
        ),
        template="plotly_dark",
        height=320,
        margin=dict(l=0, r=0, t=10, b=0),
        paper_bgcolor="#0e1117",
        plot_bgcolor="#0e1117",
        showlegend=False,
        hovermode="x unified",
    )

    return fig


def build_comparison_chart(tickers: list[str]) -> go.Figure | None:
    if not tickers:
        return None

    one_year_ago = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    fig = go.Figure()
    any_data = False

    for i, ticker in enumerate(tickers):
        with get_conn() as conn:
            rows = conn.execute(
                """
                SELECT date, close FROM price_history
                WHERE ticker = ? AND date >= ?
                ORDER BY date ASC
                """,
                (ticker.upper(), one_year_ago),
            ).fetchall()

        if not rows:
            continue

        dates = [r["date"] for r in rows]
        closes = [r["close"] for r in rows]
        base = closes[0]
        if not base:
            continue
        pct_changes = [((c - base) / base * 100) for c in closes]
        color = _COLORS[i % len(_COLORS)]

        fig.add_trace(go.Scatter(
            x=dates,
            y=pct_changes,
            mode="lines",
            name=ticker.upper(),
            line=dict(color=color, width=1.5),
            hovertemplate=f"<b>{ticker.upper()}</b><br>%{{x}}<br>%{{y:+.2f}}%<extra></extra>",
        ))
        any_data = True

    if not any_data:
        return None

    fig.update_layout(
        xaxis=dict(
            type="date",
            showgrid=True,
            gridcolor="#2a2a2a",
        ),
        yaxis=dict(
            title="% Change (1Y)",
            ticksuffix="%",
            showgrid=True,
            gridcolor="#2a2a2a",
            zeroline=True,
            zerolinecolor="#555",
        ),
        template="plotly_dark",
        height=320,
        margin=dict(l=0, r=0, t=10, b=0),
        paper_bgcolor="#0e1117",
        plot_bgcolor="#0e1117",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )

    return fig
