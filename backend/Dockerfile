# API de LotoLab. Contexto de build: la RAÍZ del repo (necesita data/raw para sembrar la BD).
#   docker build -f backend/Dockerfile -t lotolab-api .
FROM python:3.12-slim

RUN pip install --no-cache-dir uv==0.12.10
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1

WORKDIR /srv/backend
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY backend/ ./
COPY data/raw/ ../data/raw/
COPY data/backtest_summary.json ../data/backtest_summary.json
COPY data/expected_value.json ../data/expected_value.json
COPY data/picks_eval.json ../data/picks_eval.json
COPY data/ml_eval.json ../data/ml_eval.json
RUN uv sync --frozen --no-dev

ENV PATH="/srv/backend/.venv/bin:$PATH" PORT=8000
EXPOSE 8000
# init (migraciones + juegos) e import son idempotentes: la primera vez siembran la BD con los CSV.
CMD ["sh", "-c", "lotolab init && lotolab import && uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
