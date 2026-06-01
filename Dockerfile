FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_PORT=8501

WORKDIR /app

COPY requirements.txt pyproject.toml README.md ./
RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements.txt \
    && python -m pip install -e .

COPY ai_nutritionist ./ai_nutritionist
COPY data ./data
COPY app.py cli.py ./

EXPOSE 8501

CMD streamlit run app.py --server.address=0.0.0.0 --server.port=8501
