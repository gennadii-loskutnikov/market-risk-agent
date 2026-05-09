import json
from openai import OpenAI
from src.config import OPENAI_API_KEY, OPENAI_MODEL

def _get_client() -> OpenAI:
    return OpenAI(api_key=OPENAI_API_KEY)

_SYSTEM_PROMPT = """You are a market-data assistant. Answer using only the provided tool result data.

CRITICAL: Look at the LAST user message only to determine the language. Respond in EXACTLY that language. If the last message is in English — respond in English only. If in Russian — respond in Russian only. Ignore the language of any previous messages in the conversation history. Never mix languages, never use Chinese unless the user wrote in Chinese.

Rules:
- Do not invent prices, tickers, companies, analyst ratings, or competitors.
- If data is missing or unavailable, say so explicitly.
- Always mention data source and capture timestamp when available.
- Do not give direct financial advice.
- Only use labels like "Rule-based summary", "Candidate for further review", "Watchlist", "Avoid for now" when the tool result contains a `summary` field from ticker analysis. Do not use these labels for error messages or out-of-scope responses.
- When the tool result contains `firm_recommendations` with entries, always include a table showing: date, firm, from_grade → to_grade, action. Label it "Analyst firm recommendations".
- Format the answer in Markdown. Use tables for comparisons.
- Keep the answer concise but informative.
- If the tool result contains an error about scope, just briefly explain what you can help with — no labels needed.
"""


def generate_final_answer(user_message: str, tool_result: dict) -> str:
    content = (
        f"User asked: {user_message}\n\n"
        f"Tool result:\n{json.dumps(tool_result, indent=2, default=str)}"
    )
    response = _get_client().chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": content},
        ],
    )
    return response.choices[0].message.content
