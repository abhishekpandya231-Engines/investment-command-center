"""
Portfolio Compatibility Engine v0.1
Investment Command Center

Purpose:
Compares the user's current portfolio holdings against the Stock Master View.

Why this exists:
The Stock Master View tells what the system likes.
The Portfolio Compatibility Engine tells what action may be relevant for the actual portfolio.

Outputs:
- Portfolio Status
- Portfolio Compatibility Action
- Portfolio Compatibility Score
- Portfolio Compatibility Notes

Important:
This is a rules-based decision-support layer, not financial advice.
"""


def normalize_text(value):
    """Normalize text values."""
    return str(value).upper().strip()


def safe_float(value, default=0):
    """Safely convert a value to float."""
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def normalize_stock_name(value):
    """Normalize stock names for matching."""
    return str(value).strip().upper()


def build_stock_master_lookup(stock_master_df):
    """
    Builds a dictionary from Stock Master View.
    """
    lookup = {}

    if stock_master_df is None or stock_master_df.empty or "Stock" not in stock_master_df.columns:
        return lookup

    for _, row in stock_master_df.iterrows():
        stock_key = normalize_stock_name(row.get("Stock", ""))
        if stock_key:
            lookup[stock_key] = row.to_dict()

    return lookup


def classify_holding_status(row, stock_master_lookup):
    """
    Checks whether a portfolio holding appears in the current Stock Master View.
    """
    stock_key = normalize_stock_name(row.get("Stock", ""))

    if stock_key in stock_master_lookup:
        return "MATCHED WITH CURRENT SYSTEM"

    return "NOT IN CURRENT SYSTEM"


def calculate_portfolio_weight(row, total_portfolio_value):
    """
    Calculates holding weight if position value is available.
    """
    position_value = safe_float(row.get("Position Value", row.get("Current Value", 0)), default=0)

    if total_portfolio_value <= 0:
        return 0

    return round((position_value / total_portfolio_value) * 100, 2)


def score_portfolio_compatibility(holding_row, master_row, holding_weight):
    """
    Scores compatibility between actual holding and current system output.
    Max: 100
    """
    if master_row is None:
        return 20, "Holding is not present in the current Stock Master View."

    score = 50
    notes = []

    conviction = normalize_text(master_row.get("Best Conviction Level", ""))
    final_action = normalize_text(master_row.get("Final Allocation Action", ""))
    worst_risk = normalize_text(master_row.get("Worst Risk Level", ""))
    exit_verdicts = normalize_text(master_row.get("Exit Verdicts", ""))

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


def classify_portfolio_action(score, master_row, holding_weight):
    """
    Converts compatibility score into action label.
    """
    if master_row is None:
        return "HOLDING NOT IN CURRENT SYSTEM"

    final_action = normalize_text(master_row.get("Final Allocation Action", ""))
    worst_risk = normalize_text(master_row.get("Worst Risk Level", ""))
    exit_verdicts = normalize_text(master_row.get("Exit Verdicts", ""))

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


def evaluate_portfolio_holdings(portfolio_df, stock_master_df):
    """
    Adds compatibility columns to portfolio holdings.
    """
    if portfolio_df is None or portfolio_df.empty:
        return portfolio_df

    df = portfolio_df.copy()
    stock_master_lookup = build_stock_master_lookup(stock_master_df)

    if "Position Value" not in df.columns:
        if "Quantity" in df.columns and "Current Price" in df.columns:
            df["Position Value"] = (
                df["Quantity"].apply(lambda x: safe_float(x, 0))
                * df["Current Price"].apply(lambda x: safe_float(x, 0))
            )
        else:
            df["Position Value"] = 0

    total_portfolio_value = df["Position Value"].apply(lambda x: safe_float(x, 0)).sum()

    portfolio_status_list = []
    action_list = []
    score_list = []
    notes_list = []
    weight_list = []
    master_conviction_list = []
    master_action_list = []

    for _, row in df.iterrows():
        stock_key = normalize_stock_name(row.get("Stock", ""))
        master_row = stock_master_lookup.get(stock_key)

        holding_weight = calculate_portfolio_weight(row, total_portfolio_value)
        status = classify_holding_status(row, stock_master_lookup)
        score, notes = score_portfolio_compatibility(row, master_row, holding_weight)
        action = classify_portfolio_action(score, master_row, holding_weight)

        portfolio_status_list.append(status)
        action_list.append(action)
        score_list.append(score)
        notes_list.append(notes)
        weight_list.append(holding_weight)
        master_conviction_list.append(
            master_row.get("Best Conviction Level", "NOT FOUND") if master_row else "NOT FOUND"
        )
        master_action_list.append(
            master_row.get("Final Allocation Action", "NOT FOUND") if master_row else "NOT FOUND"
        )

    df["Portfolio Weight %"] = weight_list
    df["Portfolio Status"] = portfolio_status_list
    df["Master Conviction Level"] = master_conviction_list
    df["Master Allocation Action"] = master_action_list
    df["Portfolio Compatibility Score"] = score_list
    df["Portfolio Compatibility Action"] = action_list
    df["Portfolio Compatibility Notes"] = notes_list

    return df.sort_values(
        ["Portfolio Compatibility Score", "Portfolio Weight %"],
        ascending=[False, False],
    )


def find_fresh_candidates(stock_master_df, portfolio_df):
    """
    Finds stock master candidates not already held in portfolio.
    """
    if stock_master_df is None or stock_master_df.empty:
        return stock_master_df

    if portfolio_df is None or portfolio_df.empty or "Stock" not in portfolio_df.columns:
        return stock_master_df.copy()

    held_stocks = set(portfolio_df["Stock"].apply(normalize_stock_name))

    candidates = stock_master_df.copy()
    candidates["_stock_key"] = candidates["Stock"].apply(normalize_stock_name)

    candidates = candidates[~candidates["_stock_key"].isin(held_stocks)].drop(columns=["_stock_key"])

    return candidates.sort_values(
        ["Best Conviction Score", "Highest Suggested Position %", "Appearance Count"],
        ascending=[False, False, False],
    )


def summarize_portfolio_compatibility(portfolio_compatibility_df):
    """
    Summarizes compatibility actions.
    """
    if portfolio_compatibility_df is None or portfolio_compatibility_df.empty:
        return {
            "holdings": 0,
            "matched": 0,
            "not_matched": 0,
            "core_hold_or_add": 0,
            "hold_review": 0,
            "track_or_reduce": 0,
        }

    status_series = portfolio_compatibility_df["Portfolio Status"].astype(str).str.upper()
    action_series = portfolio_compatibility_df["Portfolio Compatibility Action"].astype(str).str.upper()

    return {
        "holdings": len(portfolio_compatibility_df),
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
