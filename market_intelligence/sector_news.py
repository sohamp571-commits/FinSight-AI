"""
market_intelligence/sector_news.py

Purpose: Renders the Sector News tab -- lets the user pick a sector
(from market_intelligence.news_service.SECTOR_MAP) and view aggregated
news + sentiment across every tracked ticker in that sector.
"""

import streamlit as st

from dashboard.dashboard_layout import render_section_header
from helper import format_datetime
from market_intelligence.news_service import SECTOR_MAP, get_sector_news_with_sentiment

_SENTIMENT_ICON = {"Positive": "🟢", "Neutral": "🟡", "Negative": "🔴"}
_BIAS_ICON = {"Bullish": "📈", "Bearish": "📉", "Neutral": "➖"}


def render_sector_news() -> None:
    """Render the Sector News tab: a sector picker plus aggregated news/sentiment."""
    render_section_header("Sector News", icon="🏭")

    sectors = sorted(set(SECTOR_MAP.values()))
    selected_sector = st.selectbox("Select a sector", sectors, key="sector_news_selector")

    with st.spinner(f"Fetching {selected_sector} sector news..."):
        articles, overall = get_sector_news_with_sentiment(selected_sector)

    if not articles:
        st.info(f"No recent news found for the {selected_sector} sector.")
        return

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Sector Sentiment", f"{_SENTIMENT_ICON[overall.sentiment_label]} {overall.sentiment_label}")
    with col2:
        st.metric("Sector Bias", f"{_BIAS_ICON[overall.market_bias]} {overall.market_bias}")
    with col3:
        st.metric("Articles Analyzed", overall.article_count)

    st.markdown("---")
    for article in articles[:15]:
        published = format_datetime(article["published_at"]) if article["published_at"] else "Unknown date"
        ticker_label = f"`{article['ticker_symbol']}` — " if article.get("ticker_symbol") else ""
        st.markdown(
            f"{ticker_label}**[{article['headline']}]({article['url']})**  \n"
            f"<span style='opacity:0.6;'>{article['source']} • {published}</span>",
            unsafe_allow_html=True,
        )
        st.markdown("")
