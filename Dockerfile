FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends build-essential curl && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml README_V2.md ./
COPY src ./src
RUN pip install --upgrade pip && pip install -e .
RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser
EXPOSE 8002
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD curl -fsS http://localhost:8002/healthz || exit 1
CMD ["uvicorn", "campaign.main:app", "--host", "0.0.0.0", "--port", "8002"]
