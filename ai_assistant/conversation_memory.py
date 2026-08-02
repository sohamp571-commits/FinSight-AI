"""
ai_assistant/conversation_memory.py

Purpose: Manages chat history for the AI Assistant within
`st.session_state` -- the same pattern `authentication.session_manager`
already uses for auth state. No new database table was introduced for
this (see Phase 10's pre-implementation analysis): conversation memory
is inherently per-browser-session, ephemeral context, not a durable
business record like a transaction or notification.
"""

from dataclasses import dataclass, field
from datetime import datetime

import streamlit as st

SESSION_KEY_MESSAGES = "ai_assistant_messages"
MAX_HISTORY_MESSAGES = 30  # cap to keep the prompt sent to an LLM bounded


@dataclass
class ChatMessage:
    """A single turn in the conversation."""

    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)


def get_history() -> list[ChatMessage]:
    """Return the current session's conversation history (empty list if none yet)."""
    return st.session_state.get(SESSION_KEY_MESSAGES, [])


def add_message(role: str, content: str) -> None:
    """Append a message to the session's conversation history, trimming to MAX_HISTORY_MESSAGES."""
    history = st.session_state.get(SESSION_KEY_MESSAGES, [])
    history.append(ChatMessage(role=role, content=content))
    st.session_state[SESSION_KEY_MESSAGES] = history[-MAX_HISTORY_MESSAGES:]


def clear_history() -> None:
    """Clear the conversation history for the current session (e.g. a "New Chat" button)."""
    st.session_state[SESSION_KEY_MESSAGES] = []


def get_recent_context_pairs(max_pairs: int = 5) -> list[tuple[str, str]]:
    """
    Return the most recent (user, assistant) message pairs, for
    inclusion in an LLM prompt's conversation history. Skips any
    trailing unanswered user message.
    """
    history = get_history()
    pairs: list[tuple[str, str]] = []
    i = 0
    while i < len(history) - 1:
        if history[i].role == "user" and history[i + 1].role == "assistant":
            pairs.append((history[i].content, history[i + 1].content))
            i += 2
        else:
            i += 1
    return pairs[-max_pairs:]
