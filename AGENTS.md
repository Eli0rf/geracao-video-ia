# AGENTS.md — Geração de Vídeo por IA

> Este arquivo é lido automaticamente por: Kiro, Claude Code, Codex, Gemini CLI, Cursor, Copilot e outros agentes de IA compatíveis com a convenção AGENTS.md.
>
> **Última atualização:** 2026-10-12 | **Fase atual:** DEFINE

---

## Contexto do Projeto

Sistema de geração de vídeo por IA com API REST em Python. Objetivo: receber prompts de texto/imagem e retornar vídeos gerados por modelos open-source (Wan2.1, CogVideoX, HunyuanVideo).

**Repositório:** `~/geracao-video-ia`  
**Fase pipeline:** `DEFINE → [PLAN] → BUILD → VERIFY → REVIEW → SHIP`  
**Fase atual:** DEFINE (definição de arquitetura e documentação)

---

## Regras Obrigatórias para Todo Agente

### 1. Leia antes de escrever
- Sempre leia o arquivo relevante antes de modificá-lo
- Nunca assuma o conteúdo de um arquivo sem lê-lo
- Verifique `CONTEXT.md` no início de cada sessão

### 2. Siga o pipeline
```
DEFINE → PLAN → BUILD → VERIFY → REVIEW → SHIP
```
- Não pule fases
- Cada fase tem entregáveis definidos em `docs/PIPELINE.md`
- Documente o que foi feito em `CONTEXT.md`

### 3. Commits atômicos
- Um commit por mudança lógica
- Formato: `tipo(escopo): descrição` (Conventional Commits)
- Tipos: `feat`, `fix`, `test`, `docs`, `refactor`, `chore`
- Exemplos:
  - `feat(api): adiciona endpoint POST /generate`
  - `test(services): adiciona testes unitários para VideoService`
  - `docs(adr): ADR-006 escolha de fila de tarefas`

### 4. Branches obrigatórias
```
main          → código estável, releases
develop       → integração contínua
feature/*     → novas funcionalidades
fix/*         → correções de bugs
docs/*        → apenas documentação
```
- Nunca faça push direto em `main`
- PRs obrigatórios para `develop` → `main`

### 5. TDD é mandatório
- Escreva o teste ANTES do código (Red → Green → Refactor)
- Todo código novo precisa de teste
- Cobertura mínima: 80% para unit, 15% para integration
- Rodar testes: `pytest tests/` antes de qualquer commit

### 6. Sem dependências pagas
- Zero APIs pagas (OpenAI, Replicate, etc.)
- Modelos de IA: apenas HuggingFace Hub (gratuito) ou local
- Infraestrutura: GitHub Actions free tier (2000 min/mês)

---

## Arquitetura

```
geracao-video-ia/
├── src/
│   ├── api/          → FastAPI routers + schemas Pydantic
│   ├── core/         → lógica de negócio (sem dependências externas)
│   ├── models/       → SQLModel ORM + migrations
│   ├── services/     → integração com modelos de IA
│   └── utils/        → helpers, logging, config
├── tests/
│   ├── unit/         → 80% da cobertura, sem I/O real
│   ├── integration/  → 15%, com banco de dados real
│   └── e2e/          → 5%, com API rodando
├── docs/adr/         → Architecture Decision Records
├── .kiro/skills/     → Skills customizadas para Kiro
├── .github/workflows/→ CI/CD GitHub Actions
└── outputs/          → Vídeos gerados (gitignored)
```

### Stack
- **Python 3.13** + **FastAPI** + **SQLite/SQLModel**
- **Wan2.1** (modelo primário de geração)
- **pytest** para testes
- **ruff** + **mypy** para qualidade

---

## Estratégia Anti-Alucinação (2 IAs)

Este projeto usa **dois agentes de IA** em cada ciclo de desenvolvimento:

| Papel | Agente | Responsabilidade |
|---|---|---|
| **Implementador** | Kiro (Claude) | Escreve código, testes, docs |
| **Revisor** | Gemini / GPT-4o | Questiona, revisa, detecta erros |

### Protocolo de revisão
1. IA-1 implementa uma task
2. IA-1 roda os testes: `pytest tests/`
3. IA-1 documenta o que foi feito em `CONTEXT.md`
4. IA-2 lê `CONTEXT.md` e revisa o código implementado
5. IA-2 sinaliza problemas com `⚠️ REVISOR:` no output
6. Humano aprova ou solicita correções

---

## Estado Atual do Projeto

Ver `CONTEXT.md` para o estado detalhado de cada sessão.

**Fase:** DEFINE  
**Próximo passo:** Criar PLAN.md com épicos e tasks da v0.1

---

## Skills Disponíveis

Skills do `agent-skills` instaladas em `.kiro/skills/`:

| Skill | Quando usar |
|---|---|
| `spec-driven-development` | Iniciar qualquer nova feature |
| `planning-and-task-breakdown` | Fase PLAN |
| `incremental-implementation` | Fase BUILD |
| `test-driven-development` | Sempre que escrever código |
| `code-review-and-quality` | Antes de qualquer PR |
| `git-workflow-and-versioning` | Sempre |
| `doubt-driven-development` | Decisões críticas ou irreversíveis |

---

## Comandos Úteis

```bash
# Rodar testes
pytest tests/ -v

# Verificar cobertura
pytest tests/ --cov=src --cov-report=html

# Lint e tipagem
ruff check src/ tests/
mypy src/

# Rodar API local
uvicorn src.api.main:app --reload

# Iniciar nova feature
git checkout -b feature/<nome>
```

---

## O Que NÃO Fazer

- ❌ Não commite em `main` diretamente
- ❌ Não pule testes para "entregar mais rápido"
- ❌ Não use APIs pagas sem aprovação explícita
- ❌ Não quebre endpoints/schemas existentes sem deprecation path
- ❌ Não crie arquivos de configuração com secrets
- ❌ Não assuma que o código está correto sem rodar os testes
- ❌ Não faça PRs com mais de ~200 linhas (divida em slices menores)
