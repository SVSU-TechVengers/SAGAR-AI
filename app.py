import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date, timedelta
from src.data import load_ports, load_rates
from src.forecasting import forecast_rates
from src.recommendations import vessel_options, best_vessel
from src.risk import assess_risks

st.set_page_config(page_title="SAGAR-AI | Charter Intelligence", page_icon="⚓", layout="wide", initial_sidebar_state="collapsed")

st.markdown('''<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=Space+Mono:wght@400;700&display=swap');
:root { --navy:#071B2E; --panel:#0B2740; --line:#24455F; --teal:#21D4C2; --cyan:#6EE7F9; --amber:#FFB454; --muted:#93AFC4; }
.stApp { background:var(--navy); color:#EEF7FC; font-family:'IBM Plex Sans',sans-serif; }
[data-testid="stHeader"] { background:rgba(7,27,46,.9); }
.block-container { max-width:1420px; padding-top:1.2rem; padding-bottom:2rem; }
.brand {display:flex; justify-content:space-between; align-items:flex-end; border-bottom:1px solid var(--line); padding-bottom:15px; margin-bottom:18px;}
.brand h1 {font-size:28px; letter-spacing:-.8px; margin:0; color:#F2FAFE}.brand h1 span {color:var(--teal)}
.eyebrow {font:700 11px 'Space Mono'; letter-spacing:1.4px; color:var(--teal); margin-bottom:5px}.live {font:700 11px 'Space Mono'; color:#9DE9C0; background:#113B42; padding:7px 10px; border-radius:4px}
.label {font:700 11px 'Space Mono'; letter-spacing:1px; color:var(--muted); text-transform:uppercase}.metric {background:linear-gradient(145deg,#10314E,#0A233A); border:1px solid var(--line); border-radius:8px; padding:15px 17px; min-height:105px}.metric .value {font-size:25px; font-weight:700; margin-top:7px}.metric .delta{color:var(--teal); font-size:12px; margin-top:3px}
.section-title {font-weight:600; font-size:17px; margin:18px 0 8px}.panel {background:#0A243B; border:1px solid var(--line); border-radius:8px; padding:14px;}.risk {border-left:3px solid var(--amber); background:#102B41; padding:11px 13px; margin:7px 0; border-radius:4px}.tag {font:700 10px 'Space Mono'; color:var(--amber); margin-right:8px}.small {color:var(--muted); font-size:12px}.vessel {border:1px solid var(--line); background:#0D2A43; border-radius:7px; padding:12px; min-height:155px}.vessel.best {border-color:var(--teal); box-shadow:0 0 0 1px rgba(33,212,194,.16)}
div[data-baseweb="select"]>div, div[data-baseweb="input"]>div {background:#0B2943!important;border-color:#28506D!important;color:#EFFAFF!important} .stDateInput input{background:#0B2943!important;color:#EFFAFF!important} [data-testid="stMetricValue"]{color:#F4FAFD}
</style>''', unsafe_allow_html=True)

ports, rates = load_ports(), load_rates()
st.markdown('''<div class="brand"><div><div class="eyebrow">SHIP ALLOCATION & GROWTH ANALYTICS FOR RATES</div><h1>SAGAR<span>-AI</span> <span style="font-size:13px;color:#93AFC4;font-weight:500">/ Charter Intelligence</span></h1></div><div class="live">● SYSTEM LIVE &nbsp;|&nbsp; SYNTHETIC DATA</div></div>''', unsafe_allow_html=True)

with st.container(border=True):
    a,b,c,d,e = st.columns([1.05,1.05,1.05,1.15,1.25])
    with a: cargo = st.selectbox("CARGO", ["Thermal Coal", "Coking Coal", "Iron Ore"])
    with b: volume = st.number_input("VOLUME (MT)", 10000, 500000, 75000, 5000)
    with c: origin = st.selectbox("ORIGIN", ["Australia", "Indonesia", "Mozambique", "US", "Russia"])
    with d: destination = st.selectbox("DESTINATION", ports.port.tolist())
    with e: window = st.date_input("CONTRACT WINDOW", (date.today()+timedelta(days=14), date.today()+timedelta(days=74)))

port = ports.loc[ports.port.eq(destination)].iloc[0]
subset = rates[(rates.origin == origin) & (rates.destination == destination)]
if subset.empty:
    subset = rates[(rates.origin == "Australia") & (rates.destination == "Paradip")]
    source_note = "Comparable Australia → Paradip benchmark used"
else: source_note = "Route-specific synthetic benchmark"
history = subset.groupby("date", as_index=False).freight_rate_usd_tonne.mean()
forecast = forecast_rates(history, 90)
base_rate = float(forecast.forecast.iloc[:30].mean())
options = vessel_options(port, volume, base_rate)
choice = best_vessel(options)
spot_cost = volume * base_rate * 1.06
saving = max(spot_cost - choice.estimated_cost, 0)
entry = forecast.loc[forecast.forecast.idxmin(), "date"]

