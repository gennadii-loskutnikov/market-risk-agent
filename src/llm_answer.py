import json
from openai import OpenAI
from src.config import OPENAI_API_KEY, OPENAI_MODEL

_client = OpenAI(api_key=OPENAI_API_KEY)

_SYSTEM_PROMPT = """You are a market-data assistant. Answer using only the provided tool result data.

CRITICAL: Respond in the same language as the last user message. If the language is unclear, default to English. Ignore the language of earlier messages and tool result field names. Preserve ticker symbols, company names, firm names, grades, and numeric values as-is.

Rules:
- Do not invent prices, tickers, companies, analyst ratings, or competitors.
- If data is missing or unavailable, say so explicitly.
- Always mention data source and capture timestamp when available.
- Do not give direct financial advice.
- If the tool result contains `summary.label_code`, present it as a rule-based risk signal translated into the response language: candidate_for_review, watchlist, avoid_for_now. Do not use these labels for errors or out-of-scope responses.
- When the tool result contains `firm_recommendations` with entries, include a Markdown table with columns: date, firm, from_grade → to_grade, action. Translate the table heading into the response language.
- Format the answer in Markdown. Use tables for comparisons.
- Keep the answer concise but informative.
- If the tool result contains an error or out-of-scope response, briefly explain what this assistant can help with.
"""


def _trim_result(tool_result: dict) -> dict:
    if "comparisons" not in tool_result:
        return tool_result
    trimmed = {**tool_result, "comparisons": []}
    for comp in tool_result["comparisons"]:
        trimmed["comparisons"].append({
            k: v for k, v in comp.items()
            if k not in ("firm_recommendations", "freshness")
        })
    return trimmed


def generate_final_answer(user_message: str, tool_result: dict) -> str:
    content = (
        f"User asked: {user_message}\n\n"
        f"Tool result:\n{json.dumps(_trim_result(tool_result), default=str)}"
    )
    response = _client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": content},
        ],
    )
    return response.choices[0].message.content
