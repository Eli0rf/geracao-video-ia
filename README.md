# 🎬 Geração de Vídeo por IA

> API REST para geração de vídeos por Inteligência Artificial usando modelos open-source.

[![CI](https://github.com/username/geracao-video-ia/actions/workflows/ci.yml/badge.svg)](https://github.com/username/geracao-video-ia/actions)
[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## O que é

Sistema que recebe prompts de texto ou imagens e retorna vídeos gerados por IA, usando modelos open-source rodando localmente — **sem custo de API**.

## Modelos suportados

| Modelo | VRAM | Qualidade |
|--------|------|-----------|
| Wan2.1-T2V | 8GB | ⭐⭐⭐⭐ |
| CogVideoX-5B | 6GB | ⭐⭐⭐⭐ |
| HunyuanVideo | 14GB | ⭐⭐⭐⭐⭐ |
| AnimateDiff-v3 | 4GB | ⭐⭐⭐ |

## Quick Start

```bash
# Clone o repositório
git clone https://github.com/username/geracao-video-ia.git
cd geracao-video-ia

# Crie o ambiente virtual
python3.13 -m venv .venv
source .venv/bin/activate

# Instale as dependências
pip install -r requirements.txt

# Rode a API
uvicorn src.api.main:app --reload
```

Acesse `http://localhost:8000/docs` para a documentação interativa.

## Pipeline de Desenvolvimento

```
DEFINE → PLAN → BUILD → VERIFY → REVIEW → SHIP
```

Ver `docs/PIPELINE.md` para detalhes.

## Para IAs e Agentes

Leia `AGENTS.md` antes de qualquer trabalho no projeto.  
Verifique `CONTEXT.md` para o estado atual.

## Licença

MIT
