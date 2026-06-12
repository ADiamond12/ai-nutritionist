# Streamlit Community Cloud Deployment

Deploy from the public GitHub repository with:

- Repository: `ADiamond12/ai-nutritionist`
- Branch: `main`
- Main file path: `app.py`
- Python dependencies: `requirements.txt` with `constraints-runtime.txt`
- Required committed data: `data/foods_catalog.csv`, `data/mediterranean_foods.csv`, and `data/recipes/`

No secrets are required for the default app. In a hosted deployment, profile inputs and Streamlit session feedback are processed by the hosting platform rather than only on the user's machine.

Do not configure persistent feedback storage on a public deployment unless a privacy policy, retention process, and abuse controls exist. The default Streamlit UI does not need `AI_NUTRITIONIST_ENABLE_API_FEEDBACK`; leave FastAPI feedback persistence disabled for public demos. Do not commit `.env` files, exported feedback CSVs, local feedback databases, private PDFs, or raw data archives.

Streamlit Community Cloud discovers Python dependencies from repository files such as `requirements.txt`. This project keeps `requirements.txt` constrained for repeatability, but Docker Spaces remain the closest match to the checked-in `Dockerfile` runtime.

Reference docs:

- Streamlit Community Cloud deployment: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app
- Streamlit Community Cloud dependencies: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies
- Streamlit secrets guidance: https://docs.streamlit.io/deploy/concepts/secrets
