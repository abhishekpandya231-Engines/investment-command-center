"""
Decision Journal v0.1
Investment Command Center

Purpose:
Creates an audit trail for every important investment decision.

This is not a trade execution tool.
It is a discipline and credibility tool.

Core idea:
If a decision is not logged, it cannot be reviewed, improved, or validated.
"""

from datetime import datetime
from pathlib import Path
import pandas as pd


DECISION_JOURNAL_COLUMNS = [
    "Date",
    "Time",
    "Stock",
    "Engine",
    "Signal Type",
    "Rule Verdict",
    "Exit Verdict",
    "Exit Reason",
    "Engine A Score",
    "Market Regime",
    "Action Taken",
    "Quantity",
    "Price",
    "Position Size",
    "Risk Notes",
    "User Notes",
]


def create_empty_decision_journal() -> pd.DataFrame:
    """
    Creates an empty decision journal dataframe.
    """
    return pd.DataFrame(columns=DECISION_JOURNAL_COLUMNS)


def validate_decision_journal_columns(df: pd.DataFrame) -> list:
    """
    Checks whether a decision journal file has all required columns.
    Returns missing column names.
    """
    missing_columns = []

    for column in DECISION_JOURNAL_COLUMNS:
        if column not in df.columns:
            missing_columns.append(column)

    return missing_columns


def create_decision_entry(
    stock: str,
    engine: str,
    signal_type: str,
    rule_verdict: str,
    exit_verdict: str,
    exit_reason: str,
    engine_a_score,
    market_regime: str,
    action_taken: str,
    quantity=0,
    price=0,
    position_size=0,
    risk_notes="",
    user_notes="",
) -> dict:
    """
    Creates one decision journal entry.
    """
    now = datetime.now()

    return {
        "Date": now.strftime("%Y-%m-%d"),
        "Time": now.strftime("%H:%M:%S"),
        "Stock": stock,
        "Engine": engine,
        "Signal Type": signal_type,
        "Rule Verdict": rule_verdict,
        "Exit Verdict": exit_verdict,
        "Exit Reason": exit_reason,
        "Engine A Score": engine_a_score,
        "Market Regime": market_regime,
        "Action Taken": action_taken,
        "Quantity": quantity,
        "Price": price,
        "Position Size": position_size,
        "Risk Notes": risk_notes,
        "User Notes": user_notes,
    }


def append_decision_entry(existing_df: pd.DataFrame, entry: dict) -> pd.DataFrame:
    """
    Appends a decision entry to an existing journal dataframe.
    """
    journal_df = existing_df.copy()

    for column in DECISION_JOURNAL_COLUMNS:
        if column not in journal_df.columns:
            journal_df[column] = ""

    entry_df = pd.DataFrame([entry])
    journal_df = pd.concat([journal_df, entry_df], ignore_index=True)

    return journal_df[DECISION_JOURNAL_COLUMNS]


def save_decision_journal(df: pd.DataFrame, file_path="data/decision_log.csv") -> str:
    """
    Saves decision journal to CSV.
    """
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    df.to_csv(path, index=False)

    return str(path)


def load_decision_journal(file_path="data/decision_log.csv") -> pd.DataFrame:
    """
    Loads existing decision journal if available.
    Otherwise creates an empty journal.
    """
    path = Path(file_path)

    if not path.exists():
        return create_empty_decision_journal()

    try:
        df = pd.read_csv(path)
        missing_columns = validate_decision_journal_columns(df)

        for column in missing_columns:
            df[column] = ""

        return df[DECISION_JOURNAL_COLUMNS]

    except Exception:
        return create_empty_decision_journal()


def summarize_decision_journal(df: pd.DataFrame) -> dict:
    """
    Creates simple decision journal summary metrics.
    """
    if df.empty:
        return {
            "total_decisions": 0,
            "buy_actions": 0,
            "hold_actions": 0,
            "trim_actions": 0,
            "exit_actions": 0,
            "guard_actions": 0,
        }

    action_series = df["Action Taken"].astype(str).str.upper()
    verdict_series = df["Exit Verdict"].astype(str).str.upper()

    return {
        "total_decisions": len(df),
        "buy_actions": int(action_series.str.contains("BUY").sum()),
        "hold_actions": int(action_series.str.contains("HOLD").sum()),
        "trim_actions": int(action_series.str.contains("TRIM").sum()),
        "exit_actions": int(action_series.str.contains("EXIT").sum()),
        "guard_actions": int(verdict_series.str.contains("GUARD").sum()),
    }


def generate_decision_log_template(file_path="/mnt/data/decision_log_template.csv") -> str:
    """
    Generates a blank CSV template for the user to download.
    """
    df = create_empty_decision_journal()
    df.to_csv(file_path, index=False)
    return file_path
