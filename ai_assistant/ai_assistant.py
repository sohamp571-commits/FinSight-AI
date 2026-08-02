"""
ai_assistant/ai_assistant.py

Purpose: The orchestrator -- the single function `assistant_dashboard.py`
calls per user message. Ties together every other file in this
package in order: classify intent -> build context (reusing existing
services) -> try the LLM path (if configured) -> fall back to the
rule-based path -> format -> record in conversation memory.
"""

from dataclasses import dataclass

from ai_assistant.context_builder import build_context
from ai_assistant.conversation_memory import add_message, get_recent_context_pairs
from ai_assistant.intent_classifier import classify_intent
from ai_assistant.llm_client import generate_llm_response, get_active_provider_label, is_llm_configured
from ai_assistant.prompt_builder import build_prompt
from ai_assistant.response_formatter import format_response, format_source_tag
from ai_assistant.rule_based_responder import generate_rule_based_response
from logging_config import logger


@dataclass
class AssistantReply:
    """The full result of answering one user question."""

    answer: str
    domain: str
    used_llm: bool
    source_tag: str


def ask(user_id: int, question: str) -> AssistantReply:
    """
    Answer one user question end-to-end. Always succeeds with *some*
    answer -- an LLM failure silently falls back to the rule-based
    path, and a context-gathering failure surfaces as a short, clear
    error message rather than a stack trace.
    """
    classified = classify_intent(question)
    context = build_context(user_id, classified)
    domain = context.get("domain", classified.intent.lower())

    used_llm = False
    answer: str | None = None

    if is_llm_configured():
        history_pairs = get_recent_context_pairs(max_pairs=5)
        prompt = build_prompt(question, context, history_pairs)
        answer = generate_llm_response(prompt)
        used_llm = answer is not None

    if answer is None:
        answer = generate_rule_based_response(context)

    formatted_answer = format_response(answer, domain, used_llm)
    source_tag = format_source_tag(used_llm, get_active_provider_label())

    add_message("user", question)
    add_message("assistant", formatted_answer)

    logger.info(f"AI Assistant answered (user_id={user_id}, intent={classified.intent}, used_llm={used_llm})")

    return AssistantReply(answer=formatted_answer, domain=domain, used_llm=used_llm, source_tag=source_tag)
