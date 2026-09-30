from __future__ import annotations

from datetime import date
from typing import Any

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

RANDOM_SEED = 42

EVENT_TYPES = [
    "war", "earthquake", "hurricane", "port_closure", "pipeline_failure", "cyberattack",
    "labor_strike", "sanctions", "mine_accident", "drought", "shipping_chokepoint", "pandemic",
]

RESOURCE_TICKERS = {
    "WTI Crude Oil": "CL=F", "Brent Crude Oil": "BZ=F", "Natural Gas": "NG=F", "Gold": "GC=F",
    "Silver": "SI=F", "Copper": "HG=F", "Gasoline": "RB=F", "Heating Oil": "HO=F",
}
ENERGY_RESOURCES = {"WTI Crude Oil", "Brent Crude Oil", "Natural Gas", "Gasoline", "Heating Oil"}

SUPPLY_HUBS = pd.DataFrame([
    {"hub":"Strait of Hormuz","lat":26.57,"lon":56.25,"resources":"WTI Crude Oil,Brent Crude Oil,Natural Gas,Gasoline,Heating Oil","importance":10},
    {"hub":"Suez Canal","lat":30.59,"lon":32.27,"resources":"WTI Crude Oil,Brent Crude Oil,Natural Gas,Gasoline,Heating Oil","importance":8},
    {"hub":"Panama Canal","lat":9.08,"lon":-79.68,"resources":"WTI Crude Oil,Brent Crude Oil,Natural Gas,Copper,Gold","importance":7},
    {"hub":"US Gulf Coast","lat":29.76,"lon":-95.37,"resources":"WTI Crude Oil,Natural Gas,Gasoline,Heating Oil","importance":9},
    {"hub":"North Sea","lat":57.0,"lon":2.5,"resources":"Brent Crude Oil,Natural Gas","importance":8},
    {"hub":"Chile Copper Belt","lat":-22.5,"lon":-68.9,"resources":"Copper,Gold,Silver","importance":9},
    {"hub":"South Africa Gold Belt","lat":-26.2,"lon":28.0,"resources":"Gold","importance":7},
    {"hub":"Qatar LNG Corridor","lat":25.35,"lon":51.18,"resources":"Natural Gas","importance":9},
    {"hub":"Singapore Refining Hub","lat":1.29,"lon":103.85,"resources":"WTI Crude Oil,Brent Crude Oil,Gasoline,Heating Oil","importance":8},
])

EVENT_BASE_IMPACT = {
    "war":1.0,"earthquake":0.65,"hurricane":0.70,"port_closure":0.75,"pipeline_failure":0.85,
    "cyberattack":0.55,"labor_strike":0.45,"sanctions":0.90,"mine_accident":0.60,"drought":0.40,
    "shipping_chokepoint":0.95,"pandemic":0.60,
}
RESOURCE_SENSITIVITY = {
    "WTI Crude Oil":1.00,"Brent Crude Oil":1.05,"Natural Gas":0.90,"Gold":0.55,"Silver":0.45,
    "Copper":0.70,"Gasoline":0.85,"Heating Oil":0.85,
}
CLUSTER_FEATURES = ["severity","duration_days","distance_to_hub_km","hub_importance","vol_30d","event_impact_score"]
ACTIONS = [
    "Monitor and update dashboard",
    "Reroute flows around affected hub",
    "Increase inventory buffers",
    "Diversify supplier/transport options",
    "Emergency allocation and demand response",
]


def parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def event_duration_days(start_date: str | None, end_date: str | None, fallback: int = 14) -> int:
    start = parse_iso_date(start_date)
    end = parse_iso_date(end_date) or start
    if not start or not end:
        return fallback
    return max((end - start).days + 1, 1)


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


def make_training_data(n: int = 2200) -> pd.DataFrame:
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
        base_effect = event_impact_score * severity * dist_factor * (0.55 + importance / 10) * (np.log1p(duration) / np.log1p(120))
        price_delta = 0.82 * base_effect * (0.60 + vol_30d) + rng.normal(0, 2.5)
        risk = np.clip(8.5 * base_effect / 10 + 0.045 * duration + rng.normal(0, 0.55), 0, 10)
        rows.append({
            "resource":resource,"event_type":event_type,"severity":severity,"duration_days":duration,
            "lat":lat,"lon":lon,"nearest_hub":nearest,"distance_to_hub_km":distance,"hub_importance":importance,
            "return_7d":float(rng.normal(0,0.03)),"return_30d":float(rng.normal(0,0.08)),"return_90d":float(rng.normal(0,0.15)),
            "vol_30d":vol_30d,"vol_90d":float(rng.uniform(0.10,0.70)),"price_zscore_180d":float(rng.normal(0,1)),
            "event_impact_score":event_impact_score,"price_delta_30d_pct":float(np.clip(price_delta,-18,38)),"supply_risk_index":float(risk),
        })
    return pd.DataFrame(rows)


