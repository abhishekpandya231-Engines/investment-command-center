import streamlit as st
import pandas as pd
import json
from pathlib import Path
from datetime import datetime

from core.exit_engine import evaluate_exit
from core.engine_a import calculate_engine_a_score, default_engine_a_inputs
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
# Constants
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

# --------------------------------------------------
# Helper Functions
# --------------------------------------------------
def load_manual_inputs_file():
    manual_file = Path("data/manual_inputs.json")

    if not manual_file.exists():
        return {
            "source_status": "Default code values; manual_inputs.json not found",
            "inputs": default_engine_a_inputs(),
            "metadata": {},
        }

    try:
        with open(manual_file, "r", encoding="utf-8") as file:
            data = json.load(file)

        engine_inputs = {}
        for key, details in data.get("engine_a_inputs", {}).items():
            engine_inputs[key] = details.get("value")

        return {
            "source_status": data.get("metadata", {}).get(
                "source_status",
                "Manual inputs; not live market data"
            ),
            "inputs": engine_inputs,
            "metadata": data.get("metadata", {}),
        }

    except Exception as error:
        return {
            "source_status": f"Error reading manual_inputs.json: {error}",
            "inputs": default_engine_a_inputs(),
            "metadata": {},
        }


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

    durability = pd.to_numeric(durability, errors="coerce")
    momentum = pd.to_numeric(momentum, errors="coerce")
    pe = pd.to_numeric(pe, errors="coerce")
    peg = pd.to_numeric(peg, errors="coerce")
    roe = pd.to_numeric(roe, errors="coerce")
    pio = pd.to_numeric(pio, errors="coerce")
    debt = pd.to_numeric(debt, errors="coerce")
    growth = pd.to_numeric(growth, errors="coerce")

    if engine == "B":
        if pd.notna(durability) and pd.notna(momentum):
            if durability > 55 and momentum > 59:
                return "GREEN GATE"
            if durability < 45 or momentum < 49:
                return "RED GATE"
            return "GREY GATE"
        return "DATA CHECK"

    if engine == "C":
        if pd.notna(roe) and pd.notna(pe) and pd.notna(pio):
            if roe > 15 and pe < 25 and pio > 6:
                return "VALUE QUALIFIED"
            return "VALUE WATCH"
        return "DATA CHECK"

    if engine == "D":
        if pd.notna(roe) and pd.notna(pio) and pd.notna(debt) and pd.notna(growth):
            if roe > 15 and pio > 6 and debt < 1 and growth > 15:
                if pd.notna(peg) and peg <= 1.5:
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
st.title("📊 Investment Command Center")
st.caption("Rules-Based Portfolio Intelligence System | v0.3")

# --------------------------------------------------
# Engine A Inputs
# --------------------------------------------------
manual_input_bundle = load_manual_inputs_file()
defaults = default_engine_a_inputs()
defaults.update(manual_input_bundle.get("inputs", {}))
engine_a_source_status = manual_input_bundle.get("source_status", "Manual inputs; not live market data")
engine_a_metadata = manual_input_bundle.get("metadata", {})

st.sidebar.title("⚙️ Engine A Market Gate")
st.sidebar.caption("Manual inputs for now. Later we can automate selected fields.")
st.sidebar.info(f"Source: {engine_a_source_status}")

with st.sidebar.expander("Engine A Inputs", expanded=True):
    nifty_pe = st.number_input("Nifty PE", value=float(defaults["nifty_pe"]), step=0.1)
    nifty_above_200dma = st.selectbox("Nifty above 200 DMA?", ["Yes", "No"], index=0 if str(defaults["nifty_above_200dma"]).lower() == "yes" else 1)
    breadth = st.number_input("% Stocks Above 200 DMA", value=float(defaults["percent_stocks_above_200dma"]), step=1.0)
    india_vix = st.number_input("India VIX", value=float(defaults["india_vix"]), step=0.1)
    fii_30d = st.number_input("FII 30D Flow ₹ Cr", value=float(defaults["fii_30d"]), step=500.0)
    dii_30d = st.number_input("DII 30D Flow ₹ Cr", value=float(defaults["dii_30d"]), step=500.0)
    rbi_options = ["Accommodative", "Neutral", "Withdrawal", "Tightening"]
    rbi_default_index = rbi_options.index(defaults["rbi_stance"]) if defaults["rbi_stance"] in rbi_options else 1
    rbi_stance = st.selectbox("RBI Stance", rbi_options, index=rbi_default_index)
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
st.divider()

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("System Version", "v0.3")

with col2:
    st.metric("Build Stage", "Engine A Connected")

with col3:
    st.metric("Last Updated", datetime.now().strftime("%d %b %Y"))

st.divider()

# --------------------------------------------------
# Engine A Summary
# --------------------------------------------------
st.subheader("🧠 Engine A Market Gate")

st.warning(f"Engine A Source: {engine_a_source_status}")
if engine_a_metadata.get("notes"):
    st.caption(engine_a_metadata.get("notes"))

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

with st.expander("View Engine A Manual Inputs Used"):
    inputs_used_df = pd.DataFrame(
        {
            "Input": list(engine_a_inputs.keys()),
            "Value": list(engine_a_inputs.values()),
        }
    )
    st.dataframe(inputs_used_df, use_container_width=True)

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
tab1, tab2, tab3 = st.tabs(["📂 Screener Upload", "📁 Portfolio Upload", "📝 Decision Journal"])

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

# --------------------------------------------------
# Decision Journal Tab
# --------------------------------------------------
with tab3:
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
            "Connected v0.1",
            "Basic Rules",
            "Basic Rules",
            "Basic Rules",
            "Connected v0.1",
            "Not Started",
        ],
    }
)

st.dataframe(modules, use_container_width=True)

st.success("Engine A Market Gate connection loaded successfully.")
