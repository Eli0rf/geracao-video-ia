# ADR-007: FFmpeg via subprocess para montagem do vídeo final

**Data:** 2026-10-12
**Status:** Aceito
**Decisores:** Elio + Kiro (IA)

## Contexto

Após o roteiro (ADR-006) gerar as cenas, o áudio ser sintetizado (ADR-006)
e cada cena virar um clipe de vídeo (ADR-003), o sistema precisa montar o
vídeo final: concatenar os clipes, sincronizar/mixar o áudio e normalizar
resolução/duração. Era necessário escolher entre **MoviePy** (wrapper
Python sobre FFmpeg) e **FFmpeg diretamente via subprocess**.

## Decisão

Usar **FFmpeg diretamente via `subprocess`**, sem MoviePy.

A montagem fica em `src/core/assembly/ffmpeg.py` (`VideoAssembler`),
construindo a lista de argumentos do FFmpeg (nunca via shell/string
interpolada — `subprocess.run([...], shell=False)`), usando:

- **Concat demuxer** (`-f concat`) para unir os clipes de cada cena.
- **Mux de áudio** (`-map`, `-shortest`/`-c:a aac`) para combinar a trilha
  de narração sintetizada com o vídeo concatenado.
- Normalização de resolução/fps via filtro `scale`/`fps` quando necessário.

## Justificativa

- MoviePy carrega todos os frames em memória via `imageio`/`numpy` e é
  significativamente mais lento para operações simples de concatenação
  e mux — e depende do FFmpeg de qualquer forma, apenas adicionando uma
  camada Python por cima.
- Chamar o FFmpeg diretamente permite **testar a construção dos comandos
  como funções puras** (sem precisar do binário instalado) e isolar os
  testes de execução real atrás de `pytest.mark.skipif` quando o FFmpeg
  não está disponível no ambiente.
- Evita adicionar `moviepy` ao `pyproject.toml` — reduz superfície de
  dependências, consistente com a filosofia "gratuito e enxuto" do
  projeto.
- `subprocess.run` com lista de argumentos (nunca `shell=True`) atende à
  regra de segurança `S60x` do ruff/bandit já configurada no projeto.

## Consequências

- **Positivo:** sem dependência Python nova; construção de comando 100%
  testável sem FFmpeg instalado.
- **Positivo:** mais rápido e com menor consumo de memória que MoviePy.
- **Negativo:** exige FFmpeg instalado no `PATH` (`brew install ffmpeg`
  localmente; `apt-get install ffmpeg` no CI) para a execução real.
- **Negativo:** manipulação de filtros complexos do FFmpeg é mais verbosa
  que a API do MoviePy — mitigado mantendo os filtros usados ao mínimo
  necessário (concat + mux + scale).
- **Reversível:** a lógica de montagem fica isolada atrás de uma função/
  classe única (`VideoAssembler`), podendo ser substituída por MoviePy ou
  outra ferramenta sem afetar o restante do pipeline.
