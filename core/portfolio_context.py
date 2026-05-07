import pandas as pd


REQUIRED_PORTFOLIO_COLUMNS = [
    "Stock",
    "Engine",
    "Sector",
    "Market Cap Category",
    "Quantity",
    "Buy Price",
    "Current Price",
]


def validate_portfolio_columns(df: pd.DataFrame) -> list:
    """
    Checks whether uploaded portfolio file has the required columns.
    Returns a list of missing columns.
    """
    missing_columns = []

    for column in REQUIRED_PORTFOLIO_COLUMNS:
        if column not in df.columns:
            missing_columns.append(column)

    return missing_columns


def calculate_position_values(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds invested value, current value, P&L, and P&L percentage.
    """
    df = df.copy()

    df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce").fillna(0)
    df["Buy Price"] = pd.to_numeric(df["Buy Price"], errors="coerce").fillna(0)
    df["Current Price"] = pd.to_numeric(df["Current Price"], errors="coerce").fillna(0)

    df["Invested Value"] = df["Quantity"] * df["Buy Price"]
    df["Current Value"] = df["Quantity"] * df["Current Price"]
    df["Unrealised P&L"] = df["Current Value"] - df["Invested Value"]

    df["P&L %"] = df.apply(
        lambda row: (row["Unrealised P&L"] / row["Invested Value"] * 100)
        if row["Invested Value"] > 0
        else 0,
        axis=1,
    )

    return df


def calculate_portfolio_summary(df: pd.DataFrame) -> dict:
    """
    Calculates high-level portfolio summary.
    """
    df = calculate_position_values(df)

    invested_value = df["Invested Value"].sum()
    current_value = df["Current Value"].sum()
    unrealised_pnl = current_value - invested_value

    pnl_percent = (
        (unrealised_pnl / invested_value * 100)
        if invested_value > 0
        else 0
    )

    return {
        "invested_value": invested_value,
        "current_value": current_value,
        "unrealised_pnl": unrealised_pnl,
        "pnl_percent": pnl_percent,
        "number_of_positions": len(df),
    }


def calculate_stock_weights(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates each stock's percentage weight in the portfolio.
    """
    df = calculate_position_values(df)
    total_current_value = df["Current Value"].sum()

    df["Portfolio Weight %"] = df["Current Value"].apply(
        lambda value: (value / total_current_value * 100)
        if total_current_value > 0
        else 0
    )

    return df


def calculate_sector_exposure(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates sector-wise exposure.
    """
    df = calculate_position_values(df)

    sector_df = (
        df.groupby("Sector", as_index=False)["Current Value"]
        .sum()
        .sort_values("Current Value", ascending=False)
    )

    total_current_value = sector_df["Current Value"].sum()

    sector_df["Sector Weight %"] = sector_df["Current Value"].apply(
        lambda value: (value / total_current_value * 100)
        if total_current_value > 0
        else 0
    )

    return sector_df


def calculate_market_cap_exposure(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates market-cap-wise exposure.
    """
    df = calculate_position_values(df)

    market_cap_df = (
        df.groupby("Market Cap Category", as_index=False)["Current Value"]
        .sum()
        .sort_values("Current Value", ascending=False)
    )

    total_current_value = market_cap_df["Current Value"].sum()

    market_cap_df["Market Cap Weight %"] = market_cap_df["Current Value"].apply(
        lambda value: (value / total_current_value * 100)
        if total_current_value > 0
        else 0
    )

    return market_cap_df


def generate_portfolio_risk_flags(df: pd.DataFrame) -> list:
    """
    Generates basic portfolio risk flags.
    """
    flags = []

    weighted_df = calculate_stock_weights(df)
    sector_df = calculate_sector_exposure(df)
    market_cap_df = calculate_market_cap_exposure(df)

    # Single stock concentration
    high_weight_stocks = weighted_df[weighted_df["Portfolio Weight %"] > 10]
    for _, row in high_weight_stocks.iterrows():
        flags.append(
            f"Single stock concentration: {row['Stock']} is {row['Portfolio Weight %']:.1f}% of portfolio."
        )

    # Sector concentration
    high_sector_exposure = sector_df[sector_df["Sector Weight %"] > 30]
    for _, row in high_sector_exposure.iterrows():
        flags.append(
            f"Sector concentration: {row['Sector']} is {row['Sector Weight %']:.1f}% of portfolio."
        )

    # Small-cap exposure
    small_cap_rows = market_cap_df[
        market_cap_df["Market Cap Category"].str.lower() == "small cap"
    ]

    if not small_cap_rows.empty:
        small_cap_weight = small_cap_rows.iloc[0]["Market Cap Weight %"]
        if small_cap_weight > 50:
            flags.append(
                f"Small-cap exposure is {small_cap_weight:.1f}%, above the 50% risk threshold."
            )

    if not flags:
        flags.append("No major portfolio concentration risk flags detected.")

    return flags
