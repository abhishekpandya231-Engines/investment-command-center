import streamlit as st
import pandas as pd
from datetime import datetime

from core.portfolio_context import (
    validate_portfolio_columns,
    calculate_position_values,
    calculate_portfolio_summary,
    calculate_sector_exposure,
    calculate_market_cap_exposure,
    generate_portfolio_risk_flags,
)

# --------------------------------------------------
# Page Setup
# --------------------------------------------------
st.set_page_config(
    page_title="Investment Command Center",
    page_icon="📊",
    layout="wide"
)

# --------------------------------------------------
# Header
# --------------------------------------------------
st.title("📊 Investment Command Center")
st.caption("Rules-Based Portfolio Intelligence System | v1.0")

st.divider()

# --------------------------------------------------
# System Status
# --------------------------------------------------
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("System Version", "v1.0")

with col2:
    st.metric("Build Stage", "Portfolio Upload")

with col3:
    st.metric("Last Updated", datetime.now().strftime("%d %b %Y"))

st.divider()

# --------------------------------------------------
# Portfolio Upload Section
# --------------------------------------------------
st.subheader("📁 Portfolio Upload")

st.write(
    """
    Upload your portfolio CSV with the required columns:

    **Stock, Engine, Sector, Market Cap Category, Quantity, Buy Price, Current Price**
    """
)

uploaded_file = st.file_uploader(
    "Upload portfolio CSV",
    type=["csv"]
)

if uploaded_file is not None:
    portfolio_df = pd.read_csv(uploaded_file)

    missing_columns = validate_portfolio_columns(portfolio_df)

    if missing_columns:
        st.error("Your uploaded file is missing required columns:")
        st.write(missing_columns)
        st.stop()

    portfolio_df = calculate_position_values(portfolio_df)
    summary = calculate_portfolio_summary(portfolio_df)

    st.success("Portfolio uploaded successfully.")

    # --------------------------------------------------
    # Portfolio Summary
    # --------------------------------------------------
    st.subheader("📌 Portfolio Summary")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Invested Value",
            f"₹{summary['invested_value']:,.0f}"
        )

    with col2:
        st.metric(
            "Current Value",
            f"₹{summary['current_value']:,.0f}"
        )

    with col3:
        st.metric(
            "Unrealised P&L",
            f"₹{summary['unrealised_pnl']:,.0f}",
            f"{summary['pnl_percent']:.2f}%"
        )

    with col4:
        st.metric(
            "Positions",
            summary["number_of_positions"]
        )

    st.divider()

    # --------------------------------------------------
    # Holdings Table
    # --------------------------------------------------
    st.subheader("📊 Holdings")

    display_columns = [
        "Stock",
        "Engine",
        "Sector",
        "Market Cap Category",
        "Quantity",
        "Buy Price",
        "Current Price",
        "Invested Value",
        "Current Value",
        "Unrealised P&L",
        "P&L %",
    ]

    st.dataframe(
        portfolio_df[display_columns],
        use_container_width=True
    )

    st.divider()

    # --------------------------------------------------
    # Exposure Analysis
    # --------------------------------------------------
    st.subheader("🧭 Portfolio Exposure")

    sector_df = calculate_sector_exposure(portfolio_df)
    market_cap_df = calculate_market_cap_exposure(portfolio_df)

    col1, col2 = st.columns(2)

    with col1:
        st.write("### Sector Exposure")
        st.dataframe(sector_df, use_container_width=True)

    with col2:
        st.write("### Market Cap Exposure")
        st.dataframe(market_cap_df, use_container_width=True)

    st.divider()

    # --------------------------------------------------
    # Risk Flags
    # --------------------------------------------------
    st.subheader("🚨 Risk Flags")

    risk_flags = generate_portfolio_risk_flags(portfolio_df)

    for flag in risk_flags:
        if "No major" in flag:
            st.success(flag)
        else:
            st.warning(flag)

else:
    st.info("Upload a portfolio CSV to begin.")

    st.subheader("Required CSV Format")

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
            "In Progress",
            "Not Started",
            "Not Started",
            "Not Started",
            "Not Started",
            "Not Started",
            "Not Started",
            "Not Started",
        ],
    }
)

st.dataframe(modules, use_container_width=True)

st.success("Portfolio upload module loaded successfully.")
