"""
Stock Master Engine v0.1
Investment Command Center

Purpose:
Deduplicates row-level screener output into one stock-level master view.

Why this exists:
A stock may appear multiple times across C1/C2, D1/D2, or B/C/D engines.
Row-level views are useful for diagnostics, but allocation decisions should be
reviewed at stock level.

Outputs:
- Stock
- Engines Present
- Screeners Present
- Appearance Count
- Best Conviction Score
- Best Conviction Level
- Highest Suggested Position %
- Final Allocation Action
- Best Risk Level
- Worst Risk Level
- Exit Verdicts
- Combined Notes
"""


def normalize_text(value):
    """Normalize text values."""
    return str(value).upper().strip()


def join_unique(values):
    """Joins unique non-empty values."""
    cleaned = []
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text and text.lower() != "nan":
            cleaned.append(text)

    return ", ".join(sorted(set(cleaned)))


def best_conviction_level(levels):
    """
    Returns the strongest conviction level found for a stock.
    """
    rank = {
        "HIGH CONVICTION": 6,
        "STRONG": 5,
        "MEDIUM": 4,
        "LOW": 3,
        "TACTICAL ONLY": 2,
        "WATCHLIST": 1,
        "AVOID / FREEZE": 0,
    }

    best_level = "WATCHLIST"
    best_rank = -1

    for level in levels:
        clean_level = normalize_text(level)
        current_rank = rank.get(clean_level, -1)

        if current_rank > best_rank:
            best_rank = current_rank
            best_level = clean_level

    return best_level


def worst_risk_level(levels):
    """
    Returns the worst risk level found for a stock.
    """
    rank = {
        "LOW": 1,
        "MODERATE": 2,
        "HIGH": 3,
        "CRITICAL": 4,
    }

    worst_level = "LOW"
    worst_rank = 0

    for level in levels:
        clean_level = normalize_text(level)
        current_rank = rank.get(clean_level, 0)

        if current_rank > worst_rank:
            worst_rank = current_rank
            worst_level = clean_level

    return worst_level


def best_risk_level(levels):
    """
    Returns the best risk level found for a stock.
    """
    rank = {
        "LOW": 1,
        "MODERATE": 2,
        "HIGH": 3,
        "CRITICAL": 4,
    }

    best_level = "CRITICAL"
    best_rank = 99

    for level in levels:
        clean_level = normalize_text(level)
        current_rank = rank.get(clean_level, 99)

        if current_rank < best_rank:
            best_rank = current_rank
            best_level = clean_level

    return best_level


def final_allocation_action(actions, conviction_level, worst_risk, max_position):
    """
    Creates a final stock-level action.

    Conservative philosophy:
    - If any serious risk is present, cap action.
    - If best signal is high conviction but another row says risk is high, review manually.
    - If all rows are only track-only, keep track-only.
    """
    action_text = normalize_text(join_unique(actions))
    conviction = normalize_text(conviction_level)
    risk = normalize_text(worst_risk)

    if "NO POSITION" in action_text or "AVOID" in action_text:
        return "AVOID / EXIT REVIEW"

    if risk == "CRITICAL":
        return "AVOID / CRITICAL REVIEW"

    if risk == "HIGH":
        if max_position > 0:
            return "TACTICAL / CAPPED POSITION"
        return "TRACK ONLY"

    if "HIGH CONVICTION POSITION" in action_text and conviction == "HIGH CONVICTION":
        return "HIGH CONVICTION POSITION"

    if "NORMAL POSITION" in action_text:
        return "NORMAL POSITION"

    if "STARTER POSITION" in action_text:
        return "STARTER POSITION"

    return "TRACK ONLY"


def build_combined_notes(group):
    """
    Creates human-readable combined notes.
    """
    engines = join_unique(group.get("Engine", []))
    screeners = join_unique(group.get("Screener", []))
    conviction_level = best_conviction_level(group.get("Conviction Level", []))
    best_score = group.get("Conviction Score", []).max() if "Conviction Score" in group else "NA"
    highest_position = group.get("Suggested Position Size %", []).max() if "Suggested Position Size %" in group else "NA"
    worst_risk = worst_risk_level(group.get("Risk Level", []))
    exit_verdicts = join_unique(group.get("Exit Verdict", []))

    notes = [
        f"Appears in Engine(s): {engines}.",
        f"Screeners: {screeners}.",
        f"Best conviction: {conviction_level} with score {best_score}.",
        f"Highest suggested position: {highest_position}%.",
        f"Worst risk level across appearances: {worst_risk}.",
        f"Exit verdicts observed: {exit_verdicts}.",
    ]

    return " ".join(notes)