def _make_preprocessor(cat_features: list[str], numeric_features: list[str]) -> ColumnTransformer:
    return ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore"), cat_features),
        ("num", Pipeline([("imputer", SimpleImputer(strategy="median")),("scaler", StandardScaler())]), numeric_features),
    ])


def risk_bucket(risk: float) -> str:
    return "critical" if risk >= 8.4 else "high" if risk >= 6.5 else "medium" if risk >= 3.0 else "low"


def duration_bucket(days: int) -> str:
    return "long" if days >= 45 else "medium" if days >= 14 else "short"


def criticality_bucket(resource: str) -> str:
    return "critical" if resource in ENERGY_RESOURCES else "routine"


def state_tuple_from_values(risk: float, days: int, resource: str) -> tuple[str, str, str]:
    return risk_bucket(risk), duration_bucket(days), criticality_bucket(resource)


def reward_for_action(state: tuple[str, str, str], action_index: int) -> float:
    risk_state, duration_state, criticality_state = state
    if risk_state == "low": target = 0
    elif risk_state == "medium" and duration_state == "short": target = 2
    elif risk_state in {"medium", "high"} and criticality_state == "routine": target = 3
    elif risk_state == "high" and criticality_state == "critical": target = 1
    else: target = 4
    reward = 2.9 - 0.8 * abs(action_index - target)
    if risk_state == "critical" and action_index == 0: reward -= 2.5
    if risk_state == "low" and action_index == 4: reward -= 2.0
    if duration_state == "long" and action_index in {2, 3}: reward += 0.6
    return reward


def train_q_policy(episodes: int = 2600) -> dict[tuple[str, str, str], np.ndarray]:
    rng = np.random.default_rng(RANDOM_SEED)
    states = [(r,d,c) for r in ["low","medium","high","critical"] for d in ["short","medium","long"] for c in ["routine","critical"]]
    q_table = {state: np.zeros(len(ACTIONS), dtype=float) for state in states}
    alpha, gamma, epsilon = 0.25, 0.15, 0.18
    for _ in range(episodes):
        state = states[int(rng.integers(0, len(states)))]
        action = int(rng.integers(0, len(ACTIONS))) if rng.random() < epsilon else int(np.argmax(q_table[state]))
        reward = reward_for_action(state, action)
        next_state = states[int(rng.integers(0, len(states)))]
        q_table[state][action] += alpha * (reward + gamma * np.max(q_table[next_state]) - q_table[state][action])
    return q_table


