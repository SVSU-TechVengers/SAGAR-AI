"""SAGAR-AI — a focused charter decision workspace with supply-lane master data."""
from datetime import date, timedelta

import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

from src.data import load_ports, load_rates, load_suppliers
from src.external_data import WORLD_BANK_PINK_SHEET_URL, fetch_world_bank_australian_coal
from src.forecasting import forecast_rates
from src.recommendations import best_vessel, vessel_options
from src.risk import assess_risks


st.set_page_config(
    page_title="SAGAR-AI | Charter decisions",
    page_icon="⚓",
    layout="wide",
    initial_sidebar_state="collapsed",
)

MARINE_TRAFFIC_URL = "https://www.marinetraffic.com/en/ais/home/centerx:78.0/centery:19.0/zoom:4"
VIDEO_URL = "https://www.desktophut.com/previews/Free-Stock-Video-Wide-Container-Area-On-A-Cargo-Ship-Shoreline-Live-Wallpaper-player.mp4"
THEMES = {
    "Light": {"bg":"#F6F8FB", "card":"#FFFFFF", "soft":"#F0F5F7", "text":"#12263A", "muted":"#65788A", "line":"#DCE5EC", "navy":"#09253C", "teal":"#007E7A", "blue":"#1874A8", "amber":"#B65F00", "danger":"#B64040", "shadow":"0 6px 18px rgba(19,43,63,.06)"},
    "Dark": {"bg":"#081A2A", "card":"#102B42", "soft":"#14344D", "text":"#EFF7FB", "muted":"#A2B5C3", "line":"#294B62", "navy":"#06131F", "teal":"#35D0C1", "blue":"#70D9F5", "amber":"#FFB454", "danger":"#FF7A72", "shadow":"0 8px 24px rgba(0,0,0,.18)"},
}

# Representative terminal coordinates for supply-lane visualisation. These are
# planning anchors only; an actual voyage plan must use a licensed routing and
# weather service.
SUPPLIER_PORT_COORDINATES = {
    "Newcastle": (-32.93, 151.78), "Taboneo": (-3.75, 114.45), "Nacala": (-14.54, 40.67),
    "Hay Point": (-21.28, 149.29), "Hampton Roads": (36.95, -76.33), "Vancouver": (49.30, -123.10),
    "Dampier": (-20.66, 116.70), "Ponta da Madeira": (-2.56, -44.37), "Saldanha Bay": (-33.03, 17.95),
    "Weipa": (-12.68, 141.88), "Kamsar": (10.65, -14.60), "Gladstone": (-23.84, 151.25),
    "Vila do Conde": (-1.56, -48.74), "St Petersburg": (59.93, 30.20), "Cotonou": (6.35, 2.43),
    "Port Hope": (43.95, -78.30), "Ras Tanura": (26.65, 50.15), "Ruwais": (24.11, 52.73),
    "Angra dos Reis": (-23.00, -44.32), "Ras Laffan": (25.93, 51.55), "Pluto": (-19.60, 115.10),
    "Sabine Pass": (29.70, -93.90), "Houston": (29.73, -95.20), "Jamnagar": (22.47, 69.96),
    "Jorf Lasfar": (33.10, -8.60), "Ashdod": (31.80, 34.64),
    "Baltimore": (39.27, -76.58), "Vostochny": (42.73, 133.05), "Qinhuangdao": (39.90, 119.60),
    "Puerto Bolivar": (12.46, -71.97), "Nakhodka": (42.82, 132.88), "Richards Bay": (-28.80, 32.08),
    "Novorossiysk": (44.72, 37.77), "Qingdao": (36.07, 120.32), "Yantai": (37.54, 121.39),
    "Ust-Luga": (59.67, 28.27), "Algeciras": (36.12, -5.44), "Le Havre": (49.49, 0.11),
    "Ningbo": (29.87, 121.55), "Sabetta": (71.27, 72.06), "Hammerfest": (70.66, 23.68),
}

