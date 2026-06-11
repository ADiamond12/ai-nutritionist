# Streamlit Community Cloud Deployment

Deploy from the public GitHub repository with:

- Repository: `ADiamond12/ai-nutritionist`
- Branch: `main`
- Main file path: `app.py`
- Python dependencies: `requirements.txt`
- Required committed data: `data/foods_catalog.csv`, `data/mediterranean_foods.csv`, and `data/recipes/`

No secrets are required for the default app. In a hosted deployment, profile inputs and Streamlit session feedback are processed by the hosting platform rather than only on the user's machine.

Do not configure persistent feedback storage on a public deployment unless a privacy policy, retention process, and abuse controls exist. Do not commit `.env` files, exported feedback CSVs, local feedback databases, private PDFs, or raw data archives.

Reference docs:

- Streamlit Community Cloud deployment: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app
- Streamlit Community Cloud dependencies: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies
- Streamlit secrets guidance: https://docs.streamlit.io/deploy/concepts/secrets
