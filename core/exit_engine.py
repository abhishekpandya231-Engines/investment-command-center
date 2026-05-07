"""
Exit Engine v0.1
Investment Command Center

Purpose:
Converts stock-level signals into one simple action verdict:

RIDE  = Hold normally
GUARD = Warning zone; no fresh add
TRIM  = Partial profit booking / risk reduction
EXIT  = Full exit required
FREEZE = Market regime blocks new buys; only risk-reduction allowed

This file is intentionally framework-independent.
It can be used inside Streamlit now and later inside FastAPI/Next.js.
"""


def safe_float(value, default=None):
    """Convert any value to float safely."""
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def get_market_gate_verdict(engine_a_score):
    """
    Converts Engine A score into market gate status.
    """
    score = safe_float(engine_a_score, default=50)

    if score <= 20:
        return {
            "market_regime": "EXIT",
            "market_action": "Market regime is extremely weak. Risk reduction required.",
        }

    if score <= 30:
        return {
            "market_regime": "FREEZE",
            "market_action": "No fresh equity buys. Only exits or risk reduction allowed.",
        }

    if score <= 40:
        return {
            "market_regime": "CAUTIOUS",
            "market_action": "Reduced position sizing. Avoid weak setups.",
        }

    if score <= 52:
        return {
            "market_regime": "ACTIVE",
            "market_action": "Normal deployment allowed.",
        }

    if score <= 62:
        return {
            "market_regime": "AGGRESSIVE",
            "market_action": "Strong deployment allowed, with risk controls.",
        }

    return {
        "market_regime": "FULL DEPLOY",
        "market_action": "Maximum deployment allowed, subject to portfolio limits.",
    }


def evaluate_engine_b_exit(row, engine_a_score=50):
    """
    Engine B: Momentum Hunter exit logic.
    Main thesis: ride while DVM remains strong; exit when institutional momentum decays.
    """
    market = get_market_gate_verdict(engine_a_score)

    durability = safe_float(row.get("Durability Score"))
    momentum = safe_float(row.get("Momentum Score"))
    momentum_velocity = safe_float(row.get("Momentum Velocity"))
    pnl_pct = safe_float(row.get("P&L %"), default=0)
    stop_breached = bool(row.get("Stop Breached", False))

    # Market override
    if market["market_regime"] == "EXIT":
        return {
            "verdict": "EXIT",
            "reason": "Engine A is in EXIT regime. Momentum positions should be exited first.",
            "priority": 1,
        }

    if market["market_regime"] == "FREEZE":
        freeze_note = "Engine A is in FREEZE regime. No fresh buys. Monitor exits only."
    else:
        freeze_note = ""

    # Hard DVM exits
    if durability is not None and durability < 45:
        return {
            "verdict": "EXIT",
            "reason": f"Durability is {durability:.1f}, below 45. Business quality gate broken.",
            "priority": 2,
        }

    if momentum is not None and momentum < 49:
        return {
            "verdict": "EXIT",
            "reason": f"Momentum is {momentum:.1f}, below 49. Smart-money momentum has decayed.",
            "priority": 2,
        }

    # Velocity crash
    if momentum_velocity is not None and momentum_velocity <= -10:
        return {
            "verdict": "EXIT",
            "reason": f"Momentum velocity is {momentum_velocity:.1f}. Crashing momentum signal.",
            "priority": 3,
        }

    # Stop breach
    if stop_breached:
        return {
            "verdict": "EXIT",
            "reason": "Price-based stop has been breached.",
            "priority": 4,
        }

    # Guard zone
    if durability is not None and momentum is not None:
        if 45 <= durability <= 55 or 49 <= momentum <= 59:
            return {
                "verdict": "GUARD",
                "reason": f"DVM is in grey zone. Durability={durability:.1f}, Momentum={momentum:.1f}. {freeze_note}".strip(),
                "priority": 5,
            }

    if momentum_velocity is not None and -10 < momentum_velocity < 0:
        return {
            "verdict": "GUARD",
            "reason": f"Momentum velocity is cooling at {momentum_velocity:.1f}. No adding.",
            "priority": 5,
        }

    # Profit protection
    if pnl_pct >= 30:
        return {
            "verdict": "RIDE",
            "reason": f"Momentum setup is intact and position is up {pnl_pct:.1f}%. Ride with trailing stop.",
            "priority": 6,
        }

    return {
        "verdict": "RIDE" if market["market_regime"] != "FREEZE" else "FREEZE",
        "reason": f"Momentum setup has no major exit trigger. {freeze_note}".strip(),
        "priority": 7,
    }


