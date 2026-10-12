# ADR-001: Python 3.13 + FastAPI como base do backend

**Data:** 2026-10-12  
**Status:** Aceito  
**Decisores:** Elio + Kiro (IA)

## Contexto

Precisamos de uma linguagem e framework para o backend da API de geração de vídeo.

## Decisão

Usar **Python 3.13** com **FastAPI 0.115+**.

## Justificativa

- Python é a linguagem padrão do ecossistema ML/AI (PyTorch, Diffusers, HuggingFace)
- FastAPI tem suporte async nativo (necessário para geração de vídeo demorada)
- FastAPI gera documentação OpenAPI automaticamente
- Python 3.13 já está instalado na máquina de desenvolvimento
- Comunidade enorme, zero custo

## Consequências

- **Positivo:** Integração direta com modelos HuggingFace Diffusers
- **Positivo:** Tipagem com Pydantic nativa no FastAPI
- **Negativo:** Python mais lento que Go/Rust (aceitável para este caso de uso)
- **Negativo:** GIL limita paralelismo CPU (contornado com async + subprocessos)