if "appearance" not in st.session_state:
    st.session_state.appearance = "Light"
if "show_motion" not in st.session_state:
    st.session_state.show_motion = False


@st.cache_data(ttl=60 * 60 * 12, show_spinner=False)
def live_coal_benchmark():
    """Cache external data so a refresh does not slow ordinary dashboard use."""
    return fetch_world_bank_australian_coal()


def route_corridor(origin_lat, origin_lon, destination_lat, destination_lon, origin_country):
    """Return broad ocean-gateway waypoints for a commercial route visual.

    This deliberately represents shipping corridors—not navigational waypoints.
    Its purpose is to make the selected sourcing lane understandable on the map.
    """
    origin = (origin_lat, origin_lon)
    india = (destination_lat, destination_lon)
    # Atlantic → Cape of Good Hope → Indian Ocean
    if origin_lon < -30:
        return [origin, (-32, -30), (-35, 20), (-20, 45), (5, 65), india]
    # Atlantic African suppliers → Cape of Good Hope → Indian Ocean
    if origin_country in {"Guinea", "Morocco", "Colombia", "Brazil"}:
        return [origin, (0, -15), (-35, 20), (-20, 45), (5, 65), india]
    # China / Russian Far East → South China Sea → Malacca → Bay of Bengal
    if origin_country == "China" or (origin_country == "Russia" and origin_lon > 80):
        return [origin, (20, 120), (5, 105), (5, 95), india]
    # Australia / Indonesia → Indonesian archipelago → Bay of Bengal
    if origin_country in {"Australia", "Indonesia"}:
        return [origin, (-20, 115), (-7, 105), (5, 95), india]
    # Europe, Black Sea, Baltic, Arctic Russia and eastern Mediterranean
    # → Suez gateway → Red Sea → Arabian Sea → India
    if origin_country in {"Kazakhstan", "Israel", "Russia", "France", "Spain", "Norway"}:
        return [origin, (31, 32), (13, 43), (12, 55), india]
    # Gulf / East Africa → Arabian Sea → India
    if origin_country in {"Saudi Arabia", "UAE", "Qatar", "Mozambique", "South Africa", "Niger"}:
        return [origin, (15, 55), india]
    return [origin, india]


def india_coast_map(port_frame, selected_port, supplier):
    """India port map with selected source-terminal route corridor."""
    colours = {"Green": t["teal"], "Amber": t["amber"], "Red": t["danger"]}
    figure = go.Figure()
    for status, group in port_frame.groupby("status"):
        figure.add_trace(go.Scattergeo(
            lon=group.longitude, lat=group.latitude, text=group.port,
            mode="markers+text", textposition="top center", name=status,
            marker=dict(size=10, color=colours[status], line=dict(color=t["card"], width=1.5)),
            customdata=group[["congestion_index", "max_draft_m", "berth_capacity_mtpa"]].to_numpy(),
            hovertemplate=("<b>%{text}</b><br>Congestion: %{customdata[0]}/100"
                           "<br>Max draft: %{customdata[1]:.1f} m"
                           "<br>Berth capacity: %{customdata[2]:.0f} MTPA<extra></extra>"),
        ))
    selected = port_frame.loc[port_frame.port.eq(selected_port)].iloc[0]
    figure.add_trace(go.Scattergeo(
        lon=[selected.longitude], lat=[selected.latitude], mode="markers",
        marker=dict(size=20, color="rgba(0,0,0,0)", line=dict(color=t["blue"], width=3)),
        hoverinfo="skip", showlegend=False,
    ))
    origin_lat, origin_lon = SUPPLIER_PORT_COORDINATES.get(supplier.loading_port, (0, 65))
    corridor = route_corridor(origin_lat, origin_lon, selected.latitude, selected.longitude, supplier.country)
    figure.add_trace(go.Scattergeo(
        lon=[point[1] for point in corridor], lat=[point[0] for point in corridor], mode="lines",
        line=dict(color=t["blue"], width=2, dash="dot"), name="Indicative corridor",
        hovertemplate="Indicative ocean corridor<extra></extra>",
    ))
    figure.add_trace(go.Scattergeo(
        lon=[origin_lon], lat=[origin_lat], mode="markers+text", text=[supplier.loading_port],
        textposition="bottom center", name="Load terminal", marker=dict(size=13, color=t["blue"], symbol="diamond"),
        hovertemplate=f"<b>{supplier.supplier}</b><br>{supplier.loading_port}, {supplier.country}<extra></extra>",
    ))
    figure.update_geos(
        projection_type="mercator", showland=True, landcolor="#E5EDF1" if st.session_state.appearance == "Light" else "#15374D",
        showocean=True, oceancolor="#DDEFF3" if st.session_state.appearance == "Light" else "#0A2236",
        showcoastlines=True, coastlinecolor=t["muted"], showcountries=True, countrycolor=t["line"],
        lonaxis_range=[-130, 160], lataxis_range=[-50, 65], bgcolor=t["card"],
    )
    figure.update_layout(
        height=550, margin=dict(l=0, r=0, t=15, b=0), paper_bgcolor=t["card"],
        font=dict(family="IBM Plex Sans", color=t["text"]),
        legend=dict(orientation="h", y=1.03, x=0, bgcolor="rgba(0,0,0,0)"),
    )
    return figure

