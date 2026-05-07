"""
Engine A Market Gate v0.2
Investment Command Center

Purpose:
Converts market inputs into a 0-100 market score and regime.

v0.2 upgrade:
- Adds India Rates / G-sec component.
- Rebalances Engine A to total 100 points.

Component weights:
Valuation 15
Trend 15
Breadth 12
Volatility 10
Flows 12
Macro 10
India Rates / G-sec 10
Global 8
Crude 8
Total 100
"""


def safe_float(value, default=0):
    """Safely converts a value to float."""
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def score_valuation(nifty_pe):
    """
    Valuation score out of 15.
    Lower PE = better valuation.
    """
    pe = safe_float(nifty_pe, default=22)

    if pe <= 18:
        return 15
    if pe <= 20:
        return 12
    if pe <= 22:
        return 9
    if pe <= 24:
        return 6
    if pe <= 26:
        return 3
    return 0


def score_trend(nifty_above_200dma):
    """
    Trend score out of 15.
    Input should be Yes/No or True/False.
    """
    value = str(nifty_above_200dma).lower().strip()

    if value in ["yes", "true", "1", "above"]:
        return 15

    return 3


def score_breadth(percent_stocks_above_200dma):
    """
    Breadth score out of 12.
    """
    breadth = safe_float(percent_stocks_above_200dma, default=50)

    if breadth >= 70:
        return 12
    if breadth >= 60:
        return 10
    if breadth >= 50:
        return 8
    if breadth >= 40:
        return 5
    if breadth >= 30:
        return 3
    return 0


def score_volatility(india_vix):
    """
    Volatility score out of 10.
    Lower VIX = better score.
    """
    vix = safe_float(india_vix, default=15)

    if vix <= 12:
        return 10
    if vix <= 15:
        return 8
    if vix <= 18:
        return 6
    if vix <= 22:
        return 3
    if vix <= 25:
        return 1
    return 0


def score_flows(fii_30d, dii_30d):
    """
    Flows score out of 12.
    Uses net FII + DII 30-day flow.
    Values expected in Rs crore.
    """
    fii = safe_float(fii_30d, default=0)
    dii = safe_float(dii_30d, default=0)
    net_flow = fii + dii

    if net_flow >= 30000:
        return 12
    if net_flow >= 15000:
        return 10
    if net_flow >= 0:
        return 8
    if net_flow >= -10000:
        return 5
    if net_flow >= -25000:
        return 2
    return 0


def score_macro(rbi_stance, cpi, pmi):
    """
    Macro score out of 10.
    Combines RBI stance, CPI and PMI.
    """
    score = 0

    stance = str(rbi_stance).lower().strip()
    cpi_value = safe_float(cpi, default=5)
    pmi_value = safe_float(pmi, default=52)

    # RBI stance: max 3
    if stance in ["accommodative", "dovish"]:
        score += 3
    elif stance in ["neutral"]:
        score += 2
    elif stance in ["withdrawal", "tightening", "hawkish"]:
        score += 1
    else:
        score += 1

    # CPI: max 3
    if cpi_value <= 4.5:
        score += 3
    elif cpi_value <= 5.5:
        score += 2
    elif cpi_value <= 6.5:
        score += 1
    else:
        score += 0

    # PMI: max 4
    if pmi_value >= 56:
        score += 4
    elif pmi_value >= 52:
        score += 3
    elif pmi_value >= 50:
        score += 1
    else:
        score += 0

    return min(score, 10)


