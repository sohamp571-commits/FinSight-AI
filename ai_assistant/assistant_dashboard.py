"""
ai_assistant/assistant_dashboard.py

Purpose: The main entry point for the AI Investment Assistant --
a chat interface built on Streamlit's native `st.chat_message`/
`st.chat_input` widgets. Renders conversation history from
`conversation_memory.py`, sends new questions through
`ai_assistant.ask()`, and shows which engine (LLM vs. local
rule-based) answered each message.
"""

import streamlit as st

from authentication.middleware import login_required
from authentication.session_manager import get_current_user_id
from custom_exceptions import FinSightBaseException
from dashboard.dashboard_layout import inject_dashboard_css, render_divider
from database.audit_service import audit_service
from logging_config import logger

from ai_assistant.ai_assistant import ask
from ai_assistant.conversation_memory import clear_history, get_history
from ai_assistant.llm_client import get_active_provider_label, is_llm_configured

_SUGGESTED_PROMPTS = [
    "How is my portfolio doing?",
    "What's the RSI on TCS?",
    "Should I buy more Reliance?",
    "What's the latest news on Infosys?",
    "Any IPOs open right now?",
    "What's the overall market sentiment today?",
]


def _render_sidebar_controls() -> None:
    with st.sidebar:
        st.markdown("---")
        st.markdown("### 🤖 AI Assistant")
        st.caption(get_active_provider_label())
        if st.button("🆕 New Chat", use_container_width=True, key="ai_assistant_new_chat"):
            clear_history()
            st.rerun()


def _render_suggested_prompts() -> str | None:
    """Render a row of quick-start suggestion buttons. Returns the clicked prompt, if any."""
    st.caption("Try asking:")
    columns = st.columns(3)
    for index, prompt in enumerate(_SUGGESTED_PROMPTS):
        with columns[index % 3]:
            if st.button(prompt, key=f"suggested_prompt_{index}", use_container_width=True):
                return prompt
    return None


def _render_chat_history() -> None:
    for message in get_history():
        with st.chat_message(message.role, avatar="🤖" if message.role == "assistant" else "🧑"):
            st.markdown(message.content)


def _handle_question(user_id: int, question: str) -> None:
    with st.chat_message("user", avatar="🧑"):
        st.markdown(question)

    with st.chat_message("assistant", avatar="🤖"):
        with st.spinner("Thinking..."):
            try:
                reply = ask(user_id, question)
                st.markdown(reply.answer)
                st.caption(reply.source_tag)
            except FinSightBaseException as exc:
                logger.error(f"AI Assistant failed to answer: {exc}")
                st.error(f"Sorry, something went wrong: {exc.message}")
            except Exception as exc:  # noqa: BLE001
                logger.exception(f"Unexpected AI Assistant failure: {exc}")
                st.error("Sorry, something unexpected went wrong while answering that.")


@login_required
def render() -> None:
    """Render the full AI Investment Assistant chat page."""
    try:
        inject_dashboard_css()
        user_id = get_current_user_id()

        st.title("🤖 AI Investment Assistant")
        st.caption(
            "Ask about your portfolio, watchlist, news, sentiment, IPOs, notifications, companies, "
            "technical indicators, or cached ML predictions."
        )
        if not is_llm_configured():
            st.info(
                "No LLM API key is configured, so I'm answering using FinSight AI's local rule-based "
                "engine -- same underlying data, just less conversational phrasing."
            )
        render_divider()

        _render_sidebar_controls()
        audit_service.log_action(action="AI_ASSISTANT_VIEW", user_id=user_id)

        history = get_history()
        if not history:
            clicked_prompt = _render_suggested_prompts()
        else:
            clicked_prompt = None
            _render_chat_history()

        typed_question = st.chat_input("Ask me anything about your investments...")
        question = clicked_prompt or typed_question

        if question:
            _handle_question(user_id, question)

    except FinSightBaseException as exc:
        logger.error(f"Handled error in AI assistant dashboard: {exc}")
        st.error(f"Something went wrong: {exc.message}")
    except Exception as exc:  # noqa: BLE001
        logger.exception(f"Unexpected error in AI assistant dashboard: {exc}")
        st.error("An unexpected error occurred. Please try again.")
