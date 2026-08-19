"""Energy Resource Shock Simulator

Streamlit app converted from a Lovable React UI concept.
It keeps the Lovable design pattern while running as a pure Python app that
Streamlit Community Cloud can launch from GitHub with `app.py`.
"""

from __future__ import annotations

import base64
import html
import json
import math
import uuid
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any

import folium
import numpy as np
import pandas as pd
import streamlit as st
from folium import FeatureGroup
from sklearn.cluster import KMeans
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from streamlit_folium import st_folium

APP_TITLE = "Energy Resource Shock Simulator"
RANDOM_SEED = 42
WINDOW_DAYS = 7
MAX_WORKSPACES = 3

EVENT_TYPES = [
    "war",
    "earthquake",
    "hurricane",
    "port_closure",
    "pipeline_failure",
    "cyberattack",
    "labor_strike",
    "sanctions",
    "mine_accident",
    "drought",
    "shipping_chokepoint",
    "pandemic",
]

TYPE_COLOR = {
    "war": "#dc2626",
    "earthquake": "#a16207",
    "hurricane": "#0891b2",
    "port_closure": "#1d4ed8",
    "pipeline_failure": "#ea580c",
    "cyberattack": "#7c3aed",
    "labor_strike": "#db2777",
    "sanctions": "#0f172a",
    "mine_accident": "#78350f",
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
    "active": "#c9372c",
    "upcoming": "#c8801a",
    "ended": "#7b8794",
    "inactive": "#1f4e79",
}

RESOURCE_TICKERS = {
    "WTI Crude Oil": "CL=F",
    "Brent Crude Oil": "BZ=F",
    "Natural Gas": "NG=F",
    "Gold": "GC=F",
    "Silver": "SI=F",
    "Copper": "HG=F",
    "Gasoline": "RB=F",
    "Heating Oil": "HO=F",
}

ENERGY_RESOURCES = {"WTI Crude Oil", "Brent Crude Oil", "Natural Gas", "Gasoline", "Heating Oil"}

SUPPLY_HUBS = pd.DataFrame(
    [
        {
            "hub": "Strait of Hormuz",
            "lat": 26.57,
            "lon": 56.25,
            "resources": "WTI Crude Oil,Brent Crude Oil,Natural Gas,Gasoline,Heating Oil",
            "importance": 10,
        },
        {
            "hub": "Suez Canal",
            "lat": 30.59,
            "lon": 32.27,
            "resources": "WTI Crude Oil,Brent Crude Oil,Natural Gas,Gasoline,Heating Oil",
            "importance": 8,
        },
        {
            "hub": "Panama Canal",
            "lat": 9.08,
            "lon": -79.68,
            "resources": "WTI Crude Oil,Brent Crude Oil,Natural Gas,Copper,Gold",
            "importance": 7,
        },
        {
            "hub": "US Gulf Coast",
            "lat": 29.76,
            "lon": -95.37,
            "resources": "WTI Crude Oil,Natural Gas,Gasoline,Heating Oil",
            "importance": 9,
        },
        {
            "hub": "North Sea",
            "lat": 57.0,
            "lon": 2.5,
            "resources": "Brent Crude Oil,Natural Gas",
            "importance": 8,
        },
        {
            "hub": "Chile Copper Belt",
            "lat": -22.5,
            "lon": -68.9,
            "resources": "Copper,Gold,Silver",
            "importance": 9,
        },
        {
            "hub": "South Africa Gold Belt",
            "lat": -26.2,
            "lon": 28.0,
            "resources": "Gold",
            "importance": 7,
        },
        {
            "hub": "Qatar LNG Corridor",
            "lat": 25.35,
            "lon": 51.18,
            "resources": "Natural Gas",
            "importance": 9,
        },
        {
            "hub": "Singapore Refining Hub",
            "lat": 1.29,
            "lon": 103.85,
            "resources": "WTI Crude Oil,Brent Crude Oil,Gasoline,Heating Oil",
            "importance": 8,
        },
    ]
)

EVENT_BASE_IMPACT = {
    "war": 1.0,
    "earthquake": 0.65,
    "hurricane": 0.70,
    "port_closure": 0.75,
    "pipeline_failure": 0.85,
    "cyberattack": 0.55,
    "labor_strike": 0.45,
    "sanctions": 0.90,
    "mine_accident": 0.60,
    "drought": 0.40,
    "shipping_chokepoint": 0.95,
    "pandemic": 0.60,
}

RESOURCE_SENSITIVITY = {
    "WTI Crude Oil": 1.00,
    "Brent Crude Oil": 1.05,
    "Natural Gas": 0.90,
    "Gold": 0.55,
    "Silver": 0.45,
    "Copper": 0.70,
    "Gasoline": 0.85,
    "Heating Oil": 0.85,
}

CLUSTER_FEATURES = [
    "severity",
    "duration_days",
    "distance_to_hub_km",
    "hub_importance",
    "vol_30d",
    "event_impact_score",
]

ACTIONS = [
    "Monitor and update dashboard",
    "Reroute flows around affected hub",
    "Increase inventory buffers",
    "Diversify supplier/transport options",
    "Emergency allocation and demand response",
]

