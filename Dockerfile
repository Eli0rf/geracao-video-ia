# ╔══════════════════════════════════════════════════════════════╗
# ║  BLOCO 6 — Dockerização: Dockerfile                          ║
# ║  Base: python:3.11-slim  |  FFmpeg obrigatório (system deps) ║
# ╚══════════════════════════════════════════════════════════════╝

# ─── 1. Imagem base oficial, slim ────────────────────────────────────────────
FROM python:3.11-slim

# ─── 2. Dependências do sistema (apt-get) — FFmpeg obrigatório ───────────────
#    ffmpeg é necessário para: concat + normalização (VideoAssembler) e
#    mux de áudio no passo final da montagem do vídeo.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ffmpeg \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && ffmpeg -version | head -n 1

# ─── 3. Configuração do ambiente ─────────────────────────────────────────────
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_ENV=production \
    PORT=8000

WORKDIR /app

# ─── 4. Dependências Python (instala o pacote + extras na mesma camada) ─────────
#    Copia pyproject.toml e a fonte antes de instalar, para aproveitar o
#    cache do Docker: alterações no código não invalidam a camada de deps.
COPY pyproject.toml README.md ./
COPY src/ src/

RUN pip install --no-cache-dir -U pip \
    && pip install --no-cache-dir -e ".[dev]"

# ─── 5. Frontend estático (servido via StaticFiles em src/api/main.py) ──────────
COPY static/ static/

# ─── 6. Migrations (Alembic) ──────────────────────────────────────────────────
COPY alembic.ini alembic/ ./alembic/

# ─── 7. Diretório de saída para vídeos (montado como volume no compose) ────────
RUN mkdir -p /app/outputs/videos /app/outputs/thumbnails /app/outputs/temp
VOLUME ["/app/outputs"]

# ─── 8. Porta exposta ─────────────────────────────────────────────────────────
EXPOSE 8000

# ─── 9. Comando de execução ───────────────────────────────────────────────────
#    uvicorn sem reload em produção (container unikernel)
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
