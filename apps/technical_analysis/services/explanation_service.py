"""Explanation service for stock technical ratings.

Generates human-readable, transparent, and factual explanations for
technical scores and candidate rankings without using promotional or guaranteed labels.
"""

from __future__ import annotations

from apps.technical_analysis.scoring.stock_scoring import StockTechnicalScore


def generate_stock_explanation(
    symbol: str,
    company_name: str,
    sector_name: str,
    score: StockTechnicalScore,
    *,
    sector_strength_score: float | None = None,
) -> str:
    """Generate a balanced, structured technical explanation for a security.

    Strictly adheres to research neutrality guidelines:
    - Never uses 'BUY NOW' or guaranteed-profit terminology.
    - Explicitly surfaces cautionary warnings and risk flags.
    - Identifies standalone strength regardless of sector condition.
    """
    lines: list[str] = []

    # Opening summary
    lines.append(
        f"{symbol} ({company_name}) has an algorithmic technical score of {score.total_score}/100 "
        f"and is classified as a '{score.classification}'."
    )

    # Component point attribution
    lines.append(
        f"Score Breakdown: Trend: {score.trend_score}/30, Momentum: {score.momentum_score}/20, "
        f"Volume: {score.volume_score}/15, Relative Strength: {score.relative_strength_score}/15, "
        f"Breakout/Structure: {score.breakout_score}/10, Risk Stability: {score.risk_score}/10."
    )

    # Sector context
    if sector_strength_score is not None:
        if sector_strength_score < 50.0 and score.total_score >= 65.0:
            lines.append(
                f"Notable Idiosyncratic Strength: {symbol} demonstrates independent bullish momentum "
                f"despite belonging to a weakened sector ({sector_name}, strength {sector_strength_score}/100)."
            )
        elif sector_strength_score >= 65.0 and score.total_score >= 65.0:
            lines.append(
                f"Sector Alignment: Benefiting from positive tailwinds in {sector_name} "
                f"(sector strength {sector_strength_score}/100) alongside individual outperformance."
            )
        elif sector_strength_score >= 65.0 and score.total_score < 50.0:
            lines.append(
                f"Sector Divergence Caution: Although {sector_name} is trending, {symbol}'s individual "
                f"technical metrics remain weak and do not warrant inclusion based on sector alone."
            )

    # Key Bullish Catalysts
    if score.bullish_signals:
        lines.append("Key Supporting Factors:")
        for sig in score.bullish_signals[:4]:
            lines.append(f"  • {sig}")

    # Key Bearish Factors
    if score.bearish_signals:
        lines.append("Technical Headwinds:")
        for b_sig in score.bearish_signals[:3]:
            lines.append(f"  • {b_sig}")

    # Risk Warnings & Safeguards
    if score.warnings:
        lines.append("Cautionary Flags & Risk Considerations:")
        for w in score.warnings:
            lines.append(f"  ⚠ {w}")
    else:
        lines.append("Risk Profile: Volatility and price structure are currently within standard operating thresholds.")

    lines.append(
        "Disclaimer: Algorithmic technical classifications are mathematical research outputs "
        "and do not constitute investment advice or guaranteed return forecasts."
    )

    return "\n".join(lines)
