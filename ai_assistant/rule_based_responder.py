"""
ai_assistant/rule_based_responder.py

Purpose: Generates a natural-language-ish answer directly from
`context_builder.py`'s fact dict, with no LLM call at all. This is the
mandatory fallback when no OpenAI/Gemini API key is configured (see
`llm_client.is_llm_configured()`), and it's exercised by every response
regardless -- `ai_assistant.py` always has this available as a safety
net even if an LLM call fails mid-conversation.
"""

from helper import format_currency, format_percentage


def generate_rule_based_response(context: dict) -> str:
    """Route to the right template based on the context dict's 'domain' key."""
    if "error" in context:
        return f"⚠️ {context['error']}"

    domain = context.get("domain", "general")
    handler = _DOMAIN_HANDLERS.get(domain, _handle_general)
    return handler(context)


def _handle_portfolio(ctx: dict) -> str:
    lines = [
        f"Your portfolio is currently worth **{format_currency(ctx['current_value'], '₹')}** "
        f"against a total investment of **{format_currency(ctx['total_investment'], '₹')}**.",
        f"That's an overall P&L of **{format_currency(ctx['total_profit_loss'], '₹')}** "
        f"({format_percentage(ctx['total_profit_loss_pct'])}), across {ctx['holdings_count']} holding(s).",
        f"Today's gain/loss: **{format_currency(ctx['todays_gain_loss'], '₹')}**.",
        f"Diversification: **{ctx['concentration_label']}** (score {ctx['diversification_score']:.0f}/100). "
        f"Risk level: **{ctx['risk_label']}**. Health score: **{ctx['health_score']:.0f}/100** ({ctx['health_label']}).",
    ]
    if ctx.get("top_winner"):
        lines.append(f"Your top winner is **{ctx['top_winner']}** ({format_percentage(ctx['top_winner_pct'])}) "
                      f"and your top loser is **{ctx['top_loser']}** ({format_percentage(ctx['top_loser_pct'])}).")
    return "\n\n".join(lines)


def _handle_watchlist(ctx: dict) -> str:
    if not ctx["tickers"]:
        return "Your watchlist is empty. Add tickers from the Stock Search page to start tracking them."
    lines = [f"You're watching **{ctx['count']}** ticker(s): {', '.join(ctx['tickers'])}."]
    if ctx["movers"]:
        mover_lines = [f"{m['ticker']}: {format_percentage(m['change_pct'])}" for m in ctx["movers"]]
        lines.append("Today's biggest movers on your watchlist: " + ", ".join(mover_lines))
    return "\n\n".join(lines)


def _handle_news(ctx: dict) -> str:
    if not ctx["headlines"]:
        return f"No recent news found{' for ' + ctx['ticker'] if ctx.get('ticker') else ''}."
    lines = [f"Here's the latest news{' for ' + ctx['ticker'] if ctx.get('ticker') else ' from the market'}:"]
    lines.extend(f"• {headline}" for headline in ctx["headlines"][:5])
    if ctx.get("sentiment_label"):
        lines.append(f"\nOverall sentiment: **{ctx['sentiment_label']}** ({ctx['market_bias']}).")
    return "\n".join(lines)


def _handle_sentiment(ctx: dict) -> str:
    if ctx.get("ticker"):
        return (
            f"News sentiment for **{ctx['ticker']}** is **{ctx['sentiment_label']}** "
            f"({ctx['market_bias']}), based on {ctx['article_count']} article(s) "
            f"with {ctx['confidence']:.0f}% confidence."
        )
    return (
        f"Overall market mood is **{ctx['overall_mood']}** -- {ctx['advancing']} stocks advancing vs. "
        f"{ctx['declining']} declining ({format_percentage(ctx['breadth_pct'])} breadth)."
    )


