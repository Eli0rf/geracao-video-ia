# ADR-002: SQLite como banco de dados inicial

**Data:** 2026-10-12  
**Status:** Aceito  
**Decisores:** Elio + Kiro (IA)

## Contexto

Precisamos de persistência para jobs de geração, metadados de vídeos e configurações.

## Decisão

Usar **SQLite** com **SQLModel** (ORM).

## Justificativa

- Zero configuração de servidor
- Gratuito e embutido no Python
- SQLModel combina SQLAlchemy + Pydantic (mesmos tipos da API)
- Suficiente para o volume inicial (centenas de jobs, não milhões)
- Migração para PostgreSQL é trivial quando necessário

## Consequências

- **Positivo:** Setup em segundos, sem Docker obrigatório
- **Positivo:** Arquivo único — backup trivial
- **Negativo:** Não suporta múltiplos escritores simultâneos (aceitável neste estágio)
- **Reversível:** Migração para PostgreSQL quando necessário via Alembic
