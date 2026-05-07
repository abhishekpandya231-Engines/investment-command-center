"""
Risk Engine v0.1
Investment Command Center

Purpose:
Creates portfolio and screener-level risk diagnostics.

This is not a prediction engine.
It is a risk-control layer.

Core outputs:
- Risk level: LOW / MODERATE / HIGH / CRITICAL
- Risk notes
- Concentration flags
- Quality flags
- Valuation flags
- Debt flags
"""

import pandas as pd


def safe_float(value, default=None):
    """Safely convert a value to float."""
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def classify_risk_level(score: int) -> str:
    """
    Converts numeric risk score into label.
    """
    if score >= 80:
        return "CRITICAL"
    if score >= 60:
        return "HIGH"
    if score >= 35:
        return "MODERATE"
    return "LOW"


def evaluate_stock_risk(row) -> dict:
    """
    Evaluates risk for a single stock row.
    Works with Trendlyne screener data or portfolio rows.
    """
    risk_score = 0
    notes = []

    stock = row.get("Stock", "Unknown")
    engine = str(row.get("Engine", "")).upper().strip()

    market_cap_category = str(row.get("Market Cap Category", "")).lower().strip()
    pe = safe_float(row.get("PE TTM"))
    peg = safe_float(row.get("PEG TTM"))
    roe = safe_float(row.get("ROE Ann  %"))
    pio = safe_float(row.get("Piotroski Score"))
    debt = safe_float(row.get("Total Debt to Total Equity Ann "))
    durability = safe_float(row.get("Durability Score"))
    momentum = safe_float(row.get("Momentum Score"))
    profit_growth = safe_float(row.get("Net Profit Ann  YoY Growth %"))
    revenue_growth = safe_float(row.get("Revenue QoQ Growth %"))
    portfolio_weight = safe_float(row.get("Portfolio Weight %"))

    # Market-cap risk
    if market_cap_category == "small cap":
        risk_score += 15
        notes.append("Small-cap exposure: higher volatility and liquidity risk.")
    elif market_cap_category == "mid cap":
        risk_score += 8
        notes.append("Mid-cap exposure: moderate volatility risk.")

    # Concentration risk
    if portfolio_weight is not None:
        if portfolio_weight > 15:
            risk_score += 25
            notes.append(f"Very high single-stock weight: {portfolio_weight:.1f}%.")
        elif portfolio_weight > 10:
            risk_score += 15
            notes.append(f"High single-stock weight: {portfolio_weight:.1f}%.")

    # Debt risk
    if debt is not None:
        if debt > 2:
            risk_score += 25
            notes.append(f"Debt/Equity is very high at {debt:.2f}.")
        elif debt > 1:
            risk_score += 15
            notes.append(f"Debt/Equity is elevated at {debt:.2f}.")
        elif debt < 0:
            risk_score += 5
            notes.append("Debt/Equity value appears unusual; verify data.")

    # Profitability risk
    if roe is not None:
        if roe < 8:
            risk_score += 20
            notes.append(f"ROE is weak at {roe:.1f}%.")
        elif roe < 12:
            risk_score += 10
            notes.append(f"ROE is moderate at {roe:.1f}%.")

    # Piotroski risk
    if pio is not None:
        if pio <= 3:
            risk_score += 25
            notes.append(f"Piotroski Score is weak at {pio:.0f}.")
        elif pio <= 5:
            risk_score += 12
            notes.append(f"Piotroski Score is average at {pio:.0f}.")

    # Valuation risk
    if pe is not None:
        if pe > 60:
            risk_score += 25
            notes.append(f"PE is very high at {pe:.1f}.")
        elif pe > 40:
            risk_score += 15
            notes.append(f"PE is elevated at {pe:.1f}.")
        elif pe < 0:
            risk_score += 20
            notes.append("Negative PE indicates loss-making or unusual earnings.")

    if peg is not None:
        if peg > 3:
            risk_score += 15
            notes.append(f"PEG is expensive at {peg:.2f}.")
        elif peg < 0:
            risk_score += 10
            notes.append("Negative PEG; verify growth/earnings quality.")

    # Momentum / DVM risk for Engine B
    if engine == "B":
        if durability is not None and durability < 45:
            risk_score += 25
            notes.append(f"Durability is weak at {durability:.1f}.")
        if momentum is not None and momentum < 49:
            risk_score += 25
            notes.append(f"Momentum is weak at {momentum:.1f}.")
        if durability is not None and momentum is not None:
            if 45 <= durability <= 55 or 49 <= momentum <= 59:
                risk_score += 10
                notes.append("DVM is in grey zone; momentum setup needs monitoring.")

    # Growth risk for C/D
    if engine in ["C", "D"]:
        if profit_growth is not None and profit_growth < 0:
            risk_score += 15
            notes.append(f"Profit growth is negative at {profit_growth:.1f}%.")
        if revenue_growth is not None and revenue_growth < 0:
            risk_score += 10
            notes.append(f"Revenue growth is negative at {revenue_growth:.1f}%.")

    if not notes:
        notes.append("No major stock-level risk flags detected.")

    risk_score = min(risk_score, 100)

    return {
        "Stock": stock,
        "Risk Score": risk_score,
        "Risk Level": classify_risk_level(risk_score),
        "Risk Notes": " | ".join(notes),
    }


