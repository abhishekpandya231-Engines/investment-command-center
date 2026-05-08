from core.portfolio_compatibility import (
    evaluate_portfolio_holdings,
    find_fresh_candidates,
    summarize_portfolio_compatibility,
)
import streamlit as st
import pandas as pd
import html
from datetime import datetime

from core.stock_master import (
    create_stock_master_view,
    summarize_stock_master,
)
from core.exit_engine import evaluate_exit
from core.engine_a import calculate_engine_a_score, default_engine_a_inputs
from core.risk_engine import (
    apply_stock_risk,
    evaluate_screener_risk_summary,
    evaluate_portfolio_risk_summary,
)
from core.position_sizing import (
    apply_position_sizing,
    summarize_position_sizing,
)
from core.conviction_engine import (
    apply_conviction_engine,
    summarize_conviction,
)
from core.decision_journal import load_decision_journal, summarize_decision_journal

# --------------------------------------------------
# Page Setup
# --------------------------------------------------
st.set_page_config(
    page_title="Investment Command Center",
    page_icon="📊",
    layout="wide"
)


# --------------------------------------------------
# Premium White Theme + Compact Pro UI
# --------------------------------------------------
st.markdown(
    """
    <style>
        :root {
            --icc-bg: #F6F8FC;
            --icc-card: #FFFFFF;
            --icc-border: #E5E7EB;
            --icc-text: #111827;
            --icc-muted: #6B7280;
            --icc-navy: #0B1F3A;
            --icc-blue: #2563EB;
            --icc-green: #047857;
            --icc-amber: #B45309;
            --icc-red: #B91C1C;
            --icc-gold: #B08D57;
        }

        .stApp {
            background: linear-gradient(180deg, #FFFFFF 0%, var(--icc-bg) 100%) !important;
            color: var(--icc-text) !important;
        }

        [data-testid="stAppViewContainer"] {
            background: linear-gradient(180deg, #FFFFFF 0%, var(--icc-bg) 100%) !important;
        }

        [data-testid="stHeader"] {
            background: rgba(255, 255, 255, 0.88) !important;
            backdrop-filter: blur(10px);
            border-bottom: 1px solid var(--icc-border);
        }

        [data-testid="block-container"] {
            max-width: 1180px;
            padding-top: 2rem;
            padding-bottom: 3rem;
        }

        h1, h2, h3 {
            color: var(--icc-navy) !important;
            letter-spacing: -0.03em;
            font-weight: 800 !important;
        }

        p, span, label, div {
            color: inherit;
        }

        div[data-testid="stMetric"] {
            background: var(--icc-card);
            border: 1px solid var(--icc-border);
            border-radius: 20px;
            padding: 18px 18px 16px 18px;
            box-shadow: 0 12px 28px rgba(15, 23, 42, 0.06);
            min-height: 118px;
        }

        div[data-testid="stMetricLabel"] {
            color: var(--icc-muted) !important;
            font-weight: 700;
            font-size: 0.88rem;
        }

        div[data-testid="stMetricValue"] {
            color: var(--icc-navy) !important;
            font-weight: 850;
            letter-spacing: -0.04em;
        }

        div[data-testid="stAlert"] {
            border-radius: 18px;
            border: 1px solid var(--icc-border);
            box-shadow: 0 10px 24px rgba(15, 23, 42, 0.05);
        }

        .stTabs [data-baseweb="tab-list"] {
            gap: 10px;
            background: #EEF2F7;
            padding: 8px;
            border-radius: 18px;
            border: 1px solid var(--icc-border);
        }

        .stTabs [data-baseweb="tab"] {
            height: 48px;
            background: #FFFFFF;
            border-radius: 14px;
            border: 1px solid #E5E7EB;
            color: var(--icc-navy);
            font-weight: 750;
            padding-left: 18px;
            padding-right: 18px;
        }

        .stTabs [aria-selected="true"] {
            background: var(--icc-navy) !important;
            color: #FFFFFF !important;
            border-color: var(--icc-navy) !important;
        }

        div[data-testid="stDataFrame"] {
            border: 1px solid var(--icc-border);
            border-radius: 18px;
            overflow: hidden;
            box-shadow: 0 10px 24px rgba(15, 23, 42, 0.05);
            background: #FFFFFF;
        }

        [data-testid="stFileUploader"] {
            background: #FFFFFF;
            border: 1px dashed #CBD5E1;
            border-radius: 20px;
            padding: 12px;
            box-shadow: 0 8px 20px rgba(15, 23, 42, 0.04);
        }

        button[kind="primary"], .stDownloadButton button, .stButton button {
            border-radius: 14px !important;
            border: 1px solid var(--icc-navy) !important;
            background: var(--icc-navy) !important;
            color: #FFFFFF !important;
            font-weight: 750 !important;
        }

        hr {
            border-color: #E5E7EB !important;
            margin-top: 2rem !important;
            margin-bottom: 2rem !important;
        }

        section[data-testid="stSidebar"] {
            background: #FFFFFF !important;
            border-right: 1px solid var(--icc-border);
        }

        .icc-hero {
            background: radial-gradient(circle at top left, rgba(37, 99, 235, 0.12), transparent 28%),
                        linear-gradient(135deg, #FFFFFF 0%, #F8FAFC 55%, #EEF2FF 100%);
            border: 1px solid var(--icc-border);
            border-radius: 28px;
            padding: 28px 28px 24px 28px;
            box-shadow: 0 18px 44px rgba(15, 23, 42, 0.08);
            margin-bottom: 22px;
        }

        .icc-hero-title {
            color: var(--icc-navy);
            font-size: clamp(2.2rem, 5vw, 4rem);
            line-height: 0.98;
            font-weight: 900;
            letter-spacing: -0.055em;
            margin: 0;
        }

        .icc-hero-subtitle {
            color: var(--icc-muted);
            font-size: 1.05rem;
            font-weight: 650;
            margin-top: 12px;
        }

        .icc-pill-row {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-top: 18px;
        }

        .icc-pill {
            border-radius: 999px;
            padding: 8px 12px;
            background: #FFFFFF;
            border: 1px solid #DDE3EA;
            color: var(--icc-navy);
            font-weight: 750;
            font-size: 0.86rem;
        }

        @media (max-width: 640px) {
            [data-testid="block-container"] {
                padding-left: 1rem;
                padding-right: 1rem;
                padding-top: 1.2rem;
            }

            div[data-testid="stMetric"] {
                min-height: 96px;
                padding: 14px;
                border-radius: 18px;
            }

            .icc-hero {
                padding: 22px 20px;
                border-radius: 22px;
            }

            .stTabs [data-baseweb="tab"] {
                height: 44px;
                padding-left: 12px;
                padding-right: 12px;
                font-size: 0.9rem;
            }
        }

        .icc-mobile-card {
            background: #FFFFFF;
            border: 1px solid #E5E7EB;
            border-radius: 22px;
            padding: 18px 18px 16px 18px;
            box-shadow: 0 14px 30px rgba(15, 23, 42, 0.065);
            margin: 14px 0;
        }

        .icc-mobile-card.good { border-left: 6px solid #047857; }
        .icc-mobile-card.warn { border-left: 6px solid #B45309; }
        .icc-mobile-card.danger { border-left: 6px solid #B91C1C; }
        .icc-mobile-card.info { border-left: 6px solid #2563EB; }

        .icc-card-kicker {
            color: #64748B;
            font-size: 0.78rem;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-bottom: 6px;
        }

        .icc-card-title {
            color: #0B1F3A;
            font-size: 1.18rem;
            font-weight: 900;
            letter-spacing: -0.025em;
            line-height: 1.18;
            margin-bottom: 12px;
        }

        .icc-card-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 10px;
            margin: 12px 0;
        }

        .icc-card-field {
            background: #F8FAFC;
            border: 1px solid #E5E7EB;
            border-radius: 14px;
            padding: 10px;
        }

        .icc-card-label {
            color: #64748B;
            font-size: 0.74rem;
            font-weight: 800;
            margin-bottom: 4px;
        }

        .icc-card-value {
            color: #0B1F3A;
            font-size: 0.95rem;
            font-weight: 850;
            line-height: 1.28;
            word-break: break-word;
        }

        .icc-card-note {
            color: #334155;
            font-size: 0.92rem;
            font-weight: 600;
            line-height: 1.55;
            margin-top: 12px;
            background: #F8FAFC;
            border: 1px solid #E5E7EB;
            border-radius: 14px;
            padding: 12px;
        }

        .icc-card-badge-row {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 10px;
        }

        .icc-card-badge {
            background: #EEF2FF;
            border: 1px solid #DBEAFE;
            color: #1D4ED8;
            border-radius: 999px;
            padding: 6px 10px;
            font-size: 0.78rem;
            font-weight: 850;
        }

        .icc-section-card {
            background: #FFFFFF;
            border: 1px solid #E5E7EB;
            border-radius: 24px;
            padding: 22px;
            box-shadow: 0 14px 34px rgba(15, 23, 42, 0.06);
            margin: 18px 0 22px 0;
        }

        .icc-section-title {
            color: #0B1F3A;
            font-size: 1.4rem;
            font-weight: 900;
            letter-spacing: -0.035em;
            margin-bottom: 8px;
        }

        .icc-section-subtitle {
            color: #6B7280;
            font-size: 0.98rem;
            font-weight: 650;
            line-height: 1.55;
        }

        @media (max-width: 640px) {
            .icc-card-grid { grid-template-columns: 1fr; }
            .icc-mobile-card { border-radius: 20px; padding: 16px; }
            .icc-card-title { font-size: 1.08rem; }
        }


        /* v1.2.4 clean mobile override */
        .icc-card-grid {
            grid-template-columns: 1fr !important;
            overflow: hidden !important;
        }

        .icc-mobile-card,
        .icc-card-field,
        .icc-card-note {
            overflow-wrap: anywhere !important;
            word-break: normal !important;
        }

        @media (min-width: 900px) {
            .icc-card-grid {
                grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
            }
        }


        /* v1.2.4 Compact Pro UI override */
        .icc-mobile-card {
            border-radius: 18px !important;
            padding: 14px 14px 13px 14px !important;
            margin: 10px 0 14px 0 !important;
            box-shadow: 0 10px 22px rgba(15, 23, 42, 0.055) !important;
        }

        .icc-mobile-card.good { border-left: 5px solid #047857 !important; }
        .icc-mobile-card.warn { border-left: 5px solid #B45309 !important; }
        .icc-mobile-card.danger { border-left: 5px solid #B91C1C !important; }
        .icc-mobile-card.info { border-left: 5px solid #2563EB !important; }

        .icc-card-kicker {
            font-size: 0.68rem !important;
            letter-spacing: 0.11em !important;
            margin-bottom: 5px !important;
        }

        .icc-card-title {
            font-size: 1.02rem !important;
            line-height: 1.16 !important;
            margin-bottom: 9px !important;
        }

        .icc-card-grid {
            display: grid !important;
            grid-template-columns: 1fr !important;
            gap: 6px !important;
            margin: 8px 0 !important;
        }

        .icc-card-field {
            display: grid !important;
            grid-template-columns: 38% minmax(0, 1fr) !important;
            align-items: start !important;
            column-gap: 8px !important;
            background: #F8FAFC !important;
            border: 1px solid #E5E7EB !important;
            border-radius: 12px !important;
            padding: 8px 10px !important;
            min-height: auto !important;
        }

        .icc-card-label {
            font-size: 0.68rem !important;
            line-height: 1.25 !important;
            margin-bottom: 0 !important;
            color: #64748B !important;
        }

        .icc-card-value {
            font-size: 0.82rem !important;
            line-height: 1.3 !important;
            text-align: right !important;
            overflow-wrap: anywhere !important;
        }

        .icc-card-badge-row {
            gap: 6px !important;
            margin-top: 8px !important;
        }

        .icc-card-badge {
            font-size: 0.68rem !important;
            padding: 5px 8px !important;
        }

        .icc-card-note {
            font-size: 0.82rem !important;
            line-height: 1.42 !important;
            padding: 9px 10px !important;
            margin-top: 9px !important;
            border-radius: 12px !important;
        }

        @media (max-width: 640px) {
            h1 { font-size: 2.25rem !important; line-height: 1.03 !important; }
            h2 { font-size: 2.0rem !important; line-height: 1.05 !important; }
            h3 { font-size: 1.65rem !important; line-height: 1.08 !important; }

            .icc-card-field {
                grid-template-columns: 40% minmax(0, 1fr) !important;
            }

            div[data-testid="stMetric"] {
                min-height: 88px !important;
            }
        }

        @media (min-width: 900px) {
            .icc-card-grid {
                grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
            }
        }

    </style>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------
# Session Helpers
# --------------------------------------------------
def get_active_stock_master_df():
    """Return Stock Master View from Streamlit session state if available."""
    stock_master_df = st.session_state.get("stock_master_df", None)

    if stock_master_df is not None:
        try:
            if not stock_master_df.empty:
                return stock_master_df
        except Exception:
            pass

    return None


def save_stock_master_to_session(stock_master_df):
    """Persist Stock Master View across tabs and reruns."""
    if stock_master_df is not None and not stock_master_df.empty:
        st.session_state["stock_master_df"] = stock_master_df.copy()
        st.session_state["stock_master_ready"] = True



def safe_card_value(value, default="NA"):
    """Return a display-safe value for HTML cards."""
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


def esc(value, default="NA"):
    """HTML escape a value for premium cards."""
    return html.escape(safe_card_value(value, default=default))


def render_section_card(title, subtitle):
    """Render a premium section intro card."""
    st.markdown(
        f"""
        <div class="icc-section-card">
            <div class="icc-section-title">{html.escape(str(title))}</div>
            <div class="icc-section-subtitle">{html.escape(str(subtitle))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )




def render_mobile_card(title, kicker="", fields=None, note="", tone="info", badges=None):
    """Render a compact mobile-first premium card without raw HTML leakage."""
    fields = fields or []
    badges = badges or []

    def short_text(value, max_chars=210):
        text = safe_card_value(value, default="")
        text = " ".join(str(text).split())
        if len(text) <= max_chars:
            return text
        return text[:max_chars].rsplit(" ", 1)[0] + " ..."

    field_parts = []
    for label, value in fields:
        field_parts.append(
            '<div class="icc-card-field">'
            f'<div class="icc-card-label">{html.escape(str(label))}</div>'
            f'<div class="icc-card-value">{esc(value)}</div>'
            '</div>'
        )
    field_html = "".join(field_parts)

    badge_html = ""
    if badges:
        badge_items = "".join(
            f'<span class="icc-card-badge">{esc(badge)}</span>'
            for badge in badges
            if safe_card_value(badge, default="") != ""
        )
        if badge_items:
            badge_html = f'<div class="icc-card-badge-row">{badge_items}</div>'

    note_html = ""
    if note:
        safe_note = html.escape(short_text(note, max_chars=220))
        note_html = f'<div class="icc-card-note">{safe_note}</div>'

    safe_tone = html.escape(str(tone))
    card_html = (
        f'<div class="icc-mobile-card {safe_tone}">'
        f'<div class="icc-card-kicker">{html.escape(str(kicker))}</div>'
        f'<div class="icc-card-title">{html.escape(str(title))}</div>'
        f'<div class="icc-card-grid">{field_html}</div>'
        f'{badge_html}'
        f'{note_html}'
        '</div>'
    )

    st.markdown(card_html, unsafe_allow_html=True)


# --------------------------------------------------
# Helper Functions
# --------------------------------------------------
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
    "ROE Ann  %",
    "Piotroski Score",
    "Durability Score",
    "Momentum Score",
    "Total Debt to Total Equity Ann ",
    "Net Profit Ann  YoY Growth %",
    "Net Profit 3Y Growth %",
    "Revenue QoQ Growth %",
    "1Y Low",
    "1Y High",
    "NSE Code",
]


def clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(col).strip() for col in df.columns]
    return df


def to_number(series):
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


def classify_market_cap(market_cap_value) -> str:
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

    for col in [
        "LTP",
        "Market Cap",
        "PE TTM",
        "PEG TTM",
        "ROE Ann  %",
        "Piotroski Score",
        "Durability Score",
        "Momentum Score",
        "Total Debt to Total Equity Ann ",
        "Net Profit Ann  YoY Growth %",
        "Net Profit 3Y Growth %",
        "Revenue QoQ Growth %",
        "1Y Low",
        "1Y High",
    ]:
        if col in df.columns:
            df[col] = to_number(df[col])

    return df


def generate_screener_verdict(row) -> str:
    engine = row.get("Engine", "Unknown")

    durability = row.get("Durability Score", None)
    momentum = row.get("Momentum Score", None)
    pe = row.get("PE TTM", None)
    peg = row.get("PEG TTM", None)
    roe = row.get("ROE Ann  %", None)
    pio = row.get("Piotroski Score", None)
    debt = row.get("Total Debt to Total Equity Ann ", None)
    growth = row.get("Net Profit Ann  YoY Growth %", None)

    try:
        durability = float(durability)
    except Exception:
        durability = None

    try:
        momentum = float(momentum)
    except Exception:
        momentum = None

    try:
        pe = float(pe)
    except Exception:
        pe = None

    try:
        peg = float(peg)
    except Exception:
        peg = None

    try:
        roe = float(roe)
    except Exception:
        roe = None

    try:
        pio = float(pio)
    except Exception:
        pio = None

    try:
        debt = float(debt)
    except Exception:
        debt = None

    try:
        growth = float(growth)
    except Exception:
        growth = None

    if engine == "B":
        if durability is not None and momentum is not None:
            if durability > 55 and momentum > 59:
                return "GREEN GATE"
            if durability < 45 or momentum < 49:
                return "RED GATE"
            return "GREY GATE"
        return "DATA CHECK"

    if engine == "C":
        if roe is not None and pe is not None and pio is not None:
            if roe > 15 and pe < 25 and pio > 6:
                return "VALUE QUALIFIED"
            return "VALUE WATCH"
        return "DATA CHECK"

    if engine == "D":
        if roe is not None and pio is not None and debt is not None and growth is not None:
            if roe > 15 and pio > 6 and debt < 1 and growth > 15:
                if peg is not None and peg <= 1.5:
                    return "COMPOUNDER QUALIFIED"
                return "GROWTH QUALIFIED"
            return "COMPOUNDER WATCH"
        return "DATA CHECK"

    return "UNCLASSIFIED"


