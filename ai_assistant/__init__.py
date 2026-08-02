"""
ai_assistant package

Phase 10 — AI Investment Assistant for FinSight AI.

No new database tables: conversation memory is session-scoped
(st.session_state), matching authentication.session_manager's own
pattern. Every fact the assistant states comes from an existing
Phase 1-9 service -- this package adds intent routing, prompt/response
formatting, and an optional LLM call on top, never new calculations.

Sub-modules:
    intent_classifier.py     - rule-based question -> domain classification
    context_builder.py        - gathers facts via existing services (zero duplicate calc)
    conversation_memory.py     - session-scoped chat history
    llm_client.py                - optional OpenAI/Gemini client (graceful no-op if unconfigured)
    prompt_builder.py             - builds the LLM prompt from context + history
    rule_based_responder.py        - the mandatory offline fallback (always available)
    response_formatter.py           - final formatting pass + disclaimers
    recommendation_engine.py         - portfolio-wide recommendation summaries
    ai_assistant.py                   - orchestrator (classify -> context -> LLM/rule-based -> format)
    assistant_dashboard.py             - main controller (entry point: assistant_dashboard.render)
"""

from ai_assistant.assistant_dashboard import render

__all__ = ["render"]