def score_india_rates(india_10y_gsec, india_10y_gsec_30d_change_bps):
    """
    India Rates / G-sec score out of 10.

    Inputs:
    - india_10y_gsec: current Indian 10Y G-sec yield in %
    - india_10y_gsec_30d_change_bps: 30-day change in basis points

    Lower yields and falling/stable yields are better for equities.
    """
    yield_value = safe_float(india_10y_gsec, default=7.1)
    change_bps = safe_float(india_10y_gsec_30d_change_bps, default=0)

    # Yield level: max 7
    if yield_value <= 6.75:
        score = 7
    elif yield_value <= 7.10:
        score = 6
    elif yield_value <= 7.40:
        score = 4
    elif yield_value <= 7.75:
        score = 2
    else:
        score = 0

    # Yield direction: max 3
    if change_bps <= -15:
        score += 3
    elif change_bps <= 10:
        score += 2
    elif change_bps <= 25:
        score += 1
    else:
        score += 0

    return min(score, 10)


def score_global(us_10y, dxy, inr_change_percent):
    """
    Global score out of 8.
    Lower US10Y, softer DXY and stable INR are better.
    """
    score = 0

    us10y = safe_float(us_10y, default=4.3)
    dxy_value = safe_float(dxy, default=104)
    inr_change = safe_float(inr_change_percent, default=0)

    # US 10Y: max 3
    if us10y <= 4.0:
        score += 3
    elif us10y <= 4.5:
        score += 2
    elif us10y <= 5.0:
        score += 1
    else:
        score += 0

    # DXY: max 3
    if dxy_value <= 102:
        score += 3
    elif dxy_value <= 105:
        score += 2
    elif dxy_value <= 108:
        score += 1
    else:
        score += 0

    # INR change: max 2
    # Negative means INR appreciation; positive means INR depreciation.
    if inr_change <= 0:
        score += 2
    elif inr_change <= 1:
        score += 1
    else:
        score += 0

    return min(score, 8)


def score_crude(brent_crude):
    """
    Crude score out of 8.
    Lower crude is better for India.
    """
    crude = safe_float(brent_crude, default=80)

    if crude <= 70:
        return 8
    if crude <= 80:
        return 7
    if crude <= 90:
        return 5
    if crude <= 100:
        return 3
    if crude <= 110:
        return 1
    return 0


def calculate_engine_a_score(inputs):
    """
    Main Engine A calculation.
    """

    component_scores = {
        "Valuation": score_valuation(inputs.get("nifty_pe")),
        "Trend": score_trend(inputs.get("nifty_above_200dma")),
        "Breadth": score_breadth(inputs.get("percent_stocks_above_200dma")),
        "Volatility": score_volatility(inputs.get("india_vix")),
        "Flows": score_flows(inputs.get("fii_30d"), inputs.get("dii_30d")),
        "Macro": score_macro(inputs.get("rbi_stance"), inputs.get("cpi"), inputs.get("pmi")),
        "India Rates / G-sec": score_india_rates(
            inputs.get("india_10y_gsec"),
            inputs.get("india_10y_gsec_30d_change_bps"),
        ),
        "Global": score_global(inputs.get("us_10y"), inputs.get("dxy"), inputs.get("inr_change_percent")),
        "Crude": score_crude(inputs.get("brent_crude")),
    }

    raw_score = sum(component_scores.values())

    safety_overrides = generate_safety_overrides(inputs, component_scores)
    regime_details = classify_engine_a_regime(raw_score, safety_overrides)

    return {
        "score": raw_score,
        "component_scores": component_scores,
        "safety_overrides": safety_overrides,
        "regime": regime_details["regime"],
        "equity_allocation_percent": regime_details["equity_allocation_percent"],
        "debt_allocation_percent": regime_details["debt_allocation_percent"],
        "gold_allocation_percent": regime_details["gold_allocation_percent"],
        "action": regime_details["action"],
    }


