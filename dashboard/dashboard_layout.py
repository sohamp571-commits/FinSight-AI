"""
dashboard/dashboard_layout.py

Purpose: Shared, purely-presentational layout building blocks used by
every other dashboard file -- CSS injection for the "professional
SaaS dashboard" look, section headers, and a responsive column-count
helper so widget grids adapt to how many items they're given instead
of every file hard-coding `st.columns(5)`.
"""

import streamlit as st


def inject_dashboard_css() -> None:
    """
    Inject the dashboard's shared stylesheet once per page render.
    Defines the KPI card, data-table, and badge classes used across
    market_indices.py, top_gainers.py, top_losers.py, most_active.py,
    and market_status.py.
    """
    st.markdown(
        """
        <style>
        .kpi-card {
            background: linear-gradient(145deg, rgba(30,41,59,0.65), rgba(15,23,42,0.65));
            border: 1px solid rgba(148, 163, 184, 0.15);
            border-radius: 14px;
            padding: 1rem 1.1rem;
            transition: transform 0.15s ease, border-color 0.15s ease;
        }
        .kpi-card:hover {
            transform: translateY(-2px);
            border-color: rgba(79, 139, 249, 0.45);
        }
        .kpi-label {
            font-size: 0.78rem;
            font-weight: 600;
            letter-spacing: 0.03em;
            text-transform: uppercase;
            opacity: 0.65;
            margin-bottom: 0.15rem;
        }
        .kpi-value {
            font-size: 1.5rem;
            font-weight: 700;
            line-height: 1.25;
        }
        .kpi-change-positive {
            color: #22C55E;
            font-weight: 600;
            font-size: 0.88rem;
        }
        .kpi-change-negative {
            color: #EF4444;
            font-weight: 600;
            font-size: 0.88rem;
        }
        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
            padding: 0.35rem 0.9rem;
            border-radius: 999px;
            font-weight: 600;
            font-size: 0.85rem;
        }
        .status-badge-open {
            background: rgba(34, 197, 94, 0.15);
            color: #22C55E;
            border: 1px solid rgba(34, 197, 94, 0.35);
        }
        .status-badge-closed {
            background: rgba(239, 68, 68, 0.15);
            color: #EF4444;
            border: 1px solid rgba(239, 68, 68, 0.35);
        }
        .dashboard-section-title {
            font-size: 1.15rem;
            font-weight: 700;
            margin-top: 0.5rem;
            margin-bottom: 0.35rem;
        }
        .dashboard-section-subtitle {
            font-size: 0.85rem;
            opacity: 0.65;
            margin-bottom: 0.75rem;
        }
        @keyframes fadeInUp {
            from { opacity: 0; transform: translateY(6px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .kpi-card, .dashboard-table-row {
            animation: fadeInUp 0.35s ease-out;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_section_header(title: str, subtitle: str | None = None, icon: str = "") -> None:
    """Render a consistent section title (+ optional subtitle) used above every dashboard block."""
    st.markdown(
        f'<div class="dashboard-section-title">{icon} {title}</div>',
        unsafe_allow_html=True,
    )
    if subtitle:
        st.markdown(f'<div class="dashboard-section-subtitle">{subtitle}</div>', unsafe_allow_html=True)


def responsive_columns(item_count: int, max_cols: int = 5):
    """
    Return an `st.columns` layout sized to the number of items being
    displayed, capped at `max_cols`, so a 3-item row doesn't stretch
    across 5 mostly-empty columns.
    """
    col_count = max(1, min(item_count, max_cols))
    return st.columns(col_count)


def render_divider() -> None:
    """Render a subtle horizontal divider between dashboard sections."""
    st.markdown(
        '<hr style="border: none; border-top: 1px solid rgba(148,163,184,0.15); margin: 1.25rem 0;">',
        unsafe_allow_html=True,
    )


def render_skeleton_loader(rows: int = 3, height_px: int = 18) -> None:
    """
    Render a shimmering placeholder block (Phase 12 UI polish) for use
    while data is loading, in place of a jarring blank gap. Call this
    just before a slow data fetch, then let the real content replace
    it on rerun (Streamlit has no native skeleton component, so this
    is a small reusable CSS-animation helper shared across pages).
    """
    st.markdown(
        """
        <style>
        @keyframes finsight-shimmer {
            0% { background-position: -400px 0; }
            100% { background-position: 400px 0; }
        }
        .finsight-skeleton-row {
            height: {height}px;
            border-radius: 8px;
            margin-bottom: 0.6rem;
            background: linear-gradient(
                90deg,
                rgba(148,163,184,0.08) 25%,
                rgba(148,163,184,0.18) 37%,
                rgba(148,163,184,0.08) 63%
            );
            background-size: 800px 100%;
            animation: finsight-shimmer 1.4s ease-in-out infinite;
        }
        </style>
        """.replace("{height}", str(height_px)),
        unsafe_allow_html=True,
    )
    for _ in range(rows):
        st.markdown('<div class="finsight-skeleton-row"></div>', unsafe_allow_html=True)


def render_empty_state(message: str, icon: str = "📭", action_label: str | None = None) -> bool:
    """
    Render a friendly, consistent empty state (Phase 12 UI polish) in
    place of a bare `st.info()`, with an optional call-to-action
    button. Returns True if the action button was clicked, so the
    caller can respond (e.g. navigate elsewhere) without this module
    needing to know about routing.
    """
    st.markdown(
        f"""
        <div style="text-align:center; padding: 2.5rem 1rem; opacity: 0.85;">
            <div style="font-size: 2.4rem; margin-bottom: 0.5rem;">{icon}</div>
            <div style="font-size: 0.95rem; color: #94A3B8;">{message}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if action_label:
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            return st.button(action_label, use_container_width=True, key=f"empty_state_action_{hash(message) % 10_000}")
    return False
