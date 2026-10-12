# PLAN.md — Plano de Desenvolvimento

> **Fase:** PLAN  
> **Versão:** 0.1.0  
> **Criado em:** 2026-10-12  
> **Status:** 🟡 Ativo  
> **Próxima fase:** BUILD

---

## Visão do Produto

Sistema de geração de vídeo por IA com API REST em Python. Recebe prompts de texto/imagem e retorna vídeos gerados por modelos open-source locais — sem custo de API, sem dependências pagas.

---

## Milestones

```
v0.1 — Fundação      → Infra, API base, configuração
v0.2 — Core          → Integração com modelos de IA
v0.3 — Qualidade     → Testes, observabilidade
v1.0 — Produção      → Containerização, docs finais
```

---

## v0.1 — Fundação

**Objetivo:** Projeto rodando localmente com API funcional, CI/CD ativo e estrutura de código sólida.

---

### ÉPICO E01 — Ambiente e Infraestrutura Base

**Meta:** Desenvolvedor (humano ou IA) consegue clonar o repo, instalar dependências e rodar a API em < 5 minutos.

#### TASK-001 — Setup do ambiente Python

**Estimativa:** 1h  
**Branch:** `feature/task-001-python-setup`  
**Dependências:** nenhuma

**Descrição:**  
Configurar `pyproject.toml` com todas as dependências pinadas, `Makefile` com comandos de conveniência e validar que o ambiente funciona do zero.

**Critérios de aceitação:**
- [ ] `pyproject.toml` com todas as deps pinadas (sem ranges abertos `^` para deps críticas)
- [ ] `make install` cria venv e instala tudo
- [ ] `make test` roda pytest e retorna verde (mesmo sem testes ainda)
- [ ] `make lint` roda ruff sem erros
- [ ] `make typecheck` roda mypy sem erros
- [ ] `.env.example` com todas as variáveis necessárias documentadas
- [ ] `README.md` atualizado com Quick Start de 3 comandos

**Testes necessários:**
- `tests/unit/test_config.py` — valida que configurações carregam corretamente do `.env`

**Definition of Done:**
- [ ] Todos os critérios de aceitação atendidos
- [ ] `pytest tests/unit/test_config.py` verde
- [ ] PR revisado e aprovado

---

#### TASK-002 — Scaffold da aplicação FastAPI

**Estimativa:** 2h  
**Branch:** `feature/task-002-fastapi-scaffold`  
**Dependências:** TASK-001

**Descrição:**  
Criar a estrutura base da aplicação FastAPI com rotas organizadas, middleware de logging, tratamento de erros padronizado (RFC 7807) e healthcheck.

**Critérios de aceitação:**
- [ ] `uvicorn src.api.main:app --reload` sobe sem erros
- [ ] `GET /health` retorna `{"status": "ok", "version": "0.1.0"}`
- [ ] `GET /docs` abre Swagger UI com a documentação
- [ ] Erros retornam formato RFC 7807: `{"type", "title", "status", "detail"}`
- [ ] Logging estruturado (JSON) em todas as requests
- [ ] Estrutura de routers: `src/api/v1/` com prefixo `/api/v1`

**Testes necessários:**
- `tests/unit/test_api_health.py` — testa endpoint `/health`
- `tests/unit/test_error_handlers.py` — testa formato de erro RFC 7807
- `tests/integration/test_api_startup.py` — valida que a app sobe corretamente

**Definition of Done:**
- [ ] Todos os critérios de aceitação atendidos
- [ ] `pytest tests/` verde com cobertura ≥ 80%
- [ ] `ruff check src/` sem erros
- [ ] `mypy src/` sem erros
- [ ] PR revisado por IA-2

---

#### TASK-003 — Modelo de dados e banco SQLite

**Estimativa:** 2h  
**Branch:** `feature/task-003-database-models`  
**Dependências:** TASK-001

**Descrição:**  
Criar os modelos SQLModel para jobs de geração de vídeo e configurar criação automática do banco.