def evaluate_engine_c_exit(row, engine_a_score=50):
    """
    Engine C: Value Warriors exit logic.
    Main thesis: hold while fundamentals remain healthy; harvest when valuation expands.
    """
    market = get_market_gate_verdict(engine_a_score)

    pio = safe_float(row.get("Piotroski Score"))
    roe = safe_float(row.get("ROE Ann  %"))
    debt = safe_float(row.get("Total Debt to Total Equity Ann "))
    profit_growth = safe_float(row.get("Net Profit Ann  YoY Growth %"))
    pe_expansion = safe_float(row.get("PE Expansion %"), default=0)
    months_held = safe_float(row.get("Months Held"), default=0)
    pnl_pct = safe_float(row.get("P&L %"), default=0)
    stop_breached = bool(row.get("Stop Breached", False))
    dropped_from_screeners = bool(row.get("Dropped From Screeners", False))

    if market["market_regime"] == "EXIT":
        return {
            "verdict": "EXIT",
            "reason": "Engine A is in EXIT regime. Value positions require risk reduction.",
            "priority": 1,
        }

    # Fundamental break
    if pio is not None and pio <= 4:
        return {
            "verdict": "EXIT",
            "reason": f"Piotroski Score is {pio:.1f}, at or below 4. Fundamental health broken.",
            "priority": 2,
        }

    if roe is not None and roe < 10:
        return {
            "verdict": "EXIT",
            "reason": f"ROE is {roe:.1f}%, below 10%. Profitability quality broken.",
            "priority": 2,
        }

    if debt is not None and debt > 1.5:
        return {
            "verdict": "EXIT",
            "reason": f"Debt/Equity is {debt:.2f}, above 1.5. Balance-sheet risk elevated.",
            "priority": 2,
        }

    if profit_growth is not None and profit_growth < 0:
        return {
            "verdict": "GUARD",
            "reason": f"Profit growth is negative at {profit_growth:.1f}%. Check if this is a temporary quarter or thesis break.",
            "priority": 3,
        }

    # Stop breach
    if stop_breached:
        return {
            "verdict": "EXIT",
            "reason": "Adaptive trailing stop has been breached.",
            "priority": 4,
        }

    # 30-day screener requalification concept
    if dropped_from_screeners:
        return {
            "verdict": "GUARD",
            "reason": "Stock has dropped from value screeners. Start requalification clock.",
            "priority": 5,
        }

    # PE harvest ladder
    if pe_expansion >= 80:
        return {
            "verdict": "TRIM",
            "reason": f"PE has expanded {pe_expansion:.1f}% from entry. Full harvest stage: book another 25%, keep runner.",
            "priority": 6,
        }

    if pe_expansion >= 50:
        return {
            "verdict": "TRIM",
            "reason": f"PE has expanded {pe_expansion:.1f}% from entry. Medium harvest stage: book another 25%.",
            "priority": 6,
        }

    if pe_expansion >= 30:
        return {
            "verdict": "TRIM",
            "reason": f"PE has expanded {pe_expansion:.1f}% from entry. Light harvest stage: book 25%.",
            "priority": 6,
        }

    # Time decay
    if months_held >= 12 and pnl_pct < 10:
        return {
            "verdict": "GUARD",
            "reason": f"Held {months_held:.0f} months with only {pnl_pct:.1f}% return. Time-decay review required.",
            "priority": 7,
        }

    if months_held >= 9 and pnl_pct < 5:
        return {
            "verdict": "GUARD",
            "reason": f"Held {months_held:.0f} months with only {pnl_pct:.1f}% return. Watch closely.",
            "priority": 7,
        }

    if market["market_regime"] == "FREEZE":
        return {
            "verdict": "FREEZE",
            "reason": "Engine A is in FREEZE regime. Hold only; no fresh buys.",
            "priority": 8,
        }

    return {
        "verdict": "RIDE",
        "reason": "Value thesis has no major exit trigger.",
        "priority": 9,
    }


