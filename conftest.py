"""
conftest.py — Configuração global do pytest.

Garante que `src/` está no sys.path para todos os testes.
Define fixtures compartilhadas entre unit, integration e e2e.
"""

import sys
from pathlib import Path

# Garante que a raiz do projeto está no path Python
# Necessário para `import src.config` funcionar independente de como pytest é invocado
sys.path.insert(0, str(Path(__file__).parent))
