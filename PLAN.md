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

## Resumo de Tasks

| Task | Descrição | Épico | Est. | Status |
|---|---|---|---|---|
| TASK-001 | Setup Python + pyproject.toml | E01 | 1h | ◻ Pendente |
| TASK-002 | Scaffold FastAPI | E01 | 2h | ◻ Pendente |
| TASK-003 | Modelos SQLite/SQLModel | E01 | 2h | ◻ Pendente |
| TASK-004 | CI/CD GitHub Actions | E01 | 1h | ◻ Pendente |
| TASK-005 | POST /jobs | E02 | 2h | ◻ Pendente |
| TASK-006 | GET /jobs/{id} | E02 | 1h | ◻ Pendente |
| TASK-007 | GET /jobs (lista) | E02 | 1h | ◻ Pendente |
| TASK-008 | GET /jobs/{id}/download | E02 | 1h | ◻ Pendente |
| TASK-009 | Interface VideoGenerator | E03 | 1h | ◻ Pendente |
| TASK-010 | Worker assíncrono | E03 | 3h | ◻ Pendente |
| TASK-011 | AnimateDiff (fallback) | E03 | 4h | ◻ Pendente |
| TASK-012 | Wan2.1 (primário) | E03 | 4h | ◻ Pendente |
| TASK-013 | Testes E2E | E06 | 2h | ◻ Pendente |
| TASK-014 | Logging + Métricas | E07 | 2h | ◻ Pendente |
| TASK-015 | Docker | E08 | 2h | ◻ Pendente |

**Total estimado:** ~29 horas de desenvolvimento

---

## Ordem de Execução Recomendada

```
Sprint 1 (v0.1 Fundação):
  TASK-001 → TASK-002 → TASK-003 → TASK-004
              └──────────────────────────────→ TASK-005
                                              → TASK-006
                                              → TASK-007
                                              → TASK-008

Sprint 2 (v0.2 Core):
  TASK-009 → TASK-010 → TASK-011 → TASK-012

Sprint 3 (v0.3 Qualidade + v1.0):
  TASK-013 → TASK-014 → TASK-015
```

---

## Regras desta fase (PLAN)

- Tasks devem ter estimativa ≤ 4h. Se maior → dividir.
- Toda task começa em branch `feature/task-XXX-nome`
- Nenhum código escrito sem task correspondente
- Critérios de aceitação definidos ANTES de começar a task
- Ao concluir uma task, atualizar este arquivo (status → ✅ Concluído)
