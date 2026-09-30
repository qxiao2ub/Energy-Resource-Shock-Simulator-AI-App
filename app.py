from __future__ import annotations

import base64
import copy
import html
import json
import math
import uuid
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any

import folium
import numpy as np
import pandas as pd
import streamlit as st
from folium import FeatureGroup
from streamlit_folium import st_folium

try:
    from streamlit_autorefresh import st_autorefresh
except Exception:  # pragma: no cover - fallback if optional component is unavailable
    st_autorefresh = None

from core.modeling import ACTIONS, EVENT_TYPES, predict_scenario, train_ai_stack
from core.simulation import (
    FLOW_MODES,
    RESOURCE_ICON,
    RESOURCE_INFO,
    RESOURCES,
    quadratic_curve_points,
    simulate,
)
from core.visitor_counter import CounterResult, count_visit_once

APP_TITLE = "Energy Resource Shock Simulator"
PROJECT_AUTHOR = "Ryan Zhou"
PROJECT_MENTOR = "Dr. Qingyang Xiao"
MAX_WORKSPACES = 3
WINDOW_DAYS = 7

TYPE_COLOR = {
    "war": "#dc2626",
    "earthquake": "#a16207",
    "hurricane": "#0891b2",
    "port_closure": "#1d4ed8",
    "pipeline_failure": "#ea580c",
    "cyberattack": "#7c3aed",
    "labor_strike": "#db2777",
    "sanctions": "#64748b",
    "mine_accident": "#92400e",
    "drought": "#ca8a04",
    "shipping_chokepoint": "#0d9488",
    "pandemic": "#16a34a",
}
STATUS_LABEL = {
    "active": "Happening now",
    "upcoming": "About to happen",
    "ended": "Just ended",
    "inactive": "Inactive",
}
STATUS_COLOR = {
    "active": "#ef4444",
    "upcoming": "#fbbf24",
    "ended": "#94a3b8",
    "inactive": "#64748b",
}
ROUTE_COLORS = ["#38bdf8", "#f472b6", "#a3e635", "#fb923c", "#c084fc", "#2dd4bf", "#facc15", "#f87171"]

st.set_page_config(page_title=APP_TITLE, page_icon="🌍", layout="wide", initial_sidebar_state="expanded")


def inject_theme() -> None:
    css_path = Path(__file__).parent / "assets" / "lovable_dark_theme.css"
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


inject_theme()


def secrets_dict() -> dict[str, Any]:
    try:
        if hasattr(st.secrets, "to_dict"):
            return st.secrets.to_dict()
        return dict(st.secrets)
    except Exception:
        return {}


def format_type(value: str) -> str:
    return value.replace("_", " ").title()


def parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def format_iso_date(value: str | None) -> str:
    parsed = parse_iso_date(value)
    return parsed.strftime("%d %b %Y") if parsed else ""


def get_event_status(sim_date: date, start_date: str | None, end_date: str | None) -> str:
    start = parse_iso_date(start_date)
    end = parse_iso_date(end_date) or start
    if not start or not end:
        return "inactive"
    if start <= sim_date <= end:
        return "active"
    if start > sim_date and (start - sim_date).days <= WINDOW_DAYS:
        return "upcoming"
    if sim_date > end and (sim_date - end).days <= WINDOW_DAYS:
        return "ended"
    return "inactive"


