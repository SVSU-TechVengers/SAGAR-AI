from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

def load_ports() -> pd.DataFrame:
    return pd.read_csv(DATA / "ports.csv")

def load_rates() -> pd.DataFrame:
    path = DATA / "historical_rates.csv"
    rates = pd.read_csv(path, parse_dates=["date"])
    return rates.sort_values("date")
