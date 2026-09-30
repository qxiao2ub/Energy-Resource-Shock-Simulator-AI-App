# New Lovable UI Integration

The newly supplied Lovable/TanStack/React source is preserved intact in `lovable_ui_source/`.

The runnable Streamlit version in `app.py` reproduces the major behaviors that translate well to Streamlit:

- dark navy/gold visual system from the new design,
- global Leaflet/Folium simulation map,
- selectable resources,
- map modes: All, Supply, Demand, Trade, Money, Events,
- country stress / production / demand / trade shading,
- resource supply routes with different colors,
- disruption highlighting and illustrative alternate routes,
- moving-style shipment markers as the simulation clock updates,
- event flags and impact rings,
- map click -> event coordinate capture,
- simulation price / supply / demand / balance HUD,
- start/pause simulation time, date/time editing, +/- day, speed control, reset-to-now,
- scenario timeline and play-from-first-event,
- up to three workspaces,
- JSON scenario import/export,
- event cards and sorting,
- machine-learning forecast,
- neural-network classification,
- K-means crisis clustering,
- reinforcement-learning response recommendations,
- cumulative visible app-user counter.

Some browser-native React concepts, such as a Radix side-sheet opened by clicking every map feature and Supabase login/workspace persistence, are represented with Folium popups/tooltips and local Streamlit workspaces instead. This keeps the GitHub repository directly deployable on Streamlit Community Cloud without requiring the Lovable/TanStack server or Supabase.