def apply_exit_engine(df: pd.DataFrame, engine_a_score: float) -> pd.DataFrame:
    df = df.copy()

    exit_results = df.apply(
        lambda row: evaluate_exit(row, engine_a_score=engine_a_score),
        axis=1,
    )

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


def portfolio_risk_flags(df: pd.DataFrame) -> list:
    flags = []

    if "Portfolio Weight %" in df.columns:
        high_stock = df[df["Portfolio Weight %"] > 10]
        for _, row in high_stock.iterrows():
            flags.append(f"{row['Stock']} is {row['Portfolio Weight %']:.1f}% of portfolio. Single-stock cap check required.")

    if "Sector" in df.columns:
        sector = df.groupby("Sector", as_index=False)["Current Value"].sum()
        total = sector["Current Value"].sum()
        sector["Sector Weight %"] = sector["Current Value"] / total * 100 if total > 0 else 0
        high_sector = sector[sector["Sector Weight %"] > 30]
        for _, row in high_sector.iterrows():
            flags.append(f"{row['Sector']} is {row['Sector Weight %']:.1f}% of portfolio. Sector concentration check required.")

    if "Market Cap Category" in df.columns:
        mcap = df.groupby("Market Cap Category", as_index=False)["Current Value"].sum()
        total = mcap["Current Value"].sum()
        mcap["Market Cap Weight %"] = mcap["Current Value"] / total * 100 if total > 0 else 0
        small = mcap[mcap["Market Cap Category"].str.lower() == "small cap"]
        if not small.empty and small.iloc[0]["Market Cap Weight %"] > 50:
            flags.append(f"Small-cap exposure is {small.iloc[0]['Market Cap Weight %']:.1f}%, above 50% threshold.")

    if not flags:
        flags.append("No major concentration risk flags detected.")

    return flags


