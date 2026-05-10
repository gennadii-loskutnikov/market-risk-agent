from openai import OpenAI
from pydantic import BaseModel
from typing import Literal
from src.config import OPENAI_API_KEY, OPENAI_MODEL

_client = OpenAI(api_key=OPENAI_API_KEY)

_SYSTEM_PROMPT = """You are a routing layer for a stock market assistant.

Convert the user's message into exactly one structured action.

Available actions:
- list_market_signals: user asks for top gainers, new highs, market winners, biggest movers
- analyze_ticker: user asks about a specific ticker or company
- compare_ticker: user asks to compare a ticker with competitors, peers, or related companies
- refresh_ticker: user explicitly asks to refresh or update ticker data
- database_status: user asks about data freshness, cache, or available data
- unknown: request is outside this app's scope

Rules:
- Extract ticker symbols when present (uppercase, 1-5 letters).
- Do not invent ticker symbols.
- If the user asks for new highs → signal_type = new_highs.
- If the user asks for top gainers / market winners / biggest movers up → signal_type = top_gainers.
- If the user asks for competitors, peers, or similar companies → compare_ticker.
- If no ticker is present for ticker-specific actions → unknown.
"""


class AgentAction(BaseModel):
    action: Literal[
        "list_market_signals",
        "analyze_ticker",
        "compare_ticker",
        "refresh_ticker",
        "database_status",
        "unknown",
    ]
    signal_type: Literal["top_gainers", "new_highs"] | None = None
    ticker: str | None = None


def _sanitize_history(history: list[dict]) -> list[dict]:
    return [
        {"role": msg["role"], "content": msg["content"]}
        for msg in history
        if msg.get("role") in ("user", "assistant") and msg.get("content")
    ]


def route_user_message(
    message: str,
    history: list[dict] | None = None,
    last_ticker: str | None = None,
) -> AgentAction:
    system = _SYSTEM_PROMPT
    if last_ticker:
        system += f"\n\nContext: the most recently discussed ticker was {last_ticker}. If the user's message is vague or short but plausibly about this ticker (e.g. 'should I buy?', 'what do you think?'), route it as analyze_ticker with ticker={last_ticker}."
    messages = [{"role": "system", "content": system}]
    if history:
        messages.extend(_sanitize_history(history))
    messages.append({"role": "user", "content": message})
    response = _client.beta.chat.completions.parse(
        model=OPENAI_MODEL,
        messages=messages,
        response_format=AgentAction,
    )
    return response.choices[0].message.parsed
