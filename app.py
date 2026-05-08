import streamlit as st
import pandas as pd
from datetime import datetime

from core.exit_engine import evaluate_exit

# --------------------------------------------------
# Page Setup
# --------------------------------------------------
st.set_page_config(
    page_title="Investment Command Center",
    page_icon="📊",
    layout="wide"
)


# --------------------------------------------------
# Premium White UI + Visible Tabs Patch v1.3.1
# --------------------------------------------------
st.markdown(
    """
    <style>
        :root {
            --icc-navy: #08213f;
            --icc-blue: #2563eb;
            --icc-slate: #64748b;
            --icc-line: #e5e7eb;
            --icc-card: #ffffff;
            --icc-bg: #f8fafc;
        }

        html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
            background: linear-gradient(180deg, #ffffff 0%, #f8fafc 55%, #ffffff 100%) !important;
            color: var(--icc-navy) !important;
        }

        [data-testid="stHeader"] {
            background: rgba(255,255,255,0.94) !important;
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

        /* Critical fix: Streamlit tabs render nested p/span/div elements.
           This forces selected tab text to stay white and visible on mobile. */
        .stTabs [data-baseweb="tab-list"] {
            gap: 6px;
            background: #ffffff !important;
            border: 1px solid #e5e7eb;
            border-radius: 999px;
            padding: 7px;
            box-shadow: 0 14px 32px rgba(8,33,63,0.07);
            overflow-x: auto;
            scrollbar-width: thin;
        }

        .stTabs [data-baseweb="tab"],
        .stTabs button[role="tab"] {
            border-radius: 999px !important;
            padding: 10px 15px !important;
            font-weight: 900 !important;
            color: #334155 !important;
            background: #ffffff !important;
            border: 1px solid transparent !important;
            white-space: nowrap !important;
        }

        .stTabs [data-baseweb="tab"] *,
        .stTabs button[role="tab"] *,
        .stTabs [data-baseweb="tab"] p,
        .stTabs button[role="tab"] p,
        .stTabs [data-baseweb="tab"] span,
        .stTabs button[role="tab"] span,
        .stTabs [data-baseweb="tab"] div,
        .stTabs button[role="tab"] div {
            color: #334155 !important;
            -webkit-text-fill-color: #334155 !important;
            opacity: 1 !important;
            visibility: visible !important;
            font-weight: 900 !important;
        }

        .stTabs [data-baseweb="tab"]:hover,
        .stTabs button[role="tab"]:hover {
            background: #f1f5f9 !important;
            border-color: #dbe3ef !important;
        }

        .stTabs [data-baseweb="tab"][aria-selected="true"],
        .stTabs button[role="tab"][aria-selected="true"] {
            background: var(--icc-navy) !important;
            color: #ffffff !important;
            border-color: var(--icc-navy) !important;
            box-shadow: 0 10px 22px rgba(8, 33, 63, 0.18);
        }

        .stTabs [data-baseweb="tab"][aria-selected="true"] *,
        .stTabs button[role="tab"][aria-selected="true"] *,
        .stTabs [data-baseweb="tab"][aria-selected="true"] p,
        .stTabs button[role="tab"][aria-selected="true"] p,
        .stTabs [data-baseweb="tab"][aria-selected="true"] span,
        .stTabs button[role="tab"][aria-selected="true"] span,
        .stTabs [data-baseweb="tab"][aria-selected="true"] div,
        .stTabs button[role="tab"][aria-selected="true"] div {
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
            opacity: 1 !important;
            visibility: visible !important;
            font-weight: 950 !important;
        }

        @media (max-width: 768px) {
            .block-container { padding-left: 1rem; padding-right: 1rem; }
            .stTabs [data-baseweb="tab"],
            .stTabs button[role="tab"] {
                padding: 9px 13px !important;
                min-width: max-content !important;
            }
        }
    </style>
    """,
    unsafe_allow_html=True,
)

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
    """
    Assumes Market Cap is in Rs Crore, as commonly exported by Trendlyne.
    """
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
    """
    Applies the central Exit Engine to every row.
    """
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
st.title("📊 Investment Command Center")
st.caption("Rules-Based Portfolio Intelligence System | v1.3.1")

st.divider()

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("System Version", "v1.3.1")

with col2:
    st.metric("Build Stage", "Tab Visibility Fix")

