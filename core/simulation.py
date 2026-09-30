from __future__ import annotations

import math
from datetime import date, datetime, time, timedelta, timezone
from typing import Any

RESOURCE_INFO: dict[str, dict[str, Any]] = {
    "Oil": {"base": 75.0, "unit": "/ bbl", "sensitivity": 1.00},
    "Natural Gas": {"base": 3.0, "unit": "/ MMBtu", "sensitivity": 0.90},
    "Gasoline": {"base": 2.4, "unit": "/ gal", "sensitivity": 0.85},
    "Heating Oil": {"base": 2.6, "unit": "/ gal", "sensitivity": 0.85},
    "Copper": {"base": 4.0, "unit": "/ lb", "sensitivity": 0.70},
    "Gold": {"base": 1800.0, "unit": "/ oz", "sensitivity": 0.55},
    "Silver": {"base": 23.0, "unit": "/ oz", "sensitivity": 0.45},
}
RESOURCES = list(RESOURCE_INFO)
FLOW_MODES = ["All", "Supply", "Demand", "Trade", "Money", "Events"]
RESOURCE_ICON = {
    "Oil": "🛢",
    "Natural Gas": "🔥",
    "Gasoline": "⛽",
    "Heating Oil": "♨",
    "Copper": "🔶",
    "Gold": "🪙",
    "Silver": "⚪",
}

ENERGY = ["Oil", "Natural Gas", "Gasoline", "Heating Oil"]
METALS = ["Copper", "Gold", "Silver"]

HUBS = [
    {"id": "hormuz", "name": "Strait of Hormuz", "country": "ARE", "lat": 26.57, "lon": 56.25, "resources": ENERGY, "importance": 10, "kind": "Chokepoint"},
    {"id": "suez", "name": "Suez Canal", "country": "EGY", "lat": 30.59, "lon": 32.27, "resources": ENERGY, "importance": 8, "kind": "Chokepoint"},
    {"id": "panama", "name": "Panama Canal", "country": "PAN", "lat": 9.08, "lon": -79.68, "resources": ENERGY + ["Copper", "Gold"], "importance": 7, "kind": "Chokepoint"},
    {"id": "gulf", "name": "US Gulf Coast", "country": "USA", "lat": 29.76, "lon": -95.37, "resources": ENERGY, "importance": 9, "kind": "Energy hub"},
    {"id": "north-sea", "name": "North Sea", "country": "NOR", "lat": 57.0, "lon": 2.5, "resources": ["Oil", "Natural Gas"], "importance": 8, "kind": "Energy hub"},
    {"id": "siberia", "name": "West Siberia", "country": "RUS", "lat": 61.0, "lon": 75.0, "resources": ["Oil", "Natural Gas"], "importance": 8, "kind": "Energy hub"},
    {"id": "chile", "name": "Chile Copper Belt", "country": "CHL", "lat": -22.5, "lon": -68.9, "resources": METALS, "importance": 9, "kind": "Mine"},
    {"id": "australia-mine", "name": "Western Australia Mining", "country": "AUS", "lat": -23.7, "lon": 121.0, "resources": METALS, "importance": 6, "kind": "Mine"},
    {"id": "south-africa", "name": "South Africa Gold Belt", "country": "ZAF", "lat": -26.2, "lon": 28.0, "resources": ["Gold"], "importance": 7, "kind": "Mine"},
    {"id": "indonesia", "name": "Indonesia LNG / Mining", "country": "IDN", "lat": -2.5, "lon": 118.0, "resources": ["Natural Gas", "Copper", "Gold"], "importance": 7, "kind": "Port"},
    {"id": "australia-lng", "name": "Australia LNG", "country": "AUS", "lat": -20.0, "lon": 116.0, "resources": ["Natural Gas"], "importance": 7, "kind": "Energy hub"},
    {"id": "norway", "name": "Norway Energy Hub", "country": "NOR", "lat": 60.4, "lon": 5.3, "resources": ["Oil", "Natural Gas"], "importance": 7, "kind": "Energy hub"},
]