**Entidades:**
```
VideoJob
  id: uuid
  status: enum (pending | processing | completed | failed)
  prompt: str
  model: str (wan2.1 | cogvideox | hunyuan | animatediff)
  output_path: str | None
  error_message: str | None
  created_at: datetime
  updated_at: datetime
  duration_seconds: int (default: 5)
  width: int (default: 848)
  height: int (default: 480)
```

**Critérios de aceitação:**
- [ ] Banco SQLite criado automaticamente na primeira execução
- [ ] Modelo `VideoJob` com todos os campos acima
- [ ] CRUD básico: create, get_by_id, list, update_status
- [ ] Migrations funcionando (Alembic configurado)
- [ ] Banco de testes separado (não polui o banco de dev)

**Testes necessários:**
- `tests/unit/test_video_job_model.py` — testa criação, validação de campos
- `tests/integration/test_video_job_crud.py` — testa CRUD real com SQLite

**Definition of Done:**
- [ ] Todos os critérios de aceitação atendidos
- [ ] `pytest tests/` verde
- [ ] Sem migration pendente após rodar `alembic upgrade head`

---

#### TASK-004 — CI/CD completo no GitHub Actions

**Estimativa:** 1h  
**Branch:** `feature/task-004-cicd`  
**Dependências:** TASK-001, TASK-002

**Descrição:**  
Finalizar e testar o workflow de CI para garantir que roda em todo push/PR.

**Critérios de aceitação:**
- [ ] CI passa em todo push para `feature/*`, `develop`, `main`
- [ ] Stages: lint → typecheck → unit tests → integration tests
- [ ] Badge de status no README
- [ ] Falha de qualquer stage bloqueia merge
- [ ] Cache de dependências pip ativo (builds rápidos)
- [ ] Tempo total do pipeline < 3 minutos

**Testes necessários:**
- Validação manual: criar PR e verificar que o CI dispara e passa

**Definition of Done:**
- [ ] CI verde em pelo menos 2 PRs consecutivos
- [ ] Badge atualizado no README

---

### ÉPICO E02 — API REST de Geração

**Meta:** Cliente consegue submeter um prompt via API, acompanhar o status do job e baixar o vídeo quando pronto.

---

#### TASK-005 — Endpoint POST /api/v1/jobs (submeter geração)

**Estimativa:** 2h  
**Branch:** `feature/task-005-post-jobs`  
**Dependências:** TASK-002, TASK-003

**Descrição:**  
Endpoint para criar um novo job de geração de vídeo. O vídeo é gerado de forma **assíncrona** — o endpoint apenas cria o job e retorna imediatamente com status `pending`.

**Request:**
```json
POST /api/v1/jobs
{
  "prompt": "A cat walking on the moon",
  "model": "wan2.1",
  "duration_seconds": 5,
  "width": 848,
  "height": 480
}
```

**Response 202 Accepted:**
```json
{
  "id": "uuid",
  "status": "pending",
  "prompt": "A cat walking on the moon",
  "model": "wan2.1",
  "created_at": "2026-10-12T11:00:00Z"
}
```

**Critérios de aceitação:**
- [ ] Retorna 202 (não 200) com o job criado
- [ ] Valida campos obrigatórios (prompt não vazio)
- [ ] Valida enum `model` (apenas valores permitidos)
- [ ] Valida dimensões (múltiplos de 8, máx 1920x1080)
- [ ] Job salvo no banco com status `pending`
- [ ] Retorna 422 com detalhe para inputs inválidos

**Testes necessários:**
- `tests/unit/test_jobs_endpoint.py`:
  - POST com dados válidos → 202
  - POST com prompt vazio → 422
  - POST com modelo inválido → 422
  - POST com dimensão inválida → 422

**Definition of Done:**
- [ ] Todos os critérios de aceitação atendidos
- [ ] 4 testes passando
- [ ] Schema Pydantic documentado no Swagger

---

