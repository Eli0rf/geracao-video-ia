# CONSTRAINTS.md — Padrões de Qualidade

> Definidos na fase DEFINE. Obrigatórios em todas as fases subsequentes.
> Nenhum agente de IA ou desenvolvedor pode silenciar estas restrições.

---

## Cobertura de Testes

| Tipo | Mínimo | Alvo |
|---|---|---|
| Unit | 80% | 90% |
| Integration | 15% | 20% |
| E2E | 5% | 10% |

**Regra:** PR bloqueado se cobertura total cair abaixo de 80%.

---

## Tamanho de PR

- **Máximo:** ~200 linhas por PR
- Se ultrapassar, dividir em slices menores
- Exceção documentada obrigatória para PRs maiores

---

## Qualidade de Código

```toml
# Configuração ruff (linter)
line-length = 100
target-version = "py313"
select = ["E", "W", "F", "I", "N", "UP", "S", "B", "A"]

# mypy (tipagem)
strict = true
```

**Regra:** `ruff check` e `mypy` devem passar com zero erros antes do commit.

---

## Commits (Conventional Commits)

Formato obrigatório:
```
<tipo>(<escopo>): <descrição curta em imperativo>

[corpo opcional]

[rodapé opcional]
```

Tipos válidos:
- `feat` — nova funcionalidade
- `fix` — correção de bug
- `test` — adição/modificação de testes
- `docs` — apenas documentação
- `refactor` — refatoração sem mudança de comportamento
- `chore` — tarefas de manutenção (deps, configs)
- `ci` — mudanças no pipeline CI/CD

---

## API

- Versioning obrigatório: `/api/v1/`
- Schemas Pydantic para todas as entradas e saídas
- Nunca remover campos de response (adicionar apenas)
- Erros no formato RFC 7807 (Problem Details)
- Timeout máximo de request: 30s (geração de vídeo é assíncrona)

---

## Segurança

- Zero secrets em código ou commits
- Validação de entrada em todos os endpoints
- Rate limiting em endpoints públicos
- Logs não devem conter dados sensíveis

---

## Performance

- API: P95 < 200ms para endpoints síncronos
- Geração de vídeo: assíncrona, sem timeout no endpoint
- Modelos de IA: carregados uma vez, mantidos em memória

---

## Gratuidade

- **Zero** dependências de APIs pagas
- Modelos: apenas HuggingFace Hub (gratuito) ou pesos locais
- Infraestrutura: GitHub free tier
- Monitoring: logs locais + Prometheus (auto-hospedado)

---

## Retrocompatibilidade

- Versões de API existentes nunca são removidas sem 2 versões de aviso
- Campos de schema são apenas adicionados, nunca removidos
- Breaking changes exigem novo major version (`v1` → `v2`)

---

## Definition of Done (DoD)

Uma task está concluída quando:
- [ ] Código implementado e funcionando
- [ ] Testes escritos (Red → Green → Refactor)
- [ ] `pytest tests/` passa com 100%
- [ ] `ruff check src/` sem erros
- [ ] `mypy src/` sem erros
- [ ] Documentação atualizada (se necessário)
- [ ] `CONTEXT.md` atualizado
- [ ] Commit atômico com mensagem Conventional Commits
- [ ] PR aberto com descrição clara
- [ ] Revisado por IA-2 (anti-alucinação)
- [ ] Aprovado por humano
