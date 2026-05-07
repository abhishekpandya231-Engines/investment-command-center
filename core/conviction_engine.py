"""
Conviction Engine v0.2
Investment Command Center

Purpose:
Creates a stricter conviction layer before final position sizing.

v0.2 upgrade:
- Makes High Conviction harder to achieve.
- Penalizes valuation excess, weak ROE, small-cap risk, moderate/high risk, and GUARD verdicts.
- Rewards only genuinely strong combinations.
- Keeps conviction separate from position sizing.

Outputs:
- Conviction Score
- Conviction Level
- Conviction Notes
"""


def safe_float(value, default=None):
    """Safely convert a value to float."""
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def normalize_text(value):
    """Normalize text values."""
    return str(value).upper().strip()


def score_rule_verdict(rule_verdict: str) -> tuple:
    """
    Scores the stock's rule verdict.
    Max: 20
    """
    verdict = normalize_text(rule_verdict)

    if "COMPOUNDER QUALIFIED" in verdict:
        return 20, "Strong compounder rule verdict."
    if "GROWTH QUALIFIED" in verdict:
        return 18, "Growth-qualified compounder verdict."
    if "VALUE QUALIFIED" in verdict:
        return 18, "Value-qualified verdict."
    if "GREEN GATE" in verdict:
        return 15, "Momentum green-gate verdict."
    if "VALUE WATCH" in verdict:
        return 8, "Value watch verdict; needs confirmation."
    if "COMPOUNDER WATCH" in verdict:
        return 8, "Compounder watch verdict; needs confirmation."
    if "GREY GATE" in verdict:
        return 6, "Momentum grey-gate verdict."
    if "RED GATE" in verdict:
        return 0, "Red-gate rule verdict."
    if "DATA CHECK" in verdict:
        return 3, "Data check required."

    return 5, "Unclassified rule verdict."


def score_exit_verdict(exit_verdict: str) -> tuple:
    """
    Scores Exit Engine verdict.
    Max: 20
    """
    verdict = normalize_text(exit_verdict)

    if verdict == "RIDE":
        return 20, "Exit Engine supports ride."
    if verdict == "TRIM":
        return 10, "Exit Engine suggests trim."
    if verdict == "GUARD":
        return 4, "Exit Engine suggests guard; conviction capped."
    if verdict == "FREEZE":
        return 1, "Exit Engine suggests freeze."
    if verdict == "EXIT":
        return 0, "Exit Engine suggests exit."

    return 5, "Exit verdict unclear."


def score_risk_level(risk_level: str, risk_score) -> tuple:
    """
    Scores Risk Engine output.
    Max: 18
    """
    level = normalize_text(risk_level)
    score = safe_float(risk_score, default=50)

    if level == "LOW":
        return 18, "Low risk profile."
    if level == "MODERATE":
        if score is not None and score <= 43:
            return 10, "Moderate risk but acceptable."
        return 6, "Moderate risk; conviction reduced."
    if level == "HIGH":
        return 1, "High risk; conviction heavily capped."
    if level == "CRITICAL":
        return 0, "Critical risk; avoid unless manually overridden."

    return 5, "Risk level unclear."


def score_engine_strength(engine: str) -> tuple:
    """
    Scores engine type.
    Max: 8
    """
    engine_value = normalize_text(engine)

    if engine_value == "D":
        return 8, "Engine D compounder framework."
    if engine_value == "C":
        return 7, "Engine C value framework."
    if engine_value == "B":
        return 5, "Engine B momentum framework; needs tighter sizing."

    return 3, "Unknown engine."


def score_market_regime(market_regime: str) -> tuple:
    """
    Scores Engine A regime support.
    Max: 8
    """
    regime = normalize_text(market_regime)

    if regime == "FULL DEPLOY":
        return 8, "Engine A regime is fully supportive."
    if regime == "AGGRESSIVE":
        return 7, "Engine A regime is aggressive."
    if regime == "ACTIVE":
        return 5, "Engine A regime is active."
    if regime == "CAUTIOUS":
        return 2, "Engine A regime is cautious."
    if regime == "FREEZE":
        return 0, "Engine A regime is freeze."
    if regime == "EXIT":
        return 0, "Engine A regime is exit."

    return 3, "Market regime unclear."


