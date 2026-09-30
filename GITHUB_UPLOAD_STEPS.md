# GitHub + Streamlit Deployment Steps

## GitHub

1. Create or open: `qxiao2ub/Energy-Resource-Shock-Simulator-AI-App`.
2. Upload the **contents of this folder** to the root of the repository.
3. Confirm that `app.py`, `requirements.txt`, `.streamlit/config.toml`, `core/`, `assets/`, and `lovable_ui_source/` are present.
4. Do not upload a real `.streamlit/secrets.toml` containing a token.

## Streamlit Community Cloud

Use:

- Repository: `qxiao2ub/Energy-Resource-Shock-Simulator-AI-App`
- Branch: `main`
- Main file path: `app.py`

Then deploy.

## Recommended visitor-counter setup

After the first deployment, follow `COUNTER_SETUP.md` so the no-database visitor count remains cumulative across Streamlit Cloud restarts and redeploys.
