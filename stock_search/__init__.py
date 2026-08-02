"""
stock_search package

Phase 5 — Stock Search & Company Analysis for FinSight AI.

Sub-modules:
    search_service.py       - ticker resolution, autocomplete, search history, favorites
    company_profile.py       - company identity fields + business summary
    stock_statistics.py      - market information stats grid
    valuation_metrics.py     - P/E, P/B, PEG, EV/EBITDA, Price/Sales, Dividend Yield
    fundamental_analysis.py  - ROE, ROA, D/E, liquidity ratios, margins
    income_statement.py / balance_sheet.py / cash_flow.py
                              - the three core financial statements
    financials.py             - combines the three statements into one tab
    historical_data.py        - period-selectable price history + CSV export
    stock_comparison.py       - up to 5-company side-by-side comparison
    stock_search.py            - main controller (entry point: stock_search.render)
"""

from stock_search.stock_search import render

__all__ = ["render"]