def apply_stock_risk(df: pd.DataFrame) -> pd.DataFrame:
    """
    Applies stock-level risk evaluation to a dataframe.
    """
    df = df.copy()

    risk_results = df.apply(evaluate_stock_risk, axis=1)

    df["Risk Score"] = risk_results.apply(lambda result: result["Risk Score"])
    df["Risk Level"] = risk_results.apply(lambda result: result["Risk Level"])
    df["Risk Notes"] = risk_results.apply(lambda result: result["Risk Notes"])

    return df


def evaluate_screener_risk_summary(df: pd.DataFrame) -> dict:
    """
    Summarizes risk from a screener dataframe.
    """
    if df.empty:
        return {
            "total_rows": 0,
            "critical_count": 0,
            "high_count": 0,
            "moderate_count": 0,
            "low_count": 0,
            "small_cap_count": 0,
            "high_debt_count": 0,
            "expensive_count": 0,
        }

    risk_df = apply_stock_risk(df)

    market_cap_series = risk_df.get("Market Cap Category", pd.Series(dtype=str)).astype(str).str.lower()

    debt_series = pd.to_numeric(
        risk_df.get("Total Debt to Total Equity Ann ", pd.Series(dtype=float)),
        errors="coerce"
    )

    pe_series = pd.to_numeric(
        risk_df.get("PE TTM", pd.Series(dtype=float)),
        errors="coerce"
    )

    return {
        "total_rows": len(risk_df),
        "critical_count": int((risk_df["Risk Level"] == "CRITICAL").sum()),
        "high_count": int((risk_df["Risk Level"] == "HIGH").sum()),
        "moderate_count": int((risk_df["Risk Level"] == "MODERATE").sum()),
        "low_count": int((risk_df["Risk Level"] == "LOW").sum()),
        "small_cap_count": int((market_cap_series == "small cap").sum()),
        "high_debt_count": int((debt_series > 1).sum()),
        "expensive_count": int((pe_series > 40).sum()),
    }


def evaluate_portfolio_risk_summary(df: pd.DataFrame) -> dict:
    """
    Summarizes portfolio-level risk from holdings data.
    Expects Current Value and Portfolio Weight % if available.
    """
    if df.empty:
        return {
            "portfolio_risk_level": "LOW",
            "risk_score": 0,
            "notes": ["No holdings found."],
        }

    risk_score = 0
    notes = []

    # Single stock concentration
    if "Portfolio Weight %" in df.columns:
        max_weight = pd.to_numeric(df["Portfolio Weight %"], errors="coerce").max()

        if max_weight > 20:
            risk_score += 30
            notes.append(f"Maximum stock weight is {max_weight:.1f}%, very concentrated.")
        elif max_weight > 10:
            risk_score += 15
            notes.append(f"Maximum stock weight is {max_weight:.1f}%, above 10% threshold.")

    # Sector concentration
    if "Sector" in df.columns and "Current Value" in df.columns:
        sector_df = df.groupby("Sector", as_index=False)["Current Value"].sum()
        total_value = sector_df["Current Value"].sum()

        if total_value > 0:
            sector_df["Sector Weight %"] = sector_df["Current Value"] / total_value * 100
            max_sector = sector_df["Sector Weight %"].max()

            if max_sector > 40:
                risk_score += 30
                notes.append(f"Top sector weight is {max_sector:.1f}%, very concentrated.")
            elif max_sector > 30:
                risk_score += 15
                notes.append(f"Top sector weight is {max_sector:.1f}%, above 30% threshold.")

    # Small-cap load
    if "Market Cap Category" in df.columns and "Current Value" in df.columns:
        mcap_df = df.groupby("Market Cap Category", as_index=False)["Current Value"].sum()
        total_value = mcap_df["Current Value"].sum()

        if total_value > 0:
            mcap_df["Market Cap Weight %"] = mcap_df["Current Value"] / total_value * 100
            small_rows = mcap_df[mcap_df["Market Cap Category"].astype(str).str.lower() == "small cap"]

            if not small_rows.empty:
                small_weight = small_rows.iloc[0]["Market Cap Weight %"]

                if small_weight > 60:
                    risk_score += 30
                    notes.append(f"Small-cap weight is {small_weight:.1f}%, very high.")
                elif small_weight > 50:
                    risk_score += 20
                    notes.append(f"Small-cap weight is {small_weight:.1f}%, above 50% threshold.")

    # Stock-level risk
    risk_df = apply_stock_risk(df)
    high_or_critical = risk_df[risk_df["Risk Level"].isin(["HIGH", "CRITICAL"])]

    if len(high_or_critical) >= 5:
        risk_score += 25
        notes.append(f"{len(high_or_critical)} holdings are HIGH/CRITICAL risk.")
    elif len(high_or_critical) > 0:
        risk_score += 10
        notes.append(f"{len(high_or_critical)} holdings are HIGH/CRITICAL risk.")

    if not notes:
        notes.append("No major portfolio-level risk flags detected.")

    risk_score = min(risk_score, 100)

    return {
        "portfolio_risk_level": classify_risk_level(risk_score),
        "risk_score": risk_score,
        "notes": notes,
    }
