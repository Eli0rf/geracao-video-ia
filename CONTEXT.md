# CONTEXT.md — Estado do Projeto

> **Propósito:** Arquivo de contexto de sessão. Atualizado a cada sessão de trabalho.
> Lido por todas as IAs no início de cada sessão para retomar de onde parou.
>
> **Compatível com:** Kiro, Claude Code, Gemini CLI, Cursor, Copilot, Codex, ChatGPT

---

## Status Geral

| Campo | Valor |
|---|---|
| **Fase pipeline** | DEFINE |
| **Próxima fase** | PLAN |
| **Última atualização** | 2026-10-12 |
| **Branch ativa** | `main` |
| **Versão** | 0.1.0-alpha |

---

## O Que Foi Feito (Sessão 2026-10-12)

### ✅ Concluído
- [x] Análise do repositório `addyosmani/agent-skills` (25 skills, pipeline DEFINE→SHIP)
- [x] Definição de stack tecnológica completa
- [x] Estrutura de diretórios criada
- [x] `PROJECT.md` — contexto completo do projeto
- [x] `AGENTS.md` — contexto para todas as IAs
- [x] `CONTEXT.md` — este arquivo
- [x] `CONSTRAINTS.md` — padrões de qualidade
- [x] `docs/PIPELINE.md` — pipeline detalhado
- [x] `docs/adr/ADR-001` até `ADR-005` — decisões arquiteturais
- [x] `.gitignore` configurado
- [x] `.github/workflows/ci.yml` — pipeline CI inicial
- [x] Git configurado com branches `main` e `develop`

### 🔲 Próximos Passos (Fase PLAN)
- [ ] Criar `PLAN.md` com épicos e tasks da v0.1
- [ ] Abrir Issues no GitHub para cada épico
- [ ] Definir critérios de aceitação para E01 e E02
- [ ] Setup do ambiente Python (pyproject.toml, venv)
- [ ] Scaffold inicial da API FastAPI

---

## Arquivos-Chave e Propósito

| Arquivo | Propósito |
|---|---|
| `PROJECT.md` | Visão geral, stack, épicos, princípios |
| `AGENTS.md` | Regras e contexto para IAs |
| `CONTEXT.md` | Estado atual da sessão (este arquivo) |
| `CONSTRAINTS.md` | Padrões de qualidade obrigatórios |
| `docs/PIPELINE.md` | Pipeline DEFINE→SHIP detalhado |
| `docs/adr/` | Architecture Decision Records |
| `src/` | Código-fonte |
| `tests/` | Testes automatizados |
| `.kiro/skills/` | Skills customizadas |

---

## Decisões Tomadas Nesta Sessão

### Stack Python
- Python 3.13 (já instalado na máquina)
- FastAPI por performance async e documentação automática
- SQLite para simplicidade inicial (migração fácil para PostgreSQL depois)
- SQLModel por combinar Pydantic + SQLAlchemy

### Modelos de IA
- **Wan2.1** como primário — melhor equilíbrio qualidade/VRAM (8GB)
- **CogVideoX** como alternativo — funciona com 6GB VRAM
- **HunyuanVideo** para alta qualidade — requer 14GB VRAM
- **AnimateDiff** como fallback — funciona com 4GB VRAM

### Anti-Alucinação
- Duas IAs em cada ciclo: Kiro (implementa) + Gemini/GPT (revisa)
- Testes automatizados como árbitro objetivo
- Humano com voto de minerva

### CI/CD
- GitHub Actions free tier (2000 min/mês — suficiente para o projeto)
- Testes obrigatórios antes de merge
- Nenhum deploy automático em produção (aprovação manual)

---

## Bloqueios / Riscos

| Risco | Impacto | Mitigação |
|---|---|---|
| VRAM insuficiente para Wan2.1 | Alto | AnimateDiff como fallback (4GB) |
| GitHub Actions minutos esgotados | Médio | Testes locais obrigatórios |
| Modelos HuggingFace lentos para download | Baixo | Cache local em `~/.cache/huggingface` |

---

## Como Retomar em Uma Nova Sessão

1. Leia este arquivo (`CONTEXT.md`) primeiro
2. Leia `AGENTS.md` para as regras
3. Verifique o branch ativo: `git branch`
4. Verifique o status: `git status`
5. Continue pelos "Próximos Passos" acima

---

## Histórico de Sessões

| Data | Fase | O que foi feito |
|---|---|---|
| 2026-10-12 | DEFINE | Setup inicial, estrutura, documentação base |
