from datetime import datetime
import html
import os
import pickle
from typing import Any, Iterable, Optional

import pandas as pd
import streamlit as st

from core.engine_a import calculate_engine_a_score, default_engine_a_inputs
from core.exit_engine import evaluate_exit
from core.risk_engine import (
    apply_stock_risk,
    evaluate_portfolio_risk_summary,
    evaluate_screener_risk_summary,
)
from core.conviction_engine import apply_conviction_engine, summarize_conviction
from core.position_sizing import apply_position_sizing, summarize_position_sizing
from core.stock_master import create_stock_master_view, summarize_stock_master
from core.portfolio_compatibility import (
    evaluate_portfolio_holdings,
    find_fresh_candidates,
    summarize_portfolio_compatibility,
)
from core.decision_journal import load_decision_journal, summarize_decision_journal


# ==================================================
# Investment Command Center v1.4.1
# AI Analyst Column Mapping Fix + Tab Visibility Hardening
# ==================================================

APP_VERSION = "v1.4.1"
BUILD_STAGE = "AI Analyst Layer Fixed"
LAST_UPDATED = "08 May 2026"

PORTFOLIO_REQUIRED_COLUMNS = [
    "Stock",
    "Engine",
    "Sector",
    "Market Cap Category",
    "Quantity",
    "Buy Price",
    "Current Price",
]

SCREENER_KEY_COLUMNS = [
    "Stock",
    "Sector",
    "LTP",
    "Market Cap",
    "PE TTM",
    "PEG TTM",
    "ROE Ann %",
    "Piotroski Score",
    "Durability Score",
    "Momentum Score",
    "Total Debt to Total Equity Ann ",
    "Net Profit Ann YoY Growth %",
    "Net Profit 3Y Growth %",
    "Revenue QoQ Growth %",
    "1Y Low",
    "1Y High",
    "NSE Code",
]


# --------------------------------------------------
# Persistent Runtime Storage
# --------------------------------------------------
PERSISTENCE_DIR = "data"
PERSISTENCE_FILE = os.path.join(PERSISTENCE_DIR, "icc_persistent_state.pkl")
PERSISTENT_KEYS = [
    "combined_df",
    "stock_master_df",
    "stock_master_ready",
    "portfolio_df",
    "portfolio_compatibility_df",
    "last_screener_upload_time",
    "last_portfolio_upload_time",
]

