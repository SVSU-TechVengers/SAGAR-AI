import pandas as pd

VESSELS = {
    "Handysize": {"capacity": 35000, "draft": 10.5, "loa": 190, "beam": 30, "days": 29, "factor": 1.14},
    "Supramax": {"capacity": 55000, "draft": 12.8, "loa": 200, "beam": 32, "days": 26, "factor": 1.05},
    "Panamax": {"capacity": 78000, "draft": 14.5, "loa": 230, "beam": 32, "days": 24, "factor": 1.00},
    "Capesize": {"capacity": 165000, "draft": 18.0, "loa": 290, "beam": 45, "days": 22, "factor": 0.91},
}

def vessel_options(port: pd.Series, volume: int, base_rate: float) -> pd.DataFrame:
    rows = []
    for name, spec in VESSELS.items():
        compatible = spec["draft"] <= port.max_draft_m and spec["loa"] <= port.max_loa_m and spec["beam"] <= port.max_beam_m
        loads = max(1, -(-volume // spec["capacity"]))
        cost = loads * min(volume, spec["capacity"]) * base_rate * spec["factor"]
        rows.append({"vessel_type": name, "capacity": spec["capacity"], "loads": loads, "draft_ok": spec["draft"] <= port.max_draft_m,
                     "loa_ok": spec["loa"] <= port.max_loa_m, "beam_ok": spec["beam"] <= port.max_beam_m,
                     "compatible": compatible, "estimated_cost": cost, "turnaround_days": spec["days"]})
    return pd.DataFrame(rows)

def best_vessel(options: pd.DataFrame) -> pd.Series:
    valid = options[options.compatible]
    return (valid if not valid.empty else options).sort_values(["estimated_cost", "turnaround_days"]).iloc[0]
