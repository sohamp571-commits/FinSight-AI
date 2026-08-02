"""
market_intelligence package

Phase 8 — AI News + Sentiment Analysis + IPO Tracker + Smart
Notification System for FinSight AI.

Sub-modules:
    news_parser.py            - normalizes raw news payloads into one schema
    news_fetcher.py             - external news retrieval (yfinance + optional NewsAPI)
    news_cache.py                - bridges news_fetcher to the existing news_cache table
    sentiment_analysis.py         - per-headline sentiment (TextBlob)
    sentiment_score.py             - aggregate sentiment across multiple articles
    news_classifier.py              - breaking news + trending stocks/sectors
    news_service.py                  - Streamlit-free news orchestration layer
    market_sentiment.py               - combined news + price-breadth market mood
    company_news.py / sector_news.py / global_market_news.py
                                        - news render tabs
    ipo_service.py                     - CRUD + business logic for ipo_listings
    ipo_calendar.py / ipo_details.py / ipo_subscription.py
                                         - IPO render tabs
    notification_service.py              - Notification Center CRUD + preferences
    email_notification.py                 - SMTP HTML email delivery
    price_alerts.py / watchlist_alerts.py / news_alerts.py / ipo_alerts.py
                                            - alert-generating checks
    alert_history.py                        - combined notification + alert history view
    notification_scheduler.py                - orchestrates all periodic checks (external cron)
    news_dashboard.py                         - main controller (entry point: news_dashboard.render)
"""

from market_intelligence.news_dashboard import render

__all__ = ["render"]