COUNTRIES = [
    {"code":"USA","name":"United States","lat":39,"lon":-98,"output":{"Oil":13,"Natural Gas":15,"Gasoline":11,"Heating Oil":8,"Copper":3,"Gold":3,"Silver":2},"demand":{"Oil":20,"Natural Gas":13,"Gasoline":12,"Heating Oil":9,"Copper":6,"Gold":5,"Silver":5}},
    {"code":"SAU","name":"Saudi Arabia","lat":24,"lon":45,"output":{"Oil":12,"Natural Gas":3,"Gasoline":4,"Heating Oil":3},"demand":{"Oil":4,"Natural Gas":2,"Gasoline":2,"Heating Oil":2}},
    {"code":"CHN","name":"China","lat":36,"lon":104,"output":{"Oil":4,"Natural Gas":5,"Gasoline":4,"Heating Oil":3,"Copper":6,"Gold":4,"Silver":5},"demand":{"Oil":16,"Natural Gas":10,"Gasoline":8,"Heating Oil":7,"Copper":16,"Gold":10,"Silver":9}},
    {"code":"IND","name":"India","lat":21,"lon":78,"output":{"Oil":2,"Natural Gas":2,"Gasoline":2,"Heating Oil":2,"Copper":2,"Gold":1,"Silver":1},"demand":{"Oil":8,"Natural Gas":6,"Gasoline":5,"Heating Oil":4,"Copper":6,"Gold":8,"Silver":7}},
    {"code":"RUS","name":"Russia","lat":61,"lon":96,"output":{"Oil":11,"Natural Gas":13,"Gasoline":6,"Heating Oil":6,"Gold":5,"Copper":4},"demand":{"Oil":4,"Natural Gas":5,"Gasoline":3,"Heating Oil":3,"Gold":2,"Copper":2}},
    {"code":"ARE","name":"United Arab Emirates","lat":24,"lon":54,"output":{"Oil":6,"Natural Gas":4,"Gasoline":3},"demand":{"Oil":2,"Natural Gas":2,"Gasoline":2}},
    {"code":"QAT","name":"Qatar","lat":25.3,"lon":51.2,"output":{"Natural Gas":12,"Oil":2},"demand":{"Natural Gas":1,"Oil":1}},
    {"code":"NOR","name":"Norway","lat":61,"lon":9,"output":{"Oil":6,"Natural Gas":8},"demand":{"Oil":1,"Natural Gas":1}},
    {"code":"AUS","name":"Australia","lat":-25,"lon":134,"output":{"Natural Gas":10,"Copper":7,"Gold":8,"Silver":5,"Oil":2},"demand":{"Natural Gas":2,"Copper":2,"Gold":2,"Silver":2,"Oil":2}},
    {"code":"CHL","name":"Chile","lat":-33,"lon":-71,"output":{"Copper":14,"Gold":3,"Silver":5},"demand":{"Copper":2,"Gold":1,"Silver":1,"Oil":2}},
    {"code":"ZAF","name":"South Africa","lat":-29,"lon":24,"output":{"Gold":9,"Silver":3,"Copper":2},"demand":{"Gold":2,"Silver":1,"Copper":1,"Oil":2}},
    {"code":"IDN","name":"Indonesia","lat":-2,"lon":118,"output":{"Natural Gas":6,"Copper":5,"Gold":4,"Oil":3},"demand":{"Natural Gas":2,"Copper":2,"Gold":2,"Oil":4}},
    {"code":"JPN","name":"Japan","lat":36,"lon":138,"output":{"Gold":1},"demand":{"Oil":6,"Natural Gas":8,"Gasoline":4,"Heating Oil":4,"Copper":5,"Gold":4,"Silver":3}},
    {"code":"KOR","name":"South Korea","lat":36,"lon":128,"output":{},"demand":{"Oil":5,"Natural Gas":5,"Gasoline":4,"Copper":5,"Gold":3,"Silver":3}},
    {"code":"DEU","name":"Germany","lat":51,"lon":10,"output":{"Copper":1},"demand":{"Oil":4,"Natural Gas":6,"Gasoline":4,"Heating Oil":4,"Copper":4,"Gold":3,"Silver":3}},
    {"code":"GBR","name":"United Kingdom","lat":54,"lon":-2,"output":{"Oil":2,"Natural Gas":2},"demand":{"Oil":4,"Natural Gas":4,"Gold":3,"Silver":2}},
    {"code":"BRA","name":"Brazil","lat":-11,"lon":-52,"output":{"Oil":5,"Copper":3,"Gold":3},"demand":{"Oil":5,"Copper":3,"Gold":2}},
    {"code":"CAN","name":"Canada","lat":57,"lon":-106,"output":{"Oil":7,"Natural Gas":6,"Copper":4,"Gold":3,"Silver":3},"demand":{"Oil":3,"Natural Gas":3,"Copper":2,"Gold":2,"Silver":2}},
    {"code":"NGA","name":"Nigeria","lat":9,"lon":8,"output":{"Oil":5,"Natural Gas":3},"demand":{"Oil":2,"Natural Gas":1}},
    {"code":"PER","name":"Peru","lat":-10,"lon":-75,"output":{"Copper":8,"Gold":3,"Silver":8},"demand":{"Copper":1,"Gold":1,"Silver":1}},
    {"code":"EGY","name":"Egypt","lat":27,"lon":30,"output":{"Oil":2,"Natural Gas":3},"demand":{"Oil":3,"Natural Gas":3}},
    {"code":"PAN","name":"Panama","lat":9,"lon":-80,"output":{},"demand":{"Oil":1,"Natural Gas":1}},
]