def create_stock_master_view(df):
    """
    Converts row-level screener dataframe into stock-level master dataframe.
    """
    if df is None or df.empty or "Stock" not in df.columns:
        return df

    working_df = df.copy()
    working_df["Stock"] = working_df["Stock"].astype(str).str.strip()

    stock_rows = []

    for stock_name, group in working_df.groupby("Stock", dropna=False):
        if not stock_name or str(stock_name).lower() == "nan":
            continue

        engines_present = join_unique(group["Engine"]) if "Engine" in group else ""
        screeners_present = join_unique(group["Screener"]) if "Screener" in group else ""

        best_conviction_score = (
            group["Conviction Score"].max()
            if "Conviction Score" in group
            else 0
        )

        best_conviction = (
            best_conviction_level(group["Conviction Level"])
            if "Conviction Level" in group
            else "WATCHLIST"
        )

        highest_position = (
            group["Suggested Position Size %"].max()
            if "Suggested Position Size %" in group
            else 0
        )

        max_cap = (
            group["Max Position Cap %"].max()
            if "Max Position Cap %" in group
            else 0
        )

        best_risk = (
            best_risk_level(group["Risk Level"])
            if "Risk Level" in group
            else "UNKNOWN"
        )

        worst_risk = (
            worst_risk_level(group["Risk Level"])
            if "Risk Level" in group
            else "UNKNOWN"
        )

        actions = group["Position Action"] if "Position Action" in group else []
        final_action = final_allocation_action(
            actions,
            best_conviction,
            worst_risk,
            highest_position,
        )

        row = {
            "Stock": stock_name,
            "Engines Present": engines_present,
            "Screeners Present": screeners_present,
            "Appearance Count": int(len(group)),
            "Best Conviction Score": best_conviction_score,
            "Best Conviction Level": best_conviction,
            "Highest Suggested Position %": highest_position,
            "Max Position Cap %": max_cap,
            "Final Allocation Action": final_action,
            "Best Risk Level": best_risk,
            "Worst Risk Level": worst_risk,
            "Exit Verdicts": join_unique(group["Exit Verdict"]) if "Exit Verdict" in group else "",
            "Rule Verdicts": join_unique(group["Rule Verdict"]) if "Rule Verdict" in group else "",
            "Combined Notes": build_combined_notes(group),
        }

        stock_rows.append(row)

    import pandas as pd

    stock_master_df = pd.DataFrame(stock_rows)

    if stock_master_df.empty:
        return stock_master_df

    stock_master_df = stock_master_df.sort_values(
        ["Best Conviction Score", "Highest Suggested Position %", "Appearance Count"],
        ascending=[False, False, False],
    )

    return stock_master_df.reset_index(drop=True)


def summarize_stock_master(stock_master_df):
    """
    Summarizes stock-level allocation actions.
    """
    if stock_master_df is None or stock_master_df.empty:
        return {
            "unique_stocks": 0,
            "high_conviction": 0,
            "normal_position": 0,
            "starter_position": 0,
            "track_only": 0,
            "capped_or_review": 0,
        }

    action_series = stock_master_df["Final Allocation Action"].astype(str).str.upper()
    conviction_series = stock_master_df["Best Conviction Level"].astype(str).str.upper()

    return {
        "unique_stocks": len(stock_master_df),
        "high_conviction": int((conviction_series == "HIGH CONVICTION").sum()),
        "normal_position": int(action_series.str.contains("NORMAL POSITION").sum()),
        "starter_position": int(action_series.str.contains("STARTER POSITION").sum()),
        "track_only": int(action_series.str.contains("TRACK ONLY").sum()),
        "capped_or_review": int(
            action_series.str.contains("CAPPED").sum()
            + action_series.str.contains("REVIEW").sum()
        ),
    }
