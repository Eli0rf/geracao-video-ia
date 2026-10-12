# ADR-003: Wan2.1 como modelo primário de geração de vídeo

**Data:** 2026-10-12  
**Status:** Aceito  
**Decisores:** Elio + Kiro (IA)

## Contexto

Precisamos escolher modelos de geração de vídeo open-source e gratuitos.

## Decisão

Usar **Wan2.1-T2V** como modelo primário, com fallbacks para hardware menos potente.

## Hierarquia de modelos

| Prioridade | Modelo | VRAM | Qualidade |
|---|---|---|---|
| 1 (primário) | Wan2.1-T2V-14B | 8GB | ⭐⭐⭐⭐ |
| 2 (alternativo) | CogVideoX-5B | 6GB | ⭐⭐⭐⭐ |
| 3 (premium) | HunyuanVideo | 14GB | ⭐⭐⭐⭐⭐ |
| 4 (fallback) | AnimateDiff-v3 | 4GB | ⭐⭐⭐ |

## Justificativa

- Wan2.1 tem melhor qualidade/VRAM entre os modelos com VRAM ≤ 10GB
- CogVideoX-5B funciona em GPUs de 6GB (mais acessível)
- HunyuanVideo para usuários com hardware potente
- AnimateDiff como fallback para máquinas sem GPU dedicada
- Todos disponíveis gratuitamente no HuggingFace Hub

## Consequências

- **Positivo:** Funciona em hardware de consumo (GPU 8GB)
- **Negativo:** Qualidade inferior a serviços comerciais (Sora, Runway)
- **Extensível:** Adicionar novos modelos via interface abstrata `VideoGenerator`
