import streamlit as st
import pandas as pd
from datetime import datetime

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
    st.metric("Build Stage", "Foundation")

with col3:
    st.metric("Last Updated", datetime.now().strftime("%d %b %Y"))

st.divider()

# --------------------------------------------------
# Main Intro
# --------------------------------------------------
st.subheader("Welcome")

st.write(
    """
    This dashboard will become the central command system for:

    - Engine A: Market Gate
    - Engine B: Momentum Hunter
    - Engine C: Value Warriors
    - Engine D: Compounders
    - Portfolio Context
    - Exit Engine
    - Decision Journal
    """
)

st.info("Next step: We will add portfolio upload and command center logic.")

# --------------------------------------------------
# Placeholder Section
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
            "Not Started",
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

st.success("Foundation app loaded successfully.")
