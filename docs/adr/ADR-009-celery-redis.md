# ADR-009: Celery + Redis como fila de processamento em produção

**Data:** 2026-10-14
**Status:** Aceito (substitui ADR-008 para o ambiente de produção)
**Decisores:** Elio + Kiro (IA)

## Contexto

O ADR-008 escolheu `FastAPI.BackgroundTasks` como dispatcher inicial de jobs,
com a abstração `JobDispatcher` (Protocol) prevendo explicitamente uma futura
implementação `CeleryDispatcher` "sem tocar em `JobProcessor` ou nos endpoints".

Com a consolidação do pipeline de geração (roteiro com auditoria LLM, áudio,
vídeo e montagem — 4 estágios, minutos de execução), as limitações do
`BackgroundTasks` tornaram-se o gargalo de produção:

1. **O trabalho pesado roda dentro do processo web.** Um job em execução
   consome memória/VRAM do mesmo processo que atende as requisições HTTP; com
   modelos pesados isso derruba a API.
2. **Jobs em andamento morrem com o processo.** Se a API reinicia (deploy,
   crash, OOM-killer), o job fica preso em `processing` e só é recuperado no
   próximo `lifespan` — o que exige uma nova subida da API.
3. **Sem retomada automática.** Não há re-enfileiramento de uma task que
   falhou no meio, nem limite de tempo aplicado pelo orquestrador.
4. **Sem visibilidade da fila.** Não é possível inspecionar quantos jobs
   estão pendentes nem reprocessar um job específico.

## Decisão

Adotar **Celery + Redis** como fila de tarefas em produção, mantendo
`BackgroundTasks` como caminho de desenvolvimento/teste:

- **`src/core/celery_app.py`** cria a app Celery (`geracao_video`) com broker e
  backend de resultados apontando para o Redis (`settings.celery_*`).
- **`src/core/dispatcher.py`** ganha `CeleryDispatcher`, segunda implementação
  do Protocol `JobDispatcher` — exatamente como previsto no ADR-008.
- **`src/core/job_service.py::resolve_dispatcher`** escolhe a implementação por
  ambiente: `background` (padrão, dev/teste) ou `celery` (produção, via
  `TASK_BACKEND=celery` no `docker-compose.yml`).
- **A task `video.process_job`** apenas traduz a mensagem da fila em
  `JobProcessor.process(...)` — **nenhuma lógica de geração mudou de lugar**,
  e o `JobProcessor` permanece intacto.
- **Rastreabilidade preservada (E07):** o `correlation_id` viaja como argumento
  da task e é religado aos `structlog.contextvars` dentro do worker, de modo
  que os logs do worker carregam o mesmo ID da request que originou o job.
- **Configuração de resiliência:** `acks_late=True` (a mensagem só é confirmada
  após o job terminar — worker morto não perde o job), `task_reject_on_worker_
  lost=True`, `task_time_limit`/`task_soft_time_limit` derivados de
  `job_timeout_seconds`, `worker_max_tasks_per_child=50` (evita acúmulo de
  VRAM entre execuções de modelos pesados).
- **Testes sem broker:** `task_always_eager` é forçado em `conftest.py`, então
  a suíte inteira continua rodando sem Redis ativo.

## Alternativas consideradas

| Alternativa | Motivo da rejeição |
|---|---|
| Manter apenas `BackgroundTasks` | Não resolve os 4 problemas do contexto; é o que já estava em produção |
| Substituir `BackgroundTasks` de vez | Quebraria o fluxo de desenvolvimento (`make run` sem Redis) e os testes de API |
| RQ (Redis Queue) | Mais simples, mas sem `acks_late`/time limits nativos e ecossistema menor |
| Manter tudo no `JobProcessor` com threads | Mesma limitação de processo único e sem persistência da fila |

## Consequências

- **Positivo:** processamento pesado sai do processo web — a API continua
  respondendo 202 mesmo com a GPU saturada.
- **Positivo:** job não é perdido se o worker cair (volta para a fila).
- **Positivo:** `correlation_id` e todos os logs estruturados (E07) atravessam
  a fronteira da fila.
- **Positivo:** o `JobProcessor` e o pipeline de geração não foram alterados —
  a migração ficou isolada no dispatcher, como o ADR-008 previa.
- **Negativo:** novo componente operacional (Redis) e um worker a monitorar.
- **Negativo:** o SQLite continua sendo o banco de status; com múltiplos
  workers escrevendo em concorrência, será necessário migrar para Postgres
  (fora do escopo desta task).
- **Reversível:** remover os serviços `redis`/`worker` do compose e voltar
  `TASK_BACKEND=background` restaura o comportamento do ADR-008.
