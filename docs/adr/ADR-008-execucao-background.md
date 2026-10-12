# ADR-008: FastAPI BackgroundTasks como dispatcher inicial de jobs

**Data:** 2026-10-12
**Status:** Aceito
**Decisores:** Elio + Kiro (IA)

## Contexto

O endpoint `POST /api/v1/jobs` cria o `VideoJob` com status `pending` e
retorna 202 imediatamente (TASK-005, já implementado). É preciso decidir
**como** o processamento assíncrono do job (roteiro → áudio → vídeo →
montagem) é efetivamente disparado em background, sem bloquear a request
nem exigir infraestrutura paga.

`PROJECT.md` menciona "Celery + Redis (opcional)" como visão de longo
prazo, mas isso exige um broker de mensagens rodando (Redis), o que
adiciona complexidade operacional e não é gratuito de manter em todo
ambiente (ex.: serverless, CI).

## Decisão

Usar **FastAPI `BackgroundTasks`** como mecanismo de execução assíncrona
inicial, através de uma abstração `JobDispatcher` (Protocol) em
`src/core/dispatcher.py`:

```python
class JobDispatcher(Protocol):
    def dispatch(self, job_id: str) -> None: ...
```

- `BackgroundTasksDispatcher` é a implementação concreta usada hoje,
  agendando `JobProcessor.process(job_id)` via `BackgroundTasks.add_task`
  no endpoint `POST /api/v1/jobs`.
- `JobProcessor` (`src/core/worker.py`) processa **um job por vez**
  (`asyncio.Semaphore(settings.max_concurrent_jobs)`), aplica timeout
  (`settings.job_timeout_seconds`) e atualiza o status do `VideoJob` no
  banco (`pending → processing → completed/failed`).
- No `lifespan` da aplicação, jobs que ficaram presos em `processing`
  (ex.: processo derrubado no meio da execução) são recuperados e jobs
  `pending` são reenfileirados.
- Uma futura implementação `CeleryDispatcher` pode substituir
  `BackgroundTasksDispatcher` sem alterar o endpoint ou o `JobProcessor`,
  pois ambos dependem apenas do `Protocol JobDispatcher`.

## Justificativa

- `BackgroundTasks` já vem com o FastAPI (zero dependência nova), roda no
  mesmo processo e é suficiente para `max_concurrent_jobs` baixo
  (1, conforme `.env.example`), que é o cenário real deste projeto
  (geração de vídeo é limitada por VRAM, não por paralelismo).
- Evita a complexidade operacional de um broker Redis/RabbitMQ (processo
  extra, mais um ponto de falha) numa fase em que o volume de jobs é
  baixo e o processamento é sequencial por natureza (uma GPU).
- A abstração `JobDispatcher` mantém a migração para Celery **trivial**
  quando o volume justificar fila distribuída/múltiplos workers — sem
  reescrever o pipeline de geração.
- Mantém o contrato HTTP existente (`202 Accepted` + polling por status)
  inalterado, preservando retrocompatibilidade (`CONSTRAINTS.md`).

## Consequências

- **Positivo:** zero infraestrutura nova, zero custo, simples de depurar.
- **Positivo:** troca para Celery é isolada a uma nova classe
  `CeleryDispatcher`, sem tocar em `JobProcessor` ou nos endpoints.
- **Negativo:** `BackgroundTasks` roda no mesmo processo do servidor web —
  se o processo morrer, jobs em `processing` ficam órfãos (mitigado pela
  recuperação no `lifespan` da app).
- **Negativo:** não escala horizontalmente (múltiplos workers/processos)
  sem migrar para Celery — aceitável para o volume atual do projeto.
- **Reversível:** `CeleryDispatcher` + Redis ficam documentados como
  TASK futura (pós v0.2), a ser avaliada quando houver necessidade real
  de múltiplos workers.
