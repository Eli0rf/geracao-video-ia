# ADR-006: Ollama (roteiro) + Piper TTS (áudio) como geradores locais gratuitos

**Data:** 2026-10-12
**Status:** Aceito
**Decisores:** Elio + Kiro (IA)

## Contexto

O motor de geração de vídeo (`src/core/`) precisa, além do modelo de vídeo
(ADR-003), de duas capacidades adicionais antes da montagem final:

1. **Roteiro** — transformar o prompt do usuário em um roteiro estruturado
   (uma ou mais cenas, cada uma com narração e um prompt visual para o
   gerador de vídeo).
2. **Áudio** — sintetizar a narração de cada cena em um arquivo de áudio
   para ser mixado ao vídeo final.

Nenhum ADR anterior definia esses componentes. A restrição de
`CONSTRAINTS.md`/`AGENTS.md` de **zero dependências pagas** e **apenas
HuggingFace Hub ou modelos locais** se aplica integralmente aqui.

## Decisão

- **Roteiro:** usar **Ollama** rodando localmente (`http://localhost:11434`),
  acessado via HTTP com o cliente `httpx` (já é dependência do projeto).
  Nenhuma biblioteca Python nova é necessária.
- **Áudio (TTS):** usar **Piper TTS**, um binário local leve (CPU-only,
  < 100MB por voz), invocado via `subprocess`. Não depende de GPU nem de
  `torch`.
- Ambos implementam as interfaces `ScriptGenerator` e `AudioSynthesizer`
  definidas em `src/core/interfaces.py` (ADR consistente com ADR-003, que
  já estabelece o padrão de interfaces abstratas + factory para modelos
  de vídeo).
- Um `FakeScriptGenerator` e um `FakeAudioSynthesizer` determinísticos
  existem para testes e para rodar o pipeline completo em ambientes sem
  Ollama/Piper instalados (ex.: CI, desenvolvimento sem GPU).

## Hierarquia de fallback

```
ScriptGenerator:  OllamaScriptGenerator → FakeScriptGenerator
AudioSynthesizer: PiperAudioSynthesizer → FakeAudioSynthesizer
```

`is_available()` em cada implementação verifica, respectivamente, se o
servidor Ollama responde e se o binário `piper` + o modelo de voz existem
no `HF_HOME`/caminho configurado.

## Justificativa

- Ollama e Piper são 100% gratuitos, open-source e rodam localmente —
  sem custo de API, sem chamadas de rede externas em produção.
- Comunicação via HTTP (Ollama) e subprocess (Piper) evita adicionar
  dependências Python pesadas (`torch`, `transformers`) só para texto/áudio,
  mantendo o `pyproject.toml` enxuto fora do extra `ai`.
- A interface `Protocol` + factory (mesmo padrão do `VideoGenerator`)
  permite trocar a implementação (ex.: Coqui TTS, outro LLM local) sem
  alterar o pipeline ou o worker.
- Fakes determinísticos permitem testar 100% do pipeline de orquestração
  sem exigir Ollama/Piper instalados no CI.

## Consequências

- **Positivo:** zero custo, zero dependência paga, extensível.
- **Positivo:** testável sem hardware especial (fakes cobrem o fluxo todo).
- **Negativo:** exige que o desenvolvedor instale Ollama e Piper
  manualmente para rodar a geração real (não é feito via `pip install`).
- **Negativo:** qualidade da narração/roteiro depende do modelo Ollama
  escolhido pelo usuário (ex.: `llama3.2`, `qwen2.5`) — não há garantia
  de qualidade uniforme.
- **Reversível:** novas implementações (`ScriptGenerator`/`AudioSynthesizer`)
  podem ser adicionadas sem quebrar o contrato existente.
