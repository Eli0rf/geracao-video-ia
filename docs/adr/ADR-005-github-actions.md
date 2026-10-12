# ADR-005: GitHub Actions como plataforma CI/CD

**Data:** 2026-10-12  
**Status:** Aceito  
**Decisores:** Elio + Kiro (IA)

## Contexto

Precisamos de CI/CD automatizado e gratuito para rodar testes, lint e verificações a cada push.

## Decisão

Usar **GitHub Actions** no free tier.

## Free tier disponível

- **2.000 minutos/mês** em repositórios públicos (ilimitado)
- **500 MB** de armazenamento de artifacts
- Runners Ubuntu, macOS, Windows incluídos

## Justificativa

- Integrado ao GitHub (zero configuração adicional)
- 2.000 min/mês suficientes para testes unitários e lint
- Suporte nativo a Python, cache de dependências
- Gratuito para repositórios públicos (ilimitado)
- Workflows como código (`.github/workflows/`)

## Pipeline configurado

```
push → lint (ruff) → typecheck (mypy) → unit tests → integration tests
```

## Consequências

- **Positivo:** Zero custo para repositório público
- **Positivo:** Integração nativa com PRs e Issues
- **Negativo:** Limite de 2.000 min/mês para repos privados
- **Mitigação:** Rodar testes localmente antes do push