def score_overlap(row) -> tuple:
    """
    Scores cross-engine / cross-screener evidence.
    Max: 12

    If row has Count or Engines, it uses those.
    Otherwise it treats the row as a single appearance.
    """
    overlap_count = safe_float(row.get("Count"), default=1)
    engines = str(row.get("Engines", ""))

    if overlap_count is not None and overlap_count >= 3:
        return 12, "Appears across three or more screeners."
    if "," in engines and len([x for x in engines.split(",") if x.strip()]) >= 3:
        return 12, "Appears across three or more engines."
    if overlap_count is not None and overlap_count >= 2:
        return 8, "Appears across multiple screeners."
    if "," in engines:
        return 8, "Appears across multiple engines."

    return 1, "Single screener appearance; conviction reduced."


def score_quality_and_valuation(row) -> tuple:
    """
    Adds quality/valuation adjustment.
    Max positive: +14
    Max negative: -25
    """
    score = 0
    notes = []

    pe = safe_float(row.get("PE TTM"))
    peg = safe_float(row.get("PEG TTM"))
    roe = safe_float(row.get("ROE Ann  %"))
    piotroski = safe_float(row.get("Piotroski Score"))
    debt = safe_float(row.get("Total Debt to Total Equity Ann "))
    durability = safe_float(row.get("Durability Score"))
    momentum = safe_float(row.get("Momentum Score"))
    market_cap = normalize_text(row.get("Market Cap Category", ""))

    # Valuation adjustment
    if pe is not None:
        if pe < 0:
            score -= 12
            notes.append("Negative PE / loss-making risk.")
        elif pe <= 25:
            score += 5
            notes.append("Reasonable PE valuation.")
        elif pe <= 40:
            score += 1
            notes.append("PE is acceptable but not cheap.")
        elif pe <= 60:
            score -= 6
            notes.append("PE is elevated.")
        else:
            score -= 12
            notes.append("PE is very high.")

    if peg is not None:
        if 0 < peg <= 1.5:
            score += 3
            notes.append("PEG is reasonable.")
        elif peg > 3:
            score -= 5
            notes.append("PEG is expensive.")

    # Profitability adjustment
    if roe is not None:
        if roe >= 18:
            score += 5
            notes.append("ROE is strong.")
        elif roe >= 12:
            score += 2
            notes.append("ROE is acceptable.")
        elif roe < 8:
            score -= 7
            notes.append("ROE is weak.")

    # Balance sheet / quality adjustment
    if piotroski is not None:
        if piotroski >= 8:
            score += 3
            notes.append("Piotroski score is strong.")
        elif piotroski <= 4:
            score -= 5
            notes.append("Piotroski score is weak.")

    if debt is not None:
        if debt <= 0.5:
            score += 3
            notes.append("Debt level is comfortable.")
        elif debt > 1.0:
            score -= 6
            notes.append("Debt level is elevated.")
        elif debt > 2.0:
            score -= 10
            notes.append("Debt level is very high.")

    # DVM adjustment
    if durability is not None:
        if durability >= 75:
            score += 2
            notes.append("Durability score is strong.")
        elif durability < 50:
            score -= 5
            notes.append("Durability score is weak.")

    if momentum is not None:
        if momentum >= 65:
            score += 2
            notes.append("Momentum score is strong.")
        elif momentum < 50:
            score -= 5
            notes.append("Momentum score is weak.")

    # Market-cap adjustment
    if market_cap == "SMALL CAP":
        score -= 5
        notes.append("Small-cap exposure; conviction reduced.")
    elif market_cap == "MID CAP":
        score -= 2
        notes.append("Mid-cap exposure; mild conviction haircut.")
    elif market_cap == "LARGE CAP":
        score += 2
        notes.append("Large-cap exposure supports stability.")

    if not notes:
        notes.append("No strong quality/valuation adjustment.")

    return score, " ".join(notes)


