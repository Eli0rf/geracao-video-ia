# ╔══════════════════════════════════════════════════════════════╗
# ║  BLOCO 6 — Dockerização: Dockerfile (multi-stage)          ║
# ║  Estágio deps: instala deps + ffmpeg + todos os artefatos║
# ║  Estágio runtime: serviço prod (copy do deps) + ffmpeg    ║
# ╚══════════════════════════════════════════════════════════════╝

# ─── Estágio 1: dependências Python + sistema ───────────────────────
FROM python:3.13-slim AS deps

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ffmpeg \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && ffmpeg -version | head -n 1

WORKDIR /app

# ─── Artefatos de build: pyproject, código-fonte, frontend, alembic, tests ───
COPY pyproject.toml README.md ./
COPY src/ src/
COPY static/ static/
COPY alembic.ini alembic/ ./alembic/
COPY tests/ tests/

RUN pip install --no-cache-dir -U pip \
    && pip install --no-cache-dir -e ".[dev]"

# ─── Estágio 2: runtime (serviço prod) ────────────────────
FROM python:3.13-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ffmpeg \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && ffmpeg -version | head -n 1

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_ENV=production \
    PORT=8000

WORKDIR /app

# Copia as dependências instaladas + o código-fonte do estágio deps
COPY --from=deps /usr/local /usr/local
COPY --from=deps /app /app

RUN mkdir -p /app/outputs/videos /app/outputs/thumbnails /app/outputs/temp /app/data

VOLUME ["/app/outputs"]

EXPOSE 8000

# ─── Comando de execução ────────────────────────────────────────────
#    uvicorn sem reload em produção (container unikernel)
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
