# SAGAR-AI data schema

All timestamps are ISO 8601 UTC unless stated otherwise. Freight is quoted as **USD per metric tonne**; vessel capacity is **DWT**; dimensions are **metres**.

## `historical_rates`

| Field | Type | Required | Description |
|---|---|---:|---|
| date | date | yes | Assessment / fixture date |
| origin | text | yes | Load-country/region key |
| destination | text | yes | Discharge port key |
| vessel_type | text | yes | Handysize, Supramax, Panamax, or Capesize |
| freight_rate_usd_tonne | numeric | yes | Cleaned freight assessment |
| voyage_days | numeric | no | Observed or estimated sea + port duration |
| source | text | yes | Provider and assessment identifier |

Unique key: `date, origin, destination, vessel_type, source`.

## `ports`

| Field | Type | Description |
|---|---|---|
| port | text | Unique port name |
| latitude / longitude | numeric | Decimal degrees for map presentation |
| max_draft_m | numeric | Operational maximum draft after restrictions |
| max_loa_m / max_beam_m | numeric | Maximum accepted vessel dimensions |
| berth_capacity_mtpa | numeric | Annual berth throughput capacity |
| congestion_index | integer | 0–100 current congestion proxy |
| status | text | Green / Amber / Red operational state |

## Supporting production tables

`commodity_prices(date, commodity, benchmark, price_usd_tonne, source)`; `seasonal_demand(month, destination, demand_index)`; `ais_port_calls(vessel_imo, port, arrived_at, berthed_at, departed_at, source)`; `vessel_specs(vessel_imo, dwt, draft_m, loa_m, beam_m, vessel_type)`.

## Quality gates

Reject blank route/type keys, duplicate assessments, negative rates, dimensions outside plausible ranges, and data older than its source refresh SLA. Preserve source, loaded time, original unit, and a data-quality status for every raw record. Apply port restrictions by effective time, not only the latest value.
