---
title: AI Nutritionist
emoji: AI
colorFrom: green
colorTo: blue
sdk: docker
app_port: 8501
pinned: false
license: mit
tags:
  - streamlit
  - nutrition
short_description: Local-first wellness meal planner with deterministic ranking
---

# AI Nutritionist

Profile-aware wellness meal planner built with Streamlit, USDA/FNDDS-derived local data, curated Mediterranean foods, deterministic neural ranking, and explicit non-medical safety boundaries.

This file is a deployment-ready Hugging Face Docker Space README template. Copy this file's contents into the root `README.md` of the Space repository so Hugging Face reads the YAML metadata. The Docker template keeps the Space port contract aligned with this repository's `Dockerfile`, which exposes Streamlit on port `8501`.

To publish:

1. Create a new Hugging Face Docker Space.
2. Copy the repository contents into the Space repository, then use this template as the Space root `README.md`.
3. Keep `app.py`, `Dockerfile`, `requirements.txt`, `data/foods_catalog.csv`, `data/mediterranean_foods.csv`, and `data/recipes/` committed so the hosted catalog matches the local app.
4. Do not add private PDFs, `.env` files, raw USDA ZIP archives, exported feedback CSVs, or local feedback databases.
5. Keep the app as a wellness planner. Do not add medical, clinical, diagnostic, treatment, therapeutic, or allergy-safe claims.
6. Host the Streamlit UI only. Do not expose the FastAPI feedback endpoints as a public production API without authentication, rate limiting, privacy policy, retention controls, and abuse controls.

The app does not require API keys. In a hosted Space, profile inputs and session feedback are processed by the hosting platform. Streamlit feedback remains session-scoped unless a user explicitly downloads the CSV export; do not configure persistent feedback storage without a privacy policy, retention process, and abuse controls.

Reference docs:

- Hugging Face Docker Spaces: https://huggingface.co/docs/hub/spaces-sdks-docker
- Hugging Face Spaces configuration: https://huggingface.co/docs/hub/spaces-config-reference
