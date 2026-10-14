# 🎬 Geração de Vídeo por IA

> API REST para geração de vídeos por Inteligência Artificial usando modelos open-source.

[![CI](https://github.com/Eli0rf/geracao-video-ia/actions/workflows/ci.yml/badge.svg)](https://github.com/Eli0rf/geracao-video-ia/actions)
[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green.svg)](https://fastapi.tiangolo.com/)
[![Celery](https://img.shields.io/badge/Celery-5.6-green.svg)](https://docs.celeryq.dev/)
[![Redis](https://img.shields.io/badge/Redis-7-red.svg)](https://redis.io/)
[![Versão](https://img.shields.io/badge/versão-1.0.0-brightgreen.svg)](https://github.com/Eli0rf/geracao-video-ia/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](#licença)

## O que é

Sistema que recebe prompts de texto e retorna vídeos gerados por IA, usando modelos
open-source rodando **localmente** — **sem custo de API** para inferência.

O fluxo completo é orquestrado em 4 estágios, cada um com duração registrada em log:

```
roteiro (Ollama + juiz LLM)  →  áudio (Piper TTS)  →  vídeo (Wan2.1 / AnimateDiff)  →  montagem (FFmpeg)
```

Antes de renderizar, um **auditor LLM** valida a fidelidade do roteiro ao prompt do
usuário e, se necessário, corrige o roteiro automaticamente (até 3 tentativas) —
evitando gastar GPU em vídeos fora do tema.

## Modelos suportados

| Modelo | VRAM | Qualidade | Papel |
|--------|------|-----------|-------|
| Wan2.1-T2V | 8GB | ⭐⭐⭐⭐ | Primário (`default_model=wan2.1`) |
| AnimateDiff-v3 + MotionAdapter | 4GB | ⭐⭐⭐ | Fallback leve (padrão) |
| `fake` | 0 | — | Desenvolvimento/testes (sem GPU) |

Se o modelo pedido não estiver disponível (deps ausentes ou VRAM insuficiente), a
factory (`src/core/factory.py`) cai automaticamente para o próximo até o `fake` —
o pipeline **nunca** falha por indisponibilidade de modelo.

## Quick Start

```bash
# Clone o repositório
git clone https://github.com/Eli0rf/geracao-video-ia.git
cd geracao-video-ia

# Crie o ambiente e instale as dependências (produção + dev)
make install

# Suba a API (modo desenvolvimento, com hot-reload)
make run
```

Acesse `http://localhost:8000/docs` para a documentação interativa.

### Para gerar vídeos de verdade (IA)

As dependências de IA são pesadas e ficam num extra separado:

```bash
make install-ai    # torch, diffusers, transformers, accelerate (~2GB)
make prefetch      # baixa os pesos do Wan2.1 e AnimateDiff para ./models
```

## Docker (stack completa)

```bash
docker compose up -d --build   # api + worker + redis
make docker-logs               # acompanha os 3 serviços
```

A stack sobe **três serviços**:

| Serviço | Comando | Porta | Função |
|---|---|---|---|
| `api` | `uvicorn src.api.main:app` | 8000 | Recebe os jobs (202) e consulta status |
| `worker` | `celery -A src.core.celery_app worker` | — | Executa a geração pesada |
| `redis` | `redis:7-alpine` | 6379 | Broker da fila (persistido em `./data/redis`) |

Volumes montados na máquina host: `./outputs` (vídeos), `./data` (banco + redis),
`./models` (pesos / cache HuggingFace).

## Uso da API

```bash
# Cria um job (retorna 202 + status pending)
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{"prompt": "um gato astronauta flutuando no espaço", "model": "wan2.1"}'

# Consulta o status (pending → processing → completed | failed)
curl http://localhost:8000/api/v1/jobs/{id}

# Lista jobs (paginado, com filtro por status)
curl "http://localhost:8000/api/v1/jobs?page=1&page_size=20&status=completed"

# Baixa o vídeo gerado (200 quando completed; 409 pendente; 410 arquivo ausente)
curl -O http://localhost:8000/api/v1/jobs/{id}/download
```

### Endpoints

| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/api/v1/jobs` | Cria um job (202 `Accepted`) |
| `GET` | `/api/v1/jobs` | Lista jobs com paginação e filtro |
| `GET` | `/api/v1/jobs/{id}` | Status de um job |
| `GET` | `/api/v1/jobs/{id}/download` | Download do MP4 |
| `GET` | `/metrics` | Métricas Prometheus (jobs por status) |
| `GET` | `/health` | Healthcheck |

### Frontend

A API serve uma interface web em `http://localhost:8000/` (montada por último para
não sombrear `/api/v1/*` nem `/health`).

## Fila de tarefas (Celery + Redis)

O processamento pesado **não** roda no processo web. O `POST /jobs` apenas enfileira
e responde `202` imediatamente; um **worker dedicado** consome a fila.

| Ambiente | `TASK_BACKEND` | Comportamento |
|---|---|---|
| desenvolvimento / teste | `background` | Roda no processo da API (sem Redis) |
| produção | `celery` | Enfileira no Redis, processado pelo `worker` |

```bash
make redis-up     # sobe só o broker
make worker       # sobe o worker Celery (consumidor da fila)
```

Resiliência: `acks_late` (a mensagem só é confirmada **após** o job terminar — se o
worker morrer, o job volta para a fila), `task_reject_on_worker_lost`, limite rígido
de tempo (`JOB_TIMEOUT_SECONDS`) e reinício do processo a cada 50 tasks (evita
acúmulo de VRAM).

## Observabilidade

Cada request recebe um `X-Correlation-ID` (gerado ou ecoado do cliente) que é
**repassado para dentro do worker** e religado aos contextvars do structlog — o mesmo
ID aparece em todos os logs, do `POST /jobs` até a última linha do pipeline.

- Logs estruturados (JSON em produção, console colorido em dev).
- `duration_ms` por estágio (`pipeline_stage`) e por job (`job_processed`).
- Falhas de OOM/falta de VRAM capturadas com **stack trace completo**.
- `GET /metrics` no formato Prometheus, sem biblioteca externa.

## Arquitetura em camadas

```
geracao-video-ia/
├── src/
│   ├── api/          → FastAPI: routers, schemas Pydantic, middleware, deps
│   │   ├── v1/       → endpoints (jobs, metrics) + schemas de request/response
│   │   └── main.py   → entry point (middleware de correlation ID)
│   ├── core/         → lógica de negócio, sem I/O de framework web
│   │   ├── generators/   → Wan2.1, AnimateDiff, Ollama (roteiro + juiz), Piper
│   │   ├── assembly/     → montagem FFmpeg
│   │   ├── celery_app.py → app + task de processamento (fila)
│   │   ├── worker.py     → JobProcessor (transições de status)
│   │   ├── dispatcher.py → Protocol + Background/Celery dispatchers
│   │   └── pipeline.py   → orquestrador dos 4 estágios
│   ├── models/       → SQLModel ORM + CRUD de VideoJob
│   └── utils/        → helpers e configuração
├── tests/
│   ├── unit/         → 270 testes, sem I/O real
│   ├── integration/  → 24 testes (API, dispatch, CRUD, FFmpeg)
│   └── e2e/          → cenários ponta a ponta
├── scripts/          → run_e2e.py, prefetch_models.py
├── docs/adr/         → Architecture Decision Records
└── outputs/          → vídeos gerados (gitignored)
```

**Regra de dependência:** `api` → `core` → `models`. O `core` **nunca** importa
`api` — é isso que permite o worker Celery compartilhar o mesmo `JobProcessor`.

## Decisões de arquitetura (ADRs)

| ADR | Decisão |
|---|---|
| [ADR-001](docs/adr/ADR-001-python-fastapi.md) | Python 3.13 + FastAPI |
| [ADR-002](docs/adr/ADR-002-sqlite.md) | SQLite + SQLModel |
| [ADR-003](docs/adr/ADR-003-modelos-ia.md) | Modelos: Wan2.1 primário, AnimateDiff fallback |
| [ADR-004](docs/adr/ADR-004-dupla-ia.md) | Dupla IA (implementador + revisor) |
| [ADR-005](docs/adr/ADR-005-github-actions.md) | GitHub Actions |
| [ADR-006](docs/adr/ADR-006-roteiro-audio-locais.md) | Roteiro (Ollama) + áudio (Piper) locais |
| [ADR-007](docs/adr/ADR-007-montagem-ffmpeg.md) | Montagem com FFmpeg |
| [ADR-008](docs/adr/ADR-008-execucao-background.md) | BackgroundTasks como dispatcher inicial |
| [ADR-009](docs/adr/ADR-009-celery-redis.md) | Celery + Redis como fila em produção |

## Comandos do Makefile

```bash
make help          # lista todos os comandos
make ci            # lint + typecheck + testes (cobertura mínima 80%)
make test          # pytest com cobertura
make run           # API em desenvolvimento
make worker        # worker Celery
make redis-up      # sobe o broker
make prefetch      # baixa os pesos dos modelos
make docker-up     # sobe a stack completa
```

## Pipeline de Desenvolvimento

```
DEFINE → PLAN → BUILD → VERIFY → REVIEW → SHIP
```

Ver `docs/PIPELINE.md` para detalhes.

## Para IAs e Agentes

Leia `AGENTS.md` antes de qualquer trabalho no projeto.  
Verifique `CONTEXT.md` para o estado atual.

## Licença

MIT