st.set_page_config(page_title=APP_TITLE, page_icon="🌍", layout="wide")


def inject_theme() -> None:
    css_path = Path(__file__).parent / "assets" / "lovable_theme.css"
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)


inject_theme()


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
    if not parsed:
        return ""
    return parsed.strftime("%d %b %Y")


def event_duration_days(start_date: str | None, end_date: str | None, fallback: int = 14) -> int:
    start = parse_iso_date(start_date)
    end = parse_iso_date(end_date) or start
    if not start or not end:
        return fallback
    return max((end - start).days + 1, 1)


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


def clamp_float(value: float, low: float, high: float) -> float:
    return float(min(max(value, low), high))


def haversine_km(lat1: float, lon1: float, lat2: Any, lon2: Any) -> Any:
    radius = 6371.0
    p1 = np.radians(lat1)
    p2 = np.radians(lat2)
    dphi = np.radians(np.asarray(lat2) - lat1)
    dlambda = np.radians(np.asarray(lon2) - lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dlambda / 2) ** 2
    return 2 * radius * np.arcsin(np.sqrt(a))


def nearest_hub_features(lat: float, lon: float, resource: str) -> tuple[str, float, float]:
    subset = SUPPLY_HUBS[SUPPLY_HUBS["resources"].str.contains(resource, regex=False)]
    if subset.empty:
        subset = SUPPLY_HUBS
    distances = haversine_km(lat, lon, subset["lat"].values, subset["lon"].values)
    index = int(np.argmin(distances))
    row = subset.iloc[index]
    return str(row["hub"]), float(distances[index]), float(row["importance"])


def default_event() -> dict[str, Any]:
    today = date.today()
    return {
        "id": uuid.uuid4().hex,
        "name": "Strait of Hormuz disruption",
        "type": "shipping_chokepoint",
        "severity": 7.5,
        "startDate": today.isoformat(),
        "endDate": (today + timedelta(days=14)).isoformat(),
        "notes": "Starter scenario: a disruption near a critical energy shipping lane.",
        "lat": 26.6,
        "lon": 56.3,
        "created_at": datetime.utcnow().isoformat(),
    }


def init_state() -> None:
    if "workspaces" not in st.session_state:
        st.session_state.workspaces = [
            {
                "id": "workspace-1",
                "name": "Workspace 1",
                "events": [default_event()],
            }
        ]
    if "active_workspace_id" not in st.session_state:
        st.session_state.active_workspace_id = st.session_state.workspaces[0]["id"]
    if "sim_date" not in st.session_state:
        st.session_state.sim_date = date.today()
    if "sim_speed" not in st.session_state:
        st.session_state.sim_speed = 1.0
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


def add_event(event: dict[str, Any]) -> None:
    current_events().append(event)


def delete_event(event_id: str) -> None:
    workspace = active_workspace()
    workspace["events"] = [event for event in workspace.get("events", []) if event["id"] != event_id]


def make_training_data(n: int = 2800) -> pd.DataFrame:
    rng = np.random.default_rng(RANDOM_SEED)
    rows: list[dict[str, Any]] = []
    resources = list(RESOURCE_TICKERS)
    for _ in range(n):
        resource = str(rng.choice(resources))
        event_type = str(rng.choice(EVENT_TYPES))
        severity = float(rng.uniform(1, 10))
        duration = int(rng.integers(2, 120))
        hub = SUPPLY_HUBS.sample(1, random_state=int(rng.integers(0, 1_000_000))).iloc[0]
        lat = float(np.clip(rng.normal(float(hub["lat"]), 8), -80, 80))
        lon = float(((rng.normal(float(hub["lon"]), 12) + 180) % 360) - 180)
        nearest, distance, importance = nearest_hub_features(lat, lon, resource)
        dist_factor = float(np.exp(-distance / 1500))
        vol_30d = float(rng.uniform(0.10, 0.70))
        event_impact_score = EVENT_BASE_IMPACT[event_type] * RESOURCE_SENSITIVITY[resource]
        base_effect = (
            event_impact_score
            * severity
            * dist_factor
            * (0.55 + importance / 10)
            * (np.log1p(duration) / np.log1p(120))
        )
        price_delta = 0.82 * base_effect * (0.60 + vol_30d) + rng.normal(0, 2.5)
        risk = np.clip(8.5 * base_effect / 10 + 0.045 * duration + rng.normal(0, 0.55), 0, 10)
        rows.append(
            {
                "resource": resource,
                "event_type": event_type,
                "severity": severity,
                "duration_days": duration,
                "lat": lat,
                "lon": lon,
                "nearest_hub": nearest,
                "distance_to_hub_km": distance,
                "hub_importance": importance,
                "return_7d": float(rng.normal(0, 0.03)),
                "return_30d": float(rng.normal(0, 0.08)),
                "return_90d": float(rng.normal(0, 0.15)),
                "vol_30d": vol_30d,
                "vol_90d": float(rng.uniform(0.10, 0.70)),
                "price_zscore_180d": float(rng.normal(0, 1)),
                "event_impact_score": event_impact_score,
                "price_delta_30d_pct": float(np.clip(price_delta, -18, 38)),
                "supply_risk_index": float(risk),
            }
        )
    return pd.DataFrame(rows)


