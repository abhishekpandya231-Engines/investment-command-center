"""
Conviction Engine v0.1
Investment Command Center

Purpose:
Creates a conviction layer before final position sizing.

Why this exists:
A stock should not get position size only because it passed one screener.
Conviction should improve when:
- The stock appears in multiple engines/screeners.
- Rule verdict is strong.
- Exit verdict is supportive.
- Risk level is low/moderate.
- Engine A regime is supportive.

Outputs:
- Conviction Score
- Conviction Level
- Conviction Notes
"""


def safe_float(value, default=0):
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
    Scores the stock's own rule verdict.
    Max: 25
    """
    verdict = normalize_text(rule_verdict)

    if "COMPOUNDER QUALIFIED" in verdict:
        return 25, "Strong compounder rule verdict."
    if "GROWTH QUALIFIED" in verdict:
        return 22, "Growth-qualified compounder verdict."
    if "VALUE QUALIFIED" in verdict:
        return 22, "Value-qualified verdict."
    if "GREEN GATE" in verdict:
        return 20, "Momentum green-gate verdict."
    if "VALUE WATCH" in verdict:
        return 12, "Value watch verdict; needs confirmation."
    if "COMPOUNDER WATCH" in verdict:
        return 12, "Compounder watch verdict; needs confirmation."
    if "GREY GATE" in verdict:
        return 10, "Momentum grey-gate verdict."
    if "RED GATE" in verdict:
        return 0, "Red-gate rule verdict."
    if "DATA CHECK" in verdict:
        return 5, "Data check required."

    return 8, "Unclassified rule verdict."


def score_exit_verdict(exit_verdict: str) -> tuple:
    """
    Scores Exit Engine verdict.
    Max: 25
    """
    verdict = normalize_text(exit_verdict)

    if verdict == "RIDE":
        return 25, "Exit Engine supports ride."
    if verdict == "TRIM":
        return 14, "Exit Engine suggests trim."
    if verdict == "GUARD":
        return 8, "Exit Engine suggests guard."
    if verdict == "FREEZE":
        return 3, "Exit Engine suggests freeze."
    if verdict == "EXIT":
        return 0, "Exit Engine suggests exit."

    return 8, "Exit verdict unclear."


def score_risk_level(risk_level: str, risk_score) -> tuple:
    """
    Scores Risk Engine output.
    Max: 20
    """
    level = normalize_text(risk_level)
    score = safe_float(risk_score, default=50)

    if level == "LOW":
        return 20, "Low risk profile."
    if level == "MODERATE":
        if score <= 45:
            return 14, "Moderate risk but acceptable."
        return 10, "Moderate risk; position sizing should be controlled."
    if level == "HIGH":
        return 4, "High risk; strong cap required."
    if level == "CRITICAL":
        return 0, "Critical risk; avoid unless manually overridden."

    return 8, "Risk level unclear."


def score_engine_strength(engine: str) -> tuple:
    """
    Scores engine type.
    Max: 10

    Engine D and C can carry higher fundamental conviction.
    Engine B can be strong, but generally needs stricter sizing.
    """
    engine_value = normalize_text(engine)

    if engine_value == "D":
        return 10, "Engine D compounder framework."
    if engine_value == "C":
        return 8, "Engine C value framework."
    if engine_value == "B":
        return 7, "Engine B momentum framework."

    return 4, "Unknown engine."


def score_market_regime(market_regime: str) -> tuple:
    """
    Scores Engine A regime support.
    Max: 10
    """
    regime = normalize_text(market_regime)

    if regime == "FULL DEPLOY":
        return 10, "Engine A regime is fully supportive."
    if regime == "AGGRESSIVE":
        return 8, "Engine A regime is aggressive."
    if regime == "ACTIVE":
        return 6, "Engine A regime is active."
    if regime == "CAUTIOUS":
        return 3, "Engine A regime is cautious."
    if regime == "FREEZE":
        return 1, "Engine A regime is freeze."
    if regime == "EXIT":
        return 0, "Engine A regime is exit."

    return 4, "Market regime unclear."


def score_overlap(row) -> tuple:
    """
    Scores cross-engine / cross-screener evidence.
    Max: 10

    This function can use Count if available from overlap table.
    If Count is not available in row-level screeners, it gives neutral score.
    """
    overlap_count = safe_float(row.get("Count"), default=1)
    engines = str(row.get("Engines", ""))

    if overlap_count >= 3 or ("," in engines and len(engines.split(",")) >= 3):
        return 10, "Appears across three or more engines/screeners."
    if overlap_count >= 2 or "," in engines:
        return 7, "Appears across multiple engines/screeners."

    return 3, "Single screener appearance."


def classify_conviction(score: float, exit_verdict: str, risk_level: str) -> str:
    """
    Converts conviction score to conviction label.
    Hard caps are applied for bad exit/risk states.
    """
    verdict = normalize_text(exit_verdict)
    risk = normalize_text(risk_level)

    if verdict in ["EXIT", "FREEZE"]:
        return "AVOID / FREEZE"
    if risk == "CRITICAL":
        return "AVOID / FREEZE"
    if risk == "HIGH":
        if score >= 75:
            return "TACTICAL ONLY"
        return "WATCHLIST"

    if score >= 80:
        return "HIGH CONVICTION"
    if score >= 65:
        return "STRONG"
    if score >= 50:
        return "MEDIUM"
    if score >= 35:
        return "LOW"
    return "WATCHLIST"


def calculate_conviction(row, market_regime="ACTIVE") -> dict:
    """
    Calculates conviction score for a single row.
    """
    rule_score, rule_note = score_rule_verdict(row.get("Rule Verdict", ""))
    exit_score, exit_note = score_exit_verdict(row.get("Exit Verdict", ""))
    risk_score_component, risk_note = score_risk_level(
        row.get("Risk Level", ""),
        row.get("Risk Score", 50),
    )
    engine_score, engine_note = score_engine_strength(row.get("Engine", ""))
    regime_score, regime_note = score_market_regime(market_regime)
    overlap_score, overlap_note = score_overlap(row)

    conviction_score = (
        rule_score
        + exit_score
        + risk_score_component
        + engine_score
        + regime_score
        + overlap_score
    )

    conviction_score = min(round(conviction_score, 2), 100)

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
            "avoid_freeze": 0,
        }

    levels = df["Conviction Level"].astype(str).str.upper()

    return {
        "high_conviction": int((levels == "HIGH CONVICTION").sum()),
        "strong": int((levels == "STRONG").sum()),
        "medium": int((levels == "MEDIUM").sum()),
        "low": int((levels == "LOW").sum()),
        "watchlist": int((levels == "WATCHLIST").sum()),
        "avoid_freeze": int((levels == "AVOID / FREEZE").sum()),
    }
