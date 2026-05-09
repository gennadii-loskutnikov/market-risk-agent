# Market Risk Agent

An AI-powered market data assistant that collects stock signal data from Finviz, enriches selected tickers with Yahoo Finance data, caches results in SQLite, and answers questions through a chat interface.

A language model is used for natural-language understanding and tool selection. Data collection, analysis, and storage are handled by deterministic Python functions — the LLM never writes SQL or scrapes websites directly.

> This is a prototype for demonstration purposes. It provides a rule-based risk summary, not financial advice.

---

## What it does

- Fetches **Top Gainers** and **New Highs** from Finviz on startup
- Enriches tickers with **price snapshots**, **5-year price history**, and **analyst recommendations** via yfinance
- Fetches **peer companies** via Finviz when available
- Caches all data in **SQLite** and refreshes on demand
- Answers natural-language questions via a **Streamlit chat UI**
- Shows **interactive price charts** and **competitor comparison charts**
- Includes **firm-level analyst recommendation history** when available

---

## Stack

| Layer | Technology |
|---|---|
| UI | Streamlit |
| LLM | OpenAI gpt-4.1-mini |
| Market signals | finvizfinance (pyfinviz fallback) |
| Price & fundamentals | yfinance |
| Cache | SQLite |
| Charts | Plotly |
| Language | Python 3.11 |

---

## Architecture

```
Finviz (Top Gainers, New Highs)
  → SQLite cache
  → on-demand yfinance enrichment
      (snapshot, price history, analyst recs, peers)
  → OpenAI router  →  deterministic tools  →  OpenAI answer formatter
  → Streamlit chat + Plotly charts
```

The LLM acts only as a router and answer formatter. All data fetching, SQL reads, price calculations, and risk scoring are handled by Python.

Finviz signal data is collected through `finvizfinance`, with `pyfinviz` as a fallback. A custom BeautifulSoup parser was intentionally not used because the screener data was not reliably available through static HTML requests in this prototype.

---

## Setup

### Requirements

- Python 3.11
- [uv](https://github.com/astral-sh/uv)
- OpenAI API key

### Install

```bash
git clone <repo>
cd market-risk-agent
uv sync
```

### Configure

```bash
cp .env.example .env
```

Edit `.env` and set your OpenAI API key:

```env
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4.1-mini
DATABASE_PATH=data/market_data.sqlite
STARTUP_PREFETCH_LIMIT=5
```

### Run

```bash
uv run streamlit run app.py
```

On first launch the app will:
1. Initialize the SQLite database
2. Fetch Top Gainers and New Highs from Finviz
3. Pre-fetch detailed data for the top 5 tickers
4. Open the chat UI

---

## Demo flow

```
Show me top gainers
Which companies reached new highs?
Analyze AKAM
стоит брать?
Compare AKAM with competitors
How fresh is the data?
```

The demo shows the full cross-source workflow:

```
Finviz signal → ticker → yfinance enrichment → SQLite cache → AI chat answer
```

---

## Project structure

```
app.py                  Streamlit UI and startup flow
src/
  config.py             Environment and freshness settings
  db.py                 SQLite connection and schema init
  schema.sql            Table and index definitions
  finviz_client.py      Finviz signal fetching (finvizfinance → pyfinviz)
  yahoo_client.py       yfinance data fetching
  refresh.py            Startup and on-demand refresh logic
  analysis.py           Price change calculation and rule-based summary
  tools.py              Deterministic tool functions (read SQLite)
  llm_router.py         OpenAI structured router → AgentAction
  llm_answer.py         OpenAI final answer formatter
  charts.py             Plotly price and comparison charts
data/
  market_data.sqlite    Created automatically on first run
```

---

## Supported chat actions

| User intent | Action |
|---|---|
| "Show me top gainers" | List top gainers from cache |
| "Which companies reached new highs?" | List new highs from cache |
| "Analyze AAPL" | Price snapshot, history, recommendations, chart |
| "Compare AAPL with competitors" | Peer comparison table and chart |
| "Refresh TSLA" | Force re-fetch from yfinance |
| "How fresh is the data?" | Table counts and latest timestamps |
| Follow-up without ticker | Uses last mentioned ticker |

---

## Freshness behavior

| Data type | Behavior |
|---|---|
| Market signals | Refreshed on app startup or manually from the sidebar |
| Ticker snapshot | Refreshed on demand if missing or older than 15 minutes |
| Price history | Refreshed as part of ticker refresh |
| Analyst recommendations | Refreshed as part of ticker refresh when available |
| Related companies | Refreshed as part of ticker refresh when available |

---

## Limitations

- Price history does not include intraday data — charts show daily close prices
- Firm-level analyst recommendations depend on yfinance availability; some tickers may have no data
- Very small or recently listed tickers may fail yfinance enrichment — the app logs these and continues
- This is not a trading bot and does not give direct buy/sell advice