def default_event() -> dict[str, Any]:
    today = date.today()
    return {
        "id": uuid.uuid4().hex,
        "name": "Strait of Hormuz disruption",
        "type": "shipping_chokepoint",
        "severity": 7.5,
        "startDate": today.isoformat(),
        "endDate": (today + timedelta(days=14)).isoformat(),
        "notes": "Starter scenario near a critical energy shipping lane.",
        "lat": 26.6,
        "lon": 56.3,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def init_state() -> None:
    if "workspaces" not in st.session_state:
        st.session_state.workspaces = [{"id": "workspace-1", "name": "Workspace 1", "events": [default_event()]}]
    if "active_workspace_id" not in st.session_state:
        st.session_state.active_workspace_id = st.session_state.workspaces[0]["id"]
    if "sim_datetime" not in st.session_state:
        st.session_state.sim_datetime = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    if "sim_speed" not in st.session_state:
        st.session_state.sim_speed = 1.0
    if "sim_running" not in st.session_state:
        st.session_state.sim_running = False
    if "last_clock_tick" not in st.session_state:
        st.session_state.last_clock_tick = 0
    if "selected_resource" not in st.session_state:
        st.session_state.selected_resource = "Oil"
    if "flow_mode" not in st.session_state:
        st.session_state.flow_mode = "All"
    if "event_name" not in st.session_state:
        st.session_state.event_name = "New disruption event"
    if "event_type" not in st.session_state:
        st.session_state.event_type = "earthquake"
    if "event_lat" not in st.session_state:
        st.session_state.event_lat = 26.6
    if "event_lon" not in st.session_state:
        st.session_state.event_lon = 56.3
    if "last_map_click_signature" not in st.session_state:
        st.session_state.last_map_click_signature = ""


init_state()
VISITORS = count_visit_once(st.session_state, secrets_dict())


def workspaces() -> list[dict[str, Any]]:
    return st.session_state.workspaces


def active_workspace() -> dict[str, Any]:
    active_id = st.session_state.active_workspace_id
    for workspace in workspaces():
        if workspace["id"] == active_id:
            return workspace
    st.session_state.active_workspace_id = workspaces()[0]["id"]
    return workspaces()[0]


def current_events() -> list[dict[str, Any]]:
    return active_workspace().setdefault("events", [])


def update_sim_clock() -> None:
    if not st.session_state.sim_running or st_autorefresh is None:
        return
    tick = st_autorefresh(interval=1000, limit=None, key="simulation_clock")
    previous = int(st.session_state.last_clock_tick)
    if tick > previous:
        delta = min(tick - previous, 5)
        st.session_state.sim_datetime = st.session_state.sim_datetime + timedelta(hours=float(st.session_state.sim_speed) * delta)
        st.session_state.last_clock_tick = tick


update_sim_clock()


@st.cache_resource(show_spinner=False)
def cached_ai_stack() -> dict[str, Any]:
    return train_ai_stack()


@st.cache_data(show_spinner=False)
def load_country_geo() -> dict[str, Any] | None:
    path = Path(__file__).parent / "lovable_ui_source" / "src" / "data" / "countries.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def svg_flag(color: str, width: int = 24, height: int = 29) -> str:
    return f"""<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' viewBox='0 0 20 24'>
    <path d='M4 23V2' stroke='#111827' stroke-width='1.8' stroke-linecap='round'/>
    <path d='M4.9 2.6h10.4l-2.6 3.9 2.6 3.9H4.9z' fill='{html.escape(color)}' stroke='#111827' stroke-width='1' stroke-linejoin='round'/></svg>"""


def flag_div_icon(event: dict[str, Any], status: str) -> folium.DivIcon:
    color = TYPE_COLOR.get(str(event.get("type")), "#64748b")
    size = 28 if status == "active" else 23
    halo = STATUS_COLOR.get(status, "#64748b")
    encoded = base64.b64encode(svg_flag(color, size, int(size * 1.2)).encode("utf-8")).decode("ascii")
    img = f"<img src='data:image/svg+xml;base64,{encoded}' width='{size}' style='filter:drop-shadow(0 0 4px {halo}) drop-shadow(0 1px 2px rgba(0,0,0,.7));'/>"
    return folium.DivIcon(html=img, icon_size=(size, int(size * 1.2)), icon_anchor=(5, int(size * 1.2) - 1))


def build_simulation_map(events: list[dict[str, Any]], sim_state: dict[str, Any], mode: str) -> folium.Map:
    world_map = folium.Map(
        location=[20, 0],
        zoom_start=2,
        min_zoom=2,
        max_zoom=8,
        tiles="CartoDB dark_matter",
        control_scale=True,
        prefer_canvas=True,
        zoom_control=False,
    )
    folium.TileLayer("OpenStreetMap", name="OpenStreetMap").add_to(world_map)

    # Country stress/trade layer copied conceptually from the new Lovable UI.
    if mode in {"All", "Supply", "Demand", "Trade"}:
        geo = load_country_geo()
        if geo:
            geo_copy = copy.deepcopy(geo)
            country_map = {c["code"]: c for c in sim_state["countries"]}
            for feature in geo_copy.get("features", []):
                code = str(feature.get("id", ""))
                c = country_map.get(code)
                props = feature.setdefault("properties", {})
                if c:
                    props["sim_name"] = c["name"]
                    props["production"] = round(float(c["production"]), 1)
                    props["demand"] = round(float(c["demand_now"]), 1)
                    props["balance"] = round(float(c["balance"]), 1)
                    props["stress"] = round(float(c["stress"]), 1)

            def style_country(feature: dict[str, Any]) -> dict[str, Any]:
                code = str(feature.get("id", ""))
                c = country_map.get(code)
                if not c:
                    return {"fillOpacity": 0.0, "weight": 0.45, "color": "#334155"}
                if mode == "Supply":
                    value = float(c["production"])
                    color = "#22c55e" if value > 5 else "#eab308"
                    opacity = min(0.55, 0.10 + value * 0.025)
                elif mode == "Demand":
                    value = float(c["demand_now"])
                    color = "#f59e0b"
                    opacity = min(0.55, 0.10 + value * 0.022)
                elif mode == "Trade":
                    value = float(c["balance"])
                    color = "#22c55e" if value >= 0 else "#f59e0b"
                    opacity = min(0.55, 0.10 + abs(value) * 0.035)
                else:
                    value = float(c["stress"])
                    color = "#ef4444" if value > 35 else "#f59e0b"
                    opacity = min(0.50, 0.08 + value * 0.004)
                return {"fillColor": color, "fillOpacity": opacity, "weight": 0.55, "color": "#475569"}

            layer = folium.GeoJson(geo_copy, name="Country simulation", style_function=style_country)
            try:
                folium.GeoJsonTooltip(
                    fields=["sim_name", "production", "demand", "balance", "stress"],
                    aliases=["Country", "Production", "Demand", "Balance", "Stress"],
                    sticky=True,
                ).add_to(layer)
            except Exception:
                pass
            layer.add_to(world_map)

    # Routes and money-flow view.
    if mode in {"All", "Supply", "Trade", "Money"}:
        for index, route in enumerate(sim_state["routes"]):
            source = route["from_hub"]
            dest = route["to_country"]
            is_money = mode == "Money"
            a = (dest["lat"], dest["lon"]) if is_money else (source["lat"], source["lon"])
            b = (source["lat"], source["lon"]) if is_money else (dest["lat"], dest["lon"])
            points = quadratic_curve_points(a[0], a[1], b[0], b[1], index)
            disruption = float(route["disruption"])
            color = "#22c55e" if is_money else ("#ef4444" if disruption > 0.25 else ROUTE_COLORS[index % len(ROUTE_COLORS)])
            amount = float(route["volume"]) * (1.0 - disruption)
            tooltip = (
                f"<b>{'Simulated trade value' if is_money else sim_state['resource'] + ' flow'}</b><br>"
                f"{html.escape(str(dest['name'] if is_money else source['name']))} → {html.escape(str(source['name'] if is_money else dest['name']))}<br>"
                f"Relative volume {amount:.1f}" + (f" · disruption {disruption*100:.0f}%" if disruption > 0.15 else "")
            )
            folium.PolyLine(points, color=color, weight=max(2.0, float(route["volume"]) * 0.48) * (1 - disruption * 0.55), opacity=0.82, tooltip=tooltip).add_to(world_map)
            # Shipment dots move as the simulation clock rerenders.
            drift = ((sim_state["time"].timestamp() / 3600.0) * max(0.25, float(st.session_state.sim_speed)) / 24.0) % 1.0
            for dot_index in range(3):
                pos = (drift + dot_index / 3.0) % 1.0
                point_index = min(len(points) - 1, int(pos * (len(points) - 1)))
                folium.CircleMarker(points[point_index], radius=2.5, color="#111827", weight=1, fill=True, fill_color=color, fill_opacity=0.95).add_to(world_map)
            if disruption > 0.15 and not is_money:
                alternate = next((h for h in sim_state["hubs"] if h["id"] != source["id"] and h["kind"] != "Chokepoint"), None)
                if alternate:
                    folium.PolyLine(
                        [(alternate["lat"], alternate["lon"]), (dest["lat"], dest["lon"])],
                        color="#22c55e", weight=2, opacity=min(0.85, disruption + 0.2), dash_array="4 10",
                        tooltip=f"Illustrative alternate route: {alternate['name']} → {dest['name']}",
                    ).add_to(world_map)

    # Supply hubs.
    if mode in {"All", "Supply", "Events"}:
        for hub in sim_state["hubs"]:
            impact = 0.0
            for effect in sim_state["effects"]:
                distance_deg = math.hypot(float(hub["lat"]) - float(effect["event"].get("lat", 0)), float(hub["lon"]) - float(effect["event"].get("lon", 0)))
                impact = max(impact, float(effect["impact"]) * math.exp(-max(0.0, distance_deg - 4.0) / 22.0))
            fill = "#ef4444" if impact > 0.15 else "#eab308"
            tooltip = f"<b>{hub['name']}</b><br>{hub['kind']} · {sim_state['resource']}<br>Simulated capacity {(1-min(.85,impact))*100:.0f}%"
            folium.CircleMarker([hub["lat"], hub["lon"]], radius=7 if hub["kind"] == "Chokepoint" else 5, color="#111827", weight=2, fill=True, fill_color=fill, fill_opacity=0.96, tooltip=tooltip).add_to(world_map)

    # Impact rings around events active in the model window.
    if mode in {"All", "Events"}:
        for effect in sim_state["effects"]:
            ev = effect["event"]
            phase = min(1.0, max(0.0, float(effect["age"]) / 3.0))
            radius = (60 + float(ev.get("severity", 0)) * 18) * 1000 * max(0.15, phase)
            folium.Circle([float(ev.get("lat", 0)), float(ev.get("lon", 0))], radius=radius, color="#ef4444", fill=True, fill_color="#ef4444", fill_opacity=max(0.03, 0.12 * (1 - phase / 2) * float(effect["phase"])), opacity=0.55 * float(effect["phase"]), weight=1).add_to(world_map)

    # User event flags remain visible in All / Events mode.
    if mode in {"All", "Events"}:
        for event in events:
            status = get_event_status(sim_state["time"].date(), event.get("startDate"), event.get("endDate"))
            details = [
                f"<b>{html.escape(str(event.get('name', 'Event')))}</b>",
                f"Status: {STATUS_LABEL[status]}",
                f"Type: {format_type(str(event.get('type','')))}",
                f"Severity: {float(event.get('severity',0)):.1f}/10",
                f"Dates: {format_iso_date(event.get('startDate')) or 'No start'}" + (f" → {format_iso_date(event.get('endDate'))}" if event.get("endDate") else ""),
            ]
            if event.get("notes"):
                details.append(html.escape(str(event["notes"])))
            folium.Marker(
                [float(event.get("lat", 0)), float(event.get("lon", 0))],
                icon=flag_div_icon(event, status),
                tooltip=f"{html.escape(str(event.get('name','Event')))} · {STATUS_LABEL[status]}",
                popup=folium.Popup("<br>".join(details), max_width=360),
            ).add_to(world_map)

    legend_label = {
        "Money": "Simulated trade value",
        "Trade": "Trade balance",
        "Demand": "Demand",
        "Supply": "Production",
        "Events": "Event impact",
        "All": "Supply stress",
    }[mode]
    legend = f"""
    <div style="position:fixed;bottom:26px;right:18px;z-index:9999;background:rgba(25,34,53,.94);color:#f8f3e6;padding:10px 13px;border-radius:10px;border:1px solid rgba(255,255,255,.16);box-shadow:0 8px 28px rgba(0,0,0,.38);font-size:12px;">
      <b>{legend_label}</b><br><span style='color:#22c55e'>●</span> Surplus / normal &nbsp; <span style='color:#f59e0b'>●</span> Stress &nbsp; <span style='color:#ef4444'>●</span> Disrupted
    </div>"""
    world_map.get_root().html.add_child(folium.Element(legend))
    folium.LayerControl(collapsed=True).add_to(world_map)
    return world_map


def render_floating_visitor(counter: CounterResult) -> None:
    st.markdown(
        f"<div class='visitor-floating'>👥 Cumulative app users <span class='num'>{counter.count:,}</span></div>",
        unsafe_allow_html=True,
    )


def render_header(events: list[dict[str, Any]], sim_state: dict[str, Any], counter: CounterResult) -> None:
    active_count = len(sim_state["active"])
    st.markdown(
        f"""
        <div class="app-hero">
          <div>
            <h1>{APP_TITLE}</h1>
            <p>Map wars, disasters, cyber incidents, chokepoint failures and other shocks, then explore simulated global resource-flow consequences.</p>
            <p class="credit-line"><strong>Author:</strong> {PROJECT_AUTHOR} &nbsp;·&nbsp; <strong>Mentor:</strong> {PROJECT_MENTOR}</p>
          </div>
          <div class="pill-row">
            <span class="pill primary">{RESOURCE_ICON[sim_state['resource']]} {sim_state['resource']}</span>
            <span class="pill">{len(events)} events</span>
            <span class="pill live">{active_count} active</span>
            <span class="pill">👥 {counter.count:,} users</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_hud(sim_state: dict[str, Any]) -> None:
    resource_col, price_col, index_col = st.columns([0.8, 1.1, 1.35])
    with resource_col:
        st.markdown("<div class='hud-card'>", unsafe_allow_html=True)
        st.markdown("<div class='hud-label'>Resource</div>", unsafe_allow_html=True)
        selected = st.selectbox("Resource", RESOURCES, index=RESOURCES.index(st.session_state.selected_resource), label_visibility="collapsed")
        if selected != st.session_state.selected_resource:
            st.session_state.selected_resource = selected
            st.rerun()
        st.markdown(f"<div class='hud-sub'>Scenario layer for {RESOURCE_ICON[selected]} {selected}</div></div>", unsafe_allow_html=True)
    with price_col:
        sign_class = "hud-positive" if float(sim_state["price_pct"]) >= 0 else "hud-danger"
        st.markdown(
            f"""<div class='hud-card'><div class='hud-label'>◉ Simulated price</div>
            <div class='hud-value'>${sim_state['price']:.2f} <span style='font-size:.78rem;color:var(--muted-fg)'>{RESOURCE_INFO[sim_state['resource']]['unit']}</span></div>
            <div class='hud-sub'><span class='{sign_class}'>{sim_state['price_pct']:+.1f}%</span> · 30d scenario ${sim_state['forecast']:.2f}</div></div>""",
            unsafe_allow_html=True,
        )
    with index_col:
        st.markdown(
            f"""<div class='hud-card'><div class='hud-label'>⌁ Simulated global index</div>
            <div style='display:grid;grid-template-columns:repeat(3,1fr);gap:.65rem;margin-top:.55rem'>
              <div><div class='hud-sub'>Supply</div><b>{sim_state['supply']:.0f}%</b></div>
              <div><div class='hud-sub'>Demand</div><b>{sim_state['demand']:.0f}%</b></div>
              <div><div class='hud-sub'>Balance</div><b class='hud-positive'>{sim_state['balance']:+.0f}%</b></div>
            </div><div class='hud-sub'>{len(sim_state['active'])} active shocks · risk {sim_state['risk']:.1f}/10</div></div>""",
            unsafe_allow_html=True,
        )

    mode = st.radio("Map view", FLOW_MODES, index=FLOW_MODES.index(st.session_state.flow_mode), horizontal=True, label_visibility="collapsed")
    if mode != st.session_state.flow_mode:
        st.session_state.flow_mode = mode
        st.rerun()
    play_label = "Playing" if st.session_state.sim_running else "Paused"
    st.caption(f"Illustrative classroom scenario · {play_label} · not a market forecast")


def render_timebar() -> None:
    cols = st.columns([1.0, .65, .65, 1.1, .9, 2.1, .65])
    with cols[0]:
        if st.button("Pause" if st.session_state.sim_running else "Start time", type="primary", use_container_width=True):
            st.session_state.sim_running = not st.session_state.sim_running
            st.session_state.last_clock_tick = 0
            st.rerun()
    with cols[1]:
        if st.button("−1d", use_container_width=True):
            st.session_state.sim_datetime -= timedelta(days=1)
            st.rerun()
    with cols[2]:
        if st.button("+1d", use_container_width=True):
            st.session_state.sim_datetime += timedelta(days=1)
            st.rerun()
    current_dt = st.session_state.sim_datetime
    with cols[3]:
        d = st.date_input("Current date", current_dt.date())
    with cols[4]:
        t = st.time_input("Time (24h)", current_dt.time().replace(second=0, microsecond=0), step=60)
    with cols[5]:
        speed = st.slider("Speed · simulated hours/sec", 0.5, 72.0, float(st.session_state.sim_speed), 0.5)
    with cols[6]:
        st.write("")
        if st.button("Now", use_container_width=True):
            st.session_state.sim_datetime = datetime.now(timezone.utc).replace(second=0, microsecond=0)
            st.rerun()
    if d != current_dt.date() or t != current_dt.time().replace(second=0, microsecond=0) or speed != st.session_state.sim_speed:
        st.session_state.sim_datetime = datetime.combine(d, t, tzinfo=timezone.utc)
        st.session_state.sim_speed = speed
        st.rerun()
    if st.session_state.sim_running and st_autorefresh is None:
        st.caption("Automatic playback component is unavailable; manual date/time controls remain active.")


def render_timeline(events: list[dict[str, Any]], sim_state: dict[str, Any]) -> None:
    valid_starts = [parse_iso_date(e.get("startDate")) for e in events]
    starts = [d for d in valid_starts if d]
    if not starts:
        return
    ends = [parse_iso_date(e.get("endDate")) or parse_iso_date(e.get("startDate")) for e in events]
    ends = [d for d in ends if d]
    min_d, max_d = min(starts) - timedelta(days=7), max(ends) + timedelta(days=30)
    current_d = min(max(st.session_state.sim_datetime.date(), min_d), max_d)
    left, right = st.columns([4, 1])
    with left:
        st.markdown("### Scenario timeline")
        st.caption(f"{current_d.strftime('%d %b %Y')} · {sim_state['resource']} · simulated progression")
    with right:
        if st.button("Play from first event", use_container_width=True):
            st.session_state.sim_datetime = datetime.combine(min(starts), time.min, tzinfo=timezone.utc)
            st.session_state.sim_running = True
            st.session_state.last_clock_tick = 0
            st.rerun()
    timeline_date = st.slider("Scenario date", min_value=min_d, max_value=max_d, value=current_d, step=timedelta(days=1), label_visibility="collapsed")
    if timeline_date != st.session_state.sim_datetime.date():
        st.session_state.sim_datetime = datetime.combine(timeline_date, st.session_state.sim_datetime.time(), tzinfo=timezone.utc)
        st.session_state.sim_running = False
        st.rerun()
    disrupted = sum(1 for r in sim_state["routes"] if float(r["disruption"]) > .15)
    entries: list[str] = []
    for effect in sim_state["effects"]:
        age = float(effect["age"])
        if 0 <= age < 3: entries.append(f"{effect['event']['name']} begins near {effect['nearest']['name']}")
        elif 3 <= age < 7: entries.append(f"Production responds at {effect['nearest']['name']}")
        elif 7 <= age < 13: entries.append(f"Export routes from {effect['nearest']['name']} adjust")
        elif 13 <= age < 24: entries.append("Importers and simulated price respond")
        elif age >= float(effect["duration"]): entries.append(f"Recovery begins near {effect['nearest']['name']}")
    st.caption(f"Risk {sim_state['risk']:.1f}/10 · Supply {sim_state['supply']:.0f}% · Estimated disrupted routes {disrupted}" + (f" · ↗ {entries[0]}" if entries else ""))


def render_workspace_bar() -> None:
    st.markdown("### Workspaces")
    options = {w["name"]: w["id"] for w in workspaces()}
    current_name = active_workspace()["name"]
    cols = st.columns([2.1, 2.0, .65, .65])
    with cols[0]:
        selected_name = st.selectbox("Workspace", list(options), index=list(options).index(current_name), label_visibility="collapsed")
        if options[selected_name] != st.session_state.active_workspace_id:
            st.session_state.active_workspace_id = options[selected_name]
            st.rerun()
    with cols[1]:
        rename = st.text_input("Rename", value=current_name, label_visibility="collapsed", placeholder="Workspace name")
        if rename.strip() and rename.strip() != current_name:
            active_workspace()["name"] = rename.strip()
            st.rerun()
    with cols[2]:
        if st.button("＋ New", disabled=len(workspaces()) >= MAX_WORKSPACES, use_container_width=True):
            ws_id = f"workspace-{uuid.uuid4().hex[:8]}"
            workspaces().append({"id": ws_id, "name": f"Workspace {len(workspaces())+1}", "events": []})
            st.session_state.active_workspace_id = ws_id
            st.rerun()
    with cols[3]:
        if st.button("Delete", disabled=len(workspaces()) <= 1, use_container_width=True):
            active_id = active_workspace()["id"]
            st.session_state.workspaces = [w for w in workspaces() if w["id"] != active_id]
            st.session_state.active_workspace_id = st.session_state.workspaces[0]["id"]
            st.rerun()
    if len(workspaces()) >= MAX_WORKSPACES:
        st.caption("Maximum of 3 workspaces, matching the Lovable UI design.")


def render_sidebar(events: list[dict[str, Any]], counter: CounterResult) -> None:
    with st.sidebar:
        st.title("Supply Shock Studio")
        st.markdown(f"**Author:** {PROJECT_AUTHOR}  \n**Mentor:** {PROJECT_MENTOR}")
        st.success(f"👥 Cumulative app users: **{counter.count:,}**")
        st.caption("The visitor counter increments once per Streamlit browser session, not on every widget rerun.")
        st.divider()
        st.subheader("Add an event")
        st.caption("Click the map to prefill coordinates, then complete the event form.")
        with st.form("add_event_form", clear_on_submit=False):
            name = st.text_input("Name", key="event_name", placeholder="Suez Canal blockage")
            event_type = st.selectbox("Type", EVENT_TYPES, index=EVENT_TYPES.index(st.session_state.event_type) if st.session_state.event_type in EVENT_TYPES else 0, format_func=format_type, key="event_type")
            severity = st.slider("Severity", 0.0, 10.0, 5.0, 0.1)
            start_value = st.date_input("Start date", value=st.session_state.sim_datetime.date())
            end_value = st.date_input("End date", value=st.session_state.sim_datetime.date() + timedelta(days=14), min_value=start_value)
            lat = st.number_input("Latitude", min_value=-90.0, max_value=90.0, step=0.1, key="event_lat")
            lon = st.number_input("Longitude", min_value=-180.0, max_value=180.0, step=0.1, key="event_lon")
            notes = st.text_area("Description", placeholder="What is happening here?")
            submitted = st.form_submit_button("Add event", type="primary", use_container_width=True)
        if submitted:
            trimmed = name.strip() or "Unnamed event"
            if any(str(e.get("name", "")).lower() == trimmed.lower() for e in events):
                st.error("An event with this name already exists in this workspace.")
            else:
                events.append({
                    "id": uuid.uuid4().hex,"name": trimmed,"type": event_type,"severity": float(severity),
                    "startDate": start_value.isoformat(),"endDate": end_value.isoformat(),"notes": notes.strip(),
                    "lat": float(lat),"lon": float(lon),"created_at": datetime.now(timezone.utc).isoformat(),
                })
                st.success("Event added.")
                st.rerun()

        st.divider()
        st.subheader("Scenario import / export")
        upload = st.file_uploader("Import workspace JSON", type=["json"])
        if upload is not None:
            try:
                imported = json.loads(upload.getvalue().decode("utf-8"))
                if isinstance(imported, dict) and isinstance(imported.get("events"), list):
                    active_workspace()["events"] = imported["events"]
                    st.success("Workspace imported.")
                    st.rerun()
                else:
                    st.error("JSON must contain an 'events' list.")
            except Exception as exc:
                st.error(f"Could not import JSON: {exc}")
        payload = json.dumps({"workspace": active_workspace()["name"], "events": current_events()}, indent=2)
        st.download_button("Download workspace JSON", payload, file_name="energy_shock_workspace.json", mime="application/json", use_container_width=True)

        st.divider()
        with st.expander("Visitor counter persistence"):
            if counter.persistent:
                st.success("Persistent no-database GitHub-file counter is active.")
            else:
                st.warning("Local no-database mode is active. It survives normal reruns but Streamlit Cloud can reset local files after rebuilds/restarts. Configure the GitHub-file mode in Streamlit Secrets for durable cumulative counting.")
            st.caption(counter.detail)


def render_metrics(summary: pd.DataFrame, events: list[dict[str, Any]], sim_state: dict[str, Any], counter: CounterResult) -> None:
    if summary.empty:
        top_resource, top_risk, avg_delta = "—", "0.0/10", "0.0%"
    else:
        top = summary.sort_values("supply_risk_index", ascending=False).iloc[0]
        top_resource, top_risk = str(top["resource"]), f"{top['supply_risk_index']:.1f}/10"
        avg_delta = f"{summary['predicted_30d_price_change_pct'].mean():+.1f}%"
    values = [
        ("Workspace events", str(len(events)), active_workspace()["name"]),
        ("Active shocks", str(len(sim_state["active"])), f"{sim_state['resource']} scenario"),
        ("Highest-risk resource", top_resource, top_risk),
        ("Avg 30d price Δ", avg_delta, "ML scenario output"),
        ("Cumulative app users", f"{counter.count:,}", "visible across the app"),
    ]
    cols = st.columns(len(values))
    for col, (label, value, sub) in zip(cols, values):
        with col:
            st.markdown(f"<div class='metric-card'><div class='label'>{label}</div><div class='value'>{value}</div><div class='sub'>{sub}</div></div>", unsafe_allow_html=True)


def render_event_cards(events: list[dict[str, Any]]) -> None:
    if not events:
        st.info("No events yet. Click the map and add your first supply-chain shock.")
        return
    sort_by = st.selectbox("Sort events by", ["Time created", "Start date", "Severity", "Type"])
    ordered = list(events)
    if sort_by == "Start date": ordered.sort(key=lambda e: e.get("startDate") or "9999-12-31")
    elif sort_by == "Severity": ordered.sort(key=lambda e: float(e.get("severity", 0)), reverse=True)
    elif sort_by == "Type": ordered.sort(key=lambda e: str(e.get("type", "")))
    for event in ordered:
        status = get_event_status(st.session_state.sim_datetime.date(), event.get("startDate"), event.get("endDate"))
        type_color = TYPE_COLOR.get(str(event.get("type")), "#64748b")
        dates = format_iso_date(event.get("startDate"))
        if event.get("endDate"): dates += f" → {format_iso_date(event.get('endDate'))}"
        notes = html.escape(str(event.get("notes", "")))
        st.markdown(
            f"""<div class='event-card {status}'><div class='pill-row'><h4>{html.escape(str(event.get('name','Event')))}</h4>
            <span class='pill' style='background:{type_color};color:white;border-color:transparent'>{format_type(str(event.get('type','')))}</span>
            <span class='pill'>{STATUS_LABEL[status]}</span><span class='pill'>Severity {float(event.get('severity',0)):.1f}/10</span></div>
            <p>Lat {float(event.get('lat',0)):.1f}° · Lng {float(event.get('lon',0)):.1f} · {dates}</p>{f'<p>{notes}</p>' if notes else ''}</div>""",
            unsafe_allow_html=True,
        )
        if st.button(f"Remove {event.get('name')}", key=f"remove_{event['id']}"):
            active_workspace()["events"] = [e for e in events if e.get("id") != event.get("id")]
            st.rerun()


def render_forecast_tab(summary: pd.DataFrame, event_level: pd.DataFrame) -> None:
    if summary.empty:
        st.info("Add at least one event to generate a forecast.")
        return
    st.subheader("Machine-learning forecast summary")
    display = summary.copy()
    display["predicted_30d_price_change_pct"] = display["predicted_30d_price_change_pct"].round(2)
    display["supply_risk_index"] = display["supply_risk_index"].round(2)
    st.dataframe(display, use_container_width=True, hide_index=True)
    st.bar_chart(summary.set_index("resource")[["predicted_30d_price_change_pct", "supply_risk_index"]], use_container_width=True)
    st.subheader("Event-resource detail")
    detail = event_level.copy()
    for column in ["distance_to_hub_km", "predicted_30d_price_change_pct", "supply_risk_index"]:
        detail[column] = detail[column].astype(float).round(2)
    st.dataframe(detail, use_container_width=True, hide_index=True)


def render_ai_tab(ai: dict[str, Any], event_level: pd.DataFrame) -> None:
    st.subheader("Deep neural network classification + crisis clustering")
    st.write("The educational AI stack uses an MLP neural-network classifier and K-means clustering. The workflow is inspectable and can be retrained with real historical labels.")
    st.metric("Neural-network validation accuracy on synthetic labels", f"{ai['nn_accuracy']:.1%}")
    if event_level.empty:
        st.info("Add events to see their neural-network class and crisis cluster.")
        return
    view = event_level[["event_name","event_type","resource","severity","duration_days","crisis_cluster","nn_risk_class","supply_risk_index"]].copy()
    view["supply_risk_index"] = view["supply_risk_index"].astype(float).round(2)
    st.dataframe(view, use_container_width=True, hide_index=True)
    labels = pd.DataFrame([{"cluster": k, "label": v} for k, v in ai["cluster_labels"].items()]).sort_values("cluster")
    st.dataframe(labels, use_container_width=True, hide_index=True)


def render_rl_tab(summary: pd.DataFrame) -> None:
    st.subheader("Reinforcement-learning response recommendations")
    st.write("A compact Q-learning policy chooses from transparent response actions based on simulated risk, duration, and resource criticality.")
    if summary.empty:
        st.info("Add events to get RL recommendations.")
        return
    view = summary[["resource","risk_level","supply_risk_index","top_event_driver","rl_recommended_response"]].copy()
    view["supply_risk_index"] = view["supply_risk_index"].astype(float).round(2)
    st.dataframe(view, use_container_width=True, hide_index=True)
    st.caption("Action space: " + " · ".join(ACTIONS))


def render_network_tab(sim_state: dict[str, Any]) -> None:
    st.subheader("Resource-flow simulation details")
    st.write("This tab exposes the deterministic classroom simulation layer adapted from the new Lovable UI: hubs, routes, disruptions, country production/demand balance, and event propagation.")
    if sim_state["routes"]:
        routes = pd.DataFrame([
            {
                "route": f"{r['from_hub']['name']} → {r['to_country']['name']}",
                "resource": r["resource"],
                "baseline_volume": r["volume"],
                "disruption_pct": round(float(r["disruption"]) * 100, 1),
                "remaining_volume": round(float(r["volume"]) * (1 - float(r["disruption"])), 2),
            }
            for r in sim_state["routes"]
        ])
        st.dataframe(routes, use_container_width=True, hide_index=True)
    countries = pd.DataFrame([
        {"country": c["name"], "production": round(c["production"],2), "demand": round(c["demand_now"],2), "balance": round(c["balance"],2), "stress": round(c["stress"],1)}
        for c in sim_state["countries"] if c["production"] or c["demand_now"]
    ]).sort_values("stress", ascending=False)
    st.dataframe(countries, use_container_width=True, hide_index=True)


def render_sources_tab(counter: CounterResult) -> None:
    st.subheader("Data sources, deployment, and visitor-counter notes")
    st.markdown(
        """
        **Free/student-friendly data path**

        - World Bank Pink Sheet commodity price history.
        - U.S. EIA Open Data API v2 for energy production, inventories and prices.
        - GDELT for global event/news signals.
        - User-uploaded JSON scenarios for classroom experiments.

        **Visitor counter**

        The app does **not** require a database. It increments once per Streamlit browser session. For durable counting across Streamlit Cloud restarts, configure the GitHub-file persistence mode described in `COUNTER_SETUP.md`. Without that configuration, the local-file fallback can reset when Streamlit rebuilds the app container.
        """
    )
    st.info(f"Current counter backend: {counter.backend} · durable persistence: {'yes' if counter.persistent else 'no'}")
    st.warning("Educational simulation only. This is not investment advice, emergency guidance, or an operational forecast.")


def render_footer(counter: CounterResult) -> None:
    st.markdown(
        f"""<hr><p class='small-note'><strong>Author:</strong> {PROJECT_AUTHOR} &nbsp;·&nbsp; <strong>Mentor:</strong> {PROJECT_MENTOR}<br>
        New Lovable UI source is preserved in <code>lovable_ui_source/</code>. Streamlit implementation includes map-flow views, simulation HUD, timeline, workspaces, ML/DNN/clustering/RL analysis, and a no-database cumulative visitor counter.<br>
        Current visible visitor count: <strong>{counter.count:,}</strong>.</p>""",
        unsafe_allow_html=True,
    )


def main() -> None:
    events = current_events()
    sim_state = simulate(events, st.session_state.selected_resource, st.session_state.sim_datetime)
    render_floating_visitor(VISITORS)
    render_header(events, sim_state, VISITORS)
    st.write("")

    st.markdown("<div class='map-note'>Click anywhere on the map to capture coordinates for a new supply-shock event. Hover routes, hubs, countries and flags for simulation details.</div>", unsafe_allow_html=True)
    world_map = build_simulation_map(events, sim_state, st.session_state.flow_mode)
    map_state = st_folium(
        world_map,
        height=650,
        use_container_width=True,
        key=f"shock_map_{active_workspace()['id']}_{len(events)}_{st.session_state.selected_resource}_{st.session_state.flow_mode}_{st.session_state.sim_datetime.isoformat()[:16]}",
        returned_objects=["last_clicked"],
    )
    if map_state and map_state.get("last_clicked"):
        click = map_state["last_clicked"]
        lat, lon = round(float(click["lat"]), 1), round(float(click["lng"]), 1)
        signature = f"{lat},{lon}"
        if signature != st.session_state.last_map_click_signature:
            st.session_state.last_map_click_signature = signature
            st.session_state.event_lat = lat
            st.session_state.event_lon = lon
            st.toast(f"Map coordinates captured: {lat}°, {lon}°. Complete the event in the sidebar.")
            st.rerun()

    st.write("")
    render_hud(sim_state)
    st.divider()
    render_timebar()
    st.divider()
    render_timeline(events, sim_state)
    st.divider()
    render_workspace_bar()
    st.write("")

    # Sidebar is globally visible, including while users switch analysis tabs.
    render_sidebar(events, VISITORS)

    ai = cached_ai_stack()
    summary, event_level = predict_scenario(events, ai)
    render_metrics(summary, events, sim_state, VISITORS)
    st.write("")

    tab_forecast, tab_events, tab_ai, tab_rl, tab_network, tab_sources = st.tabs(
        ["Forecast", "Your events", "Event AI", "RL response", "Network details", "Data & setup"]
    )
    with tab_forecast:
        render_forecast_tab(summary, event_level)
    with tab_events:
        render_event_cards(events)
    with tab_ai:
        render_ai_tab(ai, event_level)
    with tab_rl:
        render_rl_tab(summary)
    with tab_network:
        render_network_tab(sim_state)
    with tab_sources:
        render_sources_tab(VISITORS)

    render_footer(VISITORS)


if __name__ == "__main__":
    main()
