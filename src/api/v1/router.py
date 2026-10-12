"""
src/api/v1/router.py — Router principal da versão 1 da API.

Agrega todos os sub-routers de v1. Novos endpoints são registrados aqui.
"""

from fastapi import APIRouter

from src.api.v1 import jobs

router = APIRouter(prefix="/api/v1")

# Registra sub-routers
router.include_router(jobs.router)