ROUTES = [
    {"id":"gulf-china","from":"gulf","to":"CHN","resource":"Oil","volume":5},
    {"id":"hormuz-china","from":"hormuz","to":"CHN","resource":"Oil","volume":9},
    {"id":"hormuz-india","from":"hormuz","to":"IND","resource":"Oil","volume":7},
    {"id":"north-europe","from":"north-sea","to":"DEU","resource":"Oil","volume":4},
    {"id":"gulf-japan","from":"gulf","to":"JPN","resource":"Oil","volume":3},
    {"id":"qatar-china","from":"hormuz","to":"CHN","resource":"Natural Gas","volume":7},
    {"id":"australia-japan","from":"australia-lng","to":"JPN","resource":"Natural Gas","volume":7},
    {"id":"australia-china","from":"australia-lng","to":"CHN","resource":"Natural Gas","volume":6},
    {"id":"norway-europe","from":"norway","to":"DEU","resource":"Natural Gas","volume":5},
    {"id":"gulf-gasoline","from":"gulf","to":"BRA","resource":"Gasoline","volume":4},
    {"id":"hormuz-gasoline","from":"hormuz","to":"IND","resource":"Gasoline","volume":4},
    {"id":"north-heating","from":"north-sea","to":"GBR","resource":"Heating Oil","volume":4},
    {"id":"gulf-heating","from":"gulf","to":"DEU","resource":"Heating Oil","volume":3},
    {"id":"chile-china","from":"chile","to":"CHN","resource":"Copper","volume":9},
    {"id":"australia-copper","from":"australia-mine","to":"IND","resource":"Copper","volume":5},
    {"id":"chile-us","from":"chile","to":"USA","resource":"Copper","volume":4},
    {"id":"south-africa-india","from":"south-africa","to":"IND","resource":"Gold","volume":5},
    {"id":"australia-gold","from":"australia-mine","to":"CHN","resource":"Gold","volume":4},
    {"id":"chile-silver","from":"chile","to":"CHN","resource":"Silver","volume":4},
    {"id":"australia-silver","from":"australia-mine","to":"IND","resource":"Silver","volume":4},
]

