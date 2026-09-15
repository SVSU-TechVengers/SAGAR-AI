import numpy as np
import pandas as pd

def forecast_rates(history: pd.DataFrame, horizon_days: int = 90) -> pd.DataFrame:
    """Transparent seasonal-trend baseline; swap with Prophet/XGBoost in production."""
    y = history["freight_rate_usd_tonne"].astype(float).to_numpy()
    x = np.arange(len(y))
    slope, intercept = np.polyfit(x, y, 1) if len(y) > 1 else (0, y[-1])
    residual_std = max(float(np.std(y - (slope * x + intercept))), 0.65)
    future_x = np.arange(len(y), len(y) + horizon_days)
    # modest weekly seasonality makes synthetic outlook legible without overclaiming
    seasonal = 0.32 * np.sin(2 * np.pi * future_x / 30)
    prediction = intercept + slope * future_x + seasonal
    dates = pd.date_range(history["date"].max() + pd.Timedelta(days=1), periods=horizon_days)
    return pd.DataFrame({
        "date": dates,
        "forecast": prediction,
        "lower": np.maximum(prediction - 1.96 * residual_std, 0),
        "upper": prediction + 1.96 * residual_std,
    })