#### TASK-006 — Endpoint GET /api/v1/jobs/{id} (status do job)

**Estimativa:** 1h  
**Branch:** `feature/task-006-get-job`  
**Dependências:** TASK-005

**Descrição:**  
Endpoint para consultar o status de um job de geração.

**Response 200:**
```json
{
  "id": "uuid",
  "status": "processing | completed | failed | pending",
  "prompt": "...",
  "model": "wan2.1",
  "output_url": "/api/v1/jobs/{id}/download",
  "error_message": null,
  "created_at": "...",
  "updated_at": "...",
  "duration_seconds": 5
}
```

**Critérios de aceitação:**
- [ ] Retorna 200 com todos os campos do job
- [ ] Retorna 404 com RFC 7807 se job não existir
- [ ] `output_url` preenchido apenas quando `status == "completed"`
- [ ] `error_message` preenchido apenas quando `status == "failed"`

**Testes necessários:**
- `tests/unit/test_get_job_endpoint.py`:
  - GET com ID válido → 200
  - GET com ID inexistente → 404
  - GET de job completo → output_url preenchido
  - GET de job falho → error_message preenchido

---

#### TASK-007 — Endpoint GET /api/v1/jobs (listar jobs)

**Estimativa:** 1h  
**Branch:** `feature/task-007-list-jobs`  
**Dependências:** TASK-006

**Descrição:**  
Endpoint para listar todos os jobs com paginação.

**Query params:** `?page=1&page_size=20&status=completed`

**Response 200:**
```json
{
  "items": [...],
  "total": 42,
  "page": 1,
  "page_size": 20,
  "pages": 3
}
```

**Critérios de aceitação:**
- [ ] Paginação com `page` e `page_size` (máx 100)
- [ ] Filtro por `status` (opcional)
- [ ] Ordenação por `created_at` desc (mais recente primeiro)
- [ ] Retorna lista vazia (não 404) quando sem resultados

**Testes necessários:**
- `tests/unit/test_list_jobs_endpoint.py`:
  - Lista vazia → `{"items": [], "total": 0}`
  - Paginação → página 2 com `page_size=1` retorna item correto
  - Filtro por status → apenas jobs com status correto

---

#### TASK-008 — Endpoint GET /api/v1/jobs/{id}/download (download do vídeo)

**Estimativa:** 1h  
**Branch:** `feature/task-008-download`  
**Dependências:** TASK-006

**Descrição:**  
Endpoint para baixar o vídeo gerado.

**Critérios de aceitação:**
- [ ] Retorna o arquivo de vídeo como `FileResponse`
- [ ] Content-Type: `video/mp4`
- [ ] Retorna 404 se job não existe
- [ ] Retorna 409 se job não está `completed` (ainda processando ou falhou)
- [ ] Retorna 410 Gone se o arquivo foi removido do disco

**Testes necessários:**
- `tests/unit/test_download_endpoint.py`:
  - Job completo com arquivo → 200 + video/mp4
  - Job pendente → 409
  - Job inexistente → 404

---

## v0.2 — Core (Integração com IA)

> **Nota:** Esta milestone só começa após v0.1 **completamente** aprovada e mergada em `main`.

---

### ÉPICO E03 — Integração com Modelo de IA

#### TASK-009 — Interface abstrata VideoGenerator

**Estimativa:** 1h  
**Branch:** `feature/task-009-video-generator-interface`

**Descrição:**  
Criar a interface/protocolo abstrato que todos os modelos de IA devem implementar. Garante extensibilidade futura.

```python
class VideoGenerator(Protocol):
    def generate(self, prompt: str, **kwargs) -> Path: ...
    def is_available(self) -> bool: ...
    @property
    def name(self) -> str: ...
    @property
    def min_vram_gb(self) -> int: ...
```

**Critérios de aceitação:**
- [ ] Interface `VideoGenerator` definida em `src/core/interfaces.py`
- [ ] Mock `FakeVideoGenerator` implementado para testes
- [ ] Factory `get_generator(model_name)` que retorna a implementação correta
- [ ] Fallback automático para AnimateDiff se modelo primário não disponível

