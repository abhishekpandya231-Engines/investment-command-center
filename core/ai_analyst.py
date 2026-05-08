"""
AI Analyst Layer v0.2
Investment Command Center

Purpose:
Converts system outputs into practical review queues.

Fix included:
- Prevents Analyst Priority Queue from showing NA for Conviction and Risk.
- Reads both legacy/simple columns and Stock Master View columns.
- Keeps old app.py function names compatible as much as possible.

This is rules-based decision support, not financial advice.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import pandas as pd


# --------------------------------------------------
# Helpers
# --------------------------------------------------
def _is_empty(value: Any) -> bool:
    try:
        if pd.isna(value):
            return True
    except Exception:
        pass
    return value is None or str(value).strip() == ""


def _safe_value(value: Any, default: str = "NA") -> Any:
    if _is_empty(value):
        return default
    return value


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        if pd.isna(value):
            return default
        if isinstance(value, str):
            value = value.replace(",", "").replace("%", "").strip()
            if value == "":
                return default
        return float(value)
    except Exception:
        return default


def _first_existing(row: Dict[str, Any], candidates: list[str], default: Any = "NA") -> Any:
    for col in candidates:
        if col in row and not _is_empty(row.get(col)):
            return row.get(col)
    return default


def _upper(value: Any) -> str:
    return str(_safe_value(value, "")).upper().strip()


def _score_from_row(row: Dict[str, Any]) -> float:
    return _safe_float(
        _first_existing(
            row,
            [
                "Analyst Score",
                "Priority Score",
                "Score",
                "Best Conviction Score",
                "Conviction Score",
                "Portfolio Compatibility Score",
                "Compatibility Score",
                "Final Score",
            ],
            0,
        ),
        0,
    )


def _conviction_from_row(row: Dict[str, Any]) -> str:
    return str(
        _first_existing(
            row,
            [
                "Conviction",
                "Best Conviction Level",
                "Conviction Level",
                "Master Conviction",
                "Master Conviction Level",
            ],
            "NA",
        )
    )


def _risk_from_row(row: Dict[str, Any]) -> str:
    return str(
        _first_existing(
            row,
            [
                "Risk",
                "Risk Level",
                "Worst Risk Level",
                "Best Risk Level",
                "Master Risk",
            ],
            "NA",
        )
    )


def _action_from_row(row: Dict[str, Any]) -> str:
    return str(
        _first_existing(
            row,
            [
                "Action",
                "Analyst Action",
                "Compatibility Action",
                "Portfolio Compatibility Action",
                "Final Allocation Action",
                "Position Action",
                "Master Allocation Action",
                "Master Action",
            ],
            "Review",
        )
    )


def _note_from_row(row: Dict[str, Any], fallback: str = "") -> str:
    return str(
        _first_existing(
            row,
            [
                "Analyst Note",
                "Priority Note",
                "Compatibility Note",
                "Portfolio Compatibility Notes",
                "Notes",
                "Reason",
                "Commentary",
            ],
            fallback or "Review for allocation only after portfolio concentration and liquidity checks.",
        )
    )


def _engine_from_row(row: Dict[str, Any]) -> str:
    return str(
        _first_existing(
            row,
            [
                "Engine",
                "Engines Present",
                "Primary Engine",
            ],
            "NA",
        )
    )


def _screener_from_row(row: Dict[str, Any]) -> str:
    return str(
        _first_existing(
            row,
            [
                "Screener",
                "Screeners Present",
                "Source Screener",
            ],
            "NA",
        )
    )


# --------------------------------------------------
# Market brief
# --------------------------------------------------
def create_market_analyst_brief(engine_a_score: Any = 0, market_regime: Any = "NA") -> Dict[str, Any]:
    score = _safe_float(engine_a_score, 0)
    regime = str(_safe_value(market_regime, "NA"))

    if score >= 70:
        tone = "Supportive"
        note = "Market gate is supportive. Fresh deployment may be considered only where stock-level risk and conviction are also aligned."
    elif score >= 50:
        tone = "Selective"
        note = "Market gate is neutral to selective. Prefer staged deployment and avoid weak risk-reward candidates."
    else:
        tone = "Defensive"
        note = "Market gate is defensive. Prioritise protection, review risk, and avoid aggressive fresh deployment."

    return {
        "Engine A Score": f"{int(score)}/100",
        "Market Regime": regime,
        "Analyst Tone": tone,
        "Action": tone,
        "Note": note,
    }


# Backward-compatible aliases
build_market_analyst_brief = create_market_analyst_brief
summarize_market_analyst = create_market_analyst_brief


# --------------------------------------------------
# Priority queue
# --------------------------------------------------
def create_analyst_priority_queue(
    stock_master_df: Optional[pd.DataFrame] = None,
    portfolio_compatibility_df: Optional[pd.DataFrame] = None,
    fresh_candidates_df: Optional[pd.DataFrame] = None,
    max_items: int = 10,
) -> pd.DataFrame:
    """
    Build Analyst Priority Queue.

    Priority order:
    1. Portfolio compatibility rows needing review.
    2. Fresh high-conviction / high-score candidates.
    3. Stock Master rows if no other queue is available.
    """

    rows: list[Dict[str, Any]] = []

    # 1) Portfolio compatibility queue
    if portfolio_compatibility_df is not None and not portfolio_compatibility_df.empty:
        for _, s in portfolio_compatibility_df.iterrows():
            row = s.to_dict()

            stock = _first_existing(row, ["Stock", "Name", "Symbol"], "Unknown")
            score = _score_from_row(row)
            conviction = _conviction_from_row(row)
            risk = _risk_from_row(row)
            action = _action_from_row(row)
            note = _note_from_row(row, "Review holding against current stock master view.")

            action_upper = _upper(action)
            risk_upper = _upper(risk)

            needs_review = (
                "REVIEW" in action_upper
                or "NOT IN CURRENT SYSTEM" in action_upper
                or "CONCENTRATION" in action_upper
                or risk_upper in ["HIGH", "CRITICAL"]
            )

            if needs_review:
                rows.append(
                    {
                        "Stock": stock,
                        "Conviction": conviction,
                        "Score": score,
                        "Action": action,
                        "Risk": risk,
                        "Engine": _engine_from_row(row),
                        "Screener": _screener_from_row(row),
                        "Analyst Note": note,
                        "Priority Type": "Portfolio Review",
                    }
                )

    # 2) Fresh candidates queue
    if fresh_candidates_df is not None and not fresh_candidates_df.empty:
        for _, s in fresh_candidates_df.iterrows():
            row = s.to_dict()

            stock = _first_existing(row, ["Stock", "Name", "Symbol"], "Unknown")
            score = _score_from_row(row)
            conviction = _conviction_from_row(row)
            risk = _risk_from_row(row)
            action = _action_from_row(row)

            if action == "Review":
                master_action = _upper(
                    _first_existing(
                        row,
                        ["Final Allocation Action", "Position Action", "Master Allocation Action", "Master Action"],
                        "",
                    )
                )
                if master_action:
                    action = master_action.title()

            note = _note_from_row(
                row,
                "Fresh candidate. Review only after liquidity, valuation, concentration, and risk checks.",
            )

            if score >= 75 or _upper(conviction) in ["HIGH CONVICTION", "STRONG"]:
                rows.append(
                    {
                        "Stock": stock,
                        "Conviction": conviction,
                        "Score": score,
                        "Action": action,
                        "Risk": risk,
                        "Engine": _engine_from_row(row),
                        "Screener": _screener_from_row(row),
                        "Analyst Note": note,
                        "Priority Type": "Fresh Candidate",
                    }
                )

    # 3) Fallback to Stock Master View
    if not rows and stock_master_df is not None and not stock_master_df.empty:
        for _, s in stock_master_df.iterrows():
            row = s.to_dict()

            stock = _first_existing(row, ["Stock", "Name", "Symbol"], "Unknown")
            score = _score_from_row(row)
            conviction = _conviction_from_row(row)
            risk = _risk_from_row(row)
            action = _action_from_row(row)

            note = _note_from_row(
                row,
                "Review for allocation only after portfolio concentration and liquidity checks.",
            )

            rows.append(
                {
                    "Stock": stock,
                    "Conviction": conviction,
                    "Score": score,
                    "Action": action,
                    "Risk": risk,
                    "Engine": _engine_from_row(row),
                    "Screener": _screener_from_row(row),
                    "Analyst Note": note,
                    "Priority Type": "Stock Master Candidate",
                }
            )

    if not rows:
        return pd.DataFrame(
            columns=[
                "Stock",
                "Conviction",
                "Score",
                "Action",
                "Risk",
                "Engine",
                "Screener",
                "Analyst Note",
                "Priority Type",
            ]
        )

    df = pd.DataFrame(rows)

    # Clean final output
    for col in ["Conviction", "Action", "Risk", "Engine", "Screener", "Analyst Note", "Priority Type"]:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: _safe_value(x, "NA"))

    if "Score" in df.columns:
        df["Score"] = df["Score"].apply(lambda x: int(round(_safe_float(x, 0))))

    # Prefer meaningful rows first
    df["_risk_rank"] = df["Risk"].astype(str).str.upper().map(
        {
            "CRITICAL": 4,
            "HIGH": 3,
            "MODERATE": 2,
            "LOW": 1,
            "NA": 0,
        }
    ).fillna(0)

    df["_conviction_rank"] = df["Conviction"].astype(str).str.upper().map(
        {
            "HIGH CONVICTION": 4,
            "STRONG": 3,
            "MEDIUM": 2,
            "WATCHLIST": 1,
            "LOW": 1,
            "NA": 0,
        }
    ).fillna(0)

    df = df.sort_values(
        ["_risk_rank", "_conviction_rank", "Score"],
        ascending=[False, False, False],
    ).drop(columns=["_risk_rank", "_conviction_rank"])

    return df.head(max_items).reset_index(drop=True)


# Backward-compatible aliases
build_analyst_priority_queue = create_analyst_priority_queue
generate_analyst_priority_queue = create_analyst_priority_queue
get_analyst_priority_queue = create_analyst_priority_queue


# --------------------------------------------------
# Risk queue
# --------------------------------------------------
def create_analyst_risk_queue(
    risk_df: Optional[pd.DataFrame] = None,
    max_items: int = 10,
) -> pd.DataFrame:
    """Build AI Analyst risk queue."""
    if risk_df is None or risk_df.empty:
        return pd.DataFrame()

    rows = []

    for _, s in risk_df.iterrows():
        row = s.to_dict()
        risk = _risk_from_row(row)
        risk_upper = _upper(risk)

        if risk_upper not in ["HIGH", "CRITICAL", "MODERATE"]:
            continue

        stock = _first_existing(row, ["Stock", "Name", "Symbol"], "Unknown")
        score = _safe_float(
            _first_existing(row, ["Risk Score", "Score", "Total Risk Score"], 0),
            0,
        )

        rows.append(
            {
                "Stock": stock,
                "Risk Level": risk,
                "Risk Score": int(round(score)),
                "Exit Verdict": _first_existing(row, ["Exit Verdict", "Exit Verdicts"], "NA"),
                "Rule Verdict": _first_existing(row, ["Rule Verdict", "Verdict"], "NA"),
                "Engine": _engine_from_row(row),
                "Analyst Note": _note_from_row(
                    row,
                    "Review valuation, trend, leverage, and exit verdict before deployment.",
                ),
            }
        )

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df["_risk_rank"] = df["Risk Level"].astype(str).str.upper().map(
        {"CRITICAL": 3, "HIGH": 2, "MODERATE": 1}
    ).fillna(0)
    df = df.sort_values(["_risk_rank", "Risk Score"], ascending=[False, False])
    return df.drop(columns=["_risk_rank"]).head(max_items).reset_index(drop=True)


build_analyst_risk_queue = create_analyst_risk_queue
generate_analyst_risk_queue = create_analyst_risk_queue


# --------------------------------------------------
# Portfolio health
# --------------------------------------------------
def create_portfolio_health_snapshot(portfolio_df: Optional[pd.DataFrame]) -> Dict[str, Any]:
    """Create a simple portfolio health snapshot."""
    if portfolio_df is None or portfolio_df.empty:
        return {
            "Invested Value": "₹0",
            "Current Value": "₹0",
            "Unrealised P&L": "₹0 (0.00%)",
            "Holdings": 0,
            "Note": "Upload portfolio file to generate portfolio health snapshot.",
        }

    df = portfolio_df.copy()

    if "Invested Value" in df.columns:
        invested = df["Invested Value"].apply(_safe_float).sum()
    elif "Quantity" in df.columns and "Buy Price" in df.columns:
        invested = (df["Quantity"].apply(_safe_float) * df["Buy Price"].apply(_safe_float)).sum()
    else:
        invested = 0.0

    if "Current Value" in df.columns:
        current = df["Current Value"].apply(_safe_float).sum()
    elif "Position Value" in df.columns:
        current = df["Position Value"].apply(_safe_float).sum()
    elif "Quantity" in df.columns and "Current Price" in df.columns:
        current = (df["Quantity"].apply(_safe_float) * df["Current Price"].apply(_safe_float)).sum()
    else:
        current = 0.0

    pnl = current - invested
    pnl_pct = (pnl / invested * 100) if invested else 0.0

    return {
        "Invested Value": f"₹{invested:,.0f}",
        "Current Value": f"₹{current:,.0f}",
        "Unrealised P&L": f"₹{pnl:,.0f} ({pnl_pct:.2f}%)",
        "Holdings": int(len(df)),
        "Note": "Portfolio view should be interpreted with concentration risk, sector exposure, and compatibility output.",
    }


build_portfolio_health_snapshot = create_portfolio_health_snapshot
summarize_portfolio_health = create_portfolio_health_snapshot
