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
| **Última atualização** | 2026-10-14 (E2E Docker validado: .mp4 real 3420 bytes) |
| **Branch ativa** | `develop` |
| **Versão** | 0.1.0-alpha |

---

## Próxima Task a Executar

**TASK-012 Wan2.1 (primário)** — próxima pendente do motor de geração (ver PLAN.md).

> ✅ **TASK-011 AnimateDiff concluída:** `AnimateDiffGenerator` (MPS/CPU) + 10 testes mockados; suite 205 passed, 2 skipped, cobertura 96%.
> ✅ **TASK-013 E2E validada em 2026-10-14:** `docker compose up -d --build` + `python scripts/run_e2e.py` → job `completed`, `.mp4` real (3420 bytes, `ftypisom`) em `outputs/videos/`.

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
| TASK-011 AnimateDiff (fallback) | ✅ Concluída | 15e54fc |
| TASK-012 Wan2.1 (primário) | ◻ Pendente | — |
| TASK-013 Testes E2E | ✅ Validada (E2E PASS 2026-10-14: job completed, .mp4 3420 bytes ftypisom) | 3bb133a |
| TASK-014 Logging + Métricas | ◻ Pendente | — |
| TASK-015 Docker | ✅ Concluída | 6114e95 (feat(docker): adiciona Dockerfile, docker-compose.yml e targets de containerização no Makefile) |
| TASK-016 OllamaScriptGenerator | ✅ Concluída | PR-2 (Bloco 2) |
| TASK-017 PiperAudioSynthesizer | ✅ Concluída | PR-2 (Bloco 2) |
| TASK-018 VideoAssembler (FFmpeg) | ✅ Concluída | PR-3 (Bloco 3) |
| TASK-019 VideoPipeline | ✅ Concluída | PR-4 (Bloco 4) |
| TASK-020 BackgroundDispatcher | ✅ Concluída | PR-4 (Bloco 4) |
| TASK-021 Frontend pixel art | ✅ Concluída | PR-5 (Bloco 5) |

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

### Sessão 2026-10-12 — BUILD v0.2 — Montagem FFmpeg (Bloco 3 / PR-3)
- **Config:** `ffmpeg_binary` + `ffmpeg_timeout_seconds` (ADR-007).
- **`VideoAssembler`** (`assembly/ffmpeg.py`): funções puras `build_concat_list`/`build_concat_command`/`build_mux_command`; `assemble()` em 2 passos (concat+normalização → mux áudio) via `subprocess.run([...], shell=False)`; `tempfile` com limpeza; erros → `AssemblyError`, timeout → `GenerationTimeoutError`.
- **CI:** `.github/workflows/ci.yml` instala `ffmpeg` (apt) antes dos testes de integração.
- **Testes:** `test_ffmpeg_assembler.py` (unit, sem binário — funções puras + `assemble` mockado) e `test_ffmpeg_assembly.py` (integração, `skipif` sem ffmpeg). 164 testes (146 unit + 18 integration, 2 skip).
- **Métricas:** `src/core/*` 100% cobertura; total 99.29%; ruff 0; mypy 0.
- **Próximo:** Bloco 4 (PR-4) — `VideoPipeline` + `JobProcessor` + `BackgroundTasksDispatcher`.