def generate_safety_overrides(inputs, component_scores):
    """
    Applies safety override flags.
    """
    overrides = []

    trend_score = component_scores.get("Trend", 0)
    volatility_score = component_scores.get("Volatility", 0)
    flows_score = component_scores.get("Flows", 0)
    india_rates_score = component_scores.get("India Rates / G-sec", 0)

    fii_30d = safe_float(inputs.get("fii_30d"), default=0)
    nifty_pe = safe_float(inputs.get("nifty_pe"), default=22)
    india_vix = safe_float(inputs.get("india_vix"), default=15)
    india_10y_gsec = safe_float(inputs.get("india_10y_gsec"), default=7.1)
    india_10y_change = safe_float(inputs.get("india_10y_gsec_30d_change_bps"), default=0)

    if trend_score <= 3 and volatility_score <= 2 and (flows_score <= 3 or fii_30d < -15000):
        overrides.append({
            "name": "Red Flag",
            "action": "Cap equity at 25%",
            "severity": "High",
        })

    if nifty_pe > 26:
        overrides.append({
            "name": "PE Bubble",
            "action": "Cap equity at 70%",
            "severity": "Medium",
        })

    if india_vix > 25:
        overrides.append({
            "name": "VIX Spike",
            "action": "Reduce all position sizes by 30%",
            "severity": "High",
        })

    if india_10y_gsec > 7.75 or india_10y_change > 35:
        overrides.append({
            "name": "India Rates Stress",
            "action": "Avoid aggressive allocation; tighten growth-stock risk",
            "severity": "Medium",
        })

    if india_rates_score <= 2 and nifty_pe > 24:
        overrides.append({
            "name": "Valuation-Rates Mismatch",
            "action": "High valuation with high rates; cap equity at 55%",
            "severity": "High",
        })

    return overrides


def classify_engine_a_regime(score, safety_overrides=None):
    """
    Converts score into market regime and allocation bands.
    """
    if safety_overrides is None:
        safety_overrides = []

    if score <= 20:
        regime = "EXIT"
        equity = 10
        debt = 65
        gold = 25
        action = "Exit equity risk. No new buys."

    elif score <= 30:
        regime = "FREEZE"
        equity = 25
        debt = 50
        gold = 25
        action = "No new equity buys. Hold or exit only."

    elif score <= 40:
        regime = "CAUTIOUS"
        equity = 40
        debt = 40
        gold = 20
        action = "Reduced position sizing only."

    elif score <= 52:
        regime = "ACTIVE"
        equity = 55
        debt = 30
        gold = 15
        action = "Normal deployment allowed."

    elif score <= 62:
        regime = "AGGRESSIVE"
        equity = 70
        debt = 20
        gold = 10
        action = "Full deployment allowed."

    else:
        regime = "FULL DEPLOY"
        equity = 85
        debt = 10
        gold = 5
        action = "Maximum allocation allowed, subject to risk controls."

    # Apply overrides
    for override in safety_overrides:
        if override["name"] == "Red Flag":
            equity = min(equity, 25)
            debt = max(debt, 50)
            gold = max(gold, 25)
            action = "Red Flag override active. Equity capped at 25%."

        if override["name"] == "PE Bubble":
            equity = min(equity, 70)
            action = f"{action} PE Bubble override active."

        if override["name"] == "Valuation-Rates Mismatch":
            equity = min(equity, 55)
            debt = max(debt, 30)
            action = "Valuation-Rates Mismatch active. Equity capped at 55%."

    return {
        "regime": regime,
        "equity_allocation_percent": equity,
        "debt_allocation_percent": debt,
        "gold_allocation_percent": gold,
        "action": action,
    }


def default_engine_a_inputs():
    """
    Default placeholder inputs.
    User can change these inside Streamlit.
    """
    return {
        "nifty_pe": 22.0,
        "nifty_above_200dma": "Yes",
        "percent_stocks_above_200dma": 55.0,
        "india_vix": 15.0,
        "fii_30d": 0.0,
        "dii_30d": 10000.0,
        "rbi_stance": "Neutral",
        "cpi": 4.8,
        "pmi": 55.0,
        "india_10y_gsec": 7.1,
        "india_10y_gsec_30d_change_bps": 0.0,
        "us_10y": 4.3,
        "dxy": 104.0,
        "inr_change_percent": 0.5,
        "brent_crude": 85.0,
    }
