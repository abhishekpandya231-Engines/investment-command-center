"""
Portfolio Compatibility Engine v0.2
Investment Command Center

Purpose:
Compares current portfolio holdings against Stock Master View.

Fix included:
- Adds both legacy column names and AI Analyst column names.
- Prevents Compatibility Analyst cards from showing NA when portfolio holdings
  are matched with Stock Master View.
- Uses robust stock-name matching.
- Keeps old app.py calls compatible.

This is a rules-based decision-support layer, not financial advice.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

import pandas as pd


# --------------------------------------------------
# Basic helpers
# --------------------------------------------------
def normalize_text(value: Any) -> str:
    """Normalize text values for rule checks."""
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    return str(value).upper().strip()


def safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert a value to float."""
    try:
        if value is None:
            return default
        if pd.isna(value):
            return default
        if isinstance(value, str):
            cleaned = value.replace(",", "").replace("%", "").strip()
            if cleaned == "":
                return default
            return float(cleaned)
        return float(value)
    except Exception:
        return default


def safe_value(value: Any, default: str = "NA") -> Any:
    """Return a display-safe value."""
    try:
        if pd.isna(value):
            return default
    except Exception:
        pass
    if value is None:
        return default
    if isinstance(value, str) and value.strip() == "":
        return default
    return value


def normalize_stock_name(value: Any) -> str:
    """
    Normalize stock names for matching.

    This intentionally removes punctuation and legal suffix noise so that:
    - "Engineers India" matches "Engineers India Ltd"
    - "BSE" matches "BSE Ltd"
    """
    text = str(value or "").upper().strip()
    text = re.sub(r"\b(LTD|LIMITED|LTD\.|CO|COMPANY|INDIA LTD|INDIA LIMITED)\b", "", text)
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def first_existing(row: Dict[str, Any], candidates: list[str], default: Any = "NA") -> Any:
    """Return first non-empty value from possible column names."""
    for column in candidates:
        if column in row:
            value = row.get(column)
            if safe_value(value, default=None) is not None:
                return value
    return default


# --------------------------------------------------
# Stock Master lookup
# --------------------------------------------------
def build_stock_master_lookup(stock_master_df: Optional[pd.DataFrame]) -> Dict[str, Dict[str, Any]]:
    """
    Build lookup dictionary from Stock Master View.

    Supports exact normalized stock names and NSE-code fallback if available.
    """
    lookup: Dict[str, Dict[str, Any]] = {}

    if stock_master_df is None or stock_master_df.empty or "Stock" not in stock_master_df.columns:
        return lookup

    for _, row in stock_master_df.iterrows():
        row_dict = row.to_dict()

        stock_key = normalize_stock_name(row_dict.get("Stock", ""))
        if stock_key:
            lookup[stock_key] = row_dict

        nse_key = normalize_stock_name(row_dict.get("NSE Code", ""))
        if nse_key:
            lookup[nse_key] = row_dict

    return lookup


def classify_holding_status(row: pd.Series, stock_master_lookup: Dict[str, Dict[str, Any]]) -> str:
    """Check whether a portfolio holding appears in the current Stock Master View."""
    stock_key = normalize_stock_name(row.get("Stock", ""))
    nse_key = normalize_stock_name(row.get("NSE Code", ""))

    if stock_key in stock_master_lookup or (nse_key and nse_key in stock_master_lookup):
        return "MATCHED WITH CURRENT SYSTEM"

    return "NOT IN CURRENT SYSTEM"


