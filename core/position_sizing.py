"""
Position Sizing Engine v0.2
Investment Command Center

Purpose:
Converts signal quality, market regime, exit verdict, risk level, and conviction level
into a suggested position-size band.

v0.2 upgrade:
- Uses Conviction Score and Conviction Level.
- Makes sizing stricter for Medium/Low/Watchlist names.
- Caps High Risk, GUARD, TRIM, and single-signal candidates.
- Keeps capital allocation discipline separate from stock selection.

Outputs:
- Suggested Position Size %
- Max Position Cap %
- Position Action
- Position Sizing Reason
"""


def safe_float(value, default=0):
    """Safely converts a value to float."""
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def normalize_text(value):
    """Normalize text inputs."""
    return str(value).upper().strip()


def get_regime_multiplier(market_regime: str) -> float:
    """
    Converts Engine A regime into deployment multiplier.
    """
    regime = normalize_text(market_regime)

    if regime == "FULL DEPLOY":
        return 1.00
    if regime == "AGGRESSIVE":
        return 0.85
    if regime == "ACTIVE":
        return 0.70
    if regime == "CAUTIOUS":
        return 0.45
    if regime == "FREEZE":
        return 0.15
    if regime == "EXIT":
        return 0.00

    return 0.50


def get_exit_verdict_multiplier(exit_verdict: str) -> float:
    """
    Converts Exit Engine verdict into sizing multiplier.
    """
    verdict = normalize_text(exit_verdict)

    if verdict == "RIDE":
        return 1.00
    if verdict == "TRIM":
        return 0.45
    if verdict == "GUARD":
        return 0.20
    if verdict == "FREEZE":
        return 0.05
    if verdict == "EXIT":
        return 0.00

    return 0.30


def get_risk_multiplier(risk_level: str, risk_score) -> float:
    """
    Converts Risk Engine output into sizing multiplier.
    """
    level = normalize_text(risk_level)
    score = safe_float(risk_score, default=50)

    if level == "LOW":
        return 1.00
    if level == "MODERATE":
        if score >= 50:
            return 0.50
        return 0.65
    if level == "HIGH":
        return 0.25
    if level == "CRITICAL":
        return 0.00

    return 0.50


def get_conviction_multiplier(conviction_level: str, conviction_score) -> float:
    """
    Converts Conviction Engine output into sizing multiplier.
    This is the main v0.2 improvement.
    """
    level = normalize_text(conviction_level)
    score = safe_float(conviction_score, default=50)

    if level == "HIGH CONVICTION":
        return 1.00
    if level == "STRONG":
        return 0.80
    if level == "MEDIUM":
        if score >= 65:
            return 0.55
        return 0.45
    if level == "LOW":
        return 0.20
    if level == "TACTICAL ONLY":
        return 0.25
    if level == "WATCHLIST":
        return 0.00
    if level == "AVOID / FREEZE":
        return 0.00

    return 0.35


def get_engine_base_position(engine: str, rule_verdict: str) -> float:
    """
    Base max position before regime/risk/conviction modifiers.

    Philosophy:
    - Engine D compounders can carry larger positions if risk and conviction support it.
    - Engine C value names get moderate sizing.
    - Engine B momentum names are sized smaller due to volatility.
    """
    engine_value = normalize_text(engine)
    verdict = normalize_text(rule_verdict)

    if engine_value == "D":
        if "COMPOUNDER QUALIFIED" in verdict:
            return 5.00
        if "GROWTH QUALIFIED" in verdict:
            return 4.00
        return 2.50

    if engine_value == "C":
        if "VALUE QUALIFIED" in verdict:
            return 4.00
        return 2.25

    if engine_value == "B":
        if "GREEN GATE" in verdict:
            return 2.75
        if "GREY GATE" in verdict:
            return 1.25
        return 0.75

    return 1.00


def get_absolute_cap(risk_level: str, conviction_level: str, exit_verdict: str) -> float:
    """
    Absolute position cap after all multipliers.
    This prevents high-risk / low-conviction names from getting oversized.
    """
    risk = normalize_text(risk_level)
    conviction = normalize_text(conviction_level)
    exit_value = normalize_text(exit_verdict)

    if exit_value == "EXIT":
        return 0.00
    if exit_value == "FREEZE":
        return 0.00
    if conviction in ["WATCHLIST", "AVOID / FREEZE"]:
        return 0.00
    if risk == "CRITICAL":
        return 0.00

    if exit_value == "GUARD":
        return 0.75
    if exit_value == "TRIM":
        return 1.25

    if risk == "HIGH":
        return 1.00
    if risk == "MODERATE":
        if conviction == "HIGH CONVICTION":
            return 2.50
        if conviction == "STRONG":
            return 2.00
        return 1.25

    if conviction == "HIGH CONVICTION":
        return 5.00
    if conviction == "STRONG":
        return 3.50
    if conviction == "MEDIUM":
        return 1.75
    if conviction == "LOW":
        return 0.75

    return 1.00


