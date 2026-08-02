"""
market_intelligence/company_news.py

Purpose: Renders the Company News tab -- ties directly into
stock_search's ticker resolution so a user searching a company on
Stock Search or Technical Analysis sees the exact same ticker's news
here. Shows per-article sentiment badges plus an overall aggregate
sentiment summary for the company.
"""

import streamlit as st

from dashboard.dashboard_layout import render_section_header
from helper import format_datetime
from market_intelligence.news_service import get_company_news_with_sentiment
from market_intelligence.sentiment_analysis import analyze_headline

_SENTIMENT_ICON = {"Positive": "🟢", "Neutral": "🟡", "Negative": "🔴"}
_BIAS_ICON = {"Bullish": "📈", "Bearish": "📉", "Neutral": "➖"}


def render_company_news(ticker: str) -> None:
    """Render the Company News tab for a resolved ticker."""
    render_section_header("Company News", subtitle=f"Latest news for {ticker}", icon="📰")

    with st.spinner(f"Fetching news for {ticker}..."):
        articles, overall = get_company_news_with_sentiment(ticker, limit=10)

    if not articles:
        st.info(f"No recent news found for {ticker}.")
        return

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Overall Sentiment", f"{_SENTIMENT_ICON[overall.sentiment_label]} {overall.sentiment_label}")
    with col2:
        st.metric("Market Bias", f"{_BIAS_ICON[overall.market_bias]} {overall.market_bias}")
    with col3:
        st.metric("Confidence", f"{overall.confidence:.0f}%")

    st.caption(
        f"Based on {overall.article_count} article(s): "
        f"{overall.positive_count} positive, {overall.neutral_count} neutral, {overall.negative_count} negative"
    )
    st.markdown("---")

    for article in articles:
        result = analyze_headline(article["headline"])
        published = format_datetime(article["published_at"]) if article["published_at"] else "Unknown date"

        st.markdown(
            f"**[{article['headline']}]({article['url']})**  \n"
            f"{_SENTIMENT_ICON[result.sentiment_label]} {result.sentiment_label} · "
            f"{_BIAS_ICON[result.market_bias]} {result.market_bias} · "
            f"<span style='opacity:0.6;'>{article['source']} • {published}</span>",
            unsafe_allow_html=True,
        )
        st.markdown("")
