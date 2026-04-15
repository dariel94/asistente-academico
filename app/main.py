from contextlib import asynccontextmanager

import asyncpg
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import config
from app.routers import auth, chat

load_dotenv()


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