@st.cache_resource(show_spinner=False)
def train_ai_stack() -> dict[str, Any]:
    data = make_training_data()
    cat_features = ["resource", "event_type", "nearest_hub"]
    numeric_features = [
        "severity",
        "duration_days",
        "lat",
        "lon",
        "distance_to_hub_km",
        "hub_importance",
        "return_7d",
        "return_30d",
        "return_90d",
        "vol_30d",
        "vol_90d",
        "price_zscore_180d",
    ]
    def make_preprocessor() -> ColumnTransformer:
        return ColumnTransformer(
            [
                ("cat", OneHotEncoder(handle_unknown="ignore"), cat_features),
                (
                    "num",
                    Pipeline(
                        [
                            ("imputer", SimpleImputer(strategy="median")),
                            ("scaler", StandardScaler()),
                        ]
                    ),
                    numeric_features,
                ),
            ]
        )

    rf_model = Pipeline(
        [
            ("preprocessor", make_preprocessor()),
            (
                "rf",
                RandomForestRegressor(
                    n_estimators=160,
                    min_samples_leaf=4,
                    random_state=RANDOM_SEED,
                    n_jobs=-1,
                ),
            ),
        ]
    )
    X = data[cat_features + numeric_features]
    y = data[["price_delta_30d_pct", "supply_risk_index"]]
    rf_model.fit(X, y)

    class_labels = pd.cut(
        data["supply_risk_index"],
        bins=[-0.1, 3.0, 6.5, 8.4, 10.1],
        labels=["Low", "Medium", "High", "Critical"],
    ).astype(str)
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        class_labels,
        test_size=0.25,
        random_state=RANDOM_SEED,
        stratify=class_labels,
    )
    nn_model = Pipeline(
        [
            ("preprocessor", make_preprocessor()),
            (
                "mlp",
                MLPClassifier(
                    hidden_layer_sizes=(48, 24),
                    activation="relu",
                    alpha=0.001,
                    max_iter=350,
                    random_state=RANDOM_SEED,
                    early_stopping=True,
                ),
            ),
        ]
    )
    nn_model.fit(X_train, y_train)
    nn_accuracy = float(nn_model.score(X_test, y_test))

    cluster_scaler = StandardScaler()
    cluster_matrix = cluster_scaler.fit_transform(data[CLUSTER_FEATURES])
    kmeans = KMeans(n_clusters=4, n_init=10, random_state=RANDOM_SEED)
    cluster_ids = kmeans.fit_predict(cluster_matrix)
    cluster_summary = (
        data.assign(cluster=cluster_ids)
        .groupby("cluster")
        .agg(
            mean_risk=("supply_risk_index", "mean"),
            mean_severity=("severity", "mean"),
            mean_duration=("duration_days", "mean"),
            mean_distance=("distance_to_hub_km", "mean"),
        )
        .reset_index()
    )
    cluster_labels: dict[int, str] = {}
    for _, row in cluster_summary.iterrows():
        risk_word = "Low" if row.mean_risk < 3 else "Medium" if row.mean_risk < 6.5 else "High"
        distance_word = "near-hub" if row.mean_distance < 800 else "regional" if row.mean_distance < 2200 else "distant"
        duration_word = "short" if row.mean_duration < 25 else "medium" if row.mean_duration < 70 else "long"
        cluster_labels[int(row.cluster)] = f"{risk_word} risk / {distance_word} / {duration_word} duration"

    q_table = train_q_policy()

    return {
        "data": data,
        "rf_model": rf_model,
        "nn_model": nn_model,
        "nn_accuracy": nn_accuracy,
        "cat_features": cat_features,
        "numeric_features": numeric_features,
        "cluster_scaler": cluster_scaler,
        "kmeans": kmeans,
        "cluster_labels": cluster_labels,
        "q_table": q_table,
    }


def risk_bucket(risk: float) -> str:
    if risk >= 8.4:
        return "critical"
    if risk >= 6.5:
        return "high"
    if risk >= 3.0:
        return "medium"
    return "low"


def duration_bucket(days: int) -> str:
    if days >= 45:
        return "long"
    if days >= 14:
        return "medium"
    return "short"


def criticality_bucket(resource: str) -> str:
    return "critical" if resource in ENERGY_RESOURCES else "routine"


def state_tuple_from_values(risk: float, days: int, resource: str) -> tuple[str, str, str]:
    return risk_bucket(risk), duration_bucket(days), criticality_bucket(resource)


def reward_for_action(state: tuple[str, str, str], action_index: int) -> float:
    risk_state, duration_state, criticality_state = state
    base = -0.1
    if risk_state == "low":
        target = 0
    elif risk_state == "medium" and duration_state == "short":
        target = 2
    elif risk_state in {"medium", "high"} and criticality_state == "routine":
        target = 3
    elif risk_state == "high" and criticality_state == "critical":
        target = 1
    else:
        target = 4
    distance = abs(action_index - target)
    reward = 3.0 - 0.8 * distance + base
    if risk_state == "critical" and action_index == 0:
        reward -= 2.5
    if risk_state == "low" and action_index == 4:
        reward -= 2.0
    if duration_state == "long" and action_index in {2, 3}:
        reward += 0.6
    return reward