with col3:
    st.metric("Last Updated", datetime.now().strftime("%d %b %Y"))

st.divider()

# --------------------------------------------------
# Sidebar Controls
# --------------------------------------------------
st.sidebar.title("⚙️ System Controls")

engine_a_score = st.sidebar.slider(
    "Engine A Score",
    min_value=0,
    max_value=100,
    value=50,
    step=1,
)

st.sidebar.caption("Temporary manual score. Later this will come from Engine A Market Gate.")

if engine_a_score <= 20:
    market_regime = "EXIT"
elif engine_a_score <= 30:
    market_regime = "FREEZE"
elif engine_a_score <= 40:
    market_regime = "CAUTIOUS"
elif engine_a_score <= 52:
    market_regime = "ACTIVE"
elif engine_a_score <= 62:
    market_regime = "AGGRESSIVE"
else:
    market_regime = "FULL DEPLOY"

st.sidebar.metric("Market Regime", market_regime)

# --------------------------------------------------
# Tabs
# --------------------------------------------------
tab1, tab2 = st.tabs(["📂 Screener Upload", "📁 Portfolio Upload"])

# --------------------------------------------------
# Screener Upload Tab
# --------------------------------------------------
with tab1:
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

        st.success(f"{len(screener_files)} screener file(s) uploaded successfully.")

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

        st.subheader("🚦 Exit Engine Verdict Summary")

        verdict_summary = (
            combined_df.groupby(["Engine", "Exit Verdict"], as_index=False)
            .size()
            .rename(columns={"size": "Count"})
            .sort_values(["Engine", "Exit Verdict"])
        )

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
        ]

        watchlist_columns = [col for col in watchlist_columns if col in watchlist_df.columns]

        if not watchlist_df.empty:
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
            st.dataframe(sector_counts, use_container_width=True)

    else:
        st.info("Upload Mom.csv, C1.csv, C2.csv, D1.csv, and D2.csv to begin screener intelligence.")

# --------------------------------------------------
# Portfolio Upload Tab
# --------------------------------------------------
with tab2:
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
            st.warning("This looks like a screener CSV, not a holdings portfolio CSV. Please upload screener files in the Screener Upload tab.")
        else:
            portfolio_df = calculate_portfolio_from_holdings(portfolio_df)
            portfolio_df = apply_exit_engine(portfolio_df, engine_a_score=engine_a_score)

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
            st.dataframe(verdict_counts, use_container_width=True)

            st.divider()

            st.subheader("📊 Holdings")
            st.dataframe(portfolio_df, use_container_width=True)

            st.divider()

            col1, col2 = st.columns(2)

            with col1:
                st.write("### Sector Exposure")
                sector_df = portfolio_df.groupby("Sector", as_index=False)["Current Value"].sum()
                sector_df["Sector Weight %"] = sector_df["Current Value"] / current_value * 100 if current_value > 0 else 0
                st.dataframe(sector_df.sort_values("Sector Weight %", ascending=False), use_container_width=True)

            with col2:
                st.write("### Market Cap Exposure")
                mcap_df = portfolio_df.groupby("Market Cap Category", as_index=False)["Current Value"].sum()
                mcap_df["Market Cap Weight %"] = mcap_df["Current Value"] / current_value * 100 if current_value > 0 else 0
                st.dataframe(mcap_df.sort_values("Market Cap Weight %", ascending=False), use_container_width=True)

            st.divider()

            st.subheader("🚨 Risk Flags")
            for flag in portfolio_risk_flags(portfolio_df):
                if "No major" in flag:
                    st.success(flag)
                else:
                    st.warning(flag)
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
# Build Roadmap
# --------------------------------------------------
st.subheader("Current Build Modules")

modules = pd.DataFrame(
    {
        "Module": [
            "Multi-Screener Upload",
            "Portfolio Command Center",
            "Exit Engine",
            "Engine A Market Gate",
            "Engine B Momentum",
            "Engine C Value",
            "Engine D Compounders",
            "Decision Journal",
            "AI Analyst Layer",
        ],
        "Status": [
            "Working",
            "In Progress",
            "Connected v0.1",
            "Manual Slider",
            "Basic Rules",
            "Basic Rules",
            "Basic Rules",
            "Not Started",
            "Not Started",
        ],
    }
)

st.dataframe(modules, use_container_width=True)

st.success("Exit Engine connection loaded successfully.")
