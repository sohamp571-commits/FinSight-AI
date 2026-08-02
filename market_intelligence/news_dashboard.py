"""
market_intelligence/news_dashboard.py

Purpose: The main entry point for the whole Phase 8 module. Ties
together News (Live Market / Company / Sector / Global / Breaking /
Trending / AI Summary), the IPO module (Calendar / Details /
Subscription), and the Notification Center (list / preferences) into
one page with top-level tabs -- exactly like `dashboard.dashboard.py`
and `analytics.technical_analysis.py` do for their own modules.
"""

import streamlit as st

from authentication.middleware import login_required
from authentication.session_manager import get_current_user_id
from custom_exceptions import FinSightBaseException
from dashboard.dashboard_layout import inject_dashboard_css, render_divider, render_section_header
from database.audit_service import audit_service
from helper import format_datetime
from logging_config import logger

from market_intelligence.alert_history import render_alert_history
from market_intelligence.company_news import render_company_news
from market_intelligence.global_market_news import render_global_market_news
from market_intelligence.ipo_calendar import render_ipo_calendar
from market_intelligence.ipo_details import render_ipo_details
from market_intelligence.ipo_subscription import render_ipo_subscription_status
from market_intelligence.news_classifier import detect_trending_stocks
from market_intelligence.news_service import (
    get_ai_news_summary,
    get_breaking_news,
    get_live_market_news,
    get_trending_stocks,
)
from market_intelligence.notification_service import (
    archive_notification,
    delete_notification,
    get_notifications,
    get_preferences,
    get_unread_count,
    mark_all_read,
    mark_read,
    update_preferences,
)
from stock_search.search_service import resolve_ticker, validate_ticker_exists

_PRIORITY_ICON = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}


# ==========================================================
# News sub-sections
# ==========================================================
def _render_live_market_news() -> None:
    render_section_header("Live Market News", icon="📡")
    articles = get_live_market_news(limit=20)
    if not articles:
        st.info("No live market news available right now.")
        return
    for article in articles:
        published = format_datetime(article["published_at"]) if article["published_at"] else "Unknown date"
        ticker_label = f"`{article['ticker_symbol']}` — " if article.get("ticker_symbol") else ""
        st.markdown(f"{ticker_label}**[{article['headline']}]({article['url']})**  \n<span style='opacity:0.6;'>{article['source']} • {published}</span>", unsafe_allow_html=True)
        st.markdown("")


def _render_company_news_tab() -> None:
    query = st.text_input("🔍 Company name or ticker", placeholder="e.g. TCS, Reliance Industries", key="mi_company_query")
    if not query.strip():
        st.caption("Search for a company to see its news.")
        return
    ticker = resolve_ticker(query)
    if not validate_ticker_exists(ticker):
        st.error(f"'{query}' could not be resolved to a valid ticker.")
        return
    render_company_news(ticker)


def _render_breaking_news() -> None:
    render_section_header("Breaking News", subtitle="Published within the last 3 hours", icon="⚡")
    articles = get_breaking_news(limit=10)
    if not articles:
        st.info("No breaking news in the last 3 hours.")
        return
    for article in articles:
        published = format_datetime(article["published_at"])
        st.markdown(f"🔴 **[{article['headline']}]({article['url']})**  \n<span style='opacity:0.6;'>{article['source']} • {published}</span>", unsafe_allow_html=True)
        st.markdown("")


def _render_trending() -> None:
    render_section_header("Trending Stocks", subtitle="Ranked by recent news volume", icon="🔥")
    with st.spinner("Analyzing trending stocks..."):
        trending = get_trending_stocks(top_n=10)
    if not trending:
        st.info("No trending data available right now.")
        return
    st.dataframe([{"Ticker": t, "Article Count": c} for t, c in trending], use_container_width=True, hide_index=True)


def _render_ai_summary() -> None:
    render_section_header("AI News Summary", icon="🤖")
    st.write(get_ai_news_summary(limit=5))


def _render_news_module() -> None:
    tabs = st.tabs(["Live Market", "Company", "Sector", "Global", "Breaking", "Trending", "AI Summary"])
    with tabs[0]:
        _render_live_market_news()
    with tabs[1]:
        _render_company_news_tab()
    with tabs[2]:
        from market_intelligence.sector_news import render_sector_news
        render_sector_news()
    with tabs[3]:
        render_global_market_news()
    with tabs[4]:
        _render_breaking_news()
    with tabs[5]:
        _render_trending()
    with tabs[6]:
        _render_ai_summary()


# ==========================================================
# IPO module
# ==========================================================
def _render_ipo_module(user_id: int) -> None:
    tabs = st.tabs(["Calendar", "Details", "Subscription Status"])
    with tabs[0]:
        render_ipo_calendar()
    with tabs[1]:
        render_ipo_details(user_id)
    with tabs[2]:
        render_ipo_subscription_status()


