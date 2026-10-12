# ADR-004: Dupla IA para anti-alucinação

**Data:** 2026-10-12  
**Status:** Aceito  
**Decisores:** Elio + Kiro (IA)

## Contexto

IAs podem alucinar — gerar código que parece correto mas tem bugs sutis ou falhas de design. Precisamos de um mecanismo para reduzir esse risco.

## Decisão

Usar **dois agentes de IA** em ciclos alternados:
- **IA-1 (Kiro/Claude):** Implementa código e testes
- **IA-2 (Gemini/GPT-4o):** Revisa o trabalho da IA-1

## Protocolo

1. IA-1 implementa uma task
2. IA-1 roda testes: devem passar
3. IA-1 documenta em CONTEXT.md
4. IA-2 lê CONTEXT.md + código
5. IA-2 questiona decisões e detecta problemas
6. Humano resolve conflitos e aprova

## Justificativa

- Dois modelos diferentes têm vieses diferentes
- Revisor externo detecta o que o implementador não vê
- Testes automatizados são árbitros objetivos
- Custo zero (ambos na camada gratuita)

## Consequências

- **Positivo:** Redução significativa de bugs e alucinações
- **Positivo:** Código mais legível (segunda opinião força clareza)
- **Negativo:** Ciclo de desenvolvimento mais longo
- **Negativo:** IA-2 pode dar feedback conflitante (humano decide)
