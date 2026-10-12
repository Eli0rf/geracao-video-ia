# CONTEXT.md — Estado do Projeto

> **Propósito:** Arquivo de contexto de sessão. Atualizado a cada sessão de trabalho.
> Lido por todas as IAs no início de cada sessão para retomar de onde parou.
>
> **Compatível com:** Kiro, Claude Code, Gemini CLI, Cursor, Copilot, Codex, ChatGPT

---

## Status Geral

| Campo | Valor |
|---|---|
| **Fase pipeline** | BUILD v0.1 ✅ → próximo: BUILD v0.2 |
| **Milestone ativa** | v0.2 — Core (Integração com IA) |
| **Última atualização** | 2026-10-12 |
| **Branch ativa** | `develop` |
| **Versão** | 0.1.0-alpha |

---

## Próxima Task a Executar

**TASK-005 — Endpoint POST /api/v1/jobs**

```bash
git checkout develop
git checkout -b feature/task-005-post-jobs
```

Ver `PLAN.md` seção TASK-005 para critérios de aceitação completos.

---

## Estado das Tasks

| Task | Status | Merge |
|---|---|---|
| TASK-001 Setup Python + pyproject.toml | ✅ Concluída | 4641cbe |
| TASK-002 Scaffold FastAPI | ✅ Concluída | f1d1b5e |
| TASK-003 Modelos SQLite/SQLModel | ✅ Concluída | df59858 |
| TASK-004 CI/CD GitHub Actions | ✅ Concluída | b2cddd9 |
| TASK-005 POST /jobs | ◻ Pendente | — |
| TASK-006 GET /jobs/{id} | ◻ Pendente | — |
| TASK-007 GET /jobs (lista) | ◻ Pendente | — |
| TASK-008 GET /jobs/{id}/download | ◻ Pendente | — |
| TASK-009 Interface VideoGenerator | ◻ Pendente | — |
| TASK-010 Worker assíncrono | ◻ Pendente | — |
| TASK-011 AnimateDiff (fallback) | ◻ Pendente | — |
| TASK-012 Wan2.1 (primário) | ◻ Pendente | — |
| TASK-013 Testes E2E | ◻ Pendente | — |
| TASK-014 Logging + Métricas | ◻ Pendente | — |
| TASK-015 Docker | ◻ Pendente | — |

---

## O Que Foi Feito

### Sessão 2026-10-12 — Fase DEFINE ✅
- Estrutura de diretórios, documentação base, 5 ADRs, CI inicial
- Commit: `4dd4ad4`

### Sessão 2026-10-12 — Fase PLAN ✅
- PLAN.md (15 tasks, 4 milestones), pyproject.toml, .env.example, Makefile
- Commit: `0240fb0`

### Sessão 2026-10-12 — Dupla IA configurada ✅
- `.kiro/agents/construtor.json` + `validador.json`
- `scripts/validate.py` — cliente Gemini REST com fallback de modelos
- Modelos funcionando: `gemini-flash-latest`, `gemini-flash-lite-latest`
- Commit: `1e08335`

### Sessão 2026-10-12 — BUILD v0.1 ✅
- **TASK-001:** `src/config.py` — pydantic-settings, SecretStr, Literal types. 17 testes.
- **TASK-002:** FastAPI scaffold — `/health`, RFC 7807, structlog, router `/api/v1`. 29 testes.
- **TASK-003:** `VideoJob` SQLModel + CRUD + Alembic migration `ea1fedd1683a`. 56 testes, 98.51% cobertura.
- **TASK-004:** CI/CD GitHub Actions — 2 stages, concurrency, `--cov-append`, Gemini ✅

---

## Estrutura de Código Atual

```
src/
├── config.py              ← Settings pydantic-settings (SecretStr, Literal)
├── api/
│   ├── main.py            ← App factory, /health, middleware logging
│   ├── schemas.py         ← ProblemDetail RFC 7807, HealthResponse
│   ├── error_handlers.py  ← 404/422 → RFC 7807
│   ├── logging_config.py  ← structlog JSON/dev
│   └── v1/
│       ├── router.py      ← Agrega /api/v1
│       └── jobs.py        ← Placeholder POST /api/v1/jobs
├── models/
│   ├── video_job.py       ← VideoJob SQLModel (JobStatus enum)
│   └── video_job_crud.py  ← create, get, list (func.count), update_status
└── core/                  ← Reservado para lógica de negócio (TASK-009+)

tests/
├── unit/          ← 38 testes (config, health, errors, video_job model)
└── integration/   ← 18 testes (API startup, video_job CRUD)

alembic/
└── versions/ea1fedd1683a_create_video_jobs_table.py
```

---

## Métricas de Qualidade (BUILD v0.1)

| Métrica | Valor |
|---|---|
| Testes totais | 56 passando |
| Cobertura | 98.51% |
| ruff | ✅ 0 erros |
| mypy | ✅ 0 erros |
| Validações Gemini | 6 aprovadas (2 com melhorias aplicadas) |

---

## Comandos Úteis

```bash
# Rodar tudo
make ci

# Subir API local
make run
# → http://localhost:8000/docs

# Rodar migration
make db-upgrade

# Validar código com Gemini
python3 scripts/validate.py --code src/arquivo.py --spec "descrição"
```

---

## Decisões Técnicas Registradas

| Decisão | Motivo |
|---|---|
| `func.count()` no list_video_jobs | Eficiência — não carrega objetos em memória |
| `SecretStr` para tokens/keys | Evita vazamento em logs e repr() |
| `Literal` types para enums de config | Valida em parse-time, sem runtime overhead |
| `--cov-fail-under` só após `--cov-append` | Cobertura medida sobre unit+integration juntos |
| `render_as_batch=True` no Alembic | Compatibilidade com ALTER TABLE no SQLite |

---

## Bloqueios / Riscos

| Risco | Impacto | Mitigação |
|---|---|---|
| VRAM insuficiente para Wan2.1 | Alto | AnimateDiff como fallback (4GB) |
| Throttling da API Gemini | Baixo | Fallback gemini-flash-lite-latest |
| GitHub Actions minutos esgotados | Médio | Testes locais com `make ci` |

---

## Como Retomar em Uma Nova Sessão

1. Leia este arquivo (`CONTEXT.md`)
2. Leia `AGENTS.md` para as regras
3. Confirme o branch: `git branch`
4. Próxima task: **TASK-005** em `feature/task-005-post-jobs`

---

## Histórico de Sessões

| Data | Fase | O que foi feito |
|---|---|---|
| 2026-10-12 | DEFINE | Setup inicial, estrutura, documentação base |
| 2026-10-12 | PLAN | PLAN.md, pyproject.toml, .env.example, Makefile |
| 2026-10-12 | INFRA | Dupla IA configurada (scripts/validate.py + Gemini) |
| 2026-10-12 | BUILD v0.1 | TASK-001 a TASK-004 — fundação completa |