def _handle_ipo(ctx: dict) -> str:
    lines = []
    if ctx["open"]:
        open_lines = [f"{i['company']}" + (f" ({i['subscription']:.1f}x subscribed)" if i["subscription"] else "") for i in ctx["open"]]
        lines.append("Currently open for subscription: " + ", ".join(open_lines))
    if ctx["upcoming"]:
        lines.append("Upcoming IPOs: " + ", ".join(i["company"] for i in ctx["upcoming"]))
    return "\n\n".join(lines) if lines else "There are no open or upcoming IPOs tracked right now."


def _handle_notifications(ctx: dict) -> str:
    if ctx["unread_count"] == 0:
        return "You have no unread notifications."
    lines = [f"You have **{ctx['unread_count']}** unread notification(s)."]
    lines.extend(f"• {n['title']}: {n['message']}" for n in ctx["recent"])
    return "\n".join(lines)


def _handle_company(ctx: dict) -> str:
    if ctx.get("error"):
        return ctx["error"]
    currency = "₹" if ".NS" in ctx["ticker"] or ".BO" in ctx["ticker"] else "$"
    lines = [
        f"**{ctx['name']}** ({ctx['ticker']}) operates in the {ctx.get('sector', 'N/A')} sector "
        f"({ctx.get('industry', 'N/A')}).",
    ]
    if ctx.get("pe_ratio"):
        lines.append(
            f"Current price: {format_currency(ctx['current_price'], currency) if ctx.get('current_price') else 'N/A'} • "
            f"P/E: {ctx['pe_ratio']:.2f} • EPS: {ctx.get('eps', 'N/A')}"
        )
    if ctx.get("summary"):
        lines.append(ctx["summary"])
    return "\n\n".join(lines)


def _handle_technical(ctx: dict) -> str:
    if ctx.get("error"):
        return ctx["error"]
    trend = ctx["trend"]
    return (
        f"**{ctx['ticker']}** technical read: trend is **{trend['direction']}** ({trend['strength']}), "
        f"overall signal is **{ctx['overall_signal']}** "
        f"({ctx['buy_count']} Buy, {ctx['sell_count']} Sell, {ctx['neutral_count']} Neutral across indicators).\n\n"
        f"RSI(14): {ctx['indicators'].get('RSI (14)', 'N/A')} • "
        f"MACD: {ctx['indicators'].get('MACD', 'N/A')} • "
        f"ADX(14): {ctx['indicators'].get('ADX (14)', 'N/A')}"
    )


def _handle_prediction(ctx: dict) -> str:
    if ctx.get("error"):
        return ctx["error"]
    if ctx.get("note"):
        return ctx["note"]
    lines = [f"Cached ML predictions for **{ctx['ticker']}**:"]
    for p in ctx["predictions"]:
        conf = f" ({p['confidence']:.0f}% confidence)" if p["confidence"] is not None else ""
        lines.append(f"• {p['model']} ({p['horizon_days']}-day): {format_currency(p['predicted_price'], '₹')}{conf}")
    return "\n".join(lines)


def _handle_recommendation(ctx: dict) -> str:
    if ctx.get("error"):
        return ctx["error"]
    lines = [f"**{ctx['ticker']}**: {ctx['overall_recommendation']}"]
    lines.extend(f"• {reason}" for reason in ctx["reasoning"])
    return "\n".join(lines)


def _handle_general(_ctx: dict) -> str:
    return (
        "I can help with your portfolio, watchlist, news, market sentiment, IPOs, notifications, "
        "company profiles, technical indicators, and cached ML predictions. Try asking something like "
        "\"How is my portfolio doing?\" or \"What's the RSI on TCS?\""
    )


_DOMAIN_HANDLERS = {
    "portfolio": _handle_portfolio,
    "watchlist": _handle_watchlist,
    "news": _handle_news,
    "sentiment": _handle_sentiment,
    "ipo": _handle_ipo,
    "notifications": _handle_notifications,
    "company": _handle_company,
    "technical": _handle_technical,
    "prediction": _handle_prediction,
    "recommendation": _handle_recommendation,
}
