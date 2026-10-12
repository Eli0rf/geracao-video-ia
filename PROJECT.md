# Geração de Vídeo por IA

> **Versão:** 0.1.0 — Fase DEFINE  
> **Criado em:** 2026-10-12  
> **Status:** 🟡 Em definição

## Visão Geral

Sistema backend para geração de vídeos por Inteligência Artificial a partir de prompts de texto e/ou imagens. Utiliza modelos open-source de ponta (Wan2.1, CogVideoX, HunyuanVideo) com uma API REST em Python, desenvolvido com metodologia ágil, dupla verificação por IA e 100% gratuito.

## Objetivo

Criar uma plataforma extensível que:
1. Aceite prompts de texto/imagem via API REST
2. Execute modelos de geração de vídeo localmente (sem custo de API)
3. Retorne vídeos gerados com controle de qualidade
4. Seja auditável por múltiplas IAs para evitar alucinações
5. Cresça incrementalmente sem quebrar funcionalidades existentes

---

## Stack Tecnológica

### Backend
| Componente | Tecnologia | Versão | Motivo |
|---|---|---|---|
| Linguagem | Python | 3.13 | Ecossistema ML/AI maduro |
| API Framework | FastAPI | ^0.115 | Async nativo, OpenAPI auto-gerado |
| Banco de dados | SQLite + SQLModel | ^0.0.22 | Zero-config, free tier |
| Fila de tarefas | Celery + Redis (opcional) | ^5.4 | Processamento async de vídeos |
| Testes | pytest + pytest-asyncio | ^8 | Padrão Python |
| Linting | ruff + mypy | latest | Qualidade de código |

### Modelos de IA (open-source / gratuitos)
| Modelo | VRAM Mín. | Qualidade | Uso |
|---|---|---|---|
| **Wan2.1-T2V** | 8GB | ⭐⭐⭐⭐ | Texto → Vídeo, principal |
| **CogVideoX-5B** | 6GB | ⭐⭐⭐⭐ | Texto → Vídeo, alternativo |
| **HunyuanVideo** | 14GB | ⭐⭐⭐⭐⭐ | Cinematográfico, alta qualidade |
| **AnimateDiff** | 4GB | ⭐⭐⭐ | Fallback, hardware limitado |

### Infraestrutura CI/CD (gratuita)
| Ferramenta | Uso | Tier gratuito |
|---|---|---|
| GitHub | Repositório + Issues + PR | Ilimitado |
| GitHub Actions | CI/CD pipeline | 2.000 min/mês |
| HuggingFace Hub | Download de modelos | Gratuito |
| Ollama | Modelos de linguagem locais | Gratuito |

---

## Pipeline de Desenvolvimento

```
DEFINE → PLAN → BUILD → VERIFY → REVIEW → SHIP
```

| Fase | Atividade | Saída | Branch |
|---|---|---|---|
| DEFINE | Spec, PRD, arquitetura | PROJECT.md, AGENTS.md | `main` |
| PLAN | Tasks, épicos, critérios | PLAN.md, Issues | `feature/*` |
| BUILD | Implementação incremental | Código + testes | `feature/*` |
| VERIFY | Testes automatizados + 2 IAs | Relatório de qualidade | `feature/*` |
| REVIEW | Code review + QA gate | PR aprovado | `develop` |
| SHIP | Deploy + tag semântica | Release | `main` |

---

## Estratégia Dupla IA (Anti-Alucinação)

Para evitar alucinações e garantir qualidade, cada ciclo BUILD → VERIFY usa **duas IAs**:

```
IA-1 (Kiro/Claude) → Implementa código
     ↓
IA-2 (Gemini/GPT-4) → Revisa e questiona
     ↓
Testes automatizados → Validação objetiva
     ↓
Humano → Aprovação final
```

Os agentes estão configurados em `AGENTS.md` e `.kiro/skills/`.

---

## Estrutura do Projeto

```
geracao-video-ia/
├── .github/
│   └── workflows/          # CI/CD pipelines
├── .kiro/
│   └── skills/             # Skills para Kiro IDE
├── docs/
│   ├── adr/                # Architecture Decision Records
│   ├── PIPELINE.md         # Detalhamento do pipeline
│   └── CONSTRAINTS.md      # Padrões de qualidade
├── src/
│   ├── api/                # Endpoints FastAPI
│   ├── core/               # Lógica de negócio central
│   ├── models/             # Modelos de dados (SQLModel)
│   ├── services/           # Serviços de geração de vídeo
│   └── utils/              # Utilitários compartilhados
├── tests/
│   ├── unit/               # Testes unitários (80%)
│   ├── integration/        # Testes de integração (15%)
│   └── e2e/                # Testes end-to-end (5%)
├── scripts/                # Scripts de automação
├── references/             # Checklists e referências
├── outputs/                # Vídeos gerados (gitignored)
├── AGENTS.md               # Contexto para todas as IAs
├── CONTEXT.md              # Estado atual do projeto
├── CONSTRAINTS.md          # Restrições e qualidade
├── PROJECT.md              # Este arquivo
└── README.md               # Visão pública do projeto
```

---

## Épicos do Produto

### v0.1 — Fundação (DEFINE + PLAN)
- [ ] E01: Estrutura de projeto e CI/CD base
- [ ] E02: API REST com endpoints de geração

### v0.2 — Core (BUILD)
- [ ] E03: Integração com modelo Wan2.1
- [ ] E04: Fila de processamento assíncrono
- [ ] E05: Armazenamento e retrieval de vídeos

### v0.3 — Qualidade (VERIFY + REVIEW)
- [ ] E06: Suite de testes completa
- [ ] E07: Observabilidade e logging estruturado

### v1.0 — Produção (SHIP)
- [ ] E08: Deploy containerizado
- [ ] E09: Documentação completa

---

## Princípios de Desenvolvimento

1. **Spec antes de código** — nenhuma feature sem spec aprovada
2. **TDD** — Red → Green → Refactor
3. **Commits atômicos** — um commit por mudança lógica
4. **Feature flags** — novas features desativadas por padrão
5. **Retrocompatibilidade** — APIs existentes nunca quebram
6. **Dupla verificação** — toda lógica crítica revisada por 2 IAs
7. **Código como documentação** — nomes claros, sem comentários óbvios
8. **Gratuito por padrão** — zero dependência de serviços pagos

---

## Decisões Arquiteturais

Ver `docs/adr/` para Architecture Decision Records completos.

| ID | Decisão | Status |
|---|---|---|
| ADR-001 | Python 3.13 + FastAPI como base | ✅ Aceito |
| ADR-002 | SQLite para persistência inicial | ✅ Aceito |
| ADR-003 | Wan2.1 como modelo primário | ✅ Aceito |
| ADR-004 | Dupla IA para anti-alucinação | ✅ Aceito |
| ADR-005 | GitHub Actions para CI/CD gratuito | ✅ Aceito |

---

## Como Contribuir / Continuar

1. Leia `AGENTS.md` antes de qualquer sessão de trabalho
2. Verifique `CONTEXT.md` para o estado atual
3. Siga o pipeline: DEFINE → PLAN → BUILD → VERIFY → REVIEW → SHIP
4. Cada tarefa vira uma branch `feature/<nome-da-task>`
5. PR obrigatório mesmo para trabalho solo (rastreabilidade)

---

## Contato / Dono

- **Projeto iniciado:** 2026-10-12
- **Stack de IAs:** Kiro (primário) + Gemini/GPT (revisor)
