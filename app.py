import math
import numpy as np
import pandas as pd
import streamlit as st
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title='Energy Resource Shock Simulator', layout='wide')
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)

RESOURCE_TICKERS = {
    'WTI Crude Oil': 'CL=F',
    'Brent Crude Oil': 'BZ=F',
    'Natural Gas': 'NG=F',
    'Gold': 'GC=F',
    'Silver': 'SI=F',
    'Copper': 'HG=F',
    'Gasoline': 'RB=F',
    'Heating Oil': 'HO=F',
}
EVENT_TYPES = ['war','earthquake','hurricane','port_closure','pipeline_failure','cyberattack','labor_strike','sanctions','mine_accident','drought','shipping_chokepoint','pandemic']
SUPPLY_HUBS = pd.DataFrame([
    {'hub': 'Strait of Hormuz', 'lat': 26.57, 'lon': 56.25, 'resources': 'WTI Crude Oil,Brent Crude Oil,Natural Gas,Gasoline,Heating Oil', 'importance': 10},
    {'hub': 'Suez Canal', 'lat': 30.59, 'lon': 32.27, 'resources': 'WTI Crude Oil,Brent Crude Oil,Natural Gas,Gasoline,Heating Oil', 'importance': 8},
    {'hub': 'Panama Canal', 'lat': 9.08, 'lon': -79.68, 'resources': 'WTI Crude Oil,Brent Crude Oil,Natural Gas,Copper,Gold', 'importance': 7},
    {'hub': 'US Gulf Coast', 'lat': 29.76, 'lon': -95.37, 'resources': 'WTI Crude Oil,Natural Gas,Gasoline,Heating Oil', 'importance': 9},
    {'hub': 'North Sea', 'lat': 57.0, 'lon': 2.5, 'resources': 'Brent Crude Oil,Natural Gas', 'importance': 8},
    {'hub': 'Chile Copper Belt', 'lat': -22.5, 'lon': -68.9, 'resources': 'Copper,Gold,Silver', 'importance': 9},
    {'hub': 'South Africa Gold Belt', 'lat': -26.2, 'lon': 28.0, 'resources': 'Gold', 'importance': 7},
])
EVENT_BASE_IMPACT = {'war':1.0,'earthquake':0.65,'hurricane':0.70,'port_closure':0.75,'pipeline_failure':0.85,'cyberattack':0.55,'labor_strike':0.45,'sanctions':0.90,'mine_accident':0.60,'drought':0.40,'shipping_chokepoint':0.95,'pandemic':0.60}
RESOURCE_SENSITIVITY = {'WTI Crude Oil':1.00,'Brent Crude Oil':1.05,'Natural Gas':0.90,'Gold':0.55,'Silver':0.45,'Copper':0.70,'Gasoline':0.85,'Heating Oil':0.85}


def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlambda = np.radians(lon2 - lon1)
    a = np.sin(dphi/2)**2 + np.cos(p1)*np.cos(p2)*np.sin(dlambda/2)**2
    return 2 * R * np.arcsin(np.sqrt(a))


def nearest_hub_features(lat, lon, resource):
    subset = SUPPLY_HUBS[SUPPLY_HUBS['resources'].str.contains(resource, regex=False)]
    if subset.empty:
        subset = SUPPLY_HUBS
    distances = haversine_km(lat, lon, subset['lat'].values, subset['lon'].values)
    i = int(np.argmin(distances))
    row = subset.iloc[i]
    return row['hub'], float(distances[i]), float(row['importance'])


def make_training_data(n=3000):
    rng = np.random.default_rng(RANDOM_SEED)
    rows = []
    for _ in range(n):
        resource = rng.choice(list(RESOURCE_TICKERS))
        event_type = rng.choice(EVENT_TYPES)
        severity = rng.uniform(1, 10)
        duration = rng.integers(2, 90)
        hub = SUPPLY_HUBS.sample(1, random_state=int(rng.integers(0, 1_000_000))).iloc[0]
        lat = np.clip(rng.normal(hub['lat'], 8), -80, 80)
        lon = ((rng.normal(hub['lon'], 12) + 180) % 360) - 180
        nearest, distance, importance = nearest_hub_features(lat, lon, resource)
        dist_factor = np.exp(-distance / 1500)
        vol_30d = rng.uniform(0.10, 0.70)
        price_delta = 0.75 * EVENT_BASE_IMPACT[event_type] * RESOURCE_SENSITIVITY[resource] * severity * dist_factor * (0.55 + importance/10) * (np.log1p(duration)/np.log1p(90)) * (0.60 + vol_30d) + rng.normal(0, 2.5)
        risk = np.clip(8 * EVENT_BASE_IMPACT[event_type] * RESOURCE_SENSITIVITY[resource] * (severity/10) * dist_factor * (0.55 + importance/10) + 0.06 * duration + rng.normal(0, 0.5), 0, 10)
        rows.append({'resource':resource,'event_type':event_type,'severity':severity,'duration_days':duration,'lat':lat,'lon':lon,'nearest_hub':nearest,'distance_to_hub_km':distance,'hub_importance':importance,'return_7d':rng.normal(0,0.03),'return_30d':rng.normal(0,0.08),'return_90d':rng.normal(0,0.15),'vol_30d':vol_30d,'vol_90d':rng.uniform(0.10,0.70),'price_zscore_180d':rng.normal(0,1),'price_delta_30d_pct':np.clip(price_delta,-18,35),'supply_risk_index':risk})
    return pd.DataFrame(rows)