with st.sidebar:
    st.markdown("### SAGAR-AI")
    st.caption("Ship Allocation & Growth Analytics for Rates")
    st.divider()
    st.radio("Theme", ["Light", "Dark"], key="appearance", horizontal=True)
    st.toggle("Use motion banner", key="show_motion")
    st.caption("The default is a light, low-distraction operations view.")
    st.divider()
    st.markdown("**Internet data**")
    if st.button("Refresh public coal benchmark", width="stretch"):
        try:
            live_coal_benchmark.clear()
            st.session_state.live_coal = live_coal_benchmark()
            if "cached" in str(st.session_state.live_coal.iloc[-1].source).lower():
                st.info("Network access is blocked here; using the latest verified World Bank cache")
            else:
                st.success("World Bank benchmark refreshed")
        except Exception as error:
            st.warning(f"Could not refresh public data: {error}")

t = THEMES[st.session_state.appearance]
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=Space+Mono:wght@400;700&display=swap');
:root {{ --bg:{t['bg']}; --card:{t['card']}; --soft:{t['soft']}; --text:{t['text']}; --muted:{t['muted']}; --line:{t['line']}; --navy:{t['navy']}; --teal:{t['teal']}; --blue:{t['blue']}; --amber:{t['amber']}; --danger:{t['danger']}; }}
.stApp,[data-testid="stAppViewContainer"]{{background:var(--bg);color:var(--text);font-family:'IBM Plex Sans',sans-serif}} [data-testid="stHeader"]{{background:transparent}} [data-testid="stSidebar"]{{background:var(--navy)}} [data-testid="stSidebar"] *{{color:#EFF7FB}} .block-container{{max-width:1280px;padding-top:1.4rem;padding-bottom:3rem}}
.header{{display:flex;align-items:center;justify-content:space-between;margin-bottom:25px}} .brand{{display:flex;align-items:center;gap:11px}} .anchor{{display:grid;place-items:center;width:37px;height:37px;border-radius:10px;background:var(--navy);color:#54DDD0;font-size:19px}} .brand-name{{font-size:22px;font-weight:700;letter-spacing:-.6px;line-height:1}} .brand-name b{{color:var(--teal)}} .eyebrow{{font:700 10px 'Space Mono';letter-spacing:1.15px;color:var(--muted);text-transform:uppercase;margin-top:5px}} .badge{{font:700 10px 'Space Mono';color:var(--teal);border:1px solid var(--line);border-radius:99px;padding:7px 10px;background:var(--card)}}
.hero{{position:relative;overflow:hidden;min-height:110px;border:1px solid var(--line);border-radius:14px;background:linear-gradient(110deg,var(--navy),#145167);box-shadow:{t['shadow']};margin-bottom:18px}} .hero-copy{{position:relative;z-index:1;padding:20px 24px;color:white}} .hero h1{{font-size:25px;letter-spacing:-.55px;margin:0 0 5px}} .hero p{{font-size:14px;color:#D7E8ED;margin:0;max-width:750px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px;box-shadow:{t['shadow']}}} .label{{font:700 10px 'Space Mono';letter-spacing:1px;color:var(--muted);text-transform:uppercase}} .value{{font-size:23px;font-weight:700;letter-spacing:-.4px;color:var(--text);margin:7px 0 3px}} .sub{{font-size:12px;color:var(--muted)}} .teal{{color:var(--teal)}}
.section-title{{font-size:17px;font-weight:700;letter-spacing:-.2px;margin:25px 0 10px;color:var(--text)}} .section-title span{{font-size:12px;font-weight:400;color:var(--muted)}} .decision{{border-left:4px solid var(--teal);padding-left:15px}} .decision h2{{margin:6px 0 5px;font-size:23px;color:var(--text)}} .risk{{border-left:3px solid var(--amber);padding:10px 12px;background:var(--soft);border-radius:0 8px 8px 0;margin:8px 0}} .risk b{{font-size:13px}} .risk p{{font-size:12px;color:var(--muted);margin:4px 0 0}} .tag{{font:700 10px 'Space Mono';color:var(--amber);margin-right:7px}}
[data-testid="stVerticalBlockBorderWrapper"]{{background:var(--card);border-color:var(--line)!important;border-radius:12px}} div[data-baseweb="select"]>div,div[data-baseweb="input"]>div,.stDateInput input{{background:var(--card)!important;color:var(--text)!important;border-color:var(--line)!important}} .stTabs [data-baseweb="tab-list"]{{gap:24px;border-bottom:1px solid var(--line)}} .stTabs [data-baseweb="tab"]{{height:42px;padding:0;color:var(--muted)}} .stTabs [aria-selected="true"]{{color:var(--teal)!important;border-bottom-color:var(--teal)!important}}
</style>""", unsafe_allow_html=True)

ports, rates, suppliers = load_ports(), load_rates(), load_suppliers()
st.markdown("""<div class="header"><div class="brand"><div class="anchor">⚓</div><div><div class="brand-name">SAGAR<b>-AI</b></div><div class="eyebrow">Charter decision workspace</div></div></div><div class="badge">● SAMPLE DATA · SYSTEM READY</div></div>""", unsafe_allow_html=True)

if st.session_state.show_motion:
    components.html(f'''<div class="hero"><video autoplay muted loop playsinline aria-hidden="true" style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover;opacity:.22"><source src="{VIDEO_URL}" type="video/mp4"></video><div class="hero-copy"><h1>One view for your next fixture.</h1><p>Compare freight outlook, port compatibility, and timing before going to market.</p></div></div>''', height=112, scrolling=False)
else:
    st.markdown("""<div class="hero"><div class="hero-copy"><h1>One view for your next fixture.</h1><p>Compare freight outlook, port compatibility, and timing before going to market.</p></div></div>""", unsafe_allow_html=True)

if "live_coal" in st.session_state:
    coal = st.session_state.live_coal.iloc[-1]
    st.markdown(
        f'<div class="card" style="margin-bottom:18px"><div class="label">Internet benchmark · World Bank Pink Sheet</div>'
        f'<div style="margin-top:5px;font-weight:700;color:var(--text)">Australian coal: ${coal.price_usd_tonne:,.2f} / MT</div>'
        f'<div class="sub">Published {coal.date.strftime("%b %Y")} · Used as market context only, not a freight quote.</div></div>',
        unsafe_allow_html=True,
    )

with st.container(border=True):
    a, b, c, d = st.columns([1.15, 1.35, 1, 1.2])
    with a:
        cargo = st.selectbox("Cargo", suppliers.cargo.drop_duplicates().tolist(), key="cargo_select")
    cargo_suppliers = suppliers.loc[suppliers.cargo.eq(cargo)].reset_index(drop=True)
    supplier_options = cargo_suppliers.supplier.tolist()
    if st.session_state.get("supplier_select") not in supplier_options:
        st.session_state.supplier_select = supplier_options[0]
    with b:
        supplier_name = st.selectbox("Supplier / supply operation", supplier_options, key="supplier_select")
    supplier = cargo_suppliers.loc[cargo_suppliers.supplier.eq(supplier_name)].iloc[0]
    with c:
        volume = st.number_input("Cargo volume (MT)", 10_000, 500_000, 75_000, 5_000)
    with d:
        destination = st.selectbox("Discharge port", ports.port.tolist())
    contract_window = st.date_input("Target contract window", (date.today() + timedelta(days=14), date.today() + timedelta(days=74)))

st.caption(f"Supply lane: **{supplier.country} · {supplier.loading_port}**  |  Forecast region mapping: **{supplier.origin_key}**")

port = ports.loc[ports.port.eq(destination)].iloc[0]
origin = supplier.origin_key
subset = rates[(rates.origin == origin) & (rates.destination == destination)]
source_note = "Route-specific sample benchmark"
if subset.empty:
    subset = rates[(rates.origin == "Australia") & (rates.destination == "Paradip")]
    source_note = "Comparable sample benchmark"
history = subset.groupby("date", as_index=False).freight_rate_usd_tonne.mean()
forecast = forecast_rates(history, 90)
base_rate = float(forecast.forecast.iloc[:30].mean())
options = vessel_options(port, volume, base_rate)
choice = best_vessel(options)
saving = max(volume * base_rate * 1.06 - choice.estimated_cost, 0)
entry = forecast.loc[forecast.forecast.idxmin(), "date"]

m1, m2, m3 = st.columns(3)
with m1:
    st.markdown(f'<div class="card"><div class="label">Recommended fixture</div><div class="value">{choice.vessel_type}</div><div class="sub">{int(choice.loads)} lift(s) · {choice.turnaround_days} days estimated</div></div>', unsafe_allow_html=True)
with m2:
    st.markdown(f'<div class="card"><div class="label">Best booking window</div><div class="value">{entry.strftime("%d %b")}</div><div class="sub">Lowest point in the 90-day forecast</div></div>', unsafe_allow_html=True)
with m3:
    st.markdown(f'<div class="card"><div class="label">Potential saving vs. spot</div><div class="value">${saving / 1000:,.0f}K</div><div class="sub">Based on ${base_rate:.2f}/MT planning outlook</div></div>', unsafe_allow_html=True)

overview, market_map, fleet = st.tabs(["Decision overview", "India coast map & AIS", "Fleet fit"])
with overview:
    chart_col, decision_col = st.columns([1.65, .85], gap="large")
    with chart_col:
        st.markdown(f'<div class="section-title">Freight outlook <span>· {source_note} · USD / MT</span></div>', unsafe_allow_html=True)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=forecast.date, y=forecast.upper, line=dict(width=0), hoverinfo="skip", showlegend=False))
        fig.add_trace(go.Scatter(x=forecast.date, y=forecast.lower, fill="tonexty", fillcolor="rgba(0,126,122,.14)", line=dict(width=0), name="95% range", hovertemplate="$%{y:.2f}/MT<extra></extra>"))
        fig.add_trace(go.Scatter(x=forecast.date, y=forecast.forecast, line=dict(color=t["teal"], width=3), name="Forecast", hovertemplate="%{x|%d %b}<br><b>$%{y:.2f}/MT</b><extra></extra>"))
        fig.add_trace(go.Scatter(x=history.date, y=history.freight_rate_usd_tonne, mode="lines+markers", line=dict(color=t["blue"], width=2), marker=dict(size=5), name="Observed", hovertemplate="%{x|%d %b}<br><b>$%{y:.2f}/MT</b><extra></extra>"))
        fig.add_vline(x=entry.timestamp() * 1000, line_color=t["amber"], line_dash="dot", annotation_text=" BOOKING WINDOW", annotation_font_color=t["amber"])
        fig.update_layout(height=370, margin=dict(l=4, r=4, t=22, b=0), paper_bgcolor=t["card"], plot_bgcolor=t["card"], font=dict(family="IBM Plex Sans", color=t["text"]), legend=dict(orientation="h", y=1.12), xaxis=dict(showgrid=False), yaxis=dict(title="USD / MT", gridcolor=t["line"]))
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False}, key="freight-outlook")
    with decision_col:
        st.markdown('<div class="section-title">Charter call</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="card decision"><div class="label">Recommended action</div><h2>Secure a {choice.vessel_type}</h2><div class="sub">Target the {entry.strftime("%d %b")} window. Keep the final 20% flexible if conditions change.</div><hr style="border-color:var(--line);margin:16px 0"><div class="label">Port acceptance</div><div style="font-size:15px;font-weight:700;color:var(--text);margin-top:6px">{port.port} · {port.status}</div><div class="sub" style="margin-top:5px">Draft {port.max_draft_m} m · LOA {port.max_loa_m} m · Congestion {port.congestion_index}/100</div></div>', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Watchlist</div>', unsafe_allow_html=True)
        for risk in assess_risks(port, history)[:2]:
            st.markdown(f'<div class="risk"><span class="tag">{risk["severity"]}</span><b>{risk["title"]}</b><p>{risk["detail"]}</p></div>', unsafe_allow_html=True)

with market_map:
    st.markdown(f'<div class="section-title">Selected supply course <span>· {supplier.loading_port}, {supplier.country} → {destination} · destination is ringed</span></div>', unsafe_allow_html=True)
    st.plotly_chart(india_coast_map(ports, destination, supplier), width="stretch", config={"displayModeBar": False}, key="india-coast-map")
    st.caption("Indicative ocean corridor for commercial planning only. It is not a navigational route, weather route, or a vessel-safety instruction.")
    st.markdown('''<div class="card" style="padding:22px"><div class="label">Live AIS traffic</div><div style="font-size:18px;font-weight:700;color:var(--text);margin:7px 0">Open live vessel positions in MarineTraffic</div><div class="sub">The map above is SAGAR-AI's operational port map. Use the direct link below for provider-hosted, real-time AIS coverage around both Indian coastlines.</div></div>''', unsafe_allow_html=True)
    st.link_button("Open MarineTraffic in a new tab ↗", MARINE_TRAFFIC_URL, width="stretch")

with fleet:
    st.markdown('<div class="section-title">Vessel compatibility <span>· checked against {}</span></div>'.format(port.port), unsafe_allow_html=True)
    fleet_table = options[["vessel_type", "capacity", "loads", "draft_ok", "loa_ok", "beam_ok", "compatible", "estimated_cost", "turnaround_days"]].copy()
    fleet_table.columns = ["Vessel type", "DWT", "Lifts", "Draft", "LOA", "Beam", "Port compatible", "Estimated cost (USD)", "Turnaround (days)"]
    st.dataframe(fleet_table, width="stretch", hide_index=True, column_config={"Draft":st.column_config.CheckboxColumn(), "LOA":st.column_config.CheckboxColumn(), "Beam":st.column_config.CheckboxColumn(), "Port compatible":st.column_config.CheckboxColumn(), "Estimated cost (USD)":st.column_config.NumberColumn(format="$%.0f")})

st.caption("SAGAR-AI MVP · Forecasts and recommendations use illustrative sample data. Validate against licensed freight, AIS, and port sources before committing cargo.")
st.caption("Public commodity benchmark: World Bank Pink Sheet. Live AIS and dry-bulk freight feeds require provider credentials and appropriate data licences.")
