# PIPELINE.md — Ciclo de Desenvolvimento

```
DEFINE → PLAN → BUILD → VERIFY → REVIEW → SHIP
```

Este documento detalha cada fase, seus entregáveis, critérios de saída e o papel de cada IA.

---

## Visão Geral

```
 DEFINE          PLAN           BUILD          VERIFY         REVIEW          SHIP
 ┌──────┐      ┌──────┐      ┌──────┐      ┌──────┐      ┌──────┐      ┌──────┐
 │ Idea │ ───▶ │ Spec │ ───▶ │ Code │ ───▶ │ Test │ ───▶ │  QA  │ ───▶ │  Go  │
 │Refine│      │  PRD │      │ Impl │      │Debug │      │ Gate │      │ Live │
 └──────┘      └──────┘      └──────┘      └──────┘      └──────┘      └──────┘
  /spec          /plan          /build        /test         /review       /ship
```

---

## FASE 1: DEFINE

**Quando:** Início do projeto ou nova feature significativa  
**Branch:** `main` ou `docs/*`

### Entregáveis
- `PROJECT.md` — visão geral e arquitetura
- `AGENTS.md` — contexto para IAs
- `CONTEXT.md` — estado atual
- `CONSTRAINTS.md` — padrões de qualidade
- ADRs para decisões arquiteturais

### Critérios de saída
- [ ] Stack tecnológica definida e documentada
- [ ] Estrutura de diretórios criada
- [ ] Repositório Git com branches configuradas
- [ ] Todos os arquivos de contexto criados

### IAs envolvidas
- IA-1 (Kiro): cria documentação
- IA-2 (revisor): valida arquitetura e decisões

---

## FASE 2: PLAN

**Quando:** Após DEFINE aprovado  
**Branch:** `main` (para PLAN.md), `feature/*` (para tasks)

### Entregáveis
- `PLAN.md` — épicos e tasks com critérios de aceitação
- Issues do GitHub para cada task
- Estimativas de esforço

### Critérios de saída
- [ ] Todos os épicos do milestone documentados
- [ ] Cada task com critérios de aceitação claros
- [ ] Dependências entre tasks mapeadas
- [ ] Tasks < 4h de trabalho cada (se maior, dividir)

### Template de task
```markdown
## TASK-XXX: Nome da Task

**Épico:** E0X  
**Estimativa:** Xh  
**Dependências:** TASK-YYY (se houver)

### Critérios de aceitação
- [ ] Critério 1
- [ ] Critério 2

### Testes necessários
- [ ] Teste unitário: ...
- [ ] Teste de integração: ...

### Definition of Done
- [ ] Todos os critérios de aceitação atendidos
- [ ] Testes passando
- [ ] PR revisado e aprovado
```

---

## FASE 3: BUILD

**Quando:** Após task planejada  
**Branch:** `feature/<nome-da-task>`

### Protocolo por task

```
1. Criar branch: git checkout -b feature/<task>
2. Escrever teste (RED — deve falhar)
3. Implementar código mínimo (GREEN — testes passam)
4. Refatorar (REFACTOR — sem quebrar testes)
5. Commit atômico
6. Repetir para próxima slice
```

### Critérios de saída
- [ ] Todos os critérios de aceitação da task implementados
- [ ] Testes escritos antes do código (TDD)
- [ ] `pytest tests/` verde
- [ ] `ruff check` e `mypy` sem erros
- [ ] `CONTEXT.md` atualizado

---

## FASE 4: VERIFY

**Quando:** Após BUILD concluído  
**Branch:** `feature/<nome-da-task>`

### Checklist de verificação
- [ ] `pytest tests/ -v --cov=src` — cobertura ≥ 80%
- [ ] `ruff check src/ tests/` — zero warnings
- [ ] `mypy src/` — zero erros de tipo
- [ ] Testes de integração passando
- [ ] Revisão pela IA-2 (anti-alucinação)

### Protocolo IA-2
```
IA-2 recebe:
- Código implementado
- Testes escritos
- CONTEXT.md atualizado

IA-2 verifica:
- Lógica está correta?
- Edge cases cobertos?
- Segurança comprometida?
- Performance adequada?
- Retrocompatibilidade mantida?

IA-2 sinaliza com ⚠️ REVISOR: qualquer problema encontrado
```

---

## FASE 5: REVIEW

**Quando:** Após VERIFY aprovado  
**Branch:** PR de `feature/*` para `develop`

### Checklist de PR
- [ ] Título no formato Conventional Commits
- [ ] Descrição clara: o quê, por quê, como testar
- [ ] Tamanho ≤ 200 linhas (ou justificativa documentada)
- [ ] Todos os checks de CI passando
- [ ] Nenhum secret exposto
- [ ] Sem TODOs sem issue criada

### Template de PR
```markdown
## Resumo
Descrição curta do que foi implementado.

## Motivação
Por que esta mudança é necessária?

## Como testar
1. Passo 1
2. Passo 2

## Checklist
- [ ] Testes escritos e passando
- [ ] Documentação atualizada
- [ ] CONTEXT.md atualizado
- [ ] Revisado por IA-2
```

---

## FASE 6: SHIP

**Quando:** PR aprovado e merge em `develop`, pronto para produção  
**Branch:** `develop` → `main` via PR

### Checklist pré-ship
- [ ] Todos os testes passando em CI
- [ ] CHANGELOG.md atualizado
- [ ] Versão semântica bumped (major.minor.patch)
- [ ] Tag Git criada: `git tag v0.1.0`
- [ ] `CONTEXT.md` atualizado com o que foi shipped

### Versionamento semântico
```
MAJOR.MINOR.PATCH
  │      │     └── Bug fixes, sem breaking changes
  │      └──────── Novas features, retrocompatível
  └─────────────── Breaking changes
```

---

## Papéis das IAs

| Fase | IA-1 (Kiro/Implementador) | IA-2 (Revisor) | Humano |
|---|---|---|---|
| DEFINE | Cria documentação | Valida arquitetura | Aprova |
| PLAN | Quebra em tasks | Questiona estimativas | Prioriza |
| BUILD | Implementa código | — | Acompanha |
| VERIFY | Roda testes | Revisa código | — |
| REVIEW | Ajusta conforme feedback | Aprova ou rejeita | Decisão final |
| SHIP | Prepara release | — | Autoriza deploy |

---

## Padrão de Branches

```
main
 └── develop
      ├── feature/e01-ci-cd-base
      ├── feature/e02-api-endpoints
      ├── feature/e03-wan21-integration
      └── fix/bug-description
```

**Regras:**
- `feature/*` → merge em `develop` via PR
- `develop` → merge em `main` via PR (releases)
- Nunca força push em `main` ou `develop`
- Delete branch após merge