def get_master_row(row: pd.Series, stock_master_lookup: Dict[str, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Return the matching Stock Master row for a portfolio holding."""
    stock_key = normalize_stock_name(row.get("Stock", ""))
    nse_key = normalize_stock_name(row.get("NSE Code", ""))

    if stock_key in stock_master_lookup:
        return stock_master_lookup[stock_key]

    if nse_key and nse_key in stock_master_lookup:
        return stock_master_lookup[nse_key]

    return None


# --------------------------------------------------
# Portfolio compatibility scoring
# --------------------------------------------------
def calculate_portfolio_weight(row: pd.Series, total_portfolio_value: float) -> float:
    """Calculate holding weight."""
    position_value = safe_float(
        row.get("Position Value", row.get("Current Value", row.get("CurrentValue", 0))),
        default=0.0,
    )

    if total_portfolio_value <= 0:
        return 0.0

    return round((position_value / total_portfolio_value) * 100, 2)


def score_portfolio_compatibility(
    holding_row: pd.Series,
    master_row: Optional[Dict[str, Any]],
    holding_weight: float,
) -> tuple[float, str]:
    """Score compatibility between actual holding and current system output."""
    if master_row is None:
        return 20.0, "Holding is not present in the current Stock Master View."

    score = 50.0
    notes: list[str] = []

    conviction = normalize_text(
        first_existing(
            master_row,
            ["Best Conviction Level", "Conviction Level", "Conviction", "Master Conviction"],
            "",
        )
    )
    final_action = normalize_text(
        first_existing(
            master_row,
            ["Final Allocation Action", "Position Action", "Master Allocation Action", "Master Action"],
            "",
        )
    )
    worst_risk = normalize_text(
        first_existing(
            master_row,
            ["Worst Risk Level", "Risk Level", "Best Risk Level"],
            "",
        )
    )
    exit_verdicts = normalize_text(
        first_existing(
            master_row,
            ["Exit Verdicts", "Exit Verdict"],
            "",
        )
    )

    if conviction == "HIGH CONVICTION":
        score += 25
        notes.append("Stock has high conviction in Stock Master View.")
    elif conviction == "STRONG":
        score += 18
        notes.append("Stock has strong conviction in Stock Master View.")
    elif conviction == "MEDIUM":
        score += 8
        notes.append("Stock has medium conviction.")
    elif conviction == "LOW":
        score -= 5
        notes.append("Stock has low conviction.")
    elif conviction in ["WATCHLIST", "AVOID / FREEZE"]:
        score -= 20
        notes.append("Stock is watchlist or avoid/freeze.")

    if "HIGH CONVICTION POSITION" in final_action:
        score += 15
        notes.append("Final allocation action supports high-conviction position.")
    elif "NORMAL POSITION" in final_action:
        score += 10
        notes.append("Final allocation action supports normal position.")
    elif "STARTER POSITION" in final_action:
        score += 3
        notes.append("Final allocation action supports starter position.")
    elif "TRACK ONLY" in final_action:
        score -= 10
        notes.append("Final allocation action is track only.")
    elif "REVIEW" in final_action or "AVOID" in final_action:
        score -= 20
        notes.append("Final allocation action requires review or avoidance.")

    if worst_risk == "LOW":
        score += 8
        notes.append("Worst risk level is low.")
    elif worst_risk == "MODERATE":
        score -= 2
        notes.append("Worst risk level is moderate.")
    elif worst_risk == "HIGH":
        score -= 18
        notes.append("Worst risk level is high.")
    elif worst_risk == "CRITICAL":
        score -= 30
        notes.append("Worst risk level is critical.")

    if "RIDE" in exit_verdicts and "GUARD" not in exit_verdicts:
        score += 7
        notes.append("Exit verdict supports ride.")
    if "GUARD" in exit_verdicts:
        score -= 8
        notes.append("Guard verdict exists; monitor closely.")
    if "TRIM" in exit_verdicts:
        score -= 12
        notes.append("Trim verdict exists.")
    if "EXIT" in exit_verdicts or "FREEZE" in exit_verdicts:
        score -= 25
        notes.append("Exit/freeze verdict exists.")

    if holding_weight > 10:
        score -= 15
        notes.append("Holding weight is above 10%; concentration risk.")
    elif holding_weight > 7:
        score -= 8
        notes.append("Holding weight is above 7%; monitor concentration.")
    elif holding_weight > 5:
        score -= 3
        notes.append("Holding weight is above 5%; normal cap discipline required.")
    elif holding_weight > 0:
        score += 2
        notes.append("Holding weight is within normal range.")

    score = max(min(round(score, 2), 100), 0)

    if not notes:
        notes.append("No major compatibility notes.")

    return score, " ".join(notes)


def classify_portfolio_action(
    score: float,
    master_row: Optional[Dict[str, Any]],
    holding_weight: float,
) -> str:
    """Convert compatibility score into portfolio action label."""
    if master_row is None:
        return "HOLDING NOT IN CURRENT SYSTEM"

    final_action = normalize_text(
        first_existing(
            master_row,
            ["Final Allocation Action", "Position Action", "Master Allocation Action", "Master Action"],
            "",
        )
    )
    worst_risk = normalize_text(
        first_existing(master_row, ["Worst Risk Level", "Risk Level", "Best Risk Level"], "")
    )
    exit_verdicts = normalize_text(first_existing(master_row, ["Exit Verdicts", "Exit Verdict"], ""))

    if "EXIT" in exit_verdicts or "FREEZE" in exit_verdicts:
        return "EXIT / FREEZE REVIEW"
    if worst_risk == "CRITICAL":
        return "CRITICAL RISK REVIEW"
    if "AVOID" in final_action:
        return "AVOID / EXIT REVIEW"
    if "TRACK ONLY" in final_action:
        return "DO NOT ADD / TRACK ONLY"
    if holding_weight > 10:
        return "CONCENTRATION REVIEW"
    if score >= 80:
        return "CORE HOLD / ADD ON WEAKNESS"
    if score >= 65:
        return "HOLD / SELECTIVE ADD"
    if score >= 50:
        return "HOLD / REVIEW SIZE"
    if score >= 35:
        return "WATCH CLOSELY"
    return "REDUCE / REVIEW"


def evaluate_portfolio_holdings(
    portfolio_df: Optional[pd.DataFrame],
    stock_master_df: Optional[pd.DataFrame],
) -> pd.DataFrame:
    """
    Add compatibility columns to portfolio holdings.

    Output includes both:
    - Legacy columns used by Portfolio Intelligence tab
    - Simplified columns used by AI Analyst tab
    """
    if portfolio_df is None:
        return pd.DataFrame()

    if portfolio_df.empty:
        return portfolio_df.copy()

    df = portfolio_df.copy()
    stock_master_lookup = build_stock_master_lookup(stock_master_df)

    if "Position Value" not in df.columns:
        if "Quantity" in df.columns and "Current Price" in df.columns:
            df["Position Value"] = (
                df["Quantity"].apply(lambda x: safe_float(x, 0.0))
                * df["Current Price"].apply(lambda x: safe_float(x, 0.0))
            )
        elif "Current Value" in df.columns:
            df["Position Value"] = df["Current Value"].apply(lambda x: safe_float(x, 0.0))
        else:
            df["Position Value"] = 0.0

    total_portfolio_value = df["Position Value"].apply(lambda x: safe_float(x, 0.0)).sum()

    portfolio_status_list = []
    action_list = []
    score_list = []
    notes_list = []
    weight_list = []

    master_conviction_list = []
    master_action_list = []
    master_risk_list = []
    master_exit_list = []
    master_engines_list = []
    master_screeners_list = []

    for _, row in df.iterrows():
        master_row = get_master_row(row, stock_master_lookup)

        holding_weight = calculate_portfolio_weight(row, total_portfolio_value)
        status = classify_holding_status(row, stock_master_lookup)
        score, notes = score_portfolio_compatibility(row, master_row, holding_weight)
        action = classify_portfolio_action(score, master_row, holding_weight)

        master_conviction = (
            first_existing(
                master_row,
                ["Best Conviction Level", "Conviction Level", "Conviction", "Master Conviction"],
                "NOT FOUND",
            )
            if master_row
            else "NOT FOUND"
        )
        master_action = (
            first_existing(
                master_row,
                ["Final Allocation Action", "Position Action", "Master Allocation Action", "Master Action"],
                "NOT FOUND",
            )
            if master_row
            else "NOT FOUND"
        )
        master_risk = (
            first_existing(master_row, ["Worst Risk Level", "Risk Level", "Best Risk Level"], "NOT FOUND")
            if master_row
            else "NOT FOUND"
        )
        master_exit = (
            first_existing(master_row, ["Exit Verdicts", "Exit Verdict"], "NOT FOUND")
            if master_row
            else "NOT FOUND"
        )
        master_engines = (
            first_existing(master_row, ["Engines Present", "Engine"], "NOT FOUND")
            if master_row
            else "NOT FOUND"
        )
        master_screeners = (
            first_existing(master_row, ["Screeners Present", "Screener"], "NOT FOUND")
            if master_row
            else "NOT FOUND"
        )

        portfolio_status_list.append(status)
        action_list.append(action)
        score_list.append(score)
        notes_list.append(notes)
        weight_list.append(holding_weight)

        master_conviction_list.append(master_conviction)
        master_action_list.append(master_action)
        master_risk_list.append(master_risk)
        master_exit_list.append(master_exit)
        master_engines_list.append(master_engines)
        master_screeners_list.append(master_screeners)

    # Legacy Portfolio Intelligence columns
    df["Portfolio Weight %"] = weight_list
    df["Portfolio Status"] = portfolio_status_list
    df["Master Conviction Level"] = master_conviction_list
    df["Master Allocation Action"] = master_action_list
    df["Portfolio Compatibility Score"] = score_list
    df["Portfolio Compatibility Action"] = action_list
    df["Portfolio Compatibility Notes"] = notes_list

    # AI Analyst / simplified alias columns
    df["Status"] = portfolio_status_list
    df["Master Conviction"] = master_conviction_list
    df["Master Action"] = master_action_list
    df["Compatibility Score"] = score_list
    df["Compatibility Action"] = action_list
    df["Action"] = action_list
    df["Compatibility Note"] = notes_list
    df["Risk"] = master_risk_list
    df["Exit Verdicts"] = master_exit_list
    df["Engines Present"] = master_engines_list
    df["Screeners Present"] = master_screeners_list

    sort_columns = [column for column in ["Portfolio Compatibility Score", "Portfolio Weight %"] if column in df.columns]
    if sort_columns:
        return df.sort_values(sort_columns, ascending=[False, False][: len(sort_columns)])

    return df


# --------------------------------------------------
# Fresh candidates
# --------------------------------------------------
def find_fresh_candidates(
    stock_master_df: Optional[pd.DataFrame],
    portfolio_df: Optional[pd.DataFrame],
) -> pd.DataFrame:
    """Find stock master candidates not already held in portfolio."""
    if stock_master_df is None:
        return pd.DataFrame()

    if stock_master_df.empty:
        return stock_master_df.copy()

    if portfolio_df is None or portfolio_df.empty or "Stock" not in portfolio_df.columns:
        return stock_master_df.copy()

    held_stocks = set(portfolio_df["Stock"].apply(normalize_stock_name))

    candidates = stock_master_df.copy()
    candidates["_stock_key"] = candidates["Stock"].apply(normalize_stock_name)
    candidates = candidates[~candidates["_stock_key"].isin(held_stocks)].drop(columns=["_stock_key"])

    sort_columns = [
        column
        for column in ["Best Conviction Score", "Highest Suggested Position %", "Appearance Count"]
        if column in candidates.columns
    ]

    if sort_columns:
        return candidates.sort_values(sort_columns, ascending=[False] * len(sort_columns))

    return candidates


# --------------------------------------------------
# Summary
# --------------------------------------------------
def summarize_portfolio_compatibility(portfolio_compatibility_df: Optional[pd.DataFrame]) -> dict:
    """Summarize compatibility actions."""
    if portfolio_compatibility_df is None or portfolio_compatibility_df.empty:
        return {
            "holdings": 0,
            "matched": 0,
            "not_matched": 0,
            "core_hold_or_add": 0,
            "hold_review": 0,
            "track_or_reduce": 0,
        }

    df = portfolio_compatibility_df.copy()

    status_col = "Portfolio Status" if "Portfolio Status" in df.columns else "Status"
    action_col = (
        "Portfolio Compatibility Action"
        if "Portfolio Compatibility Action" in df.columns
        else "Compatibility Action"
        if "Compatibility Action" in df.columns
        else "Action"
    )

    status_series = df[status_col].astype(str).str.upper()
    action_series = df[action_col].astype(str).str.upper()

    return {
        "holdings": len(df),
        "matched": int(status_series.str.contains("MATCHED").sum()),
        "not_matched": int(status_series.str.contains("NOT IN CURRENT SYSTEM").sum()),
        "core_hold_or_add": int(
            action_series.str.contains("CORE HOLD").sum()
            + action_series.str.contains("SELECTIVE ADD").sum()
        ),
        "hold_review": int(
            action_series.str.contains("HOLD / REVIEW").sum()
            + action_series.str.contains("CONCENTRATION REVIEW").sum()
        ),
        "track_or_reduce": int(
            action_series.str.contains("TRACK ONLY").sum()
            + action_series.str.contains("REDUCE").sum()
            + action_series.str.contains("WATCH CLOSELY").sum()
        ),
    }
