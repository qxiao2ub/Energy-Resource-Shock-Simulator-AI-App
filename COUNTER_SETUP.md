# Cumulative App User Counter - No Database

The Streamlit app shows **Cumulative app users** in three always-visible places:

1. the top app header,
2. the Streamlit sidebar,
3. a floating badge at the lower-right corner of the app.

The counter increments **once per Streamlit browser session**, not every time a widget causes Streamlit to rerun. A hard refresh, a new browser session, or a new tab can count as a new visit. It is a visit counter, not identity tracking.

## Why there are two counter modes

Streamlit Community Cloud containers can be restarted, rebuilt, or replaced. Files written only to the running container are therefore not guaranteed to persist forever.

This repo uses:

- **GitHub-file mode - recommended:** stores the integer in `data/visitor_count.json` through the GitHub Contents API. This uses no database and survives Streamlit restarts/redeploys.
- **Local-file fallback:** works immediately without credentials and remains cumulative during normal app runtime, but a Streamlit container rebuild can reset it to the repository copy.

Therefore, if the requirement is that the global count must remain cumulative across redeploys, configure GitHub-file mode.

## GitHub-file mode setup

### 1. Create a fine-grained GitHub token

Create a fine-grained personal access token that has access only to this repository and grants **Contents: Read and write**.

Do not place the token in the repository.

### 2. Add Streamlit Secrets

In Streamlit Community Cloud open the app, then **Settings -> Secrets**, and add:

```toml
[visitor_counter]
github_token = "YOUR_FINE_GRAINED_GITHUB_TOKEN"
github_repo = "qxiao2ub/Energy-Resource-Shock-Simulator-AI-App"
counter_path = "data/visitor_count.json"
branch = "main"
```

A template is already included at `.streamlit/secrets.toml.example`.

### 3. Reboot the app

After saving the secret, reboot/redeploy the Streamlit app. The sidebar section **Visitor counter persistence** should report that the persistent GitHub-file backend is active.

## Important operational note

Each new counted visit updates `data/visitor_count.json`, which creates a small Git commit. This approach is intentionally simple and database-free for a student project. For a high-traffic production app, a purpose-built analytics or durable key-value service would be more appropriate.
