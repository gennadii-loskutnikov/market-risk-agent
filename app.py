import logging

import streamlit as st
from src.config import OPENAI_API_KEY, STARTUP_PREFETCH_LIMIT
from src.db import init_db
from src.refresh import refresh_signal, refresh_market_signals, refresh_ticker, get_top_tickers
from src.tools import (
    get_database_status,
    list_market_signals,
    analyze_ticker,
    compare_ticker,
    refresh_ticker_tool,
)
from src.llm_router import route_user_message, AgentAction
from src.llm_answer import generate_final_answer
from src.charts import build_price_chart, build_comparison_chart

_fmt = logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s")
for _name in ("src.finviz_client", "src.yahoo_client"):
    _logger = logging.getLogger(_name)
    if not _logger.handlers:
        _handler = logging.StreamHandler()
        _handler.setFormatter(_fmt)
        _logger.addHandler(_handler)
        _logger.setLevel(logging.WARNING)


def run_agent_action(action: AgentAction) -> dict:
    if action.action == "list_market_signals":
        return list_market_signals(signal_type=action.signal_type or "top_gainers", limit=10)
    if action.action == "analyze_ticker":
        if not action.ticker:
            return {"ok": False, "error": "No ticker symbol found in your message."}
        return analyze_ticker(action.ticker)
    if action.action == "compare_ticker":
        if not action.ticker:
            return {"ok": False, "error": "No ticker symbol found in your message."}
        return compare_ticker(action.ticker)
    if action.action == "refresh_ticker":
        if not action.ticker:
            return {"ok": False, "error": "No ticker symbol found in your message."}
        return refresh_ticker_tool(action.ticker)
    if action.action == "database_status":
        return get_database_status()
    return {
        "ok": False,
        "error": "I can help with: top gainers, new highs, ticker analysis, competitor comparison, and data freshness.",
    }


def render_message(msg: dict):
    st.markdown(msg["content"])
    key_suffix = f"{msg.get('chart_key', '')}"
    if msg.get("comparison_tickers"):
        fig = build_comparison_chart(msg["comparison_tickers"])
        if fig:
            st.plotly_chart(fig, width='stretch', key=f"cmp_{'_'.join(msg['comparison_tickers'])}_{key_suffix}")
    elif msg.get("chart_ticker"):
        fig = build_price_chart(msg["chart_ticker"])
        if fig:
            st.plotly_chart(fig, width='stretch', key=f"chart_{msg['chart_ticker']}_{key_suffix}")


st.set_page_config(page_title="Market Risk Agent", layout="wide")

if not OPENAI_API_KEY:
    st.error("OPENAI_API_KEY is not set. Add it to .env and restart.")
    st.stop()

st.title("Market Risk Agent")

if "startup_refresh_done" not in st.session_state:
    startup_result = {"signals": {}}
    with st.status("Starting up...", expanded=True) as status:
        st.write("Initializing database...")
        init_db()

        for signal_type, label in (("top_gainers", "Top Gainers"), ("new_highs", "New Highs")):
            st.write(f"Fetching {label} from Finviz...")
            result = refresh_signal(signal_type)
            startup_result["signals"][signal_type] = result
            if result.get("ok"):
                st.write(f"  ✓ {label}: {result['count']} tickers")
            else:
                st.write(f"  ✗ {label}: {result.get('error', 'error')}")

        tickers = get_top_tickers(STARTUP_PREFETCH_LIMIT)
        prefetch = []
        if not tickers:
            st.write("⚠ No tickers found for pre-fetch — signals may not be loaded yet")
        for i, ticker in enumerate(tickers):
            st.write(f"Pre-fetching {ticker} ({i + 1}/{len(tickers)})...")
            try:
                r = refresh_ticker(ticker, light=True)
                prefetch.append(r)
                if r.get("ok"):
                    st.write(f"  ✓ {ticker}")
                else:
                    st.write(f"  ✗ {ticker}: snap={r['snapshot_ok']}, hist={r['history_ok']}")
            except Exception as e:
                prefetch.append({"ticker": ticker, "ok": False, "error": str(e)})
                st.write(f"  ✗ {ticker}: {e}")
        startup_result["prefetch"] = prefetch

        status.update(label="Ready ✓", state="complete", expanded=False)

    st.session_state["startup_refresh_done"] = True
    st.session_state["startup_result"] = startup_result