BASE_IMPACT = {
    "war":1.0,"earthquake":0.65,"hurricane":0.7,"port_closure":0.75,"pipeline_failure":0.85,
    "cyberattack":0.55,"labor_strike":0.45,"sanctions":0.9,"mine_accident":0.6,"drought":0.4,
    "shipping_chokepoint":0.95,"pandemic":0.6,
}


def haversine_km(a_lat: float, a_lon: float, b_lat: float, b_lon: float) -> float:
    r = math.pi / 180.0
    d_lat = (b_lat - a_lat) * r
    d_lon = (b_lon - a_lon) * r
    x = math.sin(d_lat / 2) ** 2 + math.cos(a_lat * r) * math.cos(b_lat * r) * math.sin(d_lon / 2) ** 2
    return 12742.0 * math.asin(min(1.0, math.sqrt(x)))


def _event_start_end(event: dict[str, Any]) -> tuple[datetime | None, datetime | None]:
    start_s = str(event.get("startDate") or "").strip()
    end_s = str(event.get("endDate") or "").strip()
    try:
        start_d = date.fromisoformat(start_s)
    except ValueError:
        return None, None
    start = datetime.combine(start_d, time.min, tzinfo=timezone.utc)
    if end_s:
        try:
            end_d = date.fromisoformat(end_s)
        except ValueError:
            end_d = start_d
    else:
        end_d = start_d + timedelta(days=21)
    end = datetime.combine(end_d + timedelta(days=1), time.min, tzinfo=timezone.utc)
    return start, end