# --------------------------------------------------
# Header
# --------------------------------------------------
st.markdown(
    """
    <div class="icc-hero">
        <div class="icc-hero-title">📊 Investment<br>Command Center</div>
        <div class="icc-hero-subtitle">Rules-Based Portfolio Intelligence System | v1.2.4</div>
        <div class="icc-pill-row">
            <div class="icc-pill">White Premium UI</div>
            <div class="icc-pill">Rules-Based</div>
            <div class="icc-pill">Portfolio Intelligence</div>
            <div class="icc-pill">Mobile Optimised</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.divider()

# --------------------------------------------------
# Engine A Inputs
# --------------------------------------------------
defaults = default_engine_a_inputs()

st.sidebar.title("⚙️ Engine A Market Gate")
st.sidebar.caption("Manual inputs for now. Later we can automate selected fields.")

with st.sidebar.expander("Engine A Inputs", expanded=True):
    nifty_pe = st.number_input("Nifty PE", value=float(defaults["nifty_pe"]), step=0.1)
    nifty_above_200dma = st.selectbox("Nifty above 200 DMA?", ["Yes", "No"], index=0)
    breadth = st.number_input("% Stocks Above 200 DMA", value=float(defaults["percent_stocks_above_200dma"]), step=1.0)
    india_vix = st.number_input("India VIX", value=float(defaults["india_vix"]), step=0.1)
    fii_30d = st.number_input("FII 30D Flow ₹ Cr", value=float(defaults["fii_30d"]), step=500.0)
    dii_30d = st.number_input("DII 30D Flow ₹ Cr", value=float(defaults["dii_30d"]), step=500.0)
    rbi_stance = st.selectbox("RBI Stance", ["Accommodative", "Neutral", "Withdrawal", "Tightening"], index=1)
    cpi = st.number_input("CPI %", value=float(defaults["cpi"]), step=0.1)
    pmi = st.number_input("PMI", value=float(defaults["pmi"]), step=0.1)
    us_10y = st.number_input("US 10Y Yield %", value=float(defaults["us_10y"]), step=0.1)
    dxy = st.number_input("DXY", value=float(defaults["dxy"]), step=0.1)
    inr_change_percent = st.number_input("INR Change %", value=float(defaults["inr_change_percent"]), step=0.1)
    brent_crude = st.number_input("Brent Crude", value=float(defaults["brent_crude"]), step=1.0)

engine_a_inputs = {
    "nifty_pe": nifty_pe,
    "nifty_above_200dma": nifty_above_200dma,
    "percent_stocks_above_200dma": breadth,
    "india_vix": india_vix,
    "fii_30d": fii_30d,
    "dii_30d": dii_30d,
    "rbi_stance": rbi_stance,
    "cpi": cpi,
    "pmi": pmi,
    "us_10y": us_10y,
    "dxy": dxy,
    "inr_change_percent": inr_change_percent,
    "brent_crude": brent_crude,
}

engine_a_result = calculate_engine_a_score(engine_a_inputs)
engine_a_score = engine_a_result["score"]

# --------------------------------------------------
# System Status
# --------------------------------------------------
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("System Version", "v1.2.4")

with col2:
    st.metric("Build Stage", "Compact Pro UI")

with col3:
    st.metric("Last Updated", datetime.now().strftime("%d %b %Y"))

st.divider()

# --------------------------------------------------
# Engine A Summary
# --------------------------------------------------
st.subheader("🧠 Engine A Market Gate")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Engine A Score", f"{engine_a_result['score']}/100")

with col2:
    st.metric("Regime", engine_a_result["regime"])

with col3:
    st.metric("Equity Allocation", f"{engine_a_result['equity_allocation_percent']}%")

with col4:
    st.metric("Debt / Gold", f"{engine_a_result['debt_allocation_percent']}% / {engine_a_result['gold_allocation_percent']}%")

st.info(engine_a_result["action"])

component_df = pd.DataFrame(
    {
        "Component": list(engine_a_result["component_scores"].keys()),
        "Score": list(engine_a_result["component_scores"].values()),
    }
)

with st.expander("View Engine A Component Scores"):
    st.dataframe(component_df, use_container_width=True)

if engine_a_result["safety_overrides"]:
    st.warning("Safety override triggered.")
    st.dataframe(pd.DataFrame(engine_a_result["safety_overrides"]), use_container_width=True)
else:
    st.success("No Engine A safety override triggered.")

st.divider()

# --------------------------------------------------
# Tabs
# --------------------------------------------------
tab1, tab2, tab3 = st.tabs(["📂 Screener Intelligence", "💼 Portfolio Command", "🧾 Decision Journal"])

# --------------------------------------------------
# Screener Upload Tab
# --------------------------------------------------
with tab1:
    render_section_card("Screener Intelligence", "Upload Trendlyne screener files to build risk, conviction, position sizing and Stock Master intelligence.")

    st.subheader("📂 Multi-Screener Upload")

    st.write(
        """
        Upload your Trendlyne screener CSV files here.

        Supported files:
        **Mom.csv, C1.csv, C2.csv, D1.csv, D2.csv**

        This section is for **screener intelligence**, not holdings-level portfolio P&L.
        """
    )

    screener_files = st.file_uploader(
        "Upload multiple screener CSV files",
        type=["csv"],
        accept_multiple_files=True,
        key="screener_files",
    )

    if screener_files:
        all_screeners = []

        for uploaded_file in screener_files:
            raw_df = pd.read_csv(uploaded_file)
            prepared_df = prepare_screener_df(raw_df, uploaded_file.name)
            prepared_df["Rule Verdict"] = prepared_df.apply(generate_screener_verdict, axis=1)
            prepared_df = apply_exit_engine(prepared_df, engine_a_score=engine_a_score)
            all_screeners.append(prepared_df)

        combined_df = pd.concat(all_screeners, ignore_index=True)
        combined_df = apply_stock_risk(combined_df)
        combined_df = apply_conviction_engine(
            combined_df,
            market_regime=engine_a_result["regime"],
        )
        combined_df = apply_position_sizing(
            combined_df,
            engine_a_score=engine_a_score,
            market_regime=engine_a_result["regime"],
        )

        stock_master_df = create_stock_master_view(combined_df)
        save_stock_master_to_session(stock_master_df)

        st.success(f"{len(screener_files)} screener file(s) uploaded successfully.")
        st.success("Stock Master View saved for Portfolio Compatibility.")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Screener Rows", len(combined_df))

        with col2:
            st.metric("Unique Stocks", combined_df["Stock"].nunique())

        with col3:
            st.metric("Exit / Guard", int(combined_df["Exit Verdict"].isin(["EXIT", "GUARD"]).sum()))

        with col4:
            st.metric("Ride / Trim", int(combined_df["Exit Verdict"].isin(["RIDE", "TRIM"]).sum()))

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Momentum Rows", int((combined_df["Engine"] == "B").sum()))

        with col2:
            st.metric("Value Rows", int((combined_df["Engine"] == "C").sum()))

        with col3:
            st.metric("Compounder Rows", int((combined_df["Engine"] == "D").sum()))

        st.divider()

        st.subheader("🛡️ Risk Engine Summary")

        risk_summary = evaluate_screener_risk_summary(combined_df)

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Critical Risk", risk_summary["critical_count"])

        with col2:
            st.metric("High Risk", risk_summary["high_count"])

        with col3:
            st.metric("Small-Cap Rows", risk_summary["small_cap_count"])

        with col4:
            st.metric("High Debt Rows", risk_summary["high_debt_count"])

        risk_level_df = (
            combined_df.groupby(["Engine", "Risk Level"], as_index=False)
            .size()
            .rename(columns={"size": "Count"})
            .sort_values(["Engine", "Risk Level"])
        )

        with st.expander("View risk level count table"):
            st.dataframe(risk_level_df, use_container_width=True)

        st.divider()

        st.subheader("🧨 High / Moderate Risk Watchlist")

        risk_watchlist_df = combined_df[
            combined_df["Risk Level"].isin(["HIGH", "CRITICAL", "MODERATE"])
        ].copy()

        risk_watchlist_columns = [
            "Stock",
            "Engine",
            "Screener",
            "Risk Level",
            "Risk Score",
            "Risk Notes",
            "Exit Verdict",
            "Rule Verdict",
            "Market Cap Category",
            "PE TTM",
            "PEG TTM",
            "ROE Ann  %",
            "Piotroski Score",
            "Total Debt to Total Equity Ann ",
            "Durability Score",
            "Momentum Score",
            "Net Profit Ann  YoY Growth %",
            "Revenue QoQ Growth %",
        ]

        risk_watchlist_columns = [
            col for col in risk_watchlist_columns if col in risk_watchlist_df.columns
        ]

        if not risk_watchlist_df.empty:
            sorted_risk_watchlist_df = risk_watchlist_df[risk_watchlist_columns].sort_values(
                ["Risk Level", "Risk Score", "Stock"],
                ascending=[True, False, True],
            )

            for _, watch_row in sorted_risk_watchlist_df.head(5).iterrows():
                render_mobile_card(
                    title=watch_row.get("Stock", "Unknown"),
                    kicker=f"Engine {watch_row.get('Engine', 'NA')} | {watch_row.get('Screener', 'NA')}",
                    fields=[
                        ("Risk Level", watch_row.get("Risk Level", "NA")),
                        ("Risk Score", f"{watch_row.get('Risk Score', 'NA')}/100"),
                        ("Exit Verdict", watch_row.get("Exit Verdict", "NA")),
                        ("Rule Verdict", watch_row.get("Rule Verdict", "NA")),
                    ],
                    note=watch_row.get("Risk Notes", ""),
                    tone="danger" if watch_row.get("Risk Level", "") in ["HIGH", "CRITICAL"] else "warn",
                    badges=[watch_row.get("Risk Level", "NA"), watch_row.get("Exit Verdict", "NA")],
                )

            with st.expander("View full high/moderate risk watchlist table"):
                st.dataframe(sorted_risk_watchlist_df, use_container_width=True)

            st.divider()

            st.subheader("🧾 Top Risk Notes")

            top_risk_notes_df = sorted_risk_watchlist_df.head(5)

            for _, risk_row in top_risk_notes_df.iterrows():
                stock_name = risk_row.get("Stock", "Unknown")
                engine_name = risk_row.get("Engine", "Unknown")
                screener_name = risk_row.get("Screener", "Unknown")
                risk_level = risk_row.get("Risk Level", "Unknown")
                risk_score = risk_row.get("Risk Score", "NA")
                risk_notes = risk_row.get("Risk Notes", "No risk notes available.")
                exit_verdict = risk_row.get("Exit Verdict", "NA")

                render_mobile_card(
                    title=stock_name,
                    kicker=f"Engine {engine_name} | {screener_name}",
                    fields=[
                        ("Risk Level", risk_level),
                        ("Risk Score", f"{risk_score}/100"),
                        ("Exit Verdict", exit_verdict),
                        ("Rule Verdict", risk_row.get("Rule Verdict", "NA")),
                    ],
                    note=risk_notes,
                    tone="danger" if risk_level in ["HIGH", "CRITICAL"] else "warn",
                    badges=[risk_level, screener_name],
                )
        else:
            st.success("No moderate/high/critical risk rows detected.")

        st.divider()

        st.subheader("🧠 Conviction Engine Summary")

        conviction_summary = summarize_conviction(combined_df)

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("High Conviction", conviction_summary["high_conviction"])

        with col2:
            st.metric("Strong", conviction_summary["strong"])

        with col3:
            st.metric("Medium", conviction_summary["medium"])

        with col4:
            st.metric("Watchlist", conviction_summary["watchlist"])

        conviction_level_df = (
            combined_df.groupby(["Engine", "Conviction Level"], as_index=False)
            .size()
            .rename(columns={"size": "Count"})
            .sort_values(["Engine", "Conviction Level"])
        )

        with st.expander("View conviction level count table"):
            st.dataframe(conviction_level_df, use_container_width=True)

        st.divider()

        st.subheader("🏆 Top Conviction Candidates")

        conviction_candidate_columns = [
            "Stock",
            "Engine",
            "Screener",
            "Conviction Score",
            "Conviction Level",
            "Conviction Notes",
            "Rule Verdict",
            "Exit Verdict",
            "Risk Level",
            "Risk Score",
            "Suggested Position Size %",
            "Position Action",
            "Market Cap Category",
            "PE TTM",
            "ROE Ann  %",
            "Piotroski Score",
            "Durability Score",
            "Momentum Score",
        ]

        conviction_candidate_columns = [
            col for col in conviction_candidate_columns if col in combined_df.columns
        ]

        top_conviction_df = combined_df[
            combined_df["Conviction Level"].isin(["HIGH CONVICTION", "STRONG", "MEDIUM"])
        ].copy()

        if not top_conviction_df.empty:
            sorted_top_conviction_df = top_conviction_df[conviction_candidate_columns].sort_values(
                ["Conviction Score", "Risk Score"],
                ascending=[False, True],
            )

            for _, conviction_row in sorted_top_conviction_df.head(5).iterrows():
                conviction_level = conviction_row.get("Conviction Level", "NA")

                render_mobile_card(
                    title=conviction_row.get("Stock", "Unknown"),
                    kicker=f"Engine {conviction_row.get('Engine', 'NA')} | {conviction_row.get('Screener', 'NA')}",
                    fields=[
                        ("Conviction", conviction_level),
                        ("Conviction Score", f"{conviction_row.get('Conviction Score', 'NA')}/100"),
                        ("Risk Level", conviction_row.get("Risk Level", "NA")),
                        ("Exit Verdict", conviction_row.get("Exit Verdict", "NA")),
                        ("Suggested Position", f"{conviction_row.get('Suggested Position Size %', 'NA')}%"),
                        ("Action", conviction_row.get("Position Action", "NA")),
                    ],
                    note=conviction_row.get("Conviction Notes", ""),
                    tone="good" if conviction_level == "HIGH CONVICTION" else "info",
                    badges=[conviction_level, conviction_row.get("Rule Verdict", "NA")],
                )

            with st.expander("View full conviction candidates table"):
                st.dataframe(sorted_top_conviction_df, use_container_width=True)
        else:
            st.info("No medium/strong/high-conviction candidates detected.")

        st.divider()

        st.subheader("📏 Position Sizing Engine Summary")

        sizing_summary = summarize_position_sizing(combined_df)

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Track Only", sizing_summary["track_only"])

        with col2:
            st.metric("Starter Positions", sizing_summary["starter_position"])

        with col3:
            st.metric("Normal Positions", sizing_summary["normal_position"])

        with col4:
            st.metric("Avoid / Exit", sizing_summary["avoid_or_exit"])

        position_action_df = (
            combined_df.groupby(["Engine", "Position Action"], as_index=False)
            .size()
            .rename(columns={"size": "Count"})
            .sort_values(["Engine", "Position Action"])
        )

        with st.expander("View position action count table"):
            st.dataframe(position_action_df, use_container_width=True)

        st.divider()

        st.subheader("🎯 Top Position Candidates")

        position_candidates_df = combined_df[
            combined_df["Suggested Position Size %"] > 0
        ].copy()

        position_candidate_columns = [
            "Stock",
            "Engine",
            "Screener",
            "Rule Verdict",
            "Exit Verdict",
            "Risk Level",
            "Risk Score",
            "Conviction Score",
            "Conviction Level",
            "Conviction Notes",
            "Suggested Position Size %",
            "Max Position Cap %",
            "Position Action",
            "Position Sizing Reason",
            "Market Cap Category",
            "PE TTM",
            "ROE Ann  %",
            "Piotroski Score",
            "Durability Score",
            "Momentum Score",
        ]

        position_candidate_columns = [
            col for col in position_candidate_columns if col in position_candidates_df.columns
        ]

        if not position_candidates_df.empty:
            sorted_position_candidates_df = position_candidates_df[position_candidate_columns].sort_values(
                ["Suggested Position Size %", "Risk Score"],
                ascending=[False, True],
            )

            with st.expander("View full position candidates table"):
                st.dataframe(sorted_position_candidates_df, use_container_width=True)

            st.divider()

            st.subheader("🧾 Top Allocation Notes")

            top_allocation_notes_df = sorted_position_candidates_df.head(5)

            for _, position_row in top_allocation_notes_df.iterrows():
                stock_name = position_row.get("Stock", "Unknown")
                engine_name = position_row.get("Engine", "Unknown")
                screener_name = position_row.get("Screener", "Unknown")
                conviction_level = position_row.get("Conviction Level", "Unknown")
                conviction_score = position_row.get("Conviction Score", "NA")

                if conviction_level == "Unknown" and "Conviction" in str(position_row.get("Position Sizing Reason", "")):
                    sizing_reason_text = str(position_row.get("Position Sizing Reason", ""))
                    try:
                        conviction_level = sizing_reason_text.split("Conviction ")[1].split(" with multiplier")[0]
                    except Exception:
                        conviction_level = "Unknown"
                risk_level = position_row.get("Risk Level", "Unknown")
                risk_score = position_row.get("Risk Score", "NA")
                exit_verdict = position_row.get("Exit Verdict", "NA")
                suggested_position = position_row.get("Suggested Position Size %", "NA")
                max_cap = position_row.get("Max Position Cap %", "NA")
                position_action = position_row.get("Position Action", "NA")
                sizing_reason = position_row.get("Position Sizing Reason", "No sizing reason available.")

                render_mobile_card(
                    title=stock_name,
                    kicker=f"Engine {engine_name} | {screener_name}",
                    fields=[
                        ("Conviction", conviction_level),
                        ("Conviction Score", f"{conviction_score}/100"),
                        ("Risk Level", risk_level),
                        ("Risk Score", f"{risk_score}/100"),
                        ("Exit Verdict", exit_verdict),
                        ("Suggested Position", f"{suggested_position}%"),
                        ("Max Cap", f"{max_cap}%"),
                        ("Action", position_action),
                    ],
                    note=sizing_reason,
                    tone="good" if str(position_action).upper() in ["HIGH CONVICTION POSITION", "NORMAL POSITION"] else "info",
                    badges=[position_action, screener_name],
                )
        else:
            st.info("No positive position-size candidates detected.")

        st.divider()

        st.subheader("🧬 Stock Master View")

        stock_master_summary = summarize_stock_master(stock_master_df)

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Master Stocks", stock_master_summary["unique_stocks"])

        with col2:
            st.metric("High Conviction", stock_master_summary["high_conviction"])

        with col3:
            st.metric("Normal Positions", stock_master_summary["normal_position"])

        with col4:
            st.metric("Track Only", stock_master_summary["track_only"])

        stock_master_display_columns = [
            "Stock",
            "Engines Present",
            "Screeners Present",
            "Appearance Count",
            "Best Conviction Score",
            "Best Conviction Level",
            "Highest Suggested Position %",
            "Final Allocation Action",
            "Best Risk Level",
            "Worst Risk Level",
            "Exit Verdicts",
            "Combined Notes",
        ]

        stock_master_display_columns = [
            column for column in stock_master_display_columns
            if column in stock_master_df.columns
        ]

        stock_master_display_df = stock_master_df[stock_master_display_columns].copy()

        for _, master_row in stock_master_display_df.head(5).iterrows():
            action_value = master_row.get("Final Allocation Action", "NA")

            render_mobile_card(
                title=master_row.get("Stock", "Unknown"),
                kicker="Stock Master View",
                fields=[
                    ("Engines", master_row.get("Engines Present", "NA")),
                    ("Screeners", master_row.get("Screeners Present", "NA")),
                    ("Appearances", master_row.get("Appearance Count", "NA")),
                    ("Best Conviction", master_row.get("Best Conviction Level", "NA")),
                    ("Conviction Score", master_row.get("Best Conviction Score", "NA")),
                    ("Suggested Position", f"{master_row.get('Highest Suggested Position %', 'NA')}%"),
                    ("Final Action", action_value),
                    ("Worst Risk", master_row.get("Worst Risk Level", "NA")),
                    ("Exit Verdicts", master_row.get("Exit Verdicts", "NA")),
                ],
                note=master_row.get("Combined Notes", ""),
                tone="good" if "HIGH" in str(action_value).upper() or "NORMAL" in str(action_value).upper() else "info",
                badges=[master_row.get("Best Conviction Level", "NA"), action_value],
            )

        with st.expander("View full Stock Master table"):
            st.dataframe(stock_master_display_df, use_container_width=True)

        st.divider()

        st.subheader("🚦 Exit Engine Verdict Summary")

        verdict_summary = (
            combined_df.groupby(["Engine", "Exit Verdict"], as_index=False)
            .size()
            .rename(columns={"size": "Count"})
            .sort_values(["Engine", "Exit Verdict"])
        )

        with st.expander("View exit verdict summary table"):
            st.dataframe(verdict_summary, use_container_width=True)

        st.divider()

        st.subheader("🔥 Cross-Engine Overlap")

        overlap_df = (
            combined_df.groupby("Stock", as_index=False)
            .agg(
                Engines=("Engine", lambda x: ", ".join(sorted(set(x)))),
                Screeners=("Screener", lambda x: ", ".join(sorted(set(x)))),
                Count=("Screener", "nunique"),
                Sector=("Sector", "first"),
                LTP=("LTP", "first"),
                Market_Cap=("Market Cap", "first"),
                PE=("PE TTM", "first"),
                PEG=("PEG TTM", "first"),
                ROE=("ROE Ann  %", "first"),
                Piotroski=("Piotroski Score", "first"),
                Durability=("Durability Score", "first"),
                Momentum=("Momentum Score", "first"),
                Exit_Verdicts=("Exit Verdict", lambda x: ", ".join(sorted(set(x)))),
            )
            .sort_values(["Count", "Market_Cap"], ascending=[False, False])
        )

        power_picks = overlap_df[overlap_df["Count"] >= 2]

        if not power_picks.empty:
            st.success("Stocks appearing in multiple screeners detected.")

            for _, overlap_row in power_picks.head(5).iterrows():
                render_mobile_card(
                    title=overlap_row.get("Stock", "Unknown"),
                    kicker="Cross-Engine Overlap",
                    fields=[
                        ("Engines", overlap_row.get("Engines", "NA")),
                        ("Screeners", overlap_row.get("Screeners", "NA")),
                        ("Overlap Count", overlap_row.get("Count", "NA")),
                        ("Sector", overlap_row.get("Sector", "NA")),
                    ],
                    note="This stock appears in multiple screeners and should be reviewed as a possible higher-priority candidate.",
                    tone="info",
                    badges=[overlap_row.get("Engines", "NA")],
                )

            with st.expander("View full cross-engine overlap table"):
                st.dataframe(power_picks, use_container_width=True)
        else:
            st.info("No multi-screener overlaps detected yet.")

        st.divider()

        st.subheader("🚨 Exit / Guard Watchlist")

        watchlist_df = combined_df[
            combined_df["Exit Verdict"].isin(["EXIT", "GUARD", "FREEZE"])
        ].copy()

        watchlist_columns = [
            "Stock",
            "Engine",
            "Screener",
            "Rule Verdict",
            "Exit Verdict",
            "Exit Reason",
            "Durability Score",
            "Momentum Score",
            "Piotroski Score",
            "ROE Ann  %",
            "PE TTM",
            "PEG TTM",
            "Total Debt to Total Equity Ann ",
            "Net Profit Ann  YoY Growth %",
            "Revenue QoQ Growth %",
            "Risk Level",
            "Risk Score",
            "Risk Notes",
        ]

        watchlist_columns = [col for col in watchlist_columns if col in watchlist_df.columns]

        if not watchlist_df.empty:
            with st.expander("View Exit / Guard watchlist table"):
                st.dataframe(
                    watchlist_df[watchlist_columns].sort_values(["Exit Verdict", "Stock"]),
                    use_container_width=True,
                )
        else:
            st.success("No Exit/Guard items detected at current Engine A score.")

        st.divider()

        st.subheader("📊 Combined Screener Table")

        available_cols = [col for col in SCREENER_KEY_COLUMNS if col in combined_df.columns]

        display_cols = [
            "Source File",
            "Engine",
            "Screener",
            "Rule Verdict",
            "Exit Verdict",
            "Exit Reason",
        ] + available_cols + ["Market Cap Category"]

        with st.expander("View full combined screener table"):
            st.dataframe(
                combined_df[display_cols],
                use_container_width=True,
            )

        st.divider()

        st.subheader("🧭 Screener Sector Exposure")

        if "Sector" in combined_df.columns:
            sector_counts = (
                combined_df.groupby(["Engine", "Sector"], as_index=False)
                .size()
                .rename(columns={"size": "Stock Count"})
                .sort_values("Stock Count", ascending=False)
            )
            with st.expander("View screener sector exposure table"):
                st.dataframe(sector_counts, use_container_width=True)

    else:
        st.info("Upload Mom.csv, C1.csv, C2.csv, D1.csv, and D2.csv to begin screener intelligence.")

# --------------------------------------------------
# Portfolio Upload Tab
# --------------------------------------------------
with tab2:
    render_section_card("Portfolio Command", "Upload holdings to compare your actual portfolio against current system signals, risk limits and fresh candidates.")

    st.subheader("📁 Portfolio Upload")

    st.write(
        """
        Upload your holdings-level portfolio CSV here.

        Required columns:

        **Stock, Engine, Sector, Market Cap Category, Quantity, Buy Price, Current Price**
        """
    )

    portfolio_file = st.file_uploader(
        "Upload portfolio CSV",
        type=["csv"],
        accept_multiple_files=False,
        key="portfolio_file",
    )

    if portfolio_file is not None:
        portfolio_df = clean_columns(pd.read_csv(portfolio_file))

        missing_columns = [
            column for column in PORTFOLIO_REQUIRED_COLUMNS if column not in portfolio_df.columns
        ]

        if missing_columns:
            st.error("Your uploaded file is missing required portfolio columns:")
            st.write(missing_columns)
            st.warning("This looks like a screener CSV, not a holdings portfolio CSV. Please upload screener files in the Screener Intelligence tab.")
        else:
            portfolio_df = calculate_portfolio_from_holdings(portfolio_df)
            portfolio_df = apply_exit_engine(portfolio_df, engine_a_score=engine_a_score)
            portfolio_df = apply_stock_risk(portfolio_df)
            portfolio_df = apply_conviction_engine(
                portfolio_df,
                market_regime=engine_a_result["regime"],
            )
            portfolio_df = apply_position_sizing(
                portfolio_df,
                engine_a_score=engine_a_score,
                market_regime=engine_a_result["regime"],
            )

            invested_value = portfolio_df["Invested Value"].sum()
            current_value = portfolio_df["Current Value"].sum()
            pnl = current_value - invested_value
            pnl_pct = (pnl / invested_value * 100) if invested_value > 0 else 0

            st.success("Portfolio uploaded successfully.")

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("Invested Value", f"₹{invested_value:,.0f}")

            with col2:
                st.metric("Current Value", f"₹{current_value:,.0f}")

            with col3:
                st.metric("Unrealised P&L", f"₹{pnl:,.0f}", f"{pnl_pct:.2f}%")

            with col4:
                st.metric("Positions", len(portfolio_df))

            st.divider()

            st.subheader("🚦 Portfolio Exit Verdicts")
            verdict_counts = (
                portfolio_df.groupby("Exit Verdict", as_index=False)
                .size()
                .rename(columns={"size": "Count"})
            )
            with st.expander("View portfolio exit verdict table"):
                st.dataframe(verdict_counts, use_container_width=True)

            st.divider()

            st.subheader("🛡️ Portfolio Risk Engine")

            portfolio_risk = evaluate_portfolio_risk_summary(portfolio_df)

            col1, col2 = st.columns(2)

            with col1:
                st.metric("Portfolio Risk Level", portfolio_risk["portfolio_risk_level"])

            with col2:
                st.metric("Portfolio Risk Score", f"{portfolio_risk['risk_score']}/100")

            for note in portfolio_risk["notes"]:
                if portfolio_risk["portfolio_risk_level"] in ["HIGH", "CRITICAL"]:
                    st.warning(note)
                else:
                    st.info(note)

            st.divider()

            st.subheader("📏 Portfolio Position Sizing")

            portfolio_sizing_summary = summarize_position_sizing(portfolio_df)

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Starter Positions", portfolio_sizing_summary["starter_position"])

            with col2:
                st.metric("Normal Positions", portfolio_sizing_summary["normal_position"])

            with col3:
                st.metric("Avoid / Exit", portfolio_sizing_summary["avoid_or_exit"])

            st.divider()

            st.subheader("📊 Holdings")
            with st.expander("View uploaded holdings table"):
                st.dataframe(portfolio_df, use_container_width=True)

            st.divider()

            st.subheader("🧩 Portfolio Compatibility Engine")

            active_stock_master_df = get_active_stock_master_df()

            if active_stock_master_df is not None and not active_stock_master_df.empty:
                st.success("Stock Master View is available for portfolio compatibility.")
                st.metric("Stock Master Rows Available", len(active_stock_master_df))
            else:
                st.warning("Stock Master View is not loaded in this session. Upload the 5 screener CSV files first.")

            portfolio_compatibility_df = evaluate_portfolio_holdings(
                portfolio_df,
                active_stock_master_df,
            )

            compatibility_summary = summarize_portfolio_compatibility(portfolio_compatibility_df)

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("Holdings", compatibility_summary["holdings"])

            with col2:
                st.metric("Matched", compatibility_summary["matched"])

            with col3:
                st.metric("Core / Add", compatibility_summary["core_hold_or_add"])

            with col4:
                st.metric("Track / Reduce", compatibility_summary["track_or_reduce"])

            with st.expander("View full portfolio compatibility table"):
                st.dataframe(portfolio_compatibility_df, use_container_width=True)

            st.divider()

            st.subheader("🧾 Portfolio Action Notes")

            top_portfolio_notes_df = portfolio_compatibility_df.head(3)

            for _, holding_row in top_portfolio_notes_df.iterrows():
                stock_name = holding_row.get("Stock", "Unknown")
                weight = holding_row.get("Portfolio Weight %", "NA")
                status = holding_row.get("Portfolio Status", "NA")
                master_conviction = holding_row.get("Master Conviction Level", "NA")
                master_action = holding_row.get("Master Allocation Action", "NA")
                score = holding_row.get("Portfolio Compatibility Score", "NA")
                action = holding_row.get("Portfolio Compatibility Action", "NA")
                notes = holding_row.get("Portfolio Compatibility Notes", "No notes available.")

                action_upper = str(action).upper()
                if "CORE" in action_upper or "ADD" in action_upper:
                    note_tone = "good"
                elif "TRACK" in action_upper or "REDUCE" in action_upper or "REVIEW" in action_upper or "CONCENTRATION" in action_upper:
                    note_tone = "warn"
                else:
                    note_tone = "info"

                render_mobile_card(
                    title=stock_name,
                    kicker="Portfolio Action Note",
                    fields=[
                        ("Portfolio Weight", f"{weight}%"),
                        ("Status", status),
                        ("Master Conviction", master_conviction),
                        ("Master Action", master_action),
                        ("Compatibility Score", f"{score}/100"),
                        ("Action", action),
                    ],
                    note=notes,
                    tone=note_tone,
                    badges=[status, action],
                )

            st.divider()

            st.subheader("🌱 Fresh Candidates Not Currently Held")

            fresh_candidates_df = find_fresh_candidates(
                active_stock_master_df if "active_stock_master_df" in locals() else get_active_stock_master_df(),
                portfolio_df,
            )

            if fresh_candidates_df is not None and not fresh_candidates_df.empty:
                fresh_candidate_columns = [
                    "Stock",
                    "Engines Present",
                    "Screeners Present",
                    "Appearance Count",
                    "Best Conviction Score",
                    "Best Conviction Level",
                    "Highest Suggested Position %",
                    "Final Allocation Action",
                    "Best Risk Level",
                    "Worst Risk Level",
                    "Exit Verdicts",
                ]

                fresh_candidate_columns = [
                    column for column in fresh_candidate_columns
                    if column in fresh_candidates_df.columns
                ]

                fresh_display_df = fresh_candidates_df[fresh_candidate_columns].head(25).copy()

                for _, fresh_row in fresh_display_df.head(5).iterrows():
                    action_value = fresh_row.get("Final Allocation Action", "NA")

                    render_mobile_card(
                        title=fresh_row.get("Stock", "Unknown"),
                        kicker="Fresh Candidate",
                        fields=[
                            ("Engines", fresh_row.get("Engines Present", "NA")),
                            ("Screeners", fresh_row.get("Screeners Present", "NA")),
                            ("Appearances", fresh_row.get("Appearance Count", "NA")),
                            ("Conviction", fresh_row.get("Best Conviction Level", "NA")),
                            ("Conviction Score", fresh_row.get("Best Conviction Score", "NA")),
                            ("Suggested Position", f"{fresh_row.get('Highest Suggested Position %', 'NA')}%"),
                            ("Action", action_value),
                            ("Worst Risk", fresh_row.get("Worst Risk Level", "NA")),
                            ("Exit Verdicts", fresh_row.get("Exit Verdicts", "NA")),
                        ],
                        note="Candidate appears in the current Stock Master View but is not present in uploaded portfolio holdings.",
                        tone="good" if "HIGH" in str(action_value).upper() or "NORMAL" in str(action_value).upper() else "info",
                        badges=[fresh_row.get("Best Conviction Level", "NA"), action_value],
                    )

                with st.expander("View full fresh candidates table"):
                    st.dataframe(fresh_display_df, use_container_width=True)
            else:
                st.info("Fresh candidates need screener files first, then portfolio file.")

            st.divider()

            col1, col2 = st.columns(2)

            with col1:
                st.write("### Sector Exposure")
                sector_df = portfolio_df.groupby("Sector", as_index=False)["Current Value"].sum()
                sector_df["Sector Weight %"] = sector_df["Current Value"] / current_value * 100 if current_value > 0 else 0
                with st.expander("View sector exposure table"):
                    st.dataframe(sector_df.sort_values("Sector Weight %", ascending=False), use_container_width=True)

            with col2:
                st.write("### Market Cap Exposure")
                mcap_df = portfolio_df.groupby("Market Cap Category", as_index=False)["Current Value"].sum()
                mcap_df["Market Cap Weight %"] = mcap_df["Current Value"] / current_value * 100 if current_value > 0 else 0
                with st.expander("View market cap exposure table"):
                    st.dataframe(mcap_df.sort_values("Market Cap Weight %", ascending=False), use_container_width=True)

            st.divider()

            st.subheader("🚨 Risk Flags")
            for flag in portfolio_risk_flags(portfolio_df):
                render_mobile_card(
                    title="Risk Flag",
                    kicker="Portfolio Risk",
                    fields=[],
                    note=flag,
                    tone="good" if "No major" in flag else "warn",
                )
    else:
        st.info("Upload a holdings-level portfolio CSV to begin.")

        st.subheader("Required Portfolio CSV Format")

        sample_df = pd.DataFrame(
            {
                "Stock": ["Example Stock"],
                "Engine": ["B"],
                "Sector": ["Industrials"],
                "Market Cap Category": ["Small Cap"],
                "Quantity": [10],
                "Buy Price": [100],
                "Current Price": [110],
            }
        )

        st.dataframe(sample_df, use_container_width=True)

st.divider()


# --------------------------------------------------
# Decision Journal Tab
# --------------------------------------------------
with tab3:
    render_section_card("Decision Journal", "Review the audit trail for decisions. Later this can become a full logging layer with one-click decision capture.")

    st.subheader("📝 Decision Journal")

    st.write(
        """
        This section shows the audit trail file stored at:

        **data/decision_log.csv**

        For now, it is a blank template. Later, we will add buttons to log decisions directly from the screener and portfolio tables.
        """
    )

    journal_df = load_decision_journal("data/decision_log.csv")
    journal_summary = summarize_decision_journal(journal_df)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Decisions", journal_summary["total_decisions"])

    with col2:
        st.metric("Buy Actions", journal_summary["buy_actions"])

    with col3:
        st.metric("Trim Actions", journal_summary["trim_actions"])

    with col4:
        st.metric("Exit Actions", journal_summary["exit_actions"])

    st.divider()

    if journal_df.empty:
        st.info("Decision journal is currently blank. This is correct for the first setup.")
    else:
        st.success("Decision journal loaded successfully.")

    if not journal_df.empty:
        for _, journal_row in journal_df.head(5).iterrows():
            render_mobile_card(
                title=journal_row.get("Stock", "Decision"),
                kicker=journal_row.get("Date", "Decision Journal"),
                fields=[(column, journal_row.get(column, "NA")) for column in journal_df.columns if column not in ["Stock", "Date"]][:6],
                note="",
                tone="info",
            )

        with st.expander("View full decision journal table"):
            st.dataframe(journal_df, use_container_width=True)
    else:
        st.dataframe(journal_df, use_container_width=True)

    csv_data = journal_df.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="Download Decision Journal CSV",
        data=csv_data,
        file_name="decision_log.csv",
        mime="text/csv",
    )

    st.warning(
        "Important: Streamlit Cloud cannot permanently write new rows back to GitHub automatically. "
        "For now, download the CSV after updates. Later we can connect a database or GitHub API."
    )


# --------------------------------------------------
# Build Roadmap
# --------------------------------------------------
st.subheader("Current Build Modules")

modules = pd.DataFrame(
    [
        {"Module": "Multi-Screener Upload", "Status": "Working"},
        {"Module": "Portfolio Command Center", "Status": "In Progress"},
        {"Module": "Exit Engine", "Status": "Connected v0.1"},
        {"Module": "Engine A Market Gate", "Status": "Connected v0.2 with G-sec"},
        {"Module": "Engine B Momentum", "Status": "Basic Rules"},
        {"Module": "Engine C Value", "Status": "Basic Rules"},
        {"Module": "Engine D Compounders", "Status": "Basic Rules"},
        {"Module": "Risk Engine", "Status": "Connected v0.1"},
        {"Module": "Position Sizing Engine", "Status": "Connected v0.1"},
        {"Module": "Conviction Engine", "Status": "Connected v0.1"},
        {"Module": "Decision Journal", "Status": "Connected v0.1"},
        {"Module": "AI Analyst Layer", "Status": "Not Started"},
    ]
)

with st.expander("View current build modules table"):
    st.dataframe(modules, use_container_width=True)

st.success("Clean mobile card layout v1.2.4 loaded successfully.")
