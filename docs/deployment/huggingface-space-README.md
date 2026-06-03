---
title: AI Nutritionist
emoji: AI
colorFrom: green
colorTo: blue
sdk: streamlit
sdk_version: 1.50.0
app_file: app.py
pinned: false
license: mit
---

# AI Nutritionist

Profile-aware wellness meal planner built with Streamlit, USDA/FNDDS-derived local data, curated Mediterranean foods, deterministic neural ranking, and explicit non-medical safety boundaries.

This file is a deployment-ready Hugging Face Spaces README template. To publish:

1. Create a new Streamlit Space.
2. Copy the repository contents into the Space repository.
3. Keep `app.py`, `requirements.txt`, `data/foods_catalog.csv`, and `data/mediterranean_foods.csv` committed.
4. Do not add private PDFs, `.env` files, raw USDA ZIP archives, exported feedback CSVs, or local feedback databases.

The app does not require API keys. Feedback is session-local in Streamlit unless a user explicitly downloads the CSV export.
