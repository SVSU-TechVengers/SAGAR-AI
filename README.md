# SAGAR-AI — Ship Allocation & Growth Analytics for Rates

SAGAR-AI is a freight forecasting and charter-planning MVP for bulk cargo moving to India’s East Coast. It is designed for chartering teams that need an auditable view of freight outlook, port suitability, timing, and operational risk.

## Quick start

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

The dashboard opens with synthetic rate and infrastructure data. Pick a route, cargo volume, and contract window in the command bar to generate an operational recommendation.

## Project layout

```
app.py                 Streamlit control-room dashboard
src/
  data.py              CSV ingestion and typed domain helpers
  forecasting.py       baseline forecast and uncertainty intervals
  recommendations.py   vessel/port suitability and commercial logic
  risk.py              congestion, volatility, and idle-risk signals
  optimizer.py         allocation optimization interface (OR-Tools-ready)
  api.py               FastAPI service entry point
data/
  ports.csv            East Coast port constraints and congestion signals
  historical_rates.csv synthetic route/vessel freight history
  commodity_prices.csv synthetic coal benchmark history
docs/DATA_SCHEMA.md    source tables, fields, quality and integration guidance
```

## Replacing synthetic data with real sources

Keep the column names and units in `docs/DATA_SCHEMA.md`, then replace the files in `data/` or point the ingestion layer at PostgreSQL.

- **Baltic Exchange:** license route assessments/indices, map voyage definitions to `origin`, `destination`, and `vessel_type`, and retain the assessment date and methodology.
- **AIS vessel tracking:** aggregate a licensed AIS feed into vessel positions, port calls, speed, waiting time, and observed voyage duration. Never use a position ping as a port-call fact without event reconciliation.
- **Port authorities/terminal operators:** refresh published draft restrictions, berth availability, tidal windows, and queue/waiting data; preserve the effective timestamp.
- **Commodity and demand:** load delivered coal prices, plant inventories, generation/steel-production signals, and seasonal procurement plans.

For production, store raw source records and a normalized analytics table in PostgreSQL. Put credentials in environment variables or Streamlit secrets, not in CSV files. Validate units (USD/tonne, metres, DWT) before a model run.

### Internet data in this MVP

The sidebar can fetch the latest available **Australian coal** observation from the [World Bank Commodity Markets Pink Sheet](https://www.worldbank.org/en/research/commodity-markets). This is a public market-context benchmark and does not replace a delivered-coal assessment or freight quote.

If the app is deployed on a host that blocks outbound internet calls, it automatically uses the last verified World Bank observations retained in `data/world_bank_australian_coal.csv`. Run the refresh action again after outbound access is enabled to retrieve the newest workbook.

Dry-bulk freight assessments and vessel positions should not be scraped from websites. Use licensed source connections instead:

- **Baltic Exchange:** obtain the applicable data and non-display licences before automating use of dry-bulk assessments.
- **MarineTraffic:** configure an API key from its AIS API service in Streamlit secrets, then call only the endpoints and fields covered by the account's subscription.
- **Port authorities:** use published operational notices or formal data-sharing arrangements, retaining effective timestamps and provenance.

## Modelling roadmap

The MVP uses a transparent seasonal-trend baseline with confidence bands so it runs immediately. `src/forecasting.py` provides clear replacement points for Prophet and XGBoost: fit Prophet for route-level time-series structure, then add an XGBoost residual/feature model using fuel, commodity, AIS, congestion, and calendar features. Backtest by route and vessel class before enabling contract recommendations.

## FastAPI

Run `uvicorn src.api:app --reload` for a minimal health endpoint. The intended production boundary is a FastAPI inference service used by the Streamlit client.

## Disclaimer

Synthetic figures are illustrative only. This is decision support, not a chartering quote or a guarantee of vessel/port acceptance.