---

#### TASK-010 — Worker assíncrono de processamento

**Estimativa:** 3h  
**Branch:** `feature/task-010-async-worker`

**Descrição:**  
Worker que consome jobs `pending` do banco e executa a geração usando o `VideoGenerator`.

**Fluxo:**
```
job.status = pending
    ↓
worker pega job → job.status = processing
    ↓
generator.generate(prompt) → salva arquivo
    ↓
job.status = completed + output_path
    (ou failed + error_message)
```

**Critérios de aceitação:**
- [ ] Worker processa um job por vez (sem concorrência de geração)
- [ ] Atualiza status do job em tempo real
- [ ] Captura exceções e marca job como `failed` com mensagem
- [ ] Log estruturado de início, fim e duração de cada job
- [ ] Timeout configurável (padrão: 10 min)

---

#### TASK-011 — Implementação AnimateDiff (modelo fallback)

**Estimativa:** 4h  
**Branch:** `feature/task-011-animatediff`

**Descrição:**  
Implementar `AnimateDiffGenerator` como primeiro modelo real. Escolhido como fallback por exigir menos VRAM (4GB).

**Critérios de aceitação:**
- [ ] Implementa interface `VideoGenerator`
- [ ] Baixa pesos do HuggingFace Hub automaticamente
- [ ] Gera vídeo MP4 dado um prompt
- [ ] Salva em `outputs/videos/{job_id}.mp4`
- [ ] `is_available()` retorna False se GPU/VRAM insuficiente
- [ ] Testes com mock do modelo (sem download real no CI)

---

#### TASK-012 — Implementação Wan2.1 (modelo primário)

**Estimativa:** 4h  
**Branch:** `feature/task-012-wan21`

**Dependências:** TASK-011 (padrão estabelecido)

**Critérios de aceitação:**
- [ ] Implementa interface `VideoGenerator`
- [ ] Integração via HuggingFace `diffusers`
- [ ] Suporte a text-to-video
- [ ] `is_available()` retorna False se VRAM < 8GB
- [ ] Testes com mock do modelo

---

## v0.2 — Core: Motor de geração (`src/core/`)

> **Nota de revisão (2026-10-12):** Novas tasks (016–020) acrescentadas para
> cobrir o **motor de geração completo** em `src/core/`: roteiro/áudio
> (ADR-006), montagem FFmpeg (ADR-007) e execução em background (ADR-008).
> Esta milestone depende de TASK-009~012 (interface, worker, modelos de vídeo).

### ÉPICO E04 — Roteiro e áudio (ADR-006)

#### TASK-016 — OllamaScriptGenerator (roteiro via LLM local)

**Estimativa:** 3h  
**Branch:** `feature/task-016-ollama-script`  
**Dependências:** TASK-009 (interface `ScriptGenerator`)

**Descrição:**  
Implementar `ScriptGenerator` concreto que chama Ollama local via `httpx`
(`POST /api/generate`), valida a resposta JSON com Pydantic e produz um
`Script` (lista de `Scene` com narração + prompt visual). `is_available()`
faz health-check em `/api/tags`.

**Critérios de aceitação:**
- [ ] Implementa `ScriptGenerator` de `src/core/interfaces.py`
- [ ] Timeout e retry configuráveis; falha → `GenerationError`
- [ ] Fallback para `FakeScriptGenerator` quando Ollama indisponível
- [ ] Testes unitários com `httpx.MockTransport` (sem rede real)

---

#### TASK-017 — PiperAudioSynthesizer (TTS local)

**Estimativa:** 3h  
**Branch:** `feature/task-017-piper-audio`  
**Dependências:** TASK-009 (interface `AudioSynthesizer`)

**Descrição:**  
Implementar `AudioSynthesizer` concreto que invoca o binário `piper` via
`subprocess` (lista de args, nunca shell) para sintetizar narração em `.wav`.
`is_available()` verifica binário `piper` + arquivo de voz.

