"""
ai_assistant/prompt_builder.py

Purpose: Builds the text prompt sent to an LLM (only used when
`llm_client.is_llm_configured()` is True) from three ingredients: the
user's question, the fact dict `context_builder.py` gathered, and
recent conversation history from `conversation_memory.py`. The
underlying facts are never re-derived here -- this module only
formats them into text.
"""

import json

DISCLAIMER = (
    "Always be clear this is informational analysis based on FinSight AI's data, not financial advice, "
    "and that the person should do their own research or consult a financial advisor before acting."
)


def build_prompt(question: str, context: dict, history_pairs: list[tuple[str, str]]) -> str:
    """Assemble the full prompt string: system framing, conversation history, context, and the question."""
    sections = [
        "You are FinSight AI's investment assistant, answering using ONLY the data provided below "
        "(retrieved live from the FinSight AI platform's own portfolio, market, news, and analytics services). "
        "Do not invent numbers that aren't present in the data.",
        DISCLAIMER,
    ]

    if history_pairs:
        history_lines = []
        for user_msg, assistant_msg in history_pairs:
            history_lines.append(f"User: {user_msg}\nAssistant: {assistant_msg}")
        sections.append("Recent conversation:\n" + "\n\n".join(history_lines))

    sections.append(f"Data retrieved for this question:\n{json.dumps(context, default=str, indent=2)}")
    sections.append(f"User's question: {question}")
    sections.append("Answer clearly and concisely, in a few short paragraphs or bullet points.")

    return "\n\n".join(sections)
