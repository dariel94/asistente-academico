import logging
import os
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler

import asyncpg
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import config
from app.routers import auth, chat

load_dotenv()


def _setup_logging() -> None:
    os.makedirs("logs", exist_ok=True)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    stream = logging.StreamHandler()
    stream.setFormatter(fmt)
    root.addHandler(stream)

    file_handler = RotatingFileHandler(
        "logs/app.log", maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)

    requests_handler = RotatingFileHandler(
        "logs/requests.log", maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    requests_handler.setFormatter(fmt)
    req_logger = logging.getLogger("asistente.request")
    req_logger.addHandler(requests_handler)
    req_logger.addHandler(stream)
    req_logger.propagate = False


_setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Parsear DATABASE_URL para asyncpg (usa formato DSN)
    app.state.db_pool = await asyncpg.create_pool(
        dsn=config.DATABASE_URL,
        min_size=2,
        max_size=10,
    )
    yield
    await app.state.db_pool.close()


app = FastAPI(
    title="Asistente Virtual Académico",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["POST"],
    allow_headers=["Authorization"],
)

app.include_router(auth.router)
app.include_router(chat.router)
