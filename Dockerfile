FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_PORT=8501

WORKDIR /app

COPY requirements.txt constraints-runtime.txt pyproject.toml README.md ./
COPY ai_nutritionist ./ai_nutritionist
COPY data ./data
COPY app.py cli.py ./

RUN python -m pip install --upgrade --no-cache-dir pip \
    && python -m pip install --no-cache-dir -r requirements.txt -c constraints-runtime.txt \
    && python -m pip install --no-cache-dir .

RUN groupadd --system app \
    && useradd --system --gid app --home-dir /home/app --create-home app \
    && chown -R app:app /app /home/app

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=3).read()"

# Equivalent command: streamlit run app.py --server.address=0.0.0.0 --server.port=8501
USER app
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501"]
