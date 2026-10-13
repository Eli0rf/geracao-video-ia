"""
src/core/assembly — Montagem do vídeo final a partir dos clipes e do áudio.

Implementa a etapa final do pipeline: concatenar os clipes das cenas
(ADR-003), normalizar resolução/fps e mixar a narração sintetizada
(ADR-006) em um único MP4. Vide ADR-007.

    ffmpeg.py → VideoAssembler (via subprocess, sem MoviePy)
"""