**Critérios de aceitação:**
- [ ] Implementa `AudioSynthesizer` de `src/core/interfaces.py`
- [ ] `subprocess.run([...], shell=False)` (sem injeção de comando)
- [ ] Timeout de subprocess configurável
- [ ] `is_available()` False se binário/voz ausentes
- [ ] Fallback para `FakeAudioSynthesizer`
- [ ] Testes unitários com `subprocess` mockado (sem binário real)

---

### ÉPICO E05 — Montagem e orquestração (ADR-007, ADR-008)

#### TASK-018 — VideoAssembler (montagem FFmpeg)

**Estimativa:** 3h  
**Branch:** `feature/task-018-ffmpeg-assembler`  
**Dependências:** TASK-009, TASK-016, TASK-017

**Descrição:**  
Implementar a montagem do vídeo final em `src/core/assembly/ffmpeg.py`:
concatena os clipes das cenas (concat demuxer), faz mux do áudio da
narração e normaliza resolução/fps, tudo via `subprocess` + FFmpeg.

**Critérios de aceitação:**
- [ ] `VideoAssembler.assemble(clips, audio, out_path, width, height)`
- [ ] Concat demuxer (`-f concat`) + mux de áudio (`-shortest`, `-c:a aac`)
- [ ] Construção de comando como função pura testável
- [ ] Erros → `AssemblyError`
- [ ] Testes: construção de comando (puro) + execução real com `skipif`
      quando FFmpeg ausente

---

#### TASK-019 — VideoPipeline (orquestrador de estágios)

**Estimativa:** 3h  
**Branch:** `feature/task-019-video-pipeline`  
**Dependências:** TASK-009, TASK-016, TASK-017, TASK-018

**Descrição:**  
Criar `src/core/pipeline.py` (`VideoPipeline`) que orquestra o fluxo
completo: roteiro → áudio por cena → clipes de vídeo por cena → montagem
final em `outputs/videos/{job_id}.mp4`. Todas as dependências
(`ScriptGenerator`, `AudioSynthesizer`, `VideoGenerator`, `VideoAssembler`)
entram por injeção, permitindo testar com fakes.

**Critérios de aceitação:**
- [ ] `VideoPipeline.run(job) -> Path` (caminho do mp4 final)
- [ ] Dependências injetadas (fakes nos testes de unidade)
- [ ] Limpeza de arquivos temporários em caso de falha
- [ ] Testes unitários com fakes (integração do pipeline, sem I/O real)

---

#### TASK-020 — BackgroundTasksDispatcher + integração no POST /jobs

**Estimativa:** 3h  
**Branch:** `feature/task-020-background-dispatcher`  
**Dependências:** TASK-019

**Descrição:**  
Criar `src/core/dispatcher.py` (`JobDispatcher` Protocol +
`BackgroundTasksDispatcher`) e `src/core/worker.py` (`JobProcessor`), e
integrar o disparo no endpoint `POST /api/v1/jobs` via `BackgroundTasks`.
O endpoint continua retornando 202; o processamento ocorre em background.
`JobProcessor` aplica semáforo (`max_concurrent_jobs`), timeout
(`job_timeout_seconds`) e atualiza status do job no banco.

**Critérios de aceitação:**
- [ ] `JobDispatcher` Protocol + `BackgroundTasksDispatcher`
- [ ] `JobProcessor.process(job_id)` com `asyncio.Semaphore` + timeout
- [ ] Transições: `pending → processing → completed/failed`
- [ ] Idempotência (ignora job que não está `pending`)
- [ ] Recuperação de jobs órfãos no `lifespan` da app
- [ ] `POST /jobs` integrado; contrato HTTP (202) preservado
- [ ] Testes de integração: job processa end-to-end com fakes

---

## v0.3 — Qualidade

### ÉPICO E06 — Suite de testes completa