def evaluate_engine_d_exit(row, engine_a_score=50):
    """
    Engine D: Compounders exit logic.
    Main thesis: avoid premature selling; exit only on fundamental/growth thesis break.
    """
    market = get_market_gate_verdict(engine_a_score)

    pio = safe_float(row.get("Piotroski Score"))
    roe = safe_float(row.get("ROE Ann  %"))
    debt = safe_float(row.get("Total Debt to Total Equity Ann "))
    profit_growth = safe_float(row.get("Net Profit Ann  YoY Growth %"))
    revenue_growth = safe_float(row.get("Revenue QoQ Growth %"))
    ets = safe_float(row.get("Earnings Trajectory Score"))
    months_held = safe_float(row.get("Months Held"), default=0)
    pnl_pct = safe_float(row.get("P&L %"), default=0)
    stop_breached = bool(row.get("Stop Breached", False))

    # Engine A is softer for D than B, but still serious
    if market["market_regime"] == "EXIT":
        if pio is not None and pio <= 3:
            return {
                "verdict": "EXIT",
                "reason": "Engine A EXIT regime plus Piotroski <=3. Compounder thesis broken.",
                "priority": 1,
            }

        return {
            "verdict": "GUARD",
            "reason": "Engine A is in EXIT regime. Compounder requires strict thesis review before selling.",
            "priority": 1,
        }

    # Earnings wall
    if pio is not None and pio <= 3:
        return {
            "verdict": "EXIT",
            "reason": f"Piotroski Score is {pio:.1f}, at or below 3. Earnings wall trigger.",
            "priority": 2,
        }

    if roe is not None and roe < 8:
        return {
            "verdict": "EXIT",
            "reason": f"ROE is {roe:.1f}%, below 8%. Compounder profitability thesis broken.",
            "priority": 2,
        }

    if debt is not None and debt > 2:
        return {
            "verdict": "EXIT",
            "reason": f"Debt/Equity is {debt:.2f}, above 2.0. Balance-sheet risk unacceptable.",
            "priority": 2,
        }

    if profit_growth is not None and profit_growth < 0:
        return {
            "verdict": "GUARD",
            "reason": f"Profit growth is negative at {profit_growth:.1f}%. Check if growth thesis is weakening.",
            "priority": 3,
        }

    if revenue_growth is not None and revenue_growth < 0:
        return {
            "verdict": "GUARD",
            "reason": f"Revenue QoQ growth is negative at {revenue_growth:.1f}%. Watch for growth disconnect.",
            "priority": 3,
        }

    # Earnings trajectory
    if ets is not None and ets <= 0:
        return {
            "verdict": "GUARD",
            "reason": "Earnings Trajectory Score is 0. Prepare exit if repeated next quarter.",
            "priority": 4,
        }

    # 90-day incubation
    if months_held < 3 and not stop_breached:
        return {
            "verdict": "RIDE",
            "reason": "Within 90-day incubation period. No selling unless hard stop or fundamental break.",
            "priority": 5,
        }

    if stop_breached:
        return {
            "verdict": "EXIT",
            "reason": "Compounder adaptive stop has been breached.",
            "priority": 6,
        }

    # Tax-aware booking
    if months_held >= 12 and pnl_pct >= 150:
        return {
            "verdict": "TRIM",
            "reason": f"Position is up {pnl_pct:.1f}% after 12 months. Book 10%, keep long-term runner.",
            "priority": 7,
        }

    if months_held >= 12 and pnl_pct >= 100:
        return {
            "verdict": "TRIM",
            "reason": f"Position is up {pnl_pct:.1f}% after 12 months. Book another 20%.",
            "priority": 7,
        }

    if months_held >= 12 and pnl_pct >= 50:
        return {
            "verdict": "TRIM",
            "reason": f"Position is up {pnl_pct:.1f}% after 12 months. Book 20%.",
            "priority": 7,
        }

    if market["market_regime"] == "FREEZE":
        return {
            "verdict": "FREEZE",
            "reason": "Engine A is in FREEZE regime. Hold only; no fresh buys.",
            "priority": 8,
        }

    return {
        "verdict": "RIDE",
        "reason": "Compounder thesis has no major exit trigger.",
        "priority": 9,
    }


def evaluate_exit(row, engine_a_score=50):
    """
    Main exit function.
    Takes one stock row and returns final verdict.
    """
    engine = str(row.get("Engine", "")).upper().strip()

    if engine == "B":
        return evaluate_engine_b_exit(row, engine_a_score)

    if engine == "C":
        return evaluate_engine_c_exit(row, engine_a_score)

    if engine == "D":
        return evaluate_engine_d_exit(row, engine_a_score)

    if engine == "E":
        return {
            "verdict": "RIDE",
            "reason": "Engine E defensive asset. Managed by macro allocation rules.",
            "priority": 9,
        }

    return {
        "verdict": "GUARD",
        "reason": "Unknown engine classification. Manual review required.",
        "priority": 10,
    }