# ==========================================================
# Notification Center
# ==========================================================
def _render_notification_list(user_id: int) -> None:
    unread_only = st.checkbox("Show unread only", value=False, key="notif_unread_only")
    result = get_notifications(user_id, unread_only=unread_only, page_size=30)
    notifications = result["items"]

    col1, col2 = st.columns([3, 1])
    with col1:
        st.caption(f"{get_unread_count(user_id)} unread notification(s)")
    with col2:
        if st.button("Mark all read", use_container_width=True):
            mark_all_read(user_id)
            st.rerun()

    if not notifications:
        st.info("No notifications to show.")
        return

    for n in notifications:
        with st.container():
            cols = st.columns([5, 1, 1])
            with cols[0]:
                read_marker = "" if n.is_read else "**"
                st.markdown(f"{_PRIORITY_ICON.get(n.priority, '⚪')} {read_marker}{n.title}{read_marker}")
                st.caption(f"{n.message}  •  {format_datetime(n.created_at)}")
            with cols[1]:
                if not n.is_read and st.button("Read", key=f"read_{n.notification_id}"):
                    mark_read(n.notification_id)
                    st.rerun()
            with cols[2]:
                if st.button("🗑️", key=f"delete_{n.notification_id}"):
                    delete_notification(n.notification_id)
                    st.rerun()
            st.markdown("---")


def _render_notification_preferences(user_id: int) -> None:
    prefs = get_preferences(user_id)

    with st.form("notification_preferences_form"):
        st.markdown("**Subscriptions**")
        col1, col2 = st.columns(2)
        with col1:
            ipo_open = st.checkbox("IPO Opens", value=prefs.ipo_open)
            ipo_close = st.checkbox("IPO Closes", value=prefs.ipo_close)
            ipo_listing = st.checkbox("IPO Listing", value=prefs.ipo_listing)
            watchlist_news = st.checkbox("Watchlist News", value=prefs.watchlist_news)
            watchlist_price_alerts = st.checkbox("Watchlist Price Alerts", value=prefs.watchlist_price_alerts)
            prediction_changes = st.checkbox("Prediction Changes", value=prefs.prediction_changes)
            market_opening = st.checkbox("Market Opening", value=prefs.market_opening)
        with col2:
            market_closing = st.checkbox("Market Closing", value=prefs.market_closing)
            portfolio_profit_target = st.checkbox("Portfolio Profit Target", value=prefs.portfolio_profit_target)
            portfolio_stop_loss = st.checkbox("Portfolio Stop Loss", value=prefs.portfolio_stop_loss)
            market_crash_rally = st.checkbox("Market Crash / Rally", value=prefs.market_crash_rally)
            st.markdown("**Email**")
            email_daily_digest = st.checkbox("Daily Digest", value=prefs.email_daily_digest)
            email_weekly_digest = st.checkbox("Weekly Digest", value=prefs.email_weekly_digest)
            email_instant_alerts = st.checkbox("Instant Alerts", value=prefs.email_instant_alerts)

        submitted = st.form_submit_button("Save Preferences", use_container_width=True)

    if submitted:
        update_preferences(
            user_id, ipo_open=ipo_open, ipo_close=ipo_close, ipo_listing=ipo_listing,
            watchlist_news=watchlist_news, watchlist_price_alerts=watchlist_price_alerts,
            prediction_changes=prediction_changes, market_opening=market_opening, market_closing=market_closing,
            portfolio_profit_target=portfolio_profit_target, portfolio_stop_loss=portfolio_stop_loss,
            market_crash_rally=market_crash_rally, email_daily_digest=email_daily_digest,
            email_weekly_digest=email_weekly_digest, email_instant_alerts=email_instant_alerts,
        )
        st.success("Notification preferences saved.")


def _render_notification_center(user_id: int) -> None:
    tabs = st.tabs(["Notifications", "Preferences", "History"])
    with tabs[0]:
        _render_notification_list(user_id)
    with tabs[1]:
        _render_notification_preferences(user_id)
    with tabs[2]:
        render_alert_history(user_id)


# ==========================================================
# Main entry point
# ==========================================================
@login_required
def render() -> None:
    """Render the full AI News + Sentiment + IPO + Notifications page."""
    try:
        inject_dashboard_css()
        user_id = get_current_user_id()

        unread = get_unread_count(user_id)
        st.title(f"🧠 Market Intelligence {'🔴' if unread else ''}")
        st.caption("AI-powered news, sentiment analysis, IPO tracking, and smart notifications.")
        render_divider()

        audit_service.log_action(action="MARKET_INTELLIGENCE_VIEW", user_id=user_id)

        top_tabs = st.tabs([
            "📰 News & Sentiment", "🏦 IPO Tracker", f"🔔 Notifications ({unread})",
        ])
        with top_tabs[0]:
            _render_news_module()
        with top_tabs[1]:
            _render_ipo_module(user_id)
        with top_tabs[2]:
            _render_notification_center(user_id)

    except FinSightBaseException as exc:
        logger.error(f"Handled error in market intelligence dashboard: {exc}")
        st.error(f"Something went wrong: {exc.message}")
    except Exception as exc:  # noqa: BLE001
        logger.exception(f"Unexpected error in market intelligence dashboard: {exc}")
        st.error("An unexpected error occurred. Please try again.")