if "messages" not in st.session_state:
    st.session_state["messages"] = []

if "last_ticker" not in st.session_state:
    st.session_state["last_ticker"] = None

@st.fragment
def render_sidebar():
    st.header("Controls")

    if st.button("Refresh Market Signals"):
        with st.spinner("Refreshing Finviz data..."):
            result = refresh_market_signals()
        ok_count = sum(1 for v in result.values() if v.get("ok"))
        st.success(f"Refreshed {ok_count}/{len(result)} signals")

    st.divider()

    if st.button("Database Status"):
        st.session_state["db_status_open"] = not st.session_state.get("db_status_open", False)
    if st.session_state.get("db_status_open"):
        status = get_database_status()
        if status.get("ok"):
            for table, info in status["tables"].items():
                st.caption(f"**{table}**: {info['count']} rows — {info['latest'] or 'empty'}")

    st.divider()

    startup_result = st.session_state.get("startup_result", {})
    signals = startup_result.get("signals", {})
    for sig, info in signals.items():
        if info.get("ok"):
            st.caption(f"✓ {sig}: {info.get('count', 0)} tickers")
        else:
            st.caption(f"✗ {sig}: {info.get('error', 'error')}")

    prefetch = startup_result.get("prefetch", [])
    if prefetch:
        ok_count = sum(1 for r in prefetch if r.get("ok"))
        st.caption(f"Prefetch: {ok_count}/{len(prefetch)} tickers ok")
        for r in prefetch:
            if not r.get("ok"):
                errors = [k for k in ("snapshot_error", "history_error") if r.get(k)]
                st.caption(f"  ✗ {r['ticker']}: {', '.join(r.get(e, '') for e in errors) or 'failed'}")


with st.sidebar:
    render_sidebar()

for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        render_message(msg)

if raw_input := st.chat_input("Ask about top gainers, new highs, or analyze a ticker..."):
    user_message = str(raw_input)
    st.session_state["messages"].append({"role": "user", "content": user_message})
    with st.chat_message("user"):
        st.markdown(user_message)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            recent_history = st.session_state["messages"][-6:-1]
            action = route_user_message(
                user_message,
                history=recent_history,
                last_ticker=st.session_state["last_ticker"],
            )
            if action.ticker:
                st.session_state["last_ticker"] = action.ticker
            elif action.action in ("analyze_ticker", "compare_ticker", "refresh_ticker"):
                action.ticker = st.session_state["last_ticker"]
            tool_result = run_agent_action(action)
            if tool_result.get("ok") and tool_result.get("ticker"):
                st.session_state["last_ticker"] = tool_result["ticker"]
            answer = generate_final_answer(user_message, tool_result)

        assistant_msg = {"role": "assistant", "content": answer}
        if tool_result.get("ok") and action.action == "analyze_ticker":
            assistant_msg["chart_ticker"] = tool_result.get("ticker")
            assistant_msg["chart_key"] = str(len(st.session_state["messages"]))
        elif tool_result.get("ok") and action.action == "compare_ticker":
            comparisons = tool_result.get("comparisons", [])
            tickers = [c["ticker"] for c in comparisons if c.get("ok") and c.get("ticker")]
            if tickers:
                assistant_msg["comparison_tickers"] = tickers
                assistant_msg["chart_key"] = str(len(st.session_state["messages"]))

        render_message(assistant_msg)

    st.session_state["messages"].append(assistant_msg)
