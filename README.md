# Energy Resource Shock Simulator

**Author:** Ryan Zhou  
**Mentor:** Dr. Qingyang Xiao

GitHub/Streamlit-ready student prototype for simulating how wars, disasters, port closures, pipeline failures, cyberattacks, sanctions, and other supply-chain shocks may affect energy and commodity resources.

This version is prepared as a GitHub-ready repository for Ryan Zhou and integrates the Lovable UI design from the uploaded `src.zip` into a runnable Streamlit app. The original Lovable React/TypeScript source is preserved in `lovable_ui_source/` for reference, while `app.py` is the deployable Python Streamlit conversion.

## What was integrated from the Lovable UI

- Full-width global map experience with clickable event placement.
- Flag-style event markers and severity circles.
- Lovable-inspired warm neutral theme, rounded cards, pills, and map-first layout.
- Event types and colors from the uploaded React UI.
- Time controls that update event status: happening now, about to happen, just ended, inactive.
- Workspace concept with up to 3 workspaces.
- Event cards with sorting, status labels, and remove controls.

## AI features included

- **Machine learning forecast:** Random Forest model estimates 30-day commodity price change and a supply-risk index.
- **Deep learning / neural network:** Scikit-learn MLP classifier labels event-resource cases as Low, Medium, High, or Critical risk.
- **Clustering:** K-means groups crisis events into interpretable clusters.
- **Reinforcement learning:** A simple Q-learning policy recommends response actions based on risk, duration, and resource criticality.

The included model labels are synthetic and designed for a classroom prototype. Replace them with validated historical event/commodity data before any serious use.

## Repository structure

```text
.
├── app.py                              # Main Streamlit app; set this as the Streamlit entry point
├── AUTHORS.md                            # Author and mentor credits
├── CITATION.cff                          # GitHub citation metadata
├── requirements.txt                    # Python packages Streamlit Cloud installs
├── .streamlit/config.toml              # Theme and server config
├── assets/lovable_theme.css            # Converted Lovable visual theme for Streamlit
├── lovable_ui_source/src/              # Original Lovable React/TypeScript UI source from uploaded zip
├── Energy_Resource_Shock_AI_App_Colab.ipynb  # Colab notebook prototype, if included
├── LOVABLE_UI_INTEGRATION.md           # Conversion notes
├── COPYRIGHT_AND_LICENSE_NOTES.md      # Student copyright/licensing guidance
└── .gitignore
```

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## Upload to GitHub

1. Unzip this repo package.
2. Create a new empty GitHub repository.
3. Upload all files/folders from the unzipped folder to the repository root, or use Git:

```bash
git init
git add .
git commit -m "Initial Ryan Zhou energy shock simulator"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
git push -u origin main
```

## Deploy on Streamlit Community Cloud

Use these settings when creating the app:

- Repository: your new GitHub repo
- Branch: `main`
- Main file path: `app.py`

Streamlit Cloud will install packages from `requirements.txt` automatically.

## Authorship and citation

Author: Ryan Zhou. Mentor: Dr. Qingyang Xiao. Please keep `AUTHORS.md`, `CITATION.cff`, and the copyright notes with the repository when uploading to GitHub.

## Suggested next upgrades

- Replace synthetic training data with historical event and commodity datasets.
- Add free public feeds such as World Bank Pink Sheet, EIA Open Data, and GDELT.
- Save workspaces to Supabase, Firebase, or a simple database.
- Add user authentication if students need persistent individual accounts.
- Add model cards and classroom rubrics for explaining the assumptions.

## Educational disclaimer

This app is an educational simulation only. It is not investment advice, emergency guidance, or a validated operational forecast system.
