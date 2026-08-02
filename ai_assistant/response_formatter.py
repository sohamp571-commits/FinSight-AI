"""
ai_assistant/response_formatter.py

Purpose: A final, consistent formatting pass applied to every response
regardless of whether it came from the LLM path or the rule-based
path -- appends a short disclaimer for recommendation-flavored
answers, and tags the response with which engine produced it so the
UI can show that transparently.
"""

_RECOMMENDATION_DOMAINS = {"recommendation", "prediction", "technical"}


def format_response(raw_text: str, domain: str, used_llm: bool) -> str:
    """Apply the final formatting pass to a generated response."""
    text = raw_text.strip()

    if domain in _RECOMMENDATION_DOMAINS:
        text += (
            "\n\n*This is informational analysis based on FinSight AI's own data, not financial advice. "
            "Please do your own research or consult a financial advisor before making investment decisions.*"
        )

    return text


def format_source_tag(used_llm: bool, provider_label: str) -> str:
    """Build a small caption indicating which engine generated the response."""
    return f"🤖 {provider_label}" if used_llm else "🧮 Local rule-based analysis (no LLM configured)"
