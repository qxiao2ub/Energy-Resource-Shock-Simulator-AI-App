# Lovable UI integration notes

**Author:** Ryan Zhou  
**Mentor:** Dr. Qingyang Xiao


The uploaded `src.zip` contained a Lovable React/TypeScript front end under `src/`. It used TanStack Router, Leaflet, Supabase auth/workspaces, shadcn-style UI components, a warm neutral design system, map-click event creation, a time bar, and event cards.

Because Streamlit cannot directly run React/TanStack components as its main app, the UI was integrated by translating the interaction design into Streamlit-native Python:

## Preserved design and interaction elements

- `Energy Resource Shock Simulator` map-first page structure.
- Interactive world map with click-to-place event workflow.
- Event type list and event color mapping.
- SVG flag event markers inspired by the Lovable marker SVG.
- Date-based event status: active, upcoming, ended, inactive.
- Time stepping controls and simulation date.
- Workspace limit of 3.
- Sortable event list/cards.
- Rounded cards, warm background, muted borders, pill badges, and primary/accent colors.

## Implementation changes

- React state became `st.session_state`.
- Leaflet map became `folium` + `streamlit-folium`.
- Supabase persistence was replaced with in-session workspaces plus JSON import/export, so the app runs for free without secrets.
- Shadcn/Tailwind components were converted into Streamlit widgets plus `assets/lovable_theme.css`.
- The placeholder "About this place" section was replaced with ML, neural-network, clustering, RL, and data-source tabs.

## Original Lovable source

The original UI source is preserved in:

```text
lovable_ui_source/src/
```

Keep this folder if you want to continue comparing the Streamlit implementation with the Lovable design. Remove it if you want a smaller production repo.
