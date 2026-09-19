"""Small, explicit adapters for approved external market-data sources."""
from io import BytesIO
from pathlib import Path
from urllib.request import Request, urlopen

import pandas as pd


# Official World Bank monthly commodity-price workbook (Pink Sheet).
WORLD_BANK_PINK_SHEET_URL = (
    "https://thedocs.worldbank.org/en/doc/"
    "74e8be41ceb20fa0da750cda2f6b9e4e-0050012026/related/"
    "CMO-Historical-Data-Monthly.xlsx"
)
WORLD_BANK_CACHE = Path(__file__).resolve().parents[1] / "data" / "world_bank_australian_coal.csv"


def fetch_world_bank_australian_coal() -> pd.DataFrame:
    """Return cleaned Australian-coal monthly observations from the Pink Sheet.

    The workbook structure occasionally changes, so the column is identified by
    label instead of a fixed spreadsheet coordinate. Call this on demand rather
    than while the dashboard is loading.
    """
    try:
        request = Request(WORLD_BANK_PINK_SHEET_URL, headers={"User-Agent": "SAGAR-AI/0.1"})
        with urlopen(request, timeout=20) as response:  # nosec B310 - fixed HTTPS source
            workbook = response.read()
    except OSError:
        # Some managed Streamlit hosts prohibit outbound sockets. The checked-in
        # cache retains the most recently verified public observation so the UI
        # remains useful until the host/network policy permits a refresh.
        return pd.read_csv(WORLD_BANK_CACHE, parse_dates=["date"])

    # The official workbook's data sits in the "Monthly Prices" sheet. Its
    # labels are at row 5 (zero-indexed row 4), rather than Excel's first row.
    raw = pd.read_excel(BytesIO(workbook), sheet_name="Monthly Prices", header=None)
    header_row = next(
        (row for row in range(min(raw.shape[0], 20))
         if any("coal, australian" in str(value).lower() for value in raw.iloc[row])),
        None,
    )
    if header_row is None:
        raise ValueError("The World Bank workbook did not contain an Australian coal column.")
    price_column = next(
        column for column, value in enumerate(raw.iloc[header_row])
        if "coal, australian" in str(value).lower()
    )
    date_column = 0
    values = raw.iloc[header_row + 1 :, [date_column, price_column]].copy()
    values.columns = ["date", "price_usd_tonne"]
    values["date"] = pd.to_datetime(values["date"].astype(str), format="%YM%m", errors="coerce")
    values["price_usd_tonne"] = pd.to_numeric(values["price_usd_tonne"].replace("�", None), errors="coerce")
    values = values.dropna().sort_values("date")
    values["commodity"] = "Coal"
    values["benchmark"] = "Australian coal (World Bank Pink Sheet)"
    values["source"] = "World Bank"
    return values[["date", "commodity", "benchmark", "price_usd_tonne", "source"]]
