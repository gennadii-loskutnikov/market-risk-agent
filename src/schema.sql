CREATE TABLE IF NOT EXISTS market_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_type TEXT NOT NULL,
    ticker TEXT NOT NULL,
    company_name TEXT,
    price REAL,
    change_pct REAL,
    volume INTEGER,
    rank INTEGER,
    source TEXT NOT NULL,
    captured_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ticker_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    company_name TEXT,
    price REAL,
    change_abs REAL,
    change_pct REAL,
    previous_close REAL,
    open_price REAL,
    day_low REAL,
    day_high REAL,
    volume INTEGER,
    market_cap TEXT,
    sector TEXT,
    industry TEXT,
    source TEXT NOT NULL,
    captured_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS price_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    date TEXT NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume INTEGER,
    source TEXT NOT NULL,
    UNIQUE(ticker, date)
);

CREATE TABLE IF NOT EXISTS analyst_recommendations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    period TEXT,
    strong_buy INTEGER,
    buy INTEGER,
    hold INTEGER,
    sell INTEGER,
    strong_sell INTEGER,
    consensus TEXT,
    source TEXT NOT NULL,
    captured_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS related_companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    related_ticker TEXT NOT NULL,
    related_company_name TEXT,
    relation_type TEXT,
    source TEXT,
    captured_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_market_signals_type_time
    ON market_signals(signal_type, captured_at, rank);

CREATE INDEX IF NOT EXISTS idx_ticker_snapshots_ticker_time
    ON ticker_snapshots(ticker, captured_at);

CREATE INDEX IF NOT EXISTS idx_price_history_ticker_date
    ON price_history(ticker, date);

CREATE INDEX IF NOT EXISTS idx_recommendations_ticker_time
    ON analyst_recommendations(ticker, captured_at);

CREATE INDEX IF NOT EXISTS idx_related_ticker
    ON related_companies(ticker);

CREATE TABLE IF NOT EXISTS analyst_firm_recommendations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    date TEXT NOT NULL,
    firm TEXT,
    to_grade TEXT,
    from_grade TEXT,
    action TEXT,
    captured_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_firm_recs_ticker_date
    ON analyst_firm_recommendations(ticker, date);