def classify_position_action(suggested_position: float, exit_verdict: str, risk_level: str, conviction_level: str) -> str:
    """
    Converts final position size into action label.
    """
    verdict = normalize_text(exit_verdict)
    risk = normalize_text(risk_level)
    conviction = normalize_text(conviction_level)

    if verdict == "EXIT":
        return "NO POSITION / EXIT"
    if verdict == "FREEZE":
        return "NO FRESH BUY"
    if risk == "CRITICAL":
        return "AVOID"
    if conviction in ["WATCHLIST", "AVOID / FREEZE"]:
        return "TRACK ONLY"
    if suggested_position <= 0:
        return "TRACK ONLY"
    if suggested_position < 1:
        return "TRACK ONLY"
    if suggested_position < 2:
        return "STARTER POSITION"
    if suggested_position < 4:
        return "NORMAL POSITION"
    return "HIGH CONVICTION POSITION"


def calculate_position_size(row, engine_a_score=50, market_regime="ACTIVE") -> dict:
    """
    Calculates suggested position size for a single stock row.
    """
    engine = row.get("Engine", "Unknown")
    rule_verdict = row.get("Rule Verdict", "Unknown")
    exit_verdict = row.get("Exit Verdict", "GUARD")
    risk_level = row.get("Risk Level", "MODERATE")
    risk_score = row.get("Risk Score", 50)
    conviction_level = row.get("Conviction Level", "MEDIUM")
    conviction_score = row.get("Conviction Score", 50)

    base_position = get_engine_base_position(engine, rule_verdict)
    regime_multiplier = get_regime_multiplier(market_regime)
    exit_multiplier = get_exit_verdict_multiplier(exit_verdict)
    risk_multiplier = get_risk_multiplier(risk_level, risk_score)
    conviction_multiplier = get_conviction_multiplier(conviction_level, conviction_score)

    raw_position = (
        base_position
        * regime_multiplier
        * exit_multiplier
        * risk_multiplier
        * conviction_multiplier
    )

    max_cap = get_absolute_cap(risk_level, conviction_level, exit_verdict)
    suggested_position = min(round(raw_position, 2), max_cap)

    action = classify_position_action(
        suggested_position,
        exit_verdict,
        risk_level,
        conviction_level,
    )

    reason_parts = [
        f"Base {base_position:.2f}% from Engine {engine} and rule verdict.",
        f"Conviction {conviction_level} with multiplier {conviction_multiplier:.2f}.",
        f"Market regime multiplier {regime_multiplier:.2f}.",
        f"Exit verdict multiplier {exit_multiplier:.2f}.",
        f"Risk multiplier {risk_multiplier:.2f}.",
        f"Absolute cap {max_cap:.2f}%."
    ]

    return {
        "Suggested Position Size %": suggested_position,
        "Max Position Cap %": max_cap,
        "Position Action": action,
        "Position Sizing Reason": " ".join(reason_parts),
    }


def apply_position_sizing(df, engine_a_score=50, market_regime="ACTIVE"):
    """
    Applies position sizing engine to a dataframe.
    """
    df = df.copy()

    sizing_results = df.apply(
        lambda row: calculate_position_size(
            row,
            engine_a_score=engine_a_score,
            market_regime=market_regime,
        ),
        axis=1,
    )

    df["Suggested Position Size %"] = sizing_results.apply(
        lambda result: result["Suggested Position Size %"]
    )
    df["Max Position Cap %"] = sizing_results.apply(
        lambda result: result["Max Position Cap %"]
    )
    df["Position Action"] = sizing_results.apply(
        lambda result: result["Position Action"]
    )
    df["Position Sizing Reason"] = sizing_results.apply(
        lambda result: result["Position Sizing Reason"]
    )

    return df


def summarize_position_sizing(df):
    """
    Summarizes position sizing actions.
    """
    if df.empty or "Position Action" not in df.columns:
        return {
            "total_rows": 0,
            "track_only": 0,
            "starter_position": 0,
            "normal_position": 0,
            "high_conviction_position": 0,
            "avoid_or_exit": 0,
        }

    action_series = df["Position Action"].astype(str).str.upper()

    return {
        "total_rows": len(df),
        "track_only": int(action_series.str.contains("TRACK ONLY").sum()),
        "starter_position": int(action_series.str.contains("STARTER POSITION").sum()),
        "normal_position": int(action_series.str.contains("NORMAL POSITION").sum()),
        "high_conviction_position": int(action_series.str.contains("HIGH CONVICTION POSITION").sum()),
        "avoid_or_exit": int(
            action_series.str.contains("AVOID").sum()
            + action_series.str.contains("EXIT").sum()
            + action_series.str.contains("NO POSITION").sum()
        ),
    }