st.markdown('<div class="section-title">Decision brief <span class="small">— '+source_note+'</span></div>', unsafe_allow_html=True)
m1,m2,m3,m4 = st.columns(4)
for col, label, value, delta in [
    (m1,"RECOMMENDED VESSEL",choice.vessel_type,f"{int(choice.loads)} lift(s) · {choice.turnaround_days} days"),
    (m2,"OPTIMAL ENTRY WINDOW",entry.strftime("%d %b"),"Lowest modeled rate in 90 days"),
    (m3,"EST. SAVING VS SPOT",f"${saving/1000:,.0f}K",f"${base_rate:.2f}/t outlook"),
    (m4,"PORT OPERATING STATUS",port.status.upper(),f"Congestion index {port.congestion_index}/100")]:
    with col: st.markdown(f'<div class="metric"><div class="label">{label}</div><div class="value">{value}</div><div class="delta">{delta}</div></div>', unsafe_allow_html=True)

left, right = st.columns([1.72, .88])
with left:
    st.markdown('<div class="section-title">Freight-rate outlook <span class="small">USD / metric tonne · 95% confidence interval</span></div>', unsafe_allow_html=True)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=forecast.date, y=forecast.upper, line=dict(width=0), hoverinfo="skip", showlegend=False))
    fig.add_trace(go.Scatter(x=forecast.date, y=forecast.lower, fill="tonexty", fillcolor="rgba(33,212,194,.15)", line=dict(width=0), name="95% interval", hovertemplate="$%{y:.2f}/t"))
    fig.add_trace(go.Scatter(x=forecast.date, y=forecast.forecast, line=dict(color="#21D4C2", width=3), name="Forecast", hovertemplate="%{x|%d %b}<br><b>$%{y:.2f}/t</b><extra></extra>"))
    fig.add_trace(go.Scatter(x=history.date, y=history.freight_rate_usd_tonne, mode="lines+markers", line=dict(color="#6EE7F9", width=2), marker=dict(size=5), name="Observed", hovertemplate="%{x|%d %b}<br><b>$%{y:.2f}/t</b><extra></extra>"))
    fig.add_vline(x=entry.timestamp()*1000, line_dash="dot", line_color="#FFB454", annotation_text=" ENTER HERE", annotation_font_color="#FFB454")
    fig.update_layout(height=355, margin=dict(l=5,r=5,t=15,b=5), paper_bgcolor="#0A243B", plot_bgcolor="#0A243B", font=dict(color="#C9DCE8",family="IBM Plex Sans"), legend=dict(orientation="h", y=1.12), xaxis=dict(showgrid=False), yaxis=dict(gridcolor="#1D425B", title="USD/t"))
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})
with right:
    st.markdown('<div class="section-title">Risk & alerts</div>', unsafe_allow_html=True)
    for risk in assess_risks(port, history):
        st.markdown(f'<div class="risk"><span class="tag">{risk["severity"]}</span><b>{risk["title"]}</b><div class="small" style="margin-top:5px">{risk["detail"]}</div></div>', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Port intelligence</div><div class="panel small">'+f'<b style="color:#EFFAFF;font-size:15px">{port.port}</b><br><br>MAX DRAFT <b>{port.max_draft_m} m</b> &nbsp;·&nbsp; MAX LOA <b>{port.max_loa_m} m</b><br>MAX BEAM <b>{port.max_beam_m} m</b> &nbsp;·&nbsp; BERTH CAP. <b>{port.berth_capacity_mtpa} MTPA</b>'+'</div>', unsafe_allow_html=True)

st.markdown('<div class="section-title">Vessel-fit matrix <span class="small">— constraints assessed against destination port envelope</span></div>', unsafe_allow_html=True)
cols = st.columns(4)
for col, (_, row) in zip(cols, options.iterrows()):
    checks = " · ".join([f"{label} {'✓' if ok else '×'}" for label, ok in [("DRAFT",row.draft_ok),("LOA",row.loa_ok),("BEAM",row.beam_ok)]])
    cls = "vessel best" if row.vessel_type == choice.vessel_type else "vessel"
    with col:
        st.markdown(f'<div class="{cls}"><div class="label">{("RECOMMENDED" if row.vessel_type == choice.vessel_type else "VESSEL CLASS")}</div><div style="font-weight:700;font-size:18px;margin:5px 0">{row.vessel_type}</div><div class="small">{row.capacity:,.0f} DWT · {row.loads} lift(s)</div><hr style="border-color:#24455F"><div class="small">{checks}</div><div style="font-weight:600;margin-top:10px">${row.estimated_cost/1000000:.2f}M</div><div class="small">{row.turnaround_days} days est. turnaround</div></div>', unsafe_allow_html=True)

st.markdown('<div class="section-title">Route & port network</div>', unsafe_allow_html=True)
map_data = ports[["port","latitude","longitude","congestion_index"]].copy()
map_data["size"] = 50 - map_data.congestion_index / 3
fig_map = go.Figure(go.Scattermap(
    lat=map_data.latitude, lon=map_data.longitude, mode="markers+text",
    text=map_data.port, textposition="top right",
    marker=dict(size=map_data["size"], color=map_data.congestion_index,
                colorscale=[[0,"#21D4C2"],[.6,"#FFB454"],[1,"#F0695A"]], showscale=False),
    hovertemplate="<b>%{text}</b><br>Congestion: %{marker.color}/100<extra></extra>"
))
fig_map.update_layout(height=260, margin=dict(l=0,r=0,t=0,b=0),
                      map=dict(style="carto-darkmatter", center=dict(lat=19.5,lon=85), zoom=4.3),
                      paper_bgcolor="#071B2E")
st.plotly_chart(fig_map, use_container_width=True, config={"displayModeBar":False})
st.caption("SAGAR-AI MVP · Forecasts and recommendations use illustrative synthetic data. Validate against licensed market and operational sources before committing cargo.")
