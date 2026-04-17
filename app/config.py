import os

DATABASE_URL: str = os.getenv(
    "DATABASE_URL", "postgresql://postgres:admin@localhost:5432/asistente_academico"
)

JWT_SECRET: str = os.getenv("JWT_SECRET", "dev-secret-key-change-in-production-32chars!")
JWT_ALGORITHM: str = "HS256"
JWT_EXPIRATION_HOURS: int = 24

OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.1:8b-instruct-q5_K_M")
OLLAMA_EMBED_MODEL: str = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