@st.cache_resource
def train_model():
    data = make_training_data()
    cat = ['resource','event_type','nearest_hub']
    num = ['severity','duration_days','lat','lon','distance_to_hub_km','hub_importance','return_7d','return_30d','return_90d','vol_30d','vol_90d','price_zscore_180d']
    X = data[cat+num]
    y = data[['price_delta_30d_pct','supply_risk_index']]
    pre = ColumnTransformer([('cat', OneHotEncoder(handle_unknown='ignore'), cat), ('num', Pipeline([('imp', SimpleImputer(strategy='median')),('sc',StandardScaler())]), num)])
    model = Pipeline([('pre', pre), ('rf', RandomForestRegressor(n_estimators=180, min_samples_leaf=4, random_state=RANDOM_SEED, n_jobs=-1))])
    model.fit(X, y)
    return model, cat, num

model, CAT, NUM = train_model()

st.title('Energy Resource Shock Simulator')
st.caption('Student prototype: AI-assisted scenario simulation for commodity supply-chain disruptions.')

with st.sidebar:
    st.header('Scenario event')
    name = st.text_input('Event name', 'New disruption event')
    event_type = st.selectbox('Event type', EVENT_TYPES, index=EVENT_TYPES.index('earthquake'))
    severity = st.slider('Severity', 1.0, 10.0, 7.0, 0.5)
    duration_days = st.slider('Duration, days', 1, 120, 14)
    lat = st.number_input('Latitude', value=26.6, min_value=-80.0, max_value=80.0)
    lon = st.number_input('Longitude', value=56.3, min_value=-180.0, max_value=180.0)
    description = st.text_area('Description', 'Describe the disruption event.')

rows = []
for resource in RESOURCE_TICKERS:
    nearest, dist, importance = nearest_hub_features(lat, lon, resource)
    rows.append({'resource':resource,'event_type':event_type,'severity':severity,'duration_days':duration_days,'lat':lat,'lon':lon,'nearest_hub':nearest,'distance_to_hub_km':dist,'hub_importance':importance,'return_7d':0.0,'return_30d':0.0,'return_90d':0.0,'vol_30d':0.30,'vol_90d':0.35,'price_zscore_180d':0.0})
X = pd.DataFrame(rows)
pred = pd.DataFrame(model.predict(X[CAT+NUM]), columns=['predicted_30d_price_change_pct','supply_risk_index'])
summary = pd.concat([X[['resource','nearest_hub','distance_to_hub_km']], pred], axis=1)
summary['risk_level'] = pd.cut(summary['supply_risk_index'], bins=[-0.1,3,6.5,10.1], labels=['Low','Medium','High'])

col1, col2 = st.columns([1,1])
with col1:
    st.subheader('Forecast summary')
    st.dataframe(summary.sort_values('supply_risk_index', ascending=False), use_container_width=True)
    st.bar_chart(summary.set_index('resource')['predicted_30d_price_change_pct'])
with col2:
    st.subheader('Map')
    m = folium.Map(location=[lat, lon], zoom_start=3, tiles='CartoDB positron')
    folium.Marker([lat, lon], tooltip=name, popup=f'{event_type}, severity {severity}/10').add_to(m)
    folium.Circle([lat, lon], radius=severity*150000, fill=True, fill_opacity=0.12).add_to(m)
    for _, hub in SUPPLY_HUBS.iterrows():
        folium.CircleMarker([hub['lat'], hub['lon']], radius=4+hub['importance']/2, popup=hub['hub'], fill=True).add_to(m)
    st_folium(m, use_container_width=True, height=500)

st.warning('Educational simulation only. Replace synthetic labels with validated historical disruption data before any real use.')
