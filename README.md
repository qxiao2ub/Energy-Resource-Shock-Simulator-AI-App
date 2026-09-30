# Energy Resource Shock Simulator AI App

**Author:** Ryan Zhou  
**Mentor:** Dr. Qingyang Xiao

Interactive student-oriented AI simulation and analysis app for exploring how wars, earthquakes, hurricanes, port closures, sanctions, cyberattacks and other disruptions can affect global energy and commodity resource flows.

**Live App:** https://energy-resource-shock-simulator-ai.streamlit.app/  
**GitHub:** https://github.com/qxiao2ub/Energy-Resource-Shock-Simulator-AI-App

## New UI integration

This version integrates the newly supplied Lovable UI into a Streamlit-compatible application. The original React/TanStack source is preserved in `lovable_ui_source/`, while `app.py` implements the interface and simulation behaviors natively in Streamlit/Folium.

Major UI features include a dark simulation map, resource selector, supply/demand/trade/money/event map modes, resource-flow routes, disruption rings, hubs, user event flags, simulation HUD, scenario clock, timeline, workspace controls and AI analysis tabs.

See `LOVABLE_UI_INTEGRATION.md` for a detailed mapping of the Lovable UI into Streamlit.

## AI / modeling features

- **Machine learning:** Random Forest regression for educational 30-day resource price-change and supply-risk scenarios.
- **Deep learning / neural network:** MLP classification of crisis risk levels.
- **Clustering:** K-means crisis-event grouping.
- **Reinforcement learning:** Q-learning response recommendation prototype.
- **Deterministic resource-flow simulator:** country supply/demand, hubs, routes, disruption propagation and scenario timeline.

The included models train on synthetic classroom labels. Replace those labels with validated historical data before any serious analytical use.

## No-database cumulative app-user counter

The visible **Cumulative app users** count increments once per Streamlit browser session and is shown in the header, sidebar and floating app badge.

For durable persistence across Streamlit Community Cloud restarts, configure the included **GitHub-file counter**. It stores only the integer count in `data/visitor_count.json` and uses no database. Follow `COUNTER_SETUP.md`.

Without GitHub-file mode, the app falls back to a local file. Local mode works immediately but Streamlit Cloud can reset local files during a rebuild/restart.

## Run locally

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Deploy on Streamlit Community Cloud

- Branch: `main`
- Main file: `app.py`

See `GITHUB_UPLOAD_STEPS.md`.

## Repository structure

```text
app.py
requirements.txt
.streamlit/
  config.toml
  secrets.toml.example
assets/
  lovable_dark_theme.css
core/
  modeling.py
  simulation.py
  visitor_counter.py
data/
  visitor_count.json
lovable_ui_source/
Energy_Resource_Shock_AI_App_Colab.ipynb
README.md
COUNTER_SETUP.md
LOVABLE_UI_INTEGRATION.md
GITHUB_UPLOAD_STEPS.md
AUTHORS.md
CITATION.cff
COPYRIGHT_AND_LICENSE_NOTES.md
```

## Educational-use notice

This application is a student prototype. It is not investment advice, emergency guidance, a validated market forecast, or an operational supply-chain decision system.