def simulate(events: list[dict[str, Any]], resource: str, now: datetime) -> dict[str, Any]:
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    hubs = [h for h in HUBS if resource in h["resources"]]
    effects: list[dict[str, Any]] = []

    for event in events:
        start, end = _event_start_end(event)
        if start is None or end is None:
            continue
        age = (now - start).total_seconds() / 86400.0
        duration = max(1.0, (end - start).total_seconds() / 86400.0)
        if age < 0 or age > duration + 30:
            continue
        severity = max(0.0, min(10.0, float(event.get("severity", 0) or 0)))
        if not hubs:
            continue
        nearest = min(hubs, key=lambda h: haversine_km(float(event.get("lat", 0)), float(event.get("lon", 0)), h["lat"], h["lon"]))
        distance = haversine_km(float(event.get("lat", 0)), float(event.get("lon", 0)), nearest["lat"], nearest["lon"])
        safe_haven = resource in {"Gold", "Silver"} and str(event.get("type")) in {"war", "sanctions", "pandemic", "cyberattack"}
        proximity = math.exp(-distance / 1500.0)
        strength = (
            BASE_IMPACT.get(str(event.get("type")), 0.5)
            * (severity / 10.0)
            * float(RESOURCE_INFO[resource]["sensitivity"])
            * (0.55 + float(nearest["importance"]) / 10.0)
            * (max(0.45, proximity) if safe_haven else proximity)
        )
        onset = min(1.0, max(0.0, age / 3.0))
        recovery = math.exp(-(age - duration) / 9.0) if age > duration else 1.0
        phase = onset * recovery
        effects.append({
            "event": event,
            "nearest": nearest,
            "age": age,
            "duration": duration,
            "distance": distance,
            "strength": strength,
            "phase": phase,
            "impact": strength * phase,
            "safe_haven": safe_haven,
        })

    active = [e for e in effects if e["age"] <= e["duration"]]
    risk = min(10.0, sum(float(e["impact"]) * 7.0 for e in effects))
    epoch_day = now.timestamp() / 86400.0
    seed = RESOURCES.index(resource) * 13.7
    seasonal_pct = 1.6 * math.sin(epoch_day / 29.0 + seed)
    noise_pct = 0.7 * math.sin(epoch_day * 1.9 + seed * 2.3) + 0.45 * math.sin(epoch_day * 5.3 + seed)
    base_pct = seasonal_pct + noise_pct
    forecast_pct = min(35.0, base_pct + sum(float(e["strength"]) * (7.0 if e["safe_haven"] else 11.0) for e in effects))
    shock_pct = sum(
        float(e["impact"]) * (7.0 if e["safe_haven"] else 11.0) * min(1.0, max(0.0, (float(e["age"]) - 4.0) / 15.0))
        for e in effects
    )
    price_pct = max(-25.0, min(35.0, base_pct + shock_pct))
    supply = max(45.0, 100.0 - sum(float(e["impact"]) * 19.0 * min(1.0, max(0.0, (float(e["age"]) - 1.0) / 4.0)) for e in effects))
    demand = max(85.0, min(110.0, 100.0 - shock_pct * 0.16 + base_pct * 0.5))

    routes: list[dict[str, Any]] = []
    for route in [r for r in ROUTES if r["resource"] == resource]:
        source = next((h for h in hubs if h["id"] == route["from"]), None)
        dest = next((c for c in COUNTRIES if c["code"] == route["to"]), None)
        if not source or not dest:
            continue
        disruption = min(
            0.85,
            max(
                [
                    float(e["impact"])
                    * math.exp(-haversine_km(source["lat"], source["lon"], e["nearest"]["lat"], e["nearest"]["lon"]) / 2500.0)
                    * min(1.0, max(0.0, (float(e["age"]) - 3.0) / 8.0))
                    for e in effects
                ]
                or [0.0]
            ),
        )
        routes.append({**route, "from_hub": source, "to_country": dest, "disruption": disruption})

    countries: list[dict[str, Any]] = []
    for country in COUNTRIES:
        production = float(country["output"].get(resource, 0.0))
        baseline_demand = float(country["demand"].get(resource, 0.0))
        exposure = sum(
            float(e["impact"])
            * math.exp(-haversine_km(country["lat"], country["lon"], e["nearest"]["lat"], e["nearest"]["lon"]) / 5500.0)
            * min(1.0, max(0.0, (float(e["age"]) - 5.0) / 7.0))
            for e in effects
        )
        production_now = production * (1.0 - min(0.8, exposure * 0.45))
        demand_now = baseline_demand * (demand / 100.0)
        balance = production_now - demand_now
        stress = min(100.0, max(0.0, (demand_now - production_now) * 5.0 + exposure * 38.0))
        countries.append({**country, "production": production_now, "demand_now": demand_now, "balance": balance, "stress": stress, "exposure": exposure})

    return {
        "time": now,
        "resource": resource,
        "price": float(RESOURCE_INFO[resource]["base"]) * (1 + price_pct / 100.0),
        "price_pct": price_pct,
        "forecast": float(RESOURCE_INFO[resource]["base"]) * (1 + forecast_pct / 100.0),
        "forecast_pct": forecast_pct,
        "supply": supply,
        "demand": demand,
        "balance": supply - demand,
        "risk": risk,
        "effects": effects,
        "active": active,
        "countries": countries,
        "routes": routes,
        "hubs": hubs,
    }


def quadratic_curve_points(a_lat: float, a_lon: float, b_lat: float, b_lon: float, index: int, steps: int = 32) -> list[tuple[float, float]]:
    side = 1.0 if index % 2 == 0 else -1.0
    mx, my = (a_lat + b_lat) / 2.0, (a_lon + b_lon) / 2.0
    dx, dy = b_lon - a_lon, b_lat - a_lat
    length = math.hypot(dx, dy) or 1.0
    bend = side * length * 0.18
    cx = mx + (-dy / length) * bend
    cy = my + (dx / length) * bend
    points: list[tuple[float, float]] = []
    for i in range(steps + 1):
        t = i / steps
        u = 1.0 - t
        lat = u * u * a_lat + 2 * u * t * cx + t * t * b_lat
        lon = u * u * a_lon + 2 * u * t * cy + t * t * b_lon
        points.append((lat, lon))
    return points