def classify_conviction(score: float, exit_verdict: str, risk_level: str) -> str:
    """
    Converts conviction score to conviction label.
    v0.2 uses stricter bands and hard caps.
    """
    verdict = normalize_text(exit_verdict)
    risk = normalize_text(risk_level)

    if verdict in ["EXIT", "FREEZE"]:
        return "AVOID / FREEZE"
    if risk == "CRITICAL":
        return "AVOID / FREEZE"
    if risk == "HIGH":
        if score >= 80:
            return "TACTICAL ONLY"
        return "WATCHLIST"
    if verdict == "GUARD":
        if score >= 75:
            return "MEDIUM"
        return "LOW"

    if score >= 86:
        return "HIGH CONVICTION"
    if score >= 74:
        return "STRONG"
    if score >= 58:
        return "MEDIUM"
    if score >= 42:
        return "LOW"
    return "WATCHLIST"


def calculate_conviction(row, market_regime="ACTIVE") -> dict:
    """
    Calculates conviction score for a single row.
    """
    rule_score, rule_note = score_rule_verdict(row.get("Rule Verdict", ""))
    exit_score, exit_note = score_exit_verdict(row.get("Exit Verdict", ""))
    risk_component_score, risk_note = score_risk_level(
        row.get("Risk Level", ""),
        row.get("Risk Score", 50),
    )
    engine_score, engine_note = score_engine_strength(row.get("Engine", ""))
    regime_score, regime_note = score_market_regime(market_regime)
    overlap_score, overlap_note = score_overlap(row)
    quality_score, quality_note = score_quality_and_valuation(row)

    raw_score = (
        rule_score
        + exit_score
        + risk_component_score
        + engine_score
        + regime_score
        + overlap_score
        + quality_score
    )

    conviction_score = max(min(round(raw_score, 2), 100), 0)

    conviction_level = classify_conviction(
        conviction_score,
        row.get("Exit Verdict", ""),
        row.get("Risk Level", ""),
    )

    notes = [
        rule_note,
        exit_note,
        risk_note,
        engine_note,
        regime_note,
        overlap_note,
        quality_note,
    ]

    return {
        "Conviction Score": conviction_score,
        "Conviction Level": conviction_level,
        "Conviction Notes": " ".join(notes),
    }


def apply_conviction_engine(df, market_regime="ACTIVE"):
    """
    Applies conviction engine to dataframe.
    """
    df = df.copy()

    conviction_results = df.apply(
        lambda row: calculate_conviction(row, market_regime=market_regime),
        axis=1,
    )

    df["Conviction Score"] = conviction_results.apply(
        lambda result: result["Conviction Score"]
    )
    df["Conviction Level"] = conviction_results.apply(
        lambda result: result["Conviction Level"]
    )
    df["Conviction Notes"] = conviction_results.apply(
        lambda result: result["Conviction Notes"]
    )

    return df


def summarize_conviction(df):
    """
    Summarizes conviction levels.
    """
    if df.empty or "Conviction Level" not in df.columns:
        return {
            "high_conviction": 0,
            "strong": 0,
            "medium": 0,
            "low": 0,
            "watchlist": 0,
            "tactical_only": 0,
            "avoid_freeze": 0,
        }

    levels = df["Conviction Level"].astype(str).str.upper()

    return {
        "high_conviction": int((levels == "HIGH CONVICTION").sum()),
        "strong": int((levels == "STRONG").sum()),
        "medium": int((levels == "MEDIUM").sum()),
        "low": int((levels == "LOW").sum()),
        "watchlist": int((levels == "WATCHLIST").sum()),
        "tactical_only": int((levels == "TACTICAL ONLY").sum()),
        "avoid_freeze": int((levels == "AVOID / FREEZE").sum()),
    }