def train_q_policy(episodes: int = 2600) -> dict[tuple[str, str, str], np.ndarray]:
    rng = np.random.default_rng(RANDOM_SEED)
    risk_states = ["low", "medium", "high", "critical"]
    duration_states = ["short", "medium", "long"]
    criticality_states = ["routine", "critical"]
    q_table = {
        (risk, duration, criticality): np.zeros(len(ACTIONS), dtype=float)
        for risk in risk_states
        for duration in duration_states
        for criticality in criticality_states
    }
    alpha = 0.25
    gamma = 0.15
    epsilon = 0.18
    states = list(q_table)
    for _ in range(episodes):
        state = states[int(rng.integers(0, len(states)))]
        if rng.random() < epsilon:
            action = int(rng.integers(0, len(ACTIONS)))
        else:
            action = int(np.argmax(q_table[state]))
        reward = reward_for_action(state, action)
        next_state = states[int(rng.integers(0, len(states)))]
        old = q_table[state][action]
        q_table[state][action] = old + alpha * (reward + gamma * np.max(q_table[next_state]) - old)
    return q_table


def event_to_feature_rows(events: list[dict[str, Any]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for event in events:
        duration = event_duration_days(event.get("startDate"), event.get("endDate"))
        lat = clamp_float(float(event.get("lat", 0)), -80, 80)
        lon = clamp_float(float(event.get("lon", 0)), -180, 180)
        event_type = str(event.get("type") or "earthquake")
        severity = clamp_float(float(event.get("severity", 5)), 0, 10)
        for resource in RESOURCE_TICKERS:
            nearest, dist, importance = nearest_hub_features(lat, lon, resource)
            rows.append(
                {
                    "event_id": event.get("id"),
                    "event_name": event.get("name", "Unnamed event"),
                    "resource": resource,
                    "event_type": event_type,
                    "severity": severity,
                    "duration_days": duration,
                    "lat": lat,
                    "lon": lon,
                    "nearest_hub": nearest,
                    "distance_to_hub_km": dist,
                    "hub_importance": importance,
                    "return_7d": 0.0,
                    "return_30d": 0.0,
                    "return_90d": 0.0,
                    "vol_30d": 0.30,
                    "vol_90d": 0.35,
                    "price_zscore_180d": 0.0,
                    "event_impact_score": EVENT_BASE_IMPACT.get(event_type, 0.5)
                    * RESOURCE_SENSITIVITY.get(resource, 0.6),
                }
            )
    return pd.DataFrame(rows)


def classify_risk_level(value: float) -> str:
    if value >= 8.4:
        return "Critical"
    if value >= 6.5:
        return "High"
    if value >= 3.0:
        return "Medium"
    return "Low"


def predict_scenario(events: list[dict[str, Any]], ai: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    if not events:
        return pd.DataFrame(), pd.DataFrame()
    X = event_to_feature_rows(events)
    feature_cols = ai["cat_features"] + ai["numeric_features"]
    predictions = ai["rf_model"].predict(X[feature_cols])
    event_level = X[
        [
            "event_id",
            "event_name",
            "resource",
            "event_type",
            "nearest_hub",
            "distance_to_hub_km",
            "severity",
            "duration_days",
        ]
    ].copy()
    event_level["predicted_30d_price_change_pct"] = predictions[:, 0]
    event_level["supply_risk_index"] = np.clip(predictions[:, 1], 0, 10)
    cluster_matrix = ai["cluster_scaler"].transform(X[CLUSTER_FEATURES])
    clusters = ai["kmeans"].predict(cluster_matrix)
    event_level["crisis_cluster"] = [ai["cluster_labels"].get(int(c), f"Cluster {c}") for c in clusters]
    event_level["nn_risk_class"] = ai["nn_model"].predict(X[feature_cols])

    agg_rows: list[dict[str, Any]] = []
    for resource, group in event_level.groupby("resource"):
        combined_risk = 10 * (1 - np.prod(1 - np.clip(group["supply_risk_index"].values, 0, 10) / 10))
        combined_delta = float(np.clip(group["predicted_30d_price_change_pct"].sum(), -25, 60))
        top = group.sort_values("supply_risk_index", ascending=False).iloc[0]
        duration = int(group["duration_days"].max())
        state = state_tuple_from_values(float(combined_risk), duration, resource)
        q_values = ai["q_table"][state]
        action = ACTIONS[int(np.argmax(q_values))]
        agg_rows.append(
            {
                "resource": resource,
                "predicted_30d_price_change_pct": combined_delta,
                "supply_risk_index": float(np.clip(combined_risk, 0, 10)),
                "risk_level": classify_risk_level(float(combined_risk)),
                "top_event_driver": top["event_name"],
                "nearest_hub_driver": top["nearest_hub"],
                "rl_recommended_response": action,
            }
        )
    summary = pd.DataFrame(agg_rows).sort_values("supply_risk_index", ascending=False)
    return summary, event_level.sort_values("supply_risk_index", ascending=False)


def svg_flag(color: str, width: int = 24, height: int = 29) -> str:
    # Inline SVG flag inspired by the Lovable React marker design.
    return f"""
    <svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' viewBox='0 0 20 24'>
      <path d='M4 23V2' stroke='#111' stroke-width='1.8' stroke-linecap='round'/>
      <path d='M4.9 2.6h10.4l-2.6 3.9 2.6 3.9H4.9z' fill='{html.escape(color)}' stroke='#111' stroke-width='1' stroke-linejoin='round'/>
    </svg>
    """


def flag_div_icon(event: dict[str, Any], status: str) -> folium.DivIcon:
    color = TYPE_COLOR.get(str(event.get("type")), "#64748b")
    size = 28 if status == "active" else 24
    halo = STATUS_COLOR.get(status, "#1f4e79")
    svg = svg_flag(color, size, int(size * 1.2))
    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    img = (
        f"<img src='data:image/svg+xml;base64,{encoded}' width='{size}' "
        f"style='filter: drop-shadow(0 0 4px {halo}) drop-shadow(0 1px 2px rgba(0,0,0,.35));'/>"
    )
    return folium.DivIcon(html=img, icon_size=(size, int(size * 1.2)), icon_anchor=(5, int(size * 1.2) - 1))


def build_map(events: list[dict[str, Any]], sim_date: date) -> folium.Map:
    if events:
        center_lat = float(np.mean([float(e.get("lat", 20)) for e in events]))
        center_lon = float(np.mean([float(e.get("lon", 0)) for e in events]))
        zoom = 3 if len(events) == 1 else 2
    else:
        center_lat, center_lon, zoom = 20.0, 0.0, 2

    world_map = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=zoom,
        tiles="CartoDB positron",
        control_scale=True,
        prefer_canvas=True,
    )
    folium.TileLayer("OpenStreetMap", name="OpenStreetMap").add_to(world_map)

    hubs_layer = FeatureGroup(name="Supply hubs", show=True)
    for _, hub in SUPPLY_HUBS.iterrows():
        popup = folium.Popup(
            f"<b>{html.escape(str(hub['hub']))}</b><br/>Resources: {html.escape(str(hub['resources']))}<br/>Importance: {hub['importance']}/10",
            max_width=320,
        )
        folium.CircleMarker(
            [float(hub["lat"]), float(hub["lon"])],
            radius=4 + float(hub["importance"]) / 2,
            color="#1f4e79",
            fill=True,
            fill_opacity=0.75,
            popup=popup,
            tooltip=str(hub["hub"]),
        ).add_to(hubs_layer)
    hubs_layer.add_to(world_map)

    events_layer = FeatureGroup(name="User shock events", show=True)
    for event in events:
        status = get_event_status(sim_date, event.get("startDate"), event.get("endDate"))
        event_type = str(event.get("type", ""))
        tooltip = f"{html.escape(str(event.get('name', 'Event')))} - {STATUS_LABEL[status]}"
        details = [
            f"<b>{html.escape(str(event.get('name', 'Event')))}</b>",
            f"Status: {STATUS_LABEL[status]}",
            f"Type: {format_type(event_type)}",
            f"Severity: {float(event.get('severity', 0)):.1f}/10",
            f"Dates: {format_iso_date(event.get('startDate')) or 'No start'}"
            + (f" → {format_iso_date(event.get('endDate'))}" if event.get("endDate") else ""),
        ]
        if event.get("notes"):
            details.append(html.escape(str(event["notes"])))
        popup = folium.Popup("<br/>".join(details), max_width=360)
        lat = float(event.get("lat", 0))
        lon = float(event.get("lon", 0))
        folium.Marker([lat, lon], icon=flag_div_icon(event, status), popup=popup, tooltip=tooltip).add_to(events_layer)
        folium.Circle(
            [lat, lon],
            radius=75000 + float(event.get("severity", 0)) * 135000,
            color=TYPE_COLOR.get(event_type, "#64748b"),
            fill=True,
            fill_opacity=0.08 if status != "active" else 0.15,
            weight=2,
        ).add_to(events_layer)
    events_layer.add_to(world_map)

    legend = """
    <div style="position: fixed; bottom: 30px; left: 30px; z-index: 9999; background: rgba(255,255,255,0.92); padding: 12px 14px; border-radius: 14px; border: 1px solid #d9d5c4; box-shadow: 0 8px 24px rgba(0,0,0,.12); font-size: 13px; color:#21304a;">
      <b>Map legend</b><br/>
      <span style="color:#1f4e79;">●</span> supply hub<br/>
      🚩 user shock event<br/>
      Circle size ≈ event severity
    </div>
    """
    world_map.get_root().html.add_child(folium.Element(legend))
    folium.LayerControl(collapsed=True).add_to(world_map)
    return world_map


def render_header(events: list[dict[str, Any]], sim_date: date) -> None:
    active_count = sum(1 for event in events if get_event_status(sim_date, event.get("startDate"), event.get("endDate")) == "active")
    st.markdown(
        f"""
        <div class="lovable-hero">
          <div>
            <h1>{APP_TITLE}</h1>
            <p>Click the global map, add a crisis event, and forecast energy and commodity supply-chain impacts.</p>
          </div>
          <div class="lovable-pill-row">
            <span class="lovable-pill primary">{len(events)} events</span>
            <span class="lovable-pill">{active_count} active</span>
            <span class="lovable-pill">{active_workspace()['name']}</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_timebar() -> None:
    st.markdown("<div class='lovable-card'>", unsafe_allow_html=True)
    cols = st.columns([1, 1, 1, 2, 1])
    with cols[0]:
        if st.button("−1 day", use_container_width=True):
            st.session_state.sim_date = st.session_state.sim_date - timedelta(days=1)
            st.rerun()
    with cols[1]:
        if st.button("+1 day", use_container_width=True):
            st.session_state.sim_date = st.session_state.sim_date + timedelta(days=1)
            st.rerun()
    with cols[2]:
        if st.button("Today", use_container_width=True):
            st.session_state.sim_date = date.today()
            st.rerun()
    with cols[3]:
        selected_date = st.date_input("Simulation date", value=st.session_state.sim_date)
        if selected_date != st.session_state.sim_date:
            st.session_state.sim_date = selected_date
            st.rerun()
    with cols[4]:
        st.session_state.sim_speed = st.slider("Speed", 0.5, 72.0, float(st.session_state.sim_speed), 0.5)
    st.caption("Lovable-style time controls: event status changes as the simulation date moves.")
    st.markdown("</div>", unsafe_allow_html=True)


def render_workspace_bar() -> None:
    st.markdown("<div class='lovable-card'>", unsafe_allow_html=True)
    left, mid, right = st.columns([2, 1.4, 1.2])
    with left:
        options = {workspace["name"]: workspace["id"] for workspace in workspaces()}
        current_name = active_workspace()["name"]
        selected_name = st.selectbox("Workspace", list(options.keys()), index=list(options.keys()).index(current_name))
        st.session_state.active_workspace_id = options[selected_name]
    with mid:
        new_name = st.text_input("Rename active workspace", value=active_workspace()["name"])
        if new_name.strip() and new_name.strip() != active_workspace()["name"]:
            active_workspace()["name"] = new_name.strip()
            st.rerun()
    with right:
        st.write("")
        st.write("")
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("New", use_container_width=True, disabled=len(workspaces()) >= MAX_WORKSPACES):
                next_number = len(workspaces()) + 1
                workspace_id = f"workspace-{uuid.uuid4().hex[:8]}"
                workspaces().append({"id": workspace_id, "name": f"Workspace {next_number}", "events": []})
                st.session_state.active_workspace_id = workspace_id
                st.rerun()
        with col_b:
            if st.button("Delete", use_container_width=True, disabled=len(workspaces()) <= 1):
                active_id = active_workspace()["id"]
                st.session_state.workspaces = [workspace for workspace in workspaces() if workspace["id"] != active_id]
                st.session_state.active_workspace_id = st.session_state.workspaces[0]["id"]
                st.rerun()
    if len(workspaces()) >= MAX_WORKSPACES:
        st.caption("Maximum of 3 workspaces, matching the Lovable UI constraint.")
    st.markdown("</div>", unsafe_allow_html=True)


def render_sidebar(events: list[dict[str, Any]]) -> None:
    with st.sidebar:
        st.header("Add supply shock")
        st.caption("Click the map to prefill latitude/longitude, then save the event here.")
        with st.form("add_event_form", clear_on_submit=False):
            name = st.text_input("Event name", key="event_name")
            event_type = st.selectbox(
                "Event type",
                EVENT_TYPES,
                index=EVENT_TYPES.index(st.session_state.event_type)
                if st.session_state.event_type in EVENT_TYPES
                else 0,
                format_func=format_type,
                key="event_type",
            )
            severity = st.slider("Severity", 0.0, 10.0, 7.0, 0.1)
            use_dates = st.checkbox("Use event date range", value=True)
            start_value = date.today()
            end_value = date.today() + timedelta(days=14)
            if use_dates:
                start_value = st.date_input("Start date", value=start_value)
                end_value = st.date_input("End date", value=end_value, min_value=start_value)
            lat = st.number_input("Latitude", min_value=-90.0, max_value=90.0, step=0.1, key="event_lat")
            lon = st.number_input("Longitude", min_value=-180.0, max_value=180.0, step=0.1, key="event_lon")
            notes = st.text_area("Description", placeholder="What is happening here?")
            submitted = st.form_submit_button("Add event", use_container_width=True)
        if submitted:
            trimmed = name.strip() or "Unnamed event"
            duplicate = any(event["name"].lower() == trimmed.lower() for event in events)
            if duplicate:
                st.error("An event with that name already exists in this workspace.")
            else:
                add_event(
                    {
                        "id": uuid.uuid4().hex,
                        "name": trimmed,
                        "type": event_type,
                        "severity": float(severity),
                        "startDate": start_value.isoformat() if use_dates else "",
                        "endDate": end_value.isoformat() if use_dates else "",
                        "notes": notes.strip(),
                        "lat": float(lat),
                        "lon": float(lon),
                        "created_at": datetime.utcnow().isoformat(),
                    }
                )
                st.success("Event added.")
                st.rerun()

        st.divider()
        st.subheader("Scenario import/export")
        upload = st.file_uploader("Import workspace JSON", type=["json"])
        if upload is not None:
            try:
                imported = json.loads(upload.getvalue().decode("utf-8"))
                if isinstance(imported, dict) and "events" in imported:
                    active_workspace()["events"] = imported.get("events", [])
                    st.success("Workspace imported.")
                    st.rerun()
                else:
                    st.error("JSON must contain an 'events' list.")
            except Exception as exc:  # noqa: BLE001
                st.error(f"Could not import JSON: {exc}")
        export_payload = json.dumps(
            {"workspace": active_workspace()["name"], "events": current_events()},
            indent=2,
        )
        st.download_button(
            "Download workspace JSON",
            data=export_payload,
            file_name="energy_shock_workspace.json",
            mime="application/json",
            use_container_width=True,
        )

        st.divider()
        st.subheader("Model note")
        st.caption(
            "This student prototype trains on synthetic labels shaped by supply-chain distance, severity, duration, and resource sensitivity. Replace synthetic labels with validated historical data before real operational use."
        )


def render_event_cards(events: list[dict[str, Any]], sim_date: date) -> None:
    if not events:
        st.info("No events yet. Click the map and add your first supply-chain shock.")
        return
    sort_by = st.selectbox("Sort events by", ["Time created", "Start date", "Severity", "Type"])
    sorted_events = list(events)
    if sort_by == "Start date":
        sorted_events.sort(key=lambda event: event.get("startDate") or "9999-12-31")
    elif sort_by == "Severity":
        sorted_events.sort(key=lambda event: float(event.get("severity", 0)), reverse=True)
    elif sort_by == "Type":
        sorted_events.sort(key=lambda event: str(event.get("type", "")))

    for event in sorted_events:
        status = get_event_status(sim_date, event.get("startDate"), event.get("endDate"))
        type_color = TYPE_COLOR.get(str(event.get("type")), "#64748b")
        dates = format_iso_date(event.get("startDate"))
        if event.get("endDate"):
            dates += f" → {format_iso_date(event.get('endDate'))}"
        elif dates:
            dates += " (ongoing)"
        notes = html.escape(str(event.get("notes", "")))
        st.markdown(
            f"""
            <div class="event-card {status}">
              <div class="lovable-pill-row">
                <h4>{html.escape(str(event.get('name', 'Event')))}</h4>
                <span class="lovable-pill" style="background:{type_color};color:white;border-color:transparent;">{format_type(str(event.get('type', '')))}</span>
                <span class="lovable-pill">{STATUS_LABEL[status]}</span>
                <span class="lovable-pill">Severity {float(event.get('severity', 0)):.1f}/10</span>
              </div>
              <p>Lat: {float(event.get('lat', 0)):.1f}° · Lng: {float(event.get('lon', 0)):.1f}° {('· ' + dates) if dates else ''}</p>
              {f'<p>{notes}</p>' if notes else ''}
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button(f"Remove {event.get('name')}", key=f"remove_{event['id']}"):
            delete_event(event["id"])
            st.rerun()


def render_metrics(summary: pd.DataFrame, events: list[dict[str, Any]], sim_date: date) -> None:
    active = sum(1 for event in events if get_event_status(sim_date, event.get("startDate"), event.get("endDate")) == "active")
    if summary.empty:
        top_resource = "—"
        top_risk = "0.0"
        avg_delta = "0.0%"
    else:
        top = summary.sort_values("supply_risk_index", ascending=False).iloc[0]
        top_resource = str(top["resource"])
        top_risk = f"{top['supply_risk_index']:.1f}/10"
        avg_delta = f"{summary['predicted_30d_price_change_pct'].mean():+.1f}%"
    cols = st.columns(4)
    metric_data = [
        ("Workspace events", str(len(events))),
        ("Active now", str(active)),
        ("Highest-risk resource", top_resource),
        ("Top risk / avg price Δ", f"{top_risk} / {avg_delta}"),
    ]
    for col, (label, value) in zip(cols, metric_data):
        with col:
            st.markdown(
                f"<div class='metric-card'><div class='label'>{label}</div><div class='value'>{value}</div></div>",
                unsafe_allow_html=True,
            )


def render_forecast_tab(summary: pd.DataFrame, event_level: pd.DataFrame) -> None:
    if summary.empty:
        st.info("Add at least one event to generate a forecast.")
        return
    st.subheader("Forecast summary by resource")
    display = summary.copy()
    display["predicted_30d_price_change_pct"] = display["predicted_30d_price_change_pct"].map(lambda value: round(value, 2))
    display["supply_risk_index"] = display["supply_risk_index"].map(lambda value: round(value, 2))
    st.dataframe(display, use_container_width=True, hide_index=True)

    chart_df = summary.set_index("resource")[["predicted_30d_price_change_pct", "supply_risk_index"]]
    st.bar_chart(chart_df, use_container_width=True)

    st.subheader("Event-resource detail")
    detail = event_level.copy()
    for column in ["distance_to_hub_km", "predicted_30d_price_change_pct", "supply_risk_index"]:
        detail[column] = detail[column].map(lambda value: round(float(value), 2))
    st.dataframe(detail, use_container_width=True, hide_index=True)


def render_event_ai_tab(ai: dict[str, Any], event_level: pd.DataFrame) -> None:
    st.subheader("Deep-learning style classification and crisis clustering")
    st.markdown(
        "The app uses a student-friendly neural-network classifier (`sklearn.neural_network.MLPClassifier`) and K-means clustering. "
        "The labels are synthetic for classroom prototyping, but the pipeline is ready to retrain on real historical event labels."
    )
    st.metric("Neural-network validation accuracy on synthetic labels", f"{ai['nn_accuracy']:.1%}")
    if event_level.empty:
        st.info("Add events to see their neural-network class and crisis cluster.")
        return
    cluster_view = (
        event_level[
            [
                "event_name",
                "event_type",
                "resource",
                "severity",
                "duration_days",
                "crisis_cluster",
                "nn_risk_class",
                "supply_risk_index",
            ]
        ]
        .sort_values("supply_risk_index", ascending=False)
        .copy()
    )
    cluster_view["supply_risk_index"] = cluster_view["supply_risk_index"].map(lambda value: round(float(value), 2))
    st.dataframe(cluster_view, use_container_width=True, hide_index=True)

    st.subheader("Cluster labels learned from training data")
    labels = pd.DataFrame(
        [{"cluster": cluster, "label": label} for cluster, label in ai["cluster_labels"].items()]
    ).sort_values("cluster")
    st.dataframe(labels, use_container_width=True, hide_index=True)


def render_rl_tab(summary: pd.DataFrame) -> None:
    st.subheader("Reinforcement-learning response recommendations")
    st.markdown(
        "A small Q-learning policy recommends actions from the state tuple: risk level, likely duration, and resource criticality. "
        "It is intentionally simple so students can inspect and modify the reward function."
    )
    if summary.empty:
        st.info("Add events to get RL recommendations.")
        return
    rl_view = summary[["resource", "risk_level", "supply_risk_index", "top_event_driver", "rl_recommended_response"]].copy()
    rl_view["supply_risk_index"] = rl_view["supply_risk_index"].map(lambda value: round(float(value), 2))
    st.dataframe(rl_view, use_container_width=True, hide_index=True)

    top_action = rl_view.iloc[0]["rl_recommended_response"]
    st.success(f"Top recommended response for the highest-risk resource: {top_action}")


def render_data_sources_tab() -> None:
    st.subheader("Public-data integration path")
    st.markdown(
        "This repo is configured to run without paid accounts. For a classroom project, the next step is to replace synthetic labels with historical data."
    )
    st.markdown(
        """
        **Recommended free/student-friendly feeds**

        - World Bank Pink Sheet commodity prices for historical monthly commodity prices.
        - EIA Open Data API v2 for energy production, inventories, and price series; a free API key may be required.
        - GDELT event/news data for global conflict, disaster, and disruption signals.
        - User-uploaded CSV/JSON scenario data for local classroom experiments.

        **Suggested historical-label table**

        | column | meaning |
        | --- | --- |
        | `event_type` | war, earthquake, port_closure, etc. |
        | `resource` | oil, gas, gold, copper, etc. |
        | `lat`, `lon` | event location |
        | `severity` | student/analyst score from 0 to 10 |
        | `duration_days` | estimated disruption duration |
        | `price_delta_30d_pct` | observed price move after event |
        | `supply_risk_index` | validated target score from 0 to 10 |
        """
    )
    st.warning(
        "Educational simulation only. This is not investment advice, emergency guidance, or an operational forecast."
    )


def render_footer() -> None:
    st.markdown(
        """
        <hr/>
        <p class="small-note">
        Built as a GitHub/Streamlit-ready student prototype. The uploaded Lovable React UI is preserved in <code>lovable_ui_source/</code>, while <code>app.py</code> is the runnable Streamlit conversion.
        </p>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    ai = train_ai_stack()
    events = current_events()
    sim_date = st.session_state.sim_date

    render_header(events, sim_date)
    render_timebar()
    st.write("")
    render_workspace_bar()
    st.write("")

    world_map = build_map(events, sim_date)
    map_state = st_folium(
        world_map,
        height=620,
        use_container_width=True,
        key=f"shock_map_{active_workspace()['id']}_{len(events)}",
        returned_objects=["last_clicked"],
    )
    if map_state and map_state.get("last_clicked"):
        click = map_state["last_clicked"]
        lat = round(float(click["lat"]), 1)
        lon = round(float(click["lng"]), 1)
        signature = f"{lat},{lon}"
        if signature != st.session_state.last_map_click_signature:
            st.session_state.last_map_click_signature = signature
            st.session_state.event_lat = lat
            st.session_state.event_lon = lon
            st.toast(f"Map click captured: {lat}°, {lon}°. Add details in the sidebar.")
            st.rerun()

    render_sidebar(events)

    summary, event_level = predict_scenario(events, ai)
    render_metrics(summary, events, sim_date)

    tab_forecast, tab_events, tab_ai, tab_rl, tab_sources = st.tabs(
        ["Forecast", "Your events", "Event AI", "RL response", "Data sources"]
    )
    with tab_forecast:
        render_forecast_tab(summary, event_level)
    with tab_events:
        render_event_cards(events, sim_date)
    with tab_ai:
        render_event_ai_tab(ai, event_level)
    with tab_rl:
        render_rl_tab(summary)
    with tab_sources:
        render_data_sources_tab()

    render_footer()


if __name__ == "__main__":
    main()