### Sessão 2026-10-13 — BUILD v0.2 — Pipeline + Worker (Bloco 4 / PR-4)
- **Protocol `Assembler`** adicionado em `interfaces.py` (desacopla o pipeline do `VideoAssembler` concreto).
- **`VideoPipeline`** (`pipeline.py`, TASK-019): orquestra Script→Audio→Clipes→Assembly; `concat_wav_files` puro (stdlib `wave`); temporário limpo em `try/finally` mesmo com erro.
- **`JobProcessor`** (`worker.py`, TASK-020): transições `pending→processing→completed/failed` com **sessão própria por job**, `asyncio.Semaphore` + `timeout` + `to_thread`; idempotente; `recover_stale_jobs` p/ jobs presos (lifespan).
- **`dispatcher.py`** (TASK-020): Protocol `JobDispatcher` + `BackgroundTasksDispatcher`.
- **API:** `post_job` agenda via `BackgroundTasks` mantendo 202; `deps.get_engine/get_job_processor`; `lifespan` de recuperação (gate `is_testing` + try/except).
- **Testes:** `test_pipeline`, `test_worker` (engine em arquivo p/ concorrência), `test_dispatcher`, `test_jobs_dispatch` (integração). 192 testes (174 unit + 18 integration).
- **Métricas:** total 99% cobertura; ruff 0; mypy 0 (27 arquivos).
- **Validação:** smoke de integração real confirmou wiring completo (factory → pipeline → worker → banco → GET). Sem FFmpeg local → jobs `failed` (esperado); caminho `completed` coberto por fakes.
### Sessão 2026-10-13 — BUILD v0.2 — Frontend pixel art (Bloco 5 / PR-5)
- **`static/`** (TASK-021): `index.html` (fliperama 8-bits, fonte 'Press Start 2P' via Google Fonts), `style.css` (botões chunky 3D sólidos, fundo escuro + neon, scanlines CRT, GAME OVER tremendo), `app.js` (vanilla JS: `POST /api/v1/jobs` → tela de loading `[■■■□□□]` → polling 3s em `GET /api/v1/jobs/{id}` → estados pending/processing/failed/completed; `<video controls>` em completed).
- **API:** `src/api/main.py` monta `static/` em `/` via `StaticFiles(html=True)` **após** `/health` (catch-all não sombreia `/api/v1/*`); `STATIC_DIR` absoluto (robusto a CWD); branch `else` com `pragma: no cover`.
- **Testes:** `tests/integration/test_frontend.py` — `GET /` (200 + marcador pixel), `/style.css`, `/app.js`, regressão (`/health` + `/api/v1/jobs` intactos).
- **Validação:** smoke serve o index e as rotas da API respondem junto ao mount. 195 testes passando (171 unit + 24 integration, 2 skip sem ffmpeg).
- **Próximo:** Bloco 6 — TASK-013 E2E, milestones v0.3/v0.4.

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
└── core/                  ← Motor de geração (Blocos 0–4 concluídos)
    ├── interfaces.py      ← Protocols: Video/Script/Audio/Assembler
    ├── errors.py          ← GenerationError, ModelUnavailableError, GenerationTimeoutError, AssemblyError
    ├── fakes.py           ← FakeVideoGenerator/ScriptGenerator/AudioSynthesizer
    ├── factory.py         ← get_generator/get_script_generator/get_audio_synthesizer + fallback
    ├── pipeline.py        ← VideoPipeline (Script→Audio→Clipes→Assembly) + concat_wav_files
    ├── worker.py          ← JobProcessor (transições de status) + recover_stale_jobs
    ├── dispatcher.py      ← Protocol JobDispatcher + BackgroundTasksDispatcher
    ├── generators/        ← Implementações concretas (ADR-006)
    │   ├── ollama.py      ← OllamaScriptGenerator (roteiro via LLM local, httpx)
    │   └── piper.py       ← PiperAudioSynthesizer (TTS local via subprocess)
    └── assembly/          ← Montagem do vídeo final (ADR-007)
        └── ffmpeg.py      ← VideoAssembler (concat demuxer + mux áudio, subprocess)

tests/
├── unit/          ← 38 testes (config, health, errors, video_job model)
└── integration/   ← 18 testes (API startup, video_job CRUD)

alembic/
└── versions/ea1fedd1683a_create_video_jobs_table.py
```

---

## Métricas de Qualidade (BUILD v0.2 — PR-5)

| Métrica | Valor |
|---|---|
| Testes totais | 195 passando (171 unit + 24 integration, 2 skip sem ffmpeg) |
| Cobertura | 99% (`src/core/*` 100%) |
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
4. Próxima task: **TASK-013** (Testes E2E + `scripts/run_e2e.py`) — já implementado; próximo passo é merge para `main`.

---

## Histórico de Sessões

| Data | Fase | O que foi feito |
|---|---|---|
| 2026-10-12 | DEFINE | Setup inicial, estrutura, documentação base |
| 2026-10-12 | PLAN | PLAN.md, pyproject.toml, .env.example, Makefile |
| 2026-10-12 | INFRA | Dupla IA configurada (scripts/validate.py + Gemini) |
| 2026-10-12 | BUILD v0.1 | TASK-001 a TASK-004 — fundação completa |