def train_ai_stack() -> dict[str, Any]:
    data = make_training_data()
    cat_features = ["resource", "event_type", "nearest_hub"]
    numeric_features = ["severity","duration_days","lat","lon","distance_to_hub_km","hub_importance","return_7d","return_30d","return_90d","vol_30d","vol_90d","price_zscore_180d"]
    rf_model = Pipeline([
        ("preprocessor", _make_preprocessor(cat_features, numeric_features)),
        ("rf", RandomForestRegressor(n_estimators=140, min_samples_leaf=4, random_state=RANDOM_SEED, n_jobs=-1)),
    ])
    X = data[cat_features + numeric_features]
    y = data[["price_delta_30d_pct", "supply_risk_index"]]
    rf_model.fit(X, y)

    labels = pd.cut(
        data["supply_risk_index"],
        bins=[-0.1, 3.0, 6.5, 8.4, 10.1],
        labels=[0, 1, 2, 3],
    ).astype(int)
    X_train, X_test, y_train, y_test = train_test_split(X, labels, test_size=0.25, random_state=RANDOM_SEED, stratify=labels)
    nn_model = Pipeline([
        ("preprocessor", _make_preprocessor(cat_features, numeric_features)),
        ("mlp", MLPClassifier(hidden_layer_sizes=(48,24), activation="relu", alpha=0.001, max_iter=300, random_state=RANDOM_SEED, early_stopping=True)),
    ])
    nn_model.fit(X_train, y_train)
    nn_accuracy = float(nn_model.score(X_test, y_test))

    cluster_scaler = StandardScaler()
    cluster_matrix = cluster_scaler.fit_transform(data[CLUSTER_FEATURES])
    kmeans = KMeans(n_clusters=4, n_init=10, random_state=RANDOM_SEED)
    cluster_ids = kmeans.fit_predict(cluster_matrix)
    summary = data.assign(cluster=cluster_ids).groupby("cluster").agg(
        mean_risk=("supply_risk_index","mean"), mean_duration=("duration_days","mean"), mean_distance=("distance_to_hub_km","mean")
    ).reset_index()
    cluster_labels: dict[int, str] = {}
    for _, row in summary.iterrows():
        risk_word = "Low" if row.mean_risk < 3 else "Medium" if row.mean_risk < 6.5 else "High"
        distance_word = "near-hub" if row.mean_distance < 800 else "regional" if row.mean_distance < 2200 else "distant"
        duration_word = "short" if row.mean_duration < 25 else "medium" if row.mean_duration < 70 else "long"
        cluster_labels[int(row.cluster)] = f"{risk_word} risk / {distance_word} / {duration_word} duration"

    return {
        "data":data,"rf_model":rf_model,"nn_model":nn_model,"nn_accuracy":nn_accuracy,
        "cat_features":cat_features,"numeric_features":numeric_features,"cluster_scaler":cluster_scaler,
        "kmeans":kmeans,"cluster_labels":cluster_labels,"q_table":train_q_policy(),
    }


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
            rows.append({
                "event_id":event.get("id"),"event_name":event.get("name","Unnamed event"),"resource":resource,
                "event_type":event_type,"severity":severity,"duration_days":duration,"lat":lat,"lon":lon,
                "nearest_hub":nearest,"distance_to_hub_km":dist,"hub_importance":importance,
                "return_7d":0.0,"return_30d":0.0,"return_90d":0.0,"vol_30d":0.30,"vol_90d":0.35,"price_zscore_180d":0.0,
                "event_impact_score":EVENT_BASE_IMPACT.get(event_type,0.5)*RESOURCE_SENSITIVITY.get(resource,0.6),
            })
    return pd.DataFrame(rows)


def classify_risk_level(value: float) -> str:
    return "Critical" if value >= 8.4 else "High" if value >= 6.5 else "Medium" if value >= 3.0 else "Low"


def predict_scenario(events: list[dict[str, Any]], ai: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    if not events:
        return pd.DataFrame(), pd.DataFrame()
    X = event_to_feature_rows(events)
    feature_cols = ai["cat_features"] + ai["numeric_features"]
    predictions = ai["rf_model"].predict(X[feature_cols])
    event_level = X[["event_id","event_name","resource","event_type","nearest_hub","distance_to_hub_km","severity","duration_days"]].copy()
    event_level["predicted_30d_price_change_pct"] = predictions[:, 0]
    event_level["supply_risk_index"] = np.clip(predictions[:, 1], 0, 10)
    clusters = ai["kmeans"].predict(ai["cluster_scaler"].transform(X[CLUSTER_FEATURES]))
    event_level["crisis_cluster"] = [ai["cluster_labels"].get(int(c), f"Cluster {c}") for c in clusters]
    nn_names = {0: "Low", 1: "Medium", 2: "High", 3: "Critical"}
    event_level["nn_risk_class"] = [nn_names.get(int(v), "Unknown") for v in ai["nn_model"].predict(X[feature_cols])]

    rows: list[dict[str, Any]] = []
    for resource, group in event_level.groupby("resource"):
        combined_risk = 10 * (1 - np.prod(1 - np.clip(group["supply_risk_index"].values, 0, 10) / 10))
        combined_delta = float(np.clip(group["predicted_30d_price_change_pct"].sum(), -25, 60))
        top = group.sort_values("supply_risk_index", ascending=False).iloc[0]
        duration = int(group["duration_days"].max())
        q_values = ai["q_table"][state_tuple_from_values(float(combined_risk), duration, resource)]
        rows.append({
            "resource":resource,"predicted_30d_price_change_pct":combined_delta,"supply_risk_index":float(np.clip(combined_risk,0,10)),
            "risk_level":classify_risk_level(float(combined_risk)),"top_event_driver":top["event_name"],"nearest_hub_driver":top["nearest_hub"],
            "rl_recommended_response":ACTIONS[int(np.argmax(q_values))],
        })
    return pd.DataFrame(rows).sort_values("supply_risk_index", ascending=False), event_level.sort_values("supply_risk_index", ascending=False)
