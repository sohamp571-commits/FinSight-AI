"""
market_intelligence/global_market_news.py

Purpose: Renders the Global Market News tab -- broad market headlines
(NewsAPI when configured, yfinance-index fallback otherwise) plus the
full combined market_sentiment.py report (news sentiment + price
breadth).
"""

import streamlit as st

from dashboard.dashboard_layout import render_section_header, responsive_columns
from helper import format_datetime
from market_intelligence.market_sentiment import compute_market_sentiment
from market_intelligence.news_service import get_global_market_news_with_sentiment

_MOOD_ICON = {"Bullish": "📈", "Bearish": "📉", "Neutral": "➖", "Mixed": "🔀"}


def render_global_market_news() -> None:
    """Render the Global Market News tab: overall sentiment report + headline feed."""
    render_section_header("Global Market News", icon="🌍")

    with st.spinner("Analyzing overall market sentiment..."):
        report = compute_market_sentiment()

    columns = responsive_columns(4, max_cols=4)
    with columns[0]:
        st.metric("Market Mood", f"{_MOOD_ICON[report.overall_mood]} {report.overall_mood}")
    with columns[1]:
        st.metric("Advancing", report.advancing_count)
    with columns[2]:
        st.metric("Declining", report.declining_count)
    with columns[3]:
        st.metric("Breadth", f"{report.breadth_pct:.1f}%")

    st.caption(
        f"News sentiment: {report.news_sentiment.sentiment_label} "
        f"({report.news_sentiment.market_bias}, {report.news_sentiment.confidence:.0f}% confidence "
        f"across {report.news_sentiment.article_count} articles)"
    )
    st.markdown("---")

    with st.spinner("Fetching global market headlines..."):
        articles, _ = get_global_market_news_with_sentiment(limit=15)

    if not articles:
        st.info("No global market news available right now.")
        return

    for article in articles:
        published = format_datetime(article["published_at"]) if article["published_at"] else "Unknown date"
        st.markdown(
            f"**[{article['headline']}]({article['url']})**  \n"
            f"<span style='opacity:0.6;'>{article['source']} • {published}</span>",
            unsafe_allow_html=True,
        )
        st.markdown("")