#### TASK-013 — Testes E2E da API completa

**Estimativa:** 2h  
**Branch:** `feature/task-013-e2e-tests`

**Descrição:**  
Testes que cobrem o fluxo completo: submeter job → checar status → baixar vídeo, usando `FakeVideoGenerator`.

---

### ÉPICO E07 — Observabilidade

#### TASK-014 — Logging estruturado e métricas

**Estimativa:** 2h  
**Branch:** `feature/task-014-observability`

**Critérios de aceitação:**
- [ ] Todos os logs em JSON com campos: `timestamp`, `level`, `message`, `job_id`, `duration_ms`
- [ ] Métricas básicas: jobs totais, jobs por status, tempo médio de geração
- [ ] Endpoint `GET /metrics` no formato Prometheus

---

## v1.0 — Produção

### ÉPICO E08 — Containerização

#### TASK-015 — Dockerfile e docker-compose

**Estimativa:** 2h  
**Branch:** `feature/task-015-docker`

**Critérios de aceitação:**
- [ ] `Dockerfile` multi-stage (build + runtime)
- [ ] `docker-compose.yml` com API + volumes para outputs e modelos
- [ ] `docker compose up` sobe a stack completa
- [ ] Imagem final < 2GB (sem pesos de modelos)

---

## Resumo de Tasks (Revisado — Abordagem Híbrida)

> **Revisão 2026-10-12:** Tasks agrupadas por bloco lógico para reduzir overhead
> de sessão (menos branches, menos commits, menos chamadas ao validador Gemini).
> Sessões divididas em: RED (testes) → GREEN+COMMIT → validar+merge.

| Bloco | Tasks | Branch | Estimativa | Status |
|---|---|---|---|---|
| E01-setup | TASK-001~004 | concluído | — | ✅ |
| E02-api-endpoints | TASK-005~008 | `feature/e02-api-endpoints` | 4h | ◻ Pendente |
| E03-video-generator | TASK-009~012 | `feature/e03-video-generator` | 8h | ◻ Pendente |
| E04-roteiro-audio | TASK-016~017 | `feature/e04-roteiro-audio` | 6h | ◻ Pendente |
| E05-core-engine | TASK-018~020 | `feature/e05-core-engine` | 9h | ◻ Pendente |
| E06-e2e-tests | TASK-013 | `feature/e06-e2e-tests` | 2h | ◻ Pendente |
| E07-observability | TASK-014 | `feature/e07-observability` | 2h | ◻ Pendente |
| E08-docker | TASK-015 | `feature/e08-docker` | 2h | ◻ Pendente |

**Total restante estimado:** ~33h

### Regras da abordagem híbrida
- 1 branch por bloco lógico (não por task individual)
- 1 validação Gemini por bloco (não por arquivo)
- Sessões divididas: RED numa sessão → GREEN+commit noutra
- Commits atômicos por lógica dentro do bloco

---

## Ordem de Execução (Revisada)

```
Sprint 1 (v0.1 Fundação) ✅ CONCLUÍDO
  E01-setup: TASK-001 → TASK-002 → TASK-003 → TASK-004

Sprint 2 (v0.2 Core API):
  E02-api-endpoints  → todos os 4 endpoints juntos
  E03-video-generator → interface + worker + AnimateDiff + Wan2.1
  E04-roteiro-audio  → OllamaScriptGenerator + PiperAudioSynthesizer
  E05-core-engine    → VideoAssembler + VideoPipeline + BackgroundDispatcher

Sprint 3 (v0.3 Qualidade + v1.0):
  E06-e2e-tests → E07-observability → E08-docker
```

---

## Regras desta fase (PLAN)

- Tasks devem ter estimativa ≤ 4h. Se maior → dividir.
- Toda task começa em branch `feature/task-XXX-nome`
- Nenhum código escrito sem task correspondente
- Critérios de aceitação definidos ANTES de começar a task
- Ao concluir uma task, atualizar este arquivo (status → ✅ Concluído)
