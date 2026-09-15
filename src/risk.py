import pandas as pd

def assess_risks(port: pd.Series, rate_history: pd.DataFrame) -> list[dict]:
    volatility = rate_history.freight_rate_usd_tonne.pct_change().std() * 100
    items = []
    if port.congestion_index >= 70:
        items.append({"severity": "HIGH", "title": "Berth congestion", "detail": f"{port.port} congestion index is {port.congestion_index}/100; factor queue time into laycan."})
    elif port.congestion_index >= 45:
        items.append({"severity": "MEDIUM", "title": "Variable turnaround", "detail": f"{port.port} congestion index is {port.congestion_index}/100; monitor berth nominations."})
    items.append({"severity": "MEDIUM" if volatility > 4 else "LOW", "title": "Rate volatility", "detail": f"30-day rate variability proxy is {volatility:.1f}%; stagger fixture exposure."})
    items.append({"severity": "LOW", "title": "Idle-risk watch", "detail": "Seasonal demand softens after the monsoon peak; preserve optionality for the final 20% of volume."})
    return items
