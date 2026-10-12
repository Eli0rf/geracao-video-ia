# CONTEXT.md — Estado do Projeto

> **Propósito:** Arquivo de contexto de sessão. Atualizado a cada sessão de trabalho.
> Lido por todas as IAs no início de cada sessão para retomar de onde parou.
>
> **Compatível com:** Kiro, Claude Code, Gemini CLI, Cursor, Copilot, Codex, ChatGPT

---

## Status Geral

| Campo | Valor |
|---|---|
| **Fase pipeline** | BUILD |
| **Fase anterior** | PLAN ✅ |
| **Próxima fase** | VERIFY |
| **Última atualização** | 2026-10-12 |
| **Branch ativa** | `develop` (após merge de docs/plan) |
| **Versão** | 0.1.0-alpha |

---

## Próxima Task a Executar

**TASK-001 — Setup do ambiente Python**

```bash
git checkout develop
git checkout -b feature/task-001-python-setup
```

Ver `PLAN.md` para critérios de aceitação completos.

---

## O Que Foi Feito

### Sessão 2026-10-12 — Fase DEFINE ✅
- [x] Análise do repositório `addyosmani/agent-skills`
- [x] Definição de stack tecnológica completa
- [x] Estrutura de diretórios criada
- [x] `PROJECT.md`, `AGENTS.md`, `CONTEXT.md`, `CONSTRAINTS.md`
- [x] `docs/PIPELINE.md` com pipeline DEFINE→SHIP
- [x] 5 ADRs (decisões arquiteturais)
- [x] `.github/workflows/ci.yml`
- [x] `.gitignore`
- [x] Commit inicial em `main` + branch `develop`

### Sessão 2026-10-12 — Fase PLAN ✅
- [x] Branch `docs/plan` criada
- [x] `PLAN.md` com 15 tasks, 4 milestones, critérios de aceitação detalhados
- [x] `pyproject.toml` com todas as dependências pinadas
- [x] `.env.example` com todas as variáveis documentadas
- [x] `Makefile` com comandos: install, run, test, lint, typecheck, ci, clean
- [x] `AGENTS.md` e `CONTEXT.md` atualizados para fase BUILD
- [x] Merge de `docs/plan` → `develop`

---

## Estado das Tasks

| Task | Status |
|---|---|
| TASK-001 Setup Python + pyproject.toml | ◻ Pendente |
| TASK-002 Scaffold FastAPI | ◻ Pendente |
| TASK-003 Modelos SQLite/SQLModel | ◻ Pendente |
| TASK-004 CI/CD GitHub Actions | ◻ Pendente |
| TASK-005 POST /jobs | ◻ Pendente |
| TASK-006 GET /jobs/{id} | ◻ Pendente |
| TASK-007 GET /jobs (lista) | ◻ Pendente |
| TASK-008 GET /jobs/{id}/download | ◻ Pendente |
| TASK-009 Interface VideoGenerator | ◻ Pendente |
| TASK-010 Worker assíncrono | ◻ Pendente |
| TASK-011 AnimateDiff (fallback) | ◻ Pendente |
| TASK-012 Wan2.1 (primário) | ◻ Pendente |
| TASK-013 Testes E2E | ◻ Pendente |
| TASK-014 Logging + Métricas | ◻ Pendente |
| TASK-015 Docker | ◻ Pendente |

---

## Arquivos-Chave

| Arquivo | Propósito |
|---|---|
| `PROJECT.md` | Visão geral, stack, épicos, princípios |
| `AGENTS.md` | Regras e contexto para IAs |
| `CONTEXT.md` | Estado atual da sessão (este arquivo) |
| `PLAN.md` | Todas as tasks com critérios de aceitação |
| `CONSTRAINTS.md` | Padrões de qualidade obrigatórios |
| `docs/PIPELINE.md` | Pipeline DEFINE→SHIP detalhado |
| `pyproject.toml` | Dependências Python pinadas |
| `.env.example` | Template de variáveis de ambiente |
| `Makefile` | Comandos de conveniência |

---

## Decisões da Fase PLAN

### Dependências pinadas (principais)
- `fastapi==0.115.5`
- `sqlmodel==0.0.22`
- `alembic==1.14.0`
- `pydantic-settings==2.6.1`
- `structlog==24.4.0`
- `pytest==8.3.3` + `pytest-asyncio==0.24.0`
- `ruff==0.8.0` + `mypy==1.13.0`

### Modelos de IA separados em `[ai]` extra
Torch, diffusers, transformers são pesados (~5GB). Instalados separadamente com `make install-ai`.

### Ordem de implementação decidida
TASK-001 → TASK-002 → TASK-003 → TASK-004 (paralelo possível após 001) → TASK-005~008 → TASK-009~012

---

## Bloqueios / Riscos

| Risco | Impacto | Mitigação |
|---|---|---|
| VRAM insuficiente para Wan2.1 | Alto | AnimateDiff como fallback (4GB) |
| GitHub Actions minutos esgotados | Médio | Testes locais obrigatórios |
| Modelos HuggingFace lentos para download | Baixo | Cache local em `~/.cache/huggingface` |

---

## Como Retomar em Uma Nova Sessão

1. Leia este arquivo (`CONTEXT.md`)
2. Leia `AGENTS.md` para as regras
3. Verifique a branch ativa: `git branch`
4. Veja a **próxima task** na seção acima
5. Leia os critérios de aceitação em `PLAN.md`

---

## Histórico de Sessões

| Data | Fase | O que foi feito |
|---|---|---|
| 2026-10-12 | DEFINE | Setup inicial, estrutura, documentação base |
| 2026-10-12 | PLAN | PLAN.md, pyproject.toml, .env.example, Makefile |