# --------------------------------------------------
# Page Setup
# --------------------------------------------------
st.set_page_config(
    page_title="Investment Command Center",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# --------------------------------------------------
# Premium White UI Theme
# --------------------------------------------------
st.markdown(
    """
    <style>
        :root {
            --icc-navy: #08213f;
            --icc-navy-2: #0f2f57;
            --icc-blue: #1f6feb;
            --icc-green: #087f5b;
            --icc-red: #c1121f;
            --icc-amber: #b45309;
            --icc-slate: #64748b;
            --icc-muted: #f8fafc;
            --icc-card: #ffffff;
            --icc-line: #e5e7eb;
            --icc-soft-blue: #eef5ff;
            --icc-shadow: 0 18px 45px rgba(8, 33, 63, 0.08);
        }

        html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
            background: linear-gradient(180deg, #ffffff 0%, #f8fafc 52%, #ffffff 100%) !important;
            color: var(--icc-navy) !important;
        }

        [data-testid="stHeader"] {
            background: rgba(255,255,255,0.92) !important;
            backdrop-filter: blur(12px);
            border-bottom: 1px solid rgba(226,232,240,0.9);
        }

        [data-testid="stSidebar"] {
            background: #ffffff !important;
            border-right: 1px solid var(--icc-line);
        }

        .block-container {
            max-width: 1180px;
            padding-top: 2.2rem;
            padding-bottom: 4rem;
        }

        h1, h2, h3, h4, h5, h6 {
            color: var(--icc-navy) !important;
            font-weight: 900 !important;
            letter-spacing: -0.03em;
        }

        p, li, label, span, div {
            color: #111827;
        }

        .icc-hero {
            padding: 34px 38px;
            border-radius: 32px;
            background: linear-gradient(135deg, #ffffff 0%, #f7fbff 55%, #eef5ff 100%);
            border: 1px solid #dbe3ef;
            box-shadow: var(--icc-shadow);
            margin-bottom: 1.6rem;
        }

        .icc-hero-title {
            font-size: clamp(2.2rem, 6vw, 4.6rem);
            line-height: 0.96;
            font-weight: 950;
            letter-spacing: -0.06em;
            color: var(--icc-navy);
            margin-bottom: 16px;
        }

        .icc-hero-subtitle {
            font-size: 1.05rem;
            color: var(--icc-slate);
            font-weight: 750;
            margin-bottom: 20px;
        }

        .icc-chip-row {
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
        }

        .icc-chip {
            display: inline-flex;
            align-items: center;
            padding: 10px 16px;
            border: 1px solid #dbe3ef;
            border-radius: 999px;
            color: var(--icc-navy);
            background: rgba(255,255,255,0.78);
            font-weight: 850;
            box-shadow: 0 8px 24px rgba(8, 33, 63, 0.04);
        }

        .icc-section-intro {
            padding: 18px 20px;
            border: 1px solid #dbe3ef;
            border-radius: 22px;
            background: #ffffff;
            box-shadow: 0 12px 28px rgba(8,33,63,0.06);
            margin: 0.5rem 0 1.2rem 0;
        }

        .icc-section-kicker {
            color: var(--icc-slate);
            font-size: 0.78rem;
            font-weight: 900;
            letter-spacing: 0.16em;
            text-transform: uppercase;
        }

        .icc-section-title {
            color: var(--icc-navy);
            font-size: 1.45rem;
            font-weight: 950;
            line-height: 1.15;
            margin-top: 6px;
        }

        .icc-card {
            background: #ffffff;
            border: 1px solid #dfe6ef;
            border-radius: 28px;
            box-shadow: var(--icc-shadow);
            padding: 22px 24px;
            margin: 0.7rem 0 1.05rem 0;
            overflow: hidden;
            position: relative;
        }

        .icc-card::before {
            content: "";
            position: absolute;
            left: 0;
            top: 0;
            bottom: 0;
            width: 7px;
            background: var(--accent, var(--icc-blue));
            border-radius: 28px 0 0 28px;
        }

        .icc-card-title {
            color: var(--icc-navy);
            font-weight: 950;
            font-size: 1.22rem;
            line-height: 1.2;
            margin-bottom: 12px;
            padding-left: 4px;
        }

        .icc-card-kicker {
            color: var(--icc-slate);
            font-size: 0.76rem;
            font-weight: 950;
            letter-spacing: 0.16em;
            text-transform: uppercase;
            margin-bottom: 8px;
            padding-left: 4px;
        }

        .icc-fields {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 10px;
            margin-top: 12px;
        }

        .icc-field {
            background: #f8fafc;
            border: 1px solid #e5e7eb;
            border-radius: 18px;
            padding: 12px 14px;
            min-height: 58px;
        }

        .icc-field-label {
            color: var(--icc-slate);
            font-size: 0.82rem;
            font-weight: 850;
            margin-bottom: 3px;
        }

        .icc-field-value {
            color: var(--icc-navy);
            font-size: 1.02rem;
            font-weight: 950;
            word-break: break-word;
        }

        .icc-note {
            background: #f8fafc;
            color: #334155;
            border: 1px solid #e5e7eb;
            border-radius: 18px;
            padding: 14px 16px;
            margin-top: 12px;
            font-weight: 650;
            line-height: 1.55;
        }

        .icc-badges {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 12px;
        }

        .icc-badge {
            background: #eef5ff;
            border: 1px solid #d8e6ff;
            color: #1d4ed8;
            border-radius: 999px;
            padding: 8px 12px;
            font-size: 0.82rem;
            font-weight: 950;
        }

        .icc-alert {
            border-radius: 22px;
            padding: 18px 20px;
            border: 1px solid #dbe3ef;
            background: #ffffff;
            box-shadow: 0 12px 28px rgba(8,33,63,0.06);
            font-weight: 750;
            line-height: 1.5;
            margin: 0.6rem 0 1rem 0;
        }

        .icc-alert-success { background: #ecfdf5; color: #065f46; border-color: #bbf7d0; }
        .icc-alert-warning { background: #fffbeb; color: #92400e; border-color: #fde68a; }
        .icc-alert-danger  { background: #fef2f2; color: #991b1b; border-color: #fecaca; }
        .icc-alert-info    { background: #eff6ff; color: #1e3a8a; border-color: #bfdbfe; }

        div[data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid #dfe6ef;
            border-radius: 24px;
            padding: 18px 18px;
            box-shadow: 0 12px 30px rgba(8, 33, 63, 0.06);
        }

        div[data-testid="stMetric"] label p {
            color: #475569 !important;
            font-weight: 750 !important;
        }

        div[data-testid="stMetricValue"] {
            color: var(--icc-navy) !important;
            font-weight: 950 !important;
            letter-spacing: -0.04em;
        }

        div[data-testid="stDataFrame"] {
            border-radius: 22px !important;
            overflow: hidden;
            box-shadow: 0 12px 30px rgba(8,33,63,0.06);
            border: 1px solid #e5e7eb;
        }

        .stTabs [data-baseweb="tab-list"] {
            gap: 6px;
            background: #ffffff;
            border: 1px solid #e5e7eb;
            border-radius: 999px;
            padding: 7px;
            box-shadow: 0 14px 32px rgba(8,33,63,0.07);
            overflow-x: auto;
        }

        .stTabs [data-baseweb="tab"] {
            border-radius: 999px !important;
            padding: 10px 15px !important;
            font-weight: 900 !important;
            color: var(--icc-navy) !important;
            white-space: nowrap !important;
            background: #ffffff !important;
            border: 1px solid transparent !important;
        }

        .stTabs [data-baseweb="tab"] p,
        .stTabs [data-baseweb="tab"] span,
        .stTabs [data-baseweb="tab"] div {
            color: var(--icc-navy) !important;
            font-weight: 900 !important;
        }

        .stTabs [data-baseweb="tab"]:hover {
            background: #eef5ff !important;
            color: var(--icc-navy) !important;
        }

        .stTabs [data-baseweb="tab"]:hover p,
        .stTabs [data-baseweb="tab"]:hover span,
        .stTabs [data-baseweb="tab"]:hover div {
            color: var(--icc-navy) !important;
        }

        .stTabs [aria-selected="true"] {
            background: var(--icc-navy) !important;
            color: #ffffff !important;
            border: 1px solid var(--icc-navy) !important;
            box-shadow: 0 10px 22px rgba(8, 33, 63, 0.18) !important;
        }

        .stTabs [aria-selected="true"] p,
        .stTabs [aria-selected="true"] span,
        .stTabs [aria-selected="true"] div {
            color: #ffffff !important;
            font-weight: 950 !important;
        }

        .stTabs [data-baseweb="tab"]:not([aria-selected="true"]) p,
        .stTabs [data-baseweb="tab"]:not([aria-selected="true"]) span,
        .stTabs [data-baseweb="tab"]:not([aria-selected="true"]) div {
            color: var(--icc-navy) !important;
            opacity: 1 !important;
            font-weight: 900 !important;
        }


        .stTabs [aria-selected="true"],
        .stTabs [aria-selected="true"] *,
        .stTabs [aria-selected="true"] p,
        .stTabs [aria-selected="true"] span,
        .stTabs [aria-selected="true"] div,
        .stTabs button[role="tab"][aria-selected="true"],
        .stTabs button[role="tab"][aria-selected="true"] * {
            color: #ffffff !important;
            opacity: 1 !important;
            -webkit-text-fill-color: #ffffff !important;
            text-shadow: none !important;
        }

        .stTabs [aria-selected="false"],
        .stTabs [aria-selected="false"] *,
        .stTabs [aria-selected="false"] p,
        .stTabs [aria-selected="false"] span,
        .stTabs [aria-selected="false"] div,
        .stTabs button[role="tab"][aria-selected="false"],
        .stTabs button[role="tab"][aria-selected="false"] * {
            color: var(--icc-navy) !important;
            opacity: 1 !important;
            -webkit-text-fill-color: var(--icc-navy) !important;
        }

        .stTabs [data-baseweb="tab-highlight"] {
            background-color: var(--icc-blue) !important;
            height: 3px !important;
        }

        div[data-testid="stExpander"] {
            border: 1px solid #dfe6ef !important;
            border-radius: 20px !important;
            background: #ffffff !important;
            box-shadow: 0 10px 24px rgba(8,33,63,0.05);
            overflow: hidden;
        }

        @media (max-width: 768px) {
            .block-container { padding-left: 1rem; padding-right: 1rem; }
            .icc-hero { padding: 26px 22px; border-radius: 28px; }
            .icc-fields { grid-template-columns: 1fr; gap: 8px; }
            .icc-card { padding: 20px 18px 20px 20px; border-radius: 26px; }
            .icc-field { padding: 10px 12px; min-height: 52px; }
            .icc-note { padding: 12px 14px; }
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------
# Display Helpers
# --------------------------------------------------
def safe_value(value: Any, default: str = "NA") -> str:
    try:
        if pd.isna(value):
            return default
    except Exception:
        pass
    if isinstance(value, float):
        if value.is_integer():
            return f"{value:.0f}"
        return f"{value:.2f}"
    return str(value)


def esc(value: Any, default: str = "NA") -> str:
    return html.escape(safe_value(value, default=default))


def shorten(value: Any, max_chars: int = 280) -> str:
    text = " ".join(safe_value(value, default="").split())
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0] + " ..."


def accent_from_status(value: Any) -> str:
    text = str(value).upper()
    if any(word in text for word in ["EXIT", "HIGH", "CRITICAL", "RED", "AVOID"]):
        return "#c1121f"
    if any(word in text for word in ["GUARD", "MODERATE", "WATCH", "REVIEW", "TRIM", "CAUTIOUS"]):
        return "#b45309"
    if any(word in text for word in ["LOW", "RIDE", "HIGH CONVICTION", "GREEN", "MATCHED", "CORE"]):
        return "#087f5b"
    return "#1f6feb"


def section_intro(title: str, subtitle: str, kicker: str = "Investment Command Center") -> None:
    st.markdown(
        f"""
        <div class="icc-section-intro">
            <div class="icc-section-kicker">{esc(kicker)}</div>
            <div class="icc-section-title">{esc(title)}</div>
            <div style="color:#64748b;font-weight:700;margin-top:8px;line-height:1.45;">{esc(subtitle)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def alert_box(message: str, tone: str = "info") -> None:
    tone_map = {
        "success": "icc-alert-success",
        "warning": "icc-alert-warning",
        "danger": "icc-alert-danger",
        "info": "icc-alert-info",
    }
    st.markdown(
        f"<div class='icc-alert {tone_map.get(tone, 'icc-alert-info')}'>{esc(message)}</div>",
        unsafe_allow_html=True,
    )


def record_card(
    title: str,
    kicker: str = "",
    fields: Optional[list[tuple[str, Any]]] = None,
    note: str = "",
    badges: Optional[Iterable[Any]] = None,
    accent: str = "#1f6feb",
) -> None:
    fields = fields or []
    badges = list(badges or [])

    field_html = "".join(
        f"""
        <div class="icc-field">
            <div class="icc-field-label">{esc(label)}</div>
            <div class="icc-field-value">{esc(value)}</div>
        </div>
        """
        for label, value in fields
    )

    badge_html = "".join(
        f"<span class='icc-badge'>{esc(badge)}</span>"
        for badge in badges
        if safe_value(badge, default="") != ""
    )
    badge_block = f"<div class='icc-badges'>{badge_html}</div>" if badge_html else ""
    note_block = f"<div class='icc-note'>{esc(shorten(note, 320))}</div>" if note else ""

    st.markdown(
        f"""
        <div class="icc-card" style="--accent:{accent};">
            <div class="icc-card-kicker">{esc(kicker)}</div>
            <div class="icc-card-title">{esc(title)}</div>
            <div class="icc-fields">{field_html}</div>
            {badge_block}
            {note_block}
        </div>
        """,
        unsafe_allow_html=True,
    )


def compact_dataframe(df: pd.DataFrame, columns: Optional[list[str]] = None, height: int = 420) -> None:
    if df is None or df.empty:
        alert_box("No records available yet.", "info")
        return
    display_df = df.copy()
    if columns:
        available_cols = [column for column in columns if column in display_df.columns]
        display_df = display_df[available_cols]
    st.dataframe(display_df, use_container_width=True, hide_index=False, height=height)


def show_metric_grid(metrics: list[tuple[str, Any]], columns: int = 4) -> None:
    cols = st.columns(columns)
    for index, (label, value) in enumerate(metrics):
        with cols[index % columns]:
            st.metric(label, value)


# --------------------------------------------------
# Data Helpers
# --------------------------------------------------
def clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(col).strip() for col in df.columns]
    return df


def to_number(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def infer_engine_from_filename(filename: str) -> str:
    name = filename.lower()
    if "mom" in name or "momentum" in name:
        return "B"
    if name.startswith("c") or "_c" in name or "value" in name:
        return "C"
    if name.startswith("d") or "_d" in name or "compound" in name:
        return "D"
    return "Unknown"


def infer_screener_name(filename: str) -> str:
    name = filename.lower()
    if "mom" in name:
        return "Momentum"
    if "c1" in name:
        return "Value C1"
    if "c2" in name:
        return "Value C2"
    if "d1" in name:
        return "Compounder D1"
    if "d2" in name:
        return "Compounder D2"
    return filename.replace(".csv", "")


def classify_market_cap(market_cap_value: Any) -> str:
    try:
        value = float(market_cap_value)
    except Exception:
        return "Unknown"
    if value >= 50000:
        return "Large Cap"
    if value >= 10000:
        return "Mid Cap"
    return "Small Cap"


def prepare_screener_df(df: pd.DataFrame, filename: str) -> pd.DataFrame:
    df = clean_columns(df)
    df = df.copy()
    df["Source File"] = filename
    df["Engine"] = infer_engine_from_filename(filename)
    df["Screener"] = infer_screener_name(filename)

    if "Market Cap" in df.columns:
        df["Market Cap Category"] = df["Market Cap"].apply(classify_market_cap)
    else:
        df["Market Cap Category"] = "Unknown"

    numeric_cols = [
        "LTP",
        "Market Cap",
        "PE TTM",
        "PEG TTM",
        "ROE Ann %",
        "Piotroski Score",
        "Durability Score",
        "Momentum Score",
        "Total Debt to Total Equity Ann ",
        "Net Profit Ann YoY Growth %",
        "Net Profit 3Y Growth %",
        "Revenue QoQ Growth %",
        "1Y Low",
        "1Y High",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = to_number(df[col])
    return df


def generate_screener_verdict(row: pd.Series) -> str:
    engine = str(row.get("Engine", "Unknown")).upper().strip()

    durability = pd.to_numeric(row.get("Durability Score", None), errors="coerce")
    momentum = pd.to_numeric(row.get("Momentum Score", None), errors="coerce")
    pe = pd.to_numeric(row.get("PE TTM", None), errors="coerce")
    peg = pd.to_numeric(row.get("PEG TTM", None), errors="coerce")
    roe = pd.to_numeric(row.get("ROE Ann %", None), errors="coerce")
    piotroski = pd.to_numeric(row.get("Piotroski Score", None), errors="coerce")
    debt = pd.to_numeric(row.get("Total Debt to Total Equity Ann ", None), errors="coerce")
    growth = pd.to_numeric(row.get("Net Profit Ann YoY Growth %", None), errors="coerce")

    if engine == "B":
        if pd.notna(durability) and pd.notna(momentum):
            if durability > 55 and momentum > 59:
                return "GREEN GATE"
            if durability < 45 or momentum < 49:
                return "RED GATE"
            return "GREY GATE"
        return "DATA CHECK"

    if engine == "C":
        if pd.notna(roe) and pd.notna(pe) and pd.notna(piotroski):
            if roe > 15 and pe < 25 and piotroski > 6:
                return "VALUE QUALIFIED"
            return "VALUE WATCH"
        return "DATA CHECK"

    if engine == "D":
        if pd.notna(roe) and pd.notna(piotroski) and pd.notna(debt) and pd.notna(growth):
            if roe > 15 and piotroski > 6 and debt < 1 and growth > 15:
                if pd.notna(peg) and peg <= 1.5:
                    return "COMPOUNDER QUALIFIED"
                return "GROWTH QUALIFIED"
            return "COMPOUNDER WATCH"
        return "DATA CHECK"

    return "UNCLASSIFIED"


def apply_exit_engine(df: pd.DataFrame, engine_a_score: float) -> pd.DataFrame:
    df = df.copy()
    exit_results = df.apply(lambda row: evaluate_exit(row, engine_a_score=engine_a_score), axis=1)
    df["Exit Verdict"] = exit_results.apply(lambda result: result.get("verdict", "GUARD"))
    df["Exit Reason"] = exit_results.apply(lambda result: result.get("reason", "Manual review required."))
    df["Exit Priority"] = exit_results.apply(lambda result: result.get("priority", 10))
    return df


def calculate_portfolio_from_holdings(df: pd.DataFrame) -> pd.DataFrame:
    df = clean_columns(df)
    df = df.copy()
    df["Quantity"] = to_number(df["Quantity"]).fillna(0)
    df["Buy Price"] = to_number(df["Buy Price"]).fillna(0)
    df["Current Price"] = to_number(df["Current Price"]).fillna(0)
    df["Invested Value"] = df["Quantity"] * df["Buy Price"]
    df["Current Value"] = df["Quantity"] * df["Current Price"]
    df["Unrealised P&L"] = df["Current Value"] - df["Invested Value"]
    df["P&L %"] = df.apply(
        lambda row: (row["Unrealised P&L"] / row["Invested Value"] * 100)
        if row["Invested Value"] > 0
        else 0,
        axis=1,
    )
    total_current = df["Current Value"].sum()
    df["Portfolio Weight %"] = df["Current Value"].apply(
        lambda value: (value / total_current * 100) if total_current > 0 else 0
    )
    return df


def portfolio_risk_flags(df: pd.DataFrame) -> list[str]:
    flags: list[str] = []
    if df is None or df.empty:
        return ["Upload portfolio CSV to generate portfolio risk flags."]

    if "Portfolio Weight %" in df.columns:
        high_stock = df[df["Portfolio Weight %"] > 10]
        for _, row in high_stock.iterrows():
            flags.append(
                f"{row['Stock']} is {row['Portfolio Weight %']:.1f}% of portfolio. Single-stock cap check required."
            )

    if "Sector" in df.columns and "Current Value" in df.columns:
        sector = df.groupby("Sector", as_index=False)["Current Value"].sum()
        total = sector["Current Value"].sum()
        sector["Sector Weight %"] = sector["Current Value"] / total * 100 if total > 0 else 0
        high_sector = sector[sector["Sector Weight %"] > 30]
        for _, row in high_sector.iterrows():
            flags.append(
                f"{row['Sector']} is {row['Sector Weight %']:.1f}% of portfolio. Sector concentration check required."
            )

    if "Market Cap Category" in df.columns and "Current Value" in df.columns:
        mcap = df.groupby("Market Cap Category", as_index=False)["Current Value"].sum()
        total = mcap["Current Value"].sum()
        mcap["Market Cap Weight %"] = mcap["Current Value"] / total * 100 if total > 0 else 0
        small = mcap[mcap["Market Cap Category"].astype(str).str.lower() == "small cap"]
        if not small.empty and small.iloc[0]["Market Cap Weight %"] > 50:
            flags.append(
                f"Small-cap exposure is {small.iloc[0]['Market Cap Weight %']:.1f}%, above 50% threshold."
            )

    return flags or ["No major concentration risk flags detected."]


def save_stock_master_to_session(stock_master_df: pd.DataFrame) -> None:
    if stock_master_df is not None and not stock_master_df.empty:
        st.session_state["stock_master_df"] = stock_master_df.copy()
        st.session_state["stock_master_ready"] = True


def get_active_stock_master_df() -> Optional[pd.DataFrame]:
    stock_master_df = st.session_state.get("stock_master_df", None)
    if isinstance(stock_master_df, pd.DataFrame) and not stock_master_df.empty:
        return stock_master_df
    return None


def get_active_combined_df() -> Optional[pd.DataFrame]:
    combined_df = st.session_state.get("combined_df", None)
    if isinstance(combined_df, pd.DataFrame) and not combined_df.empty:
        return combined_df
    return None


def get_active_portfolio_df() -> Optional[pd.DataFrame]:
    portfolio_df = st.session_state.get("portfolio_df", None)
    if isinstance(portfolio_df, pd.DataFrame) and not portfolio_df.empty:
        return portfolio_df
    return None


def save_persistent_state() -> None:
    """Save uploaded screener, stock master, portfolio, and compatibility data to local runtime storage."""
    try:
        os.makedirs(PERSISTENCE_DIR, exist_ok=True)
        payload = {
            "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "app_version": APP_VERSION,
            "data": {key: st.session_state.get(key) for key in PERSISTENT_KEYS if key in st.session_state},
        }
        with open(PERSISTENCE_FILE, "wb") as file:
            pickle.dump(payload, file)
        st.session_state["persistent_state_saved_at"] = payload["saved_at"]
    except Exception as error:
        st.session_state["persistent_state_error"] = f"Persistent save failed: {error}"


def load_persistent_state() -> bool:
    """Restore data from local runtime storage once per app session."""
    if st.session_state.get("persistent_state_loaded_once"):
        return bool(st.session_state.get("persistent_state_available", False))

    st.session_state["persistent_state_loaded_once"] = True
    if not os.path.exists(PERSISTENCE_FILE):
        st.session_state["persistent_state_available"] = False
        return False

    try:
        with open(PERSISTENCE_FILE, "rb") as file:
            payload = pickle.load(file)
        data = payload.get("data", {}) if isinstance(payload, dict) else {}
        for key, value in data.items():
            if key not in st.session_state:
                st.session_state[key] = value
        st.session_state["persistent_state_available"] = True
        st.session_state["persistent_state_saved_at"] = payload.get("saved_at", "Unknown")
        return True
    except Exception as error:
        st.session_state["persistent_state_available"] = False
        st.session_state["persistent_state_error"] = f"Persistent load failed: {error}"
        return False


def clear_persistent_state() -> None:
    """Clear stored runtime data and matching session state keys."""
    try:
        if os.path.exists(PERSISTENCE_FILE):
            os.remove(PERSISTENCE_FILE)
        for key in PERSISTENT_KEYS:
            st.session_state.pop(key, None)
        st.session_state["persistent_state_available"] = False
        st.session_state["persistent_state_saved_at"] = "Cleared"
    except Exception as error:
        st.session_state["persistent_state_error"] = f"Persistent clear failed: {error}"


def update_portfolio_compatibility() -> None:
    portfolio_df = get_active_portfolio_df()
    stock_master_df = get_active_stock_master_df()
    if portfolio_df is not None and stock_master_df is not None:
        compatibility_df = evaluate_portfolio_holdings(portfolio_df, stock_master_df)
        st.session_state["portfolio_compatibility_df"] = compatibility_df


def process_screener_files(screener_files, engine_a_score: float, market_regime: str) -> Optional[pd.DataFrame]:
    if not screener_files:
        return None

    all_screeners = []
    for uploaded_file in screener_files:
        raw_df = pd.read_csv(uploaded_file)
        prepared_df = prepare_screener_df(raw_df, uploaded_file.name)
        prepared_df["Rule Verdict"] = prepared_df.apply(generate_screener_verdict, axis=1)
        prepared_df = apply_exit_engine(prepared_df, engine_a_score=engine_a_score)
        all_screeners.append(prepared_df)

    combined_df = pd.concat(all_screeners, ignore_index=True)
    combined_df = apply_stock_risk(combined_df)
    combined_df = apply_conviction_engine(combined_df, market_regime=market_regime)
    combined_df = apply_position_sizing(
        combined_df,
        engine_a_score=engine_a_score,
        market_regime=market_regime,
    )

    stock_master_df = create_stock_master_view(combined_df)
    save_stock_master_to_session(stock_master_df)
    st.session_state["combined_df"] = combined_df.copy()
    st.session_state["last_screener_upload_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    update_portfolio_compatibility()
    save_persistent_state()
    return combined_df


def process_portfolio_file(portfolio_file, engine_a_score: float, market_regime: str) -> tuple[Optional[pd.DataFrame], list[str]]:
    if portfolio_file is None:
        return None, []

    portfolio_df = clean_columns(pd.read_csv(portfolio_file))
    missing_columns = [column for column in PORTFOLIO_REQUIRED_COLUMNS if column not in portfolio_df.columns]
    if missing_columns:
        return None, missing_columns

    portfolio_df = calculate_portfolio_from_holdings(portfolio_df)
    portfolio_df = apply_exit_engine(portfolio_df, engine_a_score=engine_a_score)
    portfolio_df = apply_stock_risk(portfolio_df)
    portfolio_df = apply_conviction_engine(portfolio_df, market_regime=market_regime)
    portfolio_df = apply_position_sizing(
        portfolio_df,
        engine_a_score=engine_a_score,
        market_regime=market_regime,
    )
    st.session_state["portfolio_df"] = portfolio_df.copy()
    st.session_state["last_portfolio_upload_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    update_portfolio_compatibility()
    save_persistent_state()
    return portfolio_df, []


# --------------------------------------------------
# Engine A Controls
# --------------------------------------------------
def render_engine_a_sidebar() -> dict:
    defaults = default_engine_a_inputs()
    st.sidebar.title("⚙️ Engine A Market Gate")
    st.sidebar.caption("Manual market inputs. Later this can be automated through data/API layers.")

    with st.sidebar.expander("Market Inputs", expanded=True):
        nifty_pe = st.number_input("Nifty PE", value=float(defaults.get("nifty_pe", 22.0)), step=0.1)
        nifty_above_200dma = st.selectbox("Nifty above 200 DMA?", ["Yes", "No"], index=0)
        breadth = st.number_input(
            "% Stocks Above 200 DMA",
            value=float(defaults.get("percent_stocks_above_200dma", 55.0)),
            step=1.0,
        )
        india_vix = st.number_input("India VIX", value=float(defaults.get("india_vix", 15.0)), step=0.1)
        fii_30d = st.number_input("FII 30D Flow ₹ Cr", value=float(defaults.get("fii_30d", 0.0)), step=500.0)
        dii_30d = st.number_input("DII 30D Flow ₹ Cr", value=float(defaults.get("dii_30d", 10000.0)), step=500.0)
        rbi_stance = st.selectbox(
            "RBI Stance",
            ["Accommodative", "Neutral", "Withdrawal", "Tightening"],
            index=1,
        )
        cpi = st.number_input("CPI %", value=float(defaults.get("cpi", 4.8)), step=0.1)
        pmi = st.number_input("PMI", value=float(defaults.get("pmi", 55.0)), step=0.1)
        india_10y_gsec = st.number_input(
            "India 10Y G-Sec %",
            value=float(defaults.get("india_10y_gsec", 7.1)),
            step=0.05,
        )
        india_10y_gsec_30d_change_bps = st.number_input(
            "India 10Y 30D Change bps",
            value=float(defaults.get("india_10y_gsec_30d_change_bps", 0.0)),
            step=5.0,
        )
        us_10y = st.number_input("US 10Y Yield %", value=float(defaults.get("us_10y", 4.3)), step=0.1)
        dxy = st.number_input("DXY", value=float(defaults.get("dxy", 104.0)), step=0.1)
        inr_change_percent = st.number_input(
            "INR Change %",
            value=float(defaults.get("inr_change_percent", 0.5)),
            step=0.1,
        )
        brent_crude = st.number_input("Brent Crude", value=float(defaults.get("brent_crude", 85.0)), step=1.0)

    return {
        "nifty_pe": nifty_pe,
        "nifty_above_200dma": nifty_above_200dma,
        "percent_stocks_above_200dma": breadth,
        "india_vix": india_vix,
        "fii_30d": fii_30d,
        "dii_30d": dii_30d,
        "rbi_stance": rbi_stance,
        "cpi": cpi,
        "pmi": pmi,
        "india_10y_gsec": india_10y_gsec,
        "india_10y_gsec_30d_change_bps": india_10y_gsec_30d_change_bps,
        "us_10y": us_10y,
        "dxy": dxy,
        "inr_change_percent": inr_change_percent,
        "brent_crude": brent_crude,
    }


engine_a_inputs = render_engine_a_sidebar()
engine_a_result = calculate_engine_a_score(engine_a_inputs)
engine_a_score = engine_a_result["score"]
st.session_state["engine_a_result"] = engine_a_result
load_persistent_state()
update_portfolio_compatibility()
if "persistent_state_error" in st.session_state:
    st.sidebar.warning(st.session_state["persistent_state_error"])


# --------------------------------------------------
# Header
# --------------------------------------------------
st.markdown(
    f"""
    <div class="icc-hero">
        <div class="icc-hero-title">📊 Investment<br>Command Center</div>
        <div class="icc-hero-subtitle">Rules-Based Portfolio Intelligence System | {APP_VERSION}</div>
        <div class="icc-chip-row">
            <span class="icc-chip">White Premium UI</span>
            <span class="icc-chip">Rules-Based</span>
            <span class="icc-chip">Portfolio Intelligence</span>
            <span class="icc-chip">Mobile Optimised</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------
# Tabs
# --------------------------------------------------
tabs = st.tabs(
    [
        "🏠 Command Center",
        "📤 Upload Center",
        "🧬 Stock Master",
        "🛡️ Risk & Exit",
        "🧠 Conviction & Allocation",
        "🧩 Portfolio Intelligence",
        "📝 Decision Journal",
        "🤖 AI Analyst",
        "⚙️ System Status",
    ]
)


# ==================================================
# 1. Command Center
# ==================================================
with tabs[0]:
    section_intro(
        "Command Center",
        "Single-page cockpit view: market gate, system readiness, action queue, and highest priority review items.",
        "Primary cockpit",
    )

    show_metric_grid(
        [
            ("System Version", APP_VERSION),
            ("Build Stage", BUILD_STAGE),
            ("Last Updated", LAST_UPDATED),
            ("Engine A Score", f"{engine_a_result['score']}/100"),
        ],
        columns=4,
    )

    st.divider()
    st.subheader("🧠 Engine A Market Gate")
    show_metric_grid(
        [
            ("Regime", engine_a_result["regime"]),
            ("Equity Allocation", f"{engine_a_result['equity_allocation_percent']}%"),
            ("Debt Allocation", f"{engine_a_result['debt_allocation_percent']}%"),
            ("Gold Allocation", f"{engine_a_result['gold_allocation_percent']}%"),
        ],
        columns=4,
    )
    alert_box(engine_a_result["action"], "info")

    combined_df = get_active_combined_df()
    stock_master_df = get_active_stock_master_df()
    portfolio_df = get_active_portfolio_df()
    compatibility_df = st.session_state.get("portfolio_compatibility_df", None)

    st.divider()
    st.subheader("🎯 Action Queue")

    if stock_master_df is None and portfolio_df is None:
        alert_box("Upload the 5 screener files first. Then upload portfolio CSV. Action Queue will appear here.", "warning")
    else:
        if stock_master_df is not None:
            top_master = stock_master_df.head(5).copy()
            for _, row in top_master.iterrows():
                record_card(
                    title=row.get("Stock", "Unknown"),
                    kicker="Stock Master Priority",
                    fields=[
                        ("Best Conviction", row.get("Best Conviction Level", "NA")),
                        ("Score", row.get("Best Conviction Score", "NA")),
                        ("Suggested Position", f"{safe_value(row.get('Highest Suggested Position %', 0))}%"),
                        ("Final Action", row.get("Final Allocation Action", "NA")),
                    ],
                    badges=[row.get("Engines Present", ""), row.get("Exit Verdicts", "")],
                    note=row.get("Combined Notes", ""),
                    accent=accent_from_status(row.get("Final Allocation Action", "")),
                )

        if isinstance(compatibility_df, pd.DataFrame) and not compatibility_df.empty:
            st.subheader("🧩 Portfolio Review Queue")
            top_compatibility = compatibility_df.sort_values(
                ["Portfolio Compatibility Score", "Portfolio Weight %"],
                ascending=[True, False],
            ).head(5)
            for _, row in top_compatibility.iterrows():
                record_card(
                    title=row.get("Stock", "Unknown"),
                    kicker="Portfolio Compatibility",
                    fields=[
                        ("Portfolio Weight", f"{safe_value(row.get('Portfolio Weight %', 0))}%"),
                        ("Status", row.get("Portfolio Status", "NA")),
                        ("Compatibility Score", f"{safe_value(row.get('Portfolio Compatibility Score', 0))}/100"),
                        ("Action", row.get("Portfolio Compatibility Action", "NA")),
                    ],
                    note=row.get("Portfolio Compatibility Notes", ""),
                    accent=accent_from_status(row.get("Portfolio Compatibility Action", "")),
                )


# ==================================================
# 2. Upload Center
# ==================================================
with tabs[1]:
    section_intro(
        "Upload Center",
        "Upload screeners and holdings separately. The system keeps screener intelligence and portfolio P&L cleanly separated.",
        "Data intake",
    )

    if st.session_state.get("persistent_state_available"):
        alert_box(
            f"Saved data restored automatically. Last saved: {st.session_state.get('persistent_state_saved_at', 'Unknown')}",
            "success",
        )
    else:
        alert_box("No saved runtime data found yet. Upload once and the app will remember it.", "info")

    if st.button("Clear saved app data", type="secondary"):
        clear_persistent_state()
        st.rerun()

    st.subheader("📁 Multi-Screener Upload")
    st.write("Supported files: **Mom.csv, C1.csv, C2.csv, D1.csv, D2.csv**")
    screener_files = st.file_uploader(
        "Upload Trendlyne screener CSV files",
        type=["csv"],
        accept_multiple_files=True,
        key="screener_files_v130",
    )

    if screener_files:
        try:
            combined_df = process_screener_files(
                screener_files,
                engine_a_score=engine_a_score,
                market_regime=engine_a_result["regime"],
            )
            if combined_df is not None:
                alert_box(f"{len(screener_files)} screener file(s) uploaded successfully. Stock Master View is saved.", "success")
                show_metric_grid(
                    [
                        ("Total Screener Rows", len(combined_df)),
                        ("Unique Stocks", combined_df["Stock"].nunique() if "Stock" in combined_df.columns else 0),
                        ("Exit / Guard", int(combined_df["Exit Verdict"].isin(["EXIT", "GUARD", "FREEZE"]).sum()) if "Exit Verdict" in combined_df.columns else 0),
                        ("Ride / Trim", int(combined_df["Exit Verdict"].isin(["RIDE", "TRIM"]).sum()) if "Exit Verdict" in combined_df.columns else 0),
                        ("Momentum Rows", int((combined_df["Engine"] == "B").sum()) if "Engine" in combined_df.columns else 0),
                        ("Value Rows", int((combined_df["Engine"] == "C").sum()) if "Engine" in combined_df.columns else 0),
                        ("Compounder Rows", int((combined_df["Engine"] == "D").sum()) if "Engine" in combined_df.columns else 0),
                    ],
                    columns=4,
                )
        except Exception as error:
            alert_box(f"Screener upload failed: {error}", "danger")

    st.divider()
    st.subheader("📂 Portfolio Upload")
    st.write("Required columns: **Stock, Engine, Sector, Market Cap Category, Quantity, Buy Price, Current Price**")
    portfolio_file = st.file_uploader(
        "Upload holdings portfolio CSV",
        type=["csv"],
        accept_multiple_files=False,
        key="portfolio_file_v130",
    )

    if portfolio_file is not None:
        try:
            portfolio_df, missing_columns = process_portfolio_file(
                portfolio_file,
                engine_a_score=engine_a_score,
                market_regime=engine_a_result["regime"],
            )
            if missing_columns:
                alert_box("Your uploaded file is missing required portfolio columns: " + ", ".join(missing_columns), "danger")
                alert_box("This looks like a screener CSV, not a holdings portfolio CSV. Upload screener files above.", "warning")
            elif portfolio_df is not None:
                invested_value = portfolio_df["Invested Value"].sum()
                current_value = portfolio_df["Current Value"].sum()
                pnl = current_value - invested_value
                pnl_pct = (pnl / invested_value * 100) if invested_value > 0 else 0
                alert_box("Portfolio uploaded successfully.", "success")
                show_metric_grid(
                    [
                        ("Invested Value", f"₹{invested_value:,.0f}"),
                        ("Current Value", f"₹{current_value:,.0f}"),
                        ("Unrealised P&L", f"₹{pnl:,.0f}"),
                        ("P&L %", f"{pnl_pct:.2f}%"),
                        ("Positions", len(portfolio_df)),
                    ],
                    columns=4,
                )
        except Exception as error:
            alert_box(f"Portfolio upload failed: {error}", "danger")


# ==================================================
# 3. Stock Master
# ==================================================
with tabs[2]:
    section_intro(
        "Stock Master",
        "Deduplicated stock-level master view built from all uploaded screeners. This is the system's preferred candidate universe.",
        "System universe",
    )

    stock_master_df = get_active_stock_master_df()
    if stock_master_df is None:
        alert_box("Upload the 5 screener CSV files in Upload Center to generate Stock Master View.", "warning")
    else:
        summary = summarize_stock_master(stock_master_df)
        show_metric_grid(
            [
                ("Master Stocks", summary["unique_stocks"]),
                ("High Conviction", summary["high_conviction"]),
                ("Normal Positions", summary["normal_position"]),
                ("Track Only", summary["track_only"]),
            ],
            columns=4,
        )

        st.subheader("🏆 Top Stock Master Candidates")
        for _, row in stock_master_df.head(12).iterrows():
            record_card(
                title=row.get("Stock", "Unknown"),
                kicker="Stock Master View",
                fields=[
                    ("Engines", row.get("Engines Present", "NA")),
                    ("Screeners", row.get("Screeners Present", "NA")),
                    ("Appearances", row.get("Appearance Count", "NA")),
                    ("Best Conviction", row.get("Best Conviction Level", "NA")),
                    ("Conviction Score", f"{safe_value(row.get('Best Conviction Score', 0))}/100"),
                    ("Suggested Position", f"{safe_value(row.get('Highest Suggested Position %', 0))}%"),
                    ("Final Action", row.get("Final Allocation Action", "NA")),
                    ("Worst Risk", row.get("Worst Risk Level", "NA")),
                ],
                badges=[row.get("Engines Present", ""), row.get("Final Allocation Action", "")],
                note=row.get("Combined Notes", ""),
                accent=accent_from_status(row.get("Final Allocation Action", "")),
            )

        with st.expander("View full Stock Master table", expanded=False):
            compact_dataframe(stock_master_df, height=520)


# ==================================================
# 4. Risk & Exit
# ==================================================
with tabs[3]:
    section_intro(
        "Risk & Exit",
        "Risk Engine and Exit Engine together. First identify what must be watched, guarded, trimmed, or exited.",
        "Risk control",
    )

    combined_df = get_active_combined_df()
    if combined_df is None:
        alert_box("Upload screener files first to generate Risk & Exit diagnostics.", "warning")
    else:
        risk_summary = evaluate_screener_risk_summary(combined_df)
        show_metric_grid(
            [
                ("Critical Risk", risk_summary["critical_count"]),
                ("High Risk", risk_summary["high_count"]),
                ("Moderate Risk", risk_summary["moderate_count"]),
                ("Small-Cap Rows", risk_summary["small_cap_count"]),
                ("High Debt Rows", risk_summary["high_debt_count"]),
                ("Expensive Rows", risk_summary["expensive_count"]),
            ],
            columns=4,
        )

        risk_watchlist_df = combined_df[
            combined_df["Risk Level"].isin(["CRITICAL", "HIGH", "MODERATE"])
        ].copy()
        risk_watchlist_columns = [
            "Stock",
            "Engine",
            "Screener",
            "Risk Level",
            "Risk Score",
            "Exit Verdict",
            "Rule Verdict",
            "Risk Notes",
            "Market Cap Category",
            "PE TTM",
            "PEG TTM",
            "ROE Ann %",
            "Piotroski Score",
            "Durability Score",
            "Momentum Score",
        ]
        st.subheader("🧨 High / Moderate Risk Watchlist")
        if not risk_watchlist_df.empty:
            risk_watchlist_df = risk_watchlist_df.sort_values(
                ["Risk Score", "Stock"],
                ascending=[False, True],
            )
            for _, row in risk_watchlist_df.head(10).iterrows():
                record_card(
                    title=row.get("Stock", "Unknown"),
                    kicker=f"Engine {row.get('Engine', 'NA')} | {row.get('Screener', 'NA')}",
                    fields=[
                        ("Risk Level", row.get("Risk Level", "NA")),
                        ("Risk Score", f"{safe_value(row.get('Risk Score', 0))}/100"),
                        ("Exit Verdict", row.get("Exit Verdict", "NA")),
                        ("Rule Verdict", row.get("Rule Verdict", "NA")),
                    ],
                    badges=[row.get("Risk Level", ""), row.get("Screener", "")],
                    note=row.get("Risk Notes", ""),
                    accent=accent_from_status(row.get("Risk Level", "")),
                )
            with st.expander("View full high/moderate risk table", expanded=False):
                compact_dataframe(risk_watchlist_df, risk_watchlist_columns, height=520)
        else:
            alert_box("No moderate/high/critical risk rows detected.", "success")

        st.divider()
        st.subheader("🚦 Exit Engine Verdict Summary")
        exit_summary = (
            combined_df.groupby(["Engine", "Exit Verdict"], as_index=False)
            .size()
            .rename(columns={"size": "Count"})
            .sort_values(["Engine", "Exit Verdict"])
        )
        compact_dataframe(exit_summary, height=260)

        exit_watchlist = combined_df[combined_df["Exit Verdict"].isin(["EXIT", "GUARD", "FREEZE", "TRIM"])]
        with st.expander("View Exit / Guard / Trim watchlist", expanded=False):
            compact_dataframe(
                exit_watchlist,
                [
                    "Stock",
                    "Engine",
                    "Screener",
                    "Exit Verdict",
                    "Exit Reason",
                    "Risk Level",
                    "Risk Score",
                    "Rule Verdict",
                ],
                height=520,
            )


# ==================================================
# 5. Conviction & Allocation
# ==================================================
with tabs[4]:
    section_intro(
        "Conviction & Allocation",
        "Conviction Engine and Position Sizing Engine. This section ranks candidates and converts signals into controlled allocation bands.",
        "Candidate quality",
    )

    combined_df = get_active_combined_df()
    if combined_df is None:
        alert_box("Upload screener files first to generate conviction and allocation output.", "warning")
    else:
        conviction_summary = summarize_conviction(combined_df)
        show_metric_grid(
            [
                ("High Conviction", conviction_summary["high_conviction"]),
                ("Strong", conviction_summary["strong"]),
                ("Medium", conviction_summary["medium"]),
                ("Watchlist", conviction_summary["watchlist"]),
            ],
            columns=4,
        )

        st.subheader("🏆 Top Conviction Candidates")
        top_conviction_df = combined_df[
            combined_df["Conviction Level"].isin(["HIGH CONVICTION", "STRONG", "MEDIUM"])
        ].copy()
        if not top_conviction_df.empty:
            top_conviction_df = top_conviction_df.sort_values(
                ["Conviction Score", "Risk Score"],
                ascending=[False, True],
            )
            for _, row in top_conviction_df.head(10).iterrows():
                record_card(
                    title=row.get("Stock", "Unknown"),
                    kicker=f"Engine {row.get('Engine', 'NA')} | {row.get('Screener', 'NA')}",
                    fields=[
                        ("Conviction", row.get("Conviction Level", "NA")),
                        ("Conviction Score", f"{safe_value(row.get('Conviction Score', 0))}/100"),
                        ("Risk Level", row.get("Risk Level", "NA")),
                        ("Exit Verdict", row.get("Exit Verdict", "NA")),
                        ("Suggested Position", f"{safe_value(row.get('Suggested Position Size %', 0))}%"),
                        ("Action", row.get("Position Action", "NA")),
                    ],
                    badges=[row.get("Conviction Level", ""), row.get("Rule Verdict", "")],
                    note=row.get("Conviction Notes", ""),
                    accent=accent_from_status(row.get("Conviction Level", "")),
                )
            with st.expander("View full conviction candidate table", expanded=False):
                compact_dataframe(
                    top_conviction_df,
                    [
                        "Stock",
                        "Engine",
                        "Screener",
                        "Conviction Score",
                        "Conviction Level",
                        "Risk Level",
                        "Risk Score",
                        "Exit Verdict",
                        "Rule Verdict",
                        "Suggested Position Size %",
                        "Position Action",
                    ],
                    height=520,
                )
        else:
            alert_box("No medium/strong/high-conviction candidates detected.", "info")

        st.divider()
        st.subheader("📏 Position Sizing Summary")
        sizing_summary = summarize_position_sizing(combined_df)
        show_metric_grid(
            [
                ("Track Only", sizing_summary["track_only"]),
                ("Starter Positions", sizing_summary["starter_position"]),
                ("Normal Positions", sizing_summary["normal_position"]),
                ("Avoid / Exit", sizing_summary["avoid_or_exit"]),
            ],
            columns=4,
        )

        position_candidates_df = combined_df[combined_df["Suggested Position Size %"] > 0].copy()
        if not position_candidates_df.empty:
            position_candidates_df = position_candidates_df.sort_values(
                ["Suggested Position Size %", "Conviction Score", "Risk Score"],
                ascending=[False, False, True],
            )
            st.subheader("🧾 Top Allocation Notes")
            for _, row in position_candidates_df.head(10).iterrows():
                record_card(
                    title=row.get("Stock", "Unknown"),
                    kicker=f"Engine {row.get('Engine', 'NA')} | {row.get('Screener', 'NA')}",
                    fields=[
                        ("Conviction", row.get("Conviction Level", "NA")),
                        ("Score", f"{safe_value(row.get('Conviction Score', 0))}/100"),
                        ("Risk", row.get("Risk Level", "NA")),
                        ("Exit", row.get("Exit Verdict", "NA")),
                        ("Suggested Position", f"{safe_value(row.get('Suggested Position Size %', 0))}%"),
                        ("Max Cap", f"{safe_value(row.get('Max Position Cap %', 0))}%"),
                        ("Action", row.get("Position Action", "NA")),
                    ],
                    badges=[row.get("Position Action", ""), row.get("Screener", "")],
                    note=row.get("Position Sizing Reason", ""),
                    accent=accent_from_status(row.get("Position Action", "")),
                )
        else:
            alert_box("No positive position-size candidates detected.", "info")


# ==================================================
# 6. Portfolio Intelligence
# ==================================================
with tabs[5]:
    section_intro(
        "Portfolio Intelligence",
        "Holdings-level portfolio view. This connects your current portfolio with the system's Stock Master View.",
        "Portfolio cockpit",
    )

    portfolio_df = get_active_portfolio_df()
    stock_master_df = get_active_stock_master_df()
    compatibility_df = st.session_state.get("portfolio_compatibility_df", None)

    if portfolio_df is None:
        alert_box("Upload portfolio CSV in Upload Center to activate portfolio intelligence.", "warning")
    else:
        invested_value = portfolio_df["Invested Value"].sum()
        current_value = portfolio_df["Current Value"].sum()
        pnl = current_value - invested_value
        pnl_pct = (pnl / invested_value * 100) if invested_value > 0 else 0
        show_metric_grid(
            [
                ("Invested Value", f"₹{invested_value:,.0f}"),
                ("Current Value", f"₹{current_value:,.0f}"),
                ("Unrealised P&L", f"₹{pnl:,.0f}"),
                ("P&L %", f"{pnl_pct:.2f}%"),
                ("Positions", len(portfolio_df)),
            ],
            columns=4,
        )

        st.subheader("🛡️ Portfolio Risk Engine")
        portfolio_risk = evaluate_portfolio_risk_summary(portfolio_df)
        show_metric_grid(
            [
                ("Portfolio Risk Level", portfolio_risk["portfolio_risk_level"]),
                ("Portfolio Risk Score", f"{portfolio_risk['risk_score']}/100"),
            ],
            columns=2,
        )
        for note in portfolio_risk.get("notes", []):
            alert_box(note, "warning" if portfolio_risk["portfolio_risk_level"] in ["HIGH", "CRITICAL"] else "info")

        st.subheader("🚨 Risk Flags")
        for flag in portfolio_risk_flags(portfolio_df):
            alert_box(flag, "warning")

        st.divider()
        st.subheader("🧩 Portfolio Compatibility Engine")
        if stock_master_df is None:
            alert_box("Stock Master View is not loaded. Upload the 5 screener CSV files first.", "warning")
        elif isinstance(compatibility_df, pd.DataFrame) and not compatibility_df.empty:
            compatibility_summary = summarize_portfolio_compatibility(compatibility_df)
            show_metric_grid(
                [
                    ("Stock Master Rows", len(stock_master_df)),
                    ("Holdings", compatibility_summary["holdings"]),
                    ("Matched", compatibility_summary["matched"]),
                    ("Core / Add", compatibility_summary["core_hold_or_add"]),
                    ("Track / Reduce", compatibility_summary["track_or_reduce"]),
                ],
                columns=4,
            )

            st.subheader("🧾 Portfolio Action Notes")
            for _, row in compatibility_df.head(10).iterrows():
                record_card(
                    title=row.get("Stock", "Unknown"),
                    kicker="Portfolio Action Note",
                    fields=[
                        ("Portfolio Weight", f"{safe_value(row.get('Portfolio Weight %', 0))}%"),
                        ("Status", row.get("Portfolio Status", "NA")),
                        ("Master Conviction", row.get("Master Conviction Level", "NA")),
                        ("Master Action", row.get("Master Allocation Action", "NA")),
                        ("Compatibility Score", f"{safe_value(row.get('Portfolio Compatibility Score', 0))}/100"),
                        ("Action", row.get("Portfolio Compatibility Action", "NA")),
                    ],
                    note=row.get("Portfolio Compatibility Notes", ""),
                    accent=accent_from_status(row.get("Portfolio Compatibility Action", "")),
                )

            with st.expander("View full compatibility table", expanded=False):
                compact_dataframe(compatibility_df, height=520)

            st.divider()
            st.subheader("🌱 Fresh Candidates Not Currently Held")
            fresh_candidates_df = find_fresh_candidates(stock_master_df, portfolio_df)
            if fresh_candidates_df is not None and not fresh_candidates_df.empty:
                for _, row in fresh_candidates_df.head(10).iterrows():
                    record_card(
                        title=row.get("Stock", "Unknown"),
                        kicker="Fresh Candidate",
                        fields=[
                            ("Engines", row.get("Engines Present", "NA")),
                            ("Screeners", row.get("Screeners Present", "NA")),
                            ("Best Conviction", row.get("Best Conviction Level", "NA")),
                            ("Score", f"{safe_value(row.get('Best Conviction Score', 0))}/100"),
                            ("Action", row.get("Final Allocation Action", "NA")),
                        ],
                        note=row.get("Combined Notes", ""),
                        accent="#1f6feb",
                    )
            else:
                alert_box("No fresh candidates outside the current portfolio.", "info")
        else:
            alert_box("Portfolio uploaded, but compatibility view is not ready. Upload screener files again in the same session.", "warning")

        st.divider()
        st.subheader("📊 Holdings")
        compact_dataframe(portfolio_df, height=420)

        if "Sector" in portfolio_df.columns and "Current Value" in portfolio_df.columns:
            st.subheader("Sector Exposure")
            sector_df = portfolio_df.groupby("Sector", as_index=False)["Current Value"].sum()
            total_current = sector_df["Current Value"].sum()
            sector_df["Sector Weight %"] = sector_df["Current Value"] / total_current * 100 if total_current > 0 else 0
            compact_dataframe(sector_df.sort_values("Sector Weight %", ascending=False), height=260)

        if "Market Cap Category" in portfolio_df.columns and "Current Value" in portfolio_df.columns:
            st.subheader("Market Cap Exposure")
            mcap_df = portfolio_df.groupby("Market Cap Category", as_index=False)["Current Value"].sum()
            total_current = mcap_df["Current Value"].sum()
            mcap_df["Market Cap Weight %"] = mcap_df["Current Value"] / total_current * 100 if total_current > 0 else 0
            compact_dataframe(mcap_df.sort_values("Market Cap Weight %", ascending=False), height=260)


# ==================================================
# 7. Decision Journal
# ==================================================
with tabs[6]:
    section_intro(
        "Decision Journal",
        "Audit trail for every important investment decision. This is where the system becomes repeatable and reviewable.",
        "Behavioural discipline",
    )

    journal_df = load_decision_journal()
    journal_summary = summarize_decision_journal(journal_df)
    show_metric_grid(
        [
            ("Total Decisions", journal_summary["total_decisions"]),
            ("Buy Actions", journal_summary["buy_actions"]),
            ("Hold Actions", journal_summary["hold_actions"]),
            ("Trim Actions", journal_summary["trim_actions"]),
            ("Exit Actions", journal_summary["exit_actions"]),
            ("Guard Actions", journal_summary["guard_actions"]),
        ],
        columns=3,
    )

    st.subheader("📝 Journal Table")
    if journal_df.empty:
        alert_box("No decision journal entries yet. Keep the tab visible; we will automate entries in a later build.", "info")
    else:
        compact_dataframe(journal_df, height=520)

    template_df = pd.DataFrame(
        columns=[
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
    )
    st.download_button(
        "Download blank decision journal template",
        data=template_df.to_csv(index=False).encode("utf-8"),
        file_name="decision_log_template.csv",
        mime="text/csv",
    )



# ==================================================
# 8. AI Analyst
# ==================================================
with tabs[7]:
    section_intro(
        "AI Analyst",
        "Rules-based analyst layer that converts the system output into a practical review queue.",
        "Analyst Layer",
    )

    combined_df = get_active_combined_df()
    stock_master_df = get_active_stock_master_df()
    portfolio_df = get_active_portfolio_df()
    compatibility_df = st.session_state.get("portfolio_compatibility_df", None)

    def row_value(row: pd.Series, *columns: str, default: Any = "NA") -> Any:
        """Safely fetch the first available non-empty value from a row."""
        for column in columns:
            if column in row.index:
                value = row.get(column)
                try:
                    if pd.isna(value):
                        continue
                except Exception:
                    pass
                if str(value).strip() != "":
                    return value
        return default

    def sort_if_present(df: pd.DataFrame, columns: list[str], ascending: list[bool]) -> pd.DataFrame:
        available_cols = [column for column in columns if column in df.columns]
        if not available_cols:
            return df
        available_ascending = [ascending[columns.index(column)] for column in available_cols]
        return df.sort_values(available_cols, ascending=available_ascending)

    def percent_value(value: Any) -> Any:
        text = safe_value(value, default="NA")
        if text in ["NA", ""] or "%" in text:
            return text
        return f"{text}%"

    def score_value(value: Any) -> Any:
        text = safe_value(value, default="NA")
        if text in ["NA", ""] or "/" in text:
            return text
        return f"{text}/100"

    market_regime = engine_a_result.get("regime", "UNKNOWN")
    market_tone = "Supportive" if engine_a_score >= 70 else "Selective" if engine_a_score >= 50 else "Defensive"
    market_comment = (
        "Market gate is supportive. Fresh deployment may be considered only where stock-level risk and conviction are also aligned."
        if engine_a_score >= 70
        else "Market gate is selective. Prioritise only the strongest candidates and avoid weak risk-reward setups."
        if engine_a_score >= 50
        else "Market gate is defensive. Preserve capital, restrict fresh deployment, and prioritise exits, guards, and review items."
    )

    record_card(
        "Market Analyst Brief",
        kicker="AI Analyst Layer",
        fields=[
            ("Engine A Score", f"{engine_a_score}/100"),
            ("Market Regime", market_regime),
            ("Analyst Tone", market_tone),
        ],
        note=market_comment,
        badges=["Market Gate", market_tone],
        accent="#2563eb",
    )

    if stock_master_df is None and combined_df is None and portfolio_df is None:
        alert_box("Upload screener files and portfolio CSV to generate AI Analyst output.", "warning")

    if stock_master_df is not None and not stock_master_df.empty:
        st.markdown("### 🎯 Analyst Priority Queue")
        analyst_candidates = stock_master_df.copy()
        analyst_candidates = sort_if_present(
            analyst_candidates,
            ["Best Conviction Score", "Appearance Count", "Highest Suggested Position %"],
            [False, False, False],
        )

        for _, row in analyst_candidates.head(8).iterrows():
            stock_name = row_value(row, "Stock", default="Unknown Stock")
            conviction = row_value(row, "Best Conviction Level", "Conviction Level", default="NA")
            score = row_value(row, "Best Conviction Score", "Conviction Score", default="NA")
            action = row_value(row, "Final Allocation Action", "Position Action", default="Review")
            risk = row_value(row, "Worst Risk Level", "Risk Level", default="NA")
            screeners = row_value(row, "Screeners Present", "Screener", default="NA")
            engines = row_value(row, "Engines Present", "Engine", default="NA")
            appearances = row_value(row, "Appearance Count", default="NA")
            position_size = row_value(row, "Highest Suggested Position %", "Suggested Position Size %", default="NA")
            master_note = row_value(row, "Combined Notes", "Conviction Notes", "Position Sizing Reason", default="")

            if safe_value(master_note, default="") == "":
                master_note = (
                    f"Appears in engine(s): {engines}. Screeners: {screeners}. "
                    f"Best conviction: {conviction} with score {score}. "
                    f"Suggested position: {position_size}%. Worst risk level: {risk}."
                )

            record_card(
                stock_name,
                kicker="Analyst Priority Candidate",
                fields=[
                    ("Conviction", conviction),
                    ("Score", score_value(score)),
                    ("Action", action),
                    ("Risk", risk),
                    ("Engines", engines),
                    ("Appearances", appearances),
                    ("Suggested Position", percent_value(position_size)),
                    ("Screeners", screeners),
                ],
                note=master_note,
                badges=[conviction, action, risk],
                accent=accent_from_status(action if safe_value(action) != "NA" else conviction),
            )
    else:
        alert_box("Stock Master is not available yet. Upload the 5 screener files first.", "warning")

    if combined_df is not None and not combined_df.empty:
        st.markdown("### 🛡️ Analyst Risk Queue")
        risk_df = combined_df.copy()
        if "Risk Score" in risk_df.columns:
            risk_df = risk_df.sort_values("Risk Score", ascending=False)
        elif "Risk Level" in risk_df.columns:
            risk_df["_risk_order"] = risk_df["Risk Level"].astype(str).str.upper().map(
                {"CRITICAL": 4, "HIGH": 3, "MODERATE": 2, "LOW": 1}
            ).fillna(0)
            risk_df = risk_df.sort_values("_risk_order", ascending=False)

        for _, row in risk_df.head(6).iterrows():
            risk_level = row_value(row, "Risk Level", default="NA")
            risk_score = row_value(row, "Risk Score", default="NA")
            exit_verdict = row_value(row, "Exit Verdict", default="NA")
            rule_verdict = row_value(row, "Rule Verdict", default="NA")
            screener = row_value(row, "Screener", default="NA")
            note = row_value(
                row,
                "Risk Notes",
                "Risk Note",
                "Exit Reason",
                default="Review valuation, trend, leverage, and exit verdict before deployment.",
            )

            record_card(
                row_value(row, "Stock", default="Unknown Stock"),
                kicker=f"Engine {row_value(row, 'Engine', default='NA')} | {screener}",
                fields=[
                    ("Risk Level", risk_level),
                    ("Risk Score", score_value(risk_score)),
                    ("Exit Verdict", exit_verdict),
                    ("Rule Verdict", rule_verdict),
                ],
                note=note,
                badges=[risk_level, exit_verdict],
                accent=accent_from_status(risk_level),
            )

    if portfolio_df is not None and not portfolio_df.empty:
        st.markdown("### 💼 Portfolio Analyst Brief")
        invested_value = portfolio_df["Invested Value"].sum() if "Invested Value" in portfolio_df.columns else 0
        current_value = portfolio_df["Current Value"].sum() if "Current Value" in portfolio_df.columns else 0
        pnl = current_value - invested_value
        pnl_pct = (pnl / invested_value * 100) if invested_value else 0

        record_card(
            "Portfolio Health Snapshot",
            kicker="Portfolio Analyst",
            fields=[
                ("Invested Value", f"₹{invested_value:,.0f}"),
                ("Current Value", f"₹{current_value:,.0f}"),
                ("Unrealised P&L", f"₹{pnl:,.0f} ({pnl_pct:.2f}%)"),
                ("Holdings", len(portfolio_df)),
            ],
            note="Portfolio view should be interpreted with concentration risk, sector exposure, and compatibility output.",
            badges=["Portfolio", "Risk Review"],
            accent="#7c3aed",
        )

        for flag in portfolio_risk_flags(portfolio_df)[:5]:
            alert_box(flag, "warning")

    if isinstance(compatibility_df, pd.DataFrame) and not compatibility_df.empty:
        st.markdown("### 🧩 Compatibility Analyst Notes")
        top_compat = compatibility_df.copy()
        top_compat = sort_if_present(
            top_compat,
            ["Portfolio Compatibility Score", "Portfolio Weight %"],
            [True, False],
        )
        for _, row in top_compat.head(8).iterrows():
            status = row_value(row, "Portfolio Status", default="NA")
            master_conviction = row_value(row, "Master Conviction Level", default="NA")
            master_action = row_value(row, "Master Allocation Action", default="NA")
            compatibility_score = row_value(row, "Portfolio Compatibility Score", default="NA")
            compatibility_action = row_value(row, "Portfolio Compatibility Action", default="Review")
            compatibility_note = row_value(
                row,
                "Portfolio Compatibility Notes",
                default="Review holding against current stock master view.",
            )

            record_card(
                row_value(row, "Stock", default="Unknown Stock"),
                kicker="Portfolio Compatibility",
                fields=[
                    ("Portfolio Weight", percent_value(row_value(row, "Portfolio Weight %", default="NA"))),
                    ("Status", status),
                    ("Master Conviction", master_conviction),
                    ("Master Action", master_action),
                    ("Compatibility Score", score_value(compatibility_score)),
                    ("Action", compatibility_action),
                ],
                note=compatibility_note,
                badges=[status, compatibility_action],
                accent=accent_from_status(compatibility_action),
            )


# ==================================================
# 9. System Status
# ==================================================
with tabs[8]:
    section_intro(
        "System Status",
        "Build map and module readiness. This helps keep the system disciplined before adding more intelligence layers.",
        "Control panel",
    )

    modules_df = pd.DataFrame(
        [
            {"Module": "White Premium UI", "Status": f"Connected {APP_VERSION}"},
            {"Module": "Navigation Tabs", "Status": "Connected v1.4.1"},
            {"Module": "Engine A Market Gate", "Status": "Connected v0.2"},
            {"Module": "Engine B Momentum", "Status": "Rules Connected"},
            {"Module": "Engine C Value", "Status": "Rules Connected"},
            {"Module": "Engine D Compounders", "Status": "Rules Connected"},
            {"Module": "Exit Engine", "Status": "Connected v0.1"},
            {"Module": "Risk Engine", "Status": "Connected v0.1"},
            {"Module": "Conviction Engine", "Status": "Connected v0.2"},
            {"Module": "Position Sizing Engine", "Status": "Connected v0.1"},
            {"Module": "Stock Master View", "Status": "Connected v0.1"},
            {"Module": "Portfolio Compatibility", "Status": "Connected v0.1"},
            {"Module": "Decision Journal", "Status": "Connected v0.1"},
            {"Module": "AI Analyst Layer", "Status": "Column mapping fixed v0.2"},
            {"Module": "Persistent Data Storage", "Status": "Connected v0.1"},
        ]
    )
    compact_dataframe(modules_df, height=520)
    alert_box("v1.4.1 AI Analyst column mapping fixed. Previous dashboard modules and tab visibility fixes are preserved.", "success")
