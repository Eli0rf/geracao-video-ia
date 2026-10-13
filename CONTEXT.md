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

**TASK-018 — VideoAssembler (montagem FFmpeg)** — Bloco 3 (PR 3)

```bash
git checkout develop
git checkout -b feature/e05-core-engine
```

Ver `PLAN.md` seção TASK-018 para critérios de aceitação completos.
Roteiro (Ollama) e áudio (Piper) já implementados — próximos: montagem,
pipeline e dispatcher.

---

## Estado das Tasks

| Task | Status | Merge |
|---|---|---|
| TASK-001 Setup Python + pyproject.toml | ✅ Concluída | 4641cbe |
| TASK-002 Scaffold FastAPI | ✅ Concluída | f1d1b5e |
| TASK-003 Modelos SQLite/SQLModel | ✅ Concluída | df59858 |
| TASK-004 CI/CD GitHub Actions | ✅ Concluída | b2cddd9 |
| TASK-005 POST /jobs | ✅ Concluída | a4e0d28 (E02) |
| TASK-006 GET /jobs/{id} | ✅ Concluída | a4e0d28 (E02) |
| TASK-007 GET /jobs (lista) | ✅ Concluída | a4e0d28 (E02) |
| TASK-008 GET /jobs/{id}/download | ✅ Concluída | a4e0d28 (E02) |
| TASK-009 Interface VideoGenerator | ✅ Concluída | PR-1 (Bloco 0&1) |
| TASK-010 Worker assíncrono | ◻ Pendente | — (ver TASK-019/020) |
| TASK-011 AnimateDiff (fallback) | ◻ Pendente | — |
| TASK-012 Wan2.1 (primário) | ◻ Pendente | — |
| TASK-013 Testes E2E | ◻ Pendente | — |
| TASK-014 Logging + Métricas | ◻ Pendente | — |
| TASK-015 Docker | ◻ Pendente | — |
| TASK-016 OllamaScriptGenerator | ✅ Concluída | PR-2 (Bloco 2) |
| TASK-017 PiperAudioSynthesizer | ✅ Concluída | PR-2 (Bloco 2) |
| TASK-018 VideoAssembler (FFmpeg) | ◻ Pendente | — (Bloco 3) |
| TASK-019 VideoPipeline | ◻ Pendente | — (Bloco 4) |
| TASK-020 BackgroundDispatcher | ◻ Pendente | — (Bloco 4) |

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

### Sessão 2026-10-12 — BUILD v0.2 — Motor de geração (Bloco 0&1 / PR-1)
- **Docs:** ADR-006 (Ollama+Piper locais), ADR-007 (FFmpeg subprocess), ADR-008 (BackgroundTasks). PLAN.md com TASK-016~020.
- **Contratos `src/core/`:** `interfaces.py` (Protocols `VideoGenerator`/`ScriptGenerator`/`AudioSynthesizer` + tipos `Scene`/`Script`), `errors.py` (hierarquia `GenerationError`), `fakes.py` (implementações determinísticas, WAV real), `factory.py` (resolução + fallback automático para fake).
- **Config:** `fake` adicionado aos modelos permitidos (`config.py`, `_ALLOWED_MODELS`).
- **Testes:** +27 unit (`test_core_interfaces/fakes/factory.py`). 95 unit + 18 integration = 113 passando.
- **Métricas:** `src/core/*` 100% cobertura; total 99%; ruff 0; mypy 0.
- **Próximo:** Bloco 2 (PR-2) — `OllamaScriptGenerator` + `PiperAudioSynthesizer`.

### Sessão 2026-10-12 — BUILD v0.2 — Roteiro e áudio (Bloco 2 / PR-2)
- **Config:** bloco "IA local" em `src/config.py` — `ollama_host/model/timeout/max_retries`, `piper_binary/voice_path/timeout` (validados com `Field`).
- **`OllamaScriptGenerator`** (`generators/ollama.py`): `httpx.Client` injetável; `is_available()` via `GET /api/tags`; `generate_script()` via `POST /api/generate` com `format=json`; retry em 5xx/rede (não em 4xx/timeout); parse+validação Pydantic → `Script`.
- **`PiperAudioSynthesizer`** (`generators/piper.py`): `is_available()` sem subprocess (`shutil.which` + voz); `synthesize()` via `subprocess.run` (lista, `shell=False`, texto por stdin); timeout → `GenerationTimeoutError`.
- **Testes:** `test_ollama_generator.py` (httpx.MockTransport), `test_piper_synth.py` (subprocess/which mockados), +config e ajustes na factory. 142 testes (124 unit + 18 integration).
- **Métricas:** `src/core/*` 100% cobertura; total 99.22%; ruff 0; mypy 0.
- **Próximo:** Bloco 3 (PR-3) — `VideoAssembler` (FFmpeg subprocess).

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
│       └── jobs.py        ← 4 endpoints REST de jobs (202/polling/download)
├── models/
│   ├── video_job.py       ← VideoJob SQLModel (JobStatus enum)
│   └── video_job_crud.py  ← create, get, list (func.count), update_status
└── core/                  ← Motor de geração (Bloco 0&1 e 2 concluídos)
    ├── interfaces.py      ← Protocols: VideoGenerator/ScriptGenerator/AudioSynthesizer
    ├── errors.py          ← GenerationError, ModelUnavailableError, GenerationTimeoutError, AssemblyError
    ├── fakes.py           ← FakeVideoGenerator/ScriptGenerator/AudioSynthesizer
    ├── factory.py         ← get_generator/get_script_generator/get_audio_synthesizer + fallback
    └── generators/        ← Implementações concretas (ADR-006)
        ├── ollama.py      ← OllamaScriptGenerator (roteiro via LLM local, httpx)
        └── piper.py       ← PiperAudioSynthesizer (TTS local via subprocess)

tests/
├── unit/          ← 38 testes (config, health, errors, video_job model)
└── integration/   ← 18 testes (API startup, video_job CRUD)

alembic/
└── versions/ea1fedd1683a_create_video_jobs_table.py
```

---

## Métricas de Qualidade (BUILD v0.2 — PR-2)

| Métrica | Valor |
|---|---|
| Testes totais | 142 passando (124 unit + 18 integration) |
| Cobertura | 99.22% (`src/core/*` = 100%) |
| ruff | ✅ 0 erros |
| mypy | ✅ 0 erros |

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
