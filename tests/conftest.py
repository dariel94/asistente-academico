"""Configuración común de pytest para los tests unitarios.

Estos tests son **puros**: no requieren PostgreSQL, Ollama ni red. Las
dependencias externas se mockean (`AsyncMock`, `respx`).
"""
import os
import sys
from pathlib import Path

# Asegurar que la raíz del repo esté en sys.path para que `import app...` funcione
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Forzar configuración determinista para los tests (evita depender de variables
# de entorno del entorno de desarrollo).
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-unit-tests-only-32c!")
os.environ.setdefault("RATE_LIMIT_MAX", "30")
os.environ.setdefault("RATE_LIMIT_WINDOW_SECONDS", "60")
