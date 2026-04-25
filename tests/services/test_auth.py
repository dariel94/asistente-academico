"""Tests para `app.services.auth`.

Cubre `create_token`, `verify_token`, `verify_password` y `get_current_user`
con la dependencia `Request`/`app.state.db_pool` mockeada.
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import bcrypt
import jwt
import pytest
from fastapi import HTTPException

from app import config
from app.services import auth


# ─── create_token / verify_token ────────────────────────────────────────────

def test_create_token_codifica_id_alumno_en_sub():
    token = auth.create_token(42)
    payload = jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
    assert payload["sub"] == "42"
    assert "iat" in payload and "exp" in payload


def test_create_token_expira_en_la_ventana_configurada():
    token = auth.create_token(1)
    payload = jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
    # exp debe estar entre +23h y +25h (margen para drift de reloj del test)
    delta = payload["exp"] - payload["iat"]
    esperado = config.JWT_EXPIRATION_HOURS * 3600
    assert abs(delta - esperado) < 60  # tolerancia de 1 minuto


def test_verify_token_devuelve_id_alumno():
    token = auth.create_token(99)
    assert auth.verify_token(token) == 99


def test_verify_token_rechaza_secreto_invalido():
    payload = {
        "sub": "1",
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    fake = jwt.encode(payload, "otro-secreto-distinto", algorithm="HS256")
    with pytest.raises(HTTPException) as exc:
        auth.verify_token(fake)
    assert exc.value.status_code == 401


def test_verify_token_rechaza_expirado():
    now = datetime.now(timezone.utc)
    payload = {
        "sub": "1",
        "iat": now - timedelta(hours=2),
        "exp": now - timedelta(hours=1),  # expirado hace 1 hora
    }
    expirado = jwt.encode(payload, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)
    with pytest.raises(HTTPException) as exc:
        auth.verify_token(expirado)
    assert exc.value.status_code == 401


def test_verify_token_rechaza_token_malformado():
    with pytest.raises(HTTPException) as exc:
        auth.verify_token("no-es-un-jwt-valido")
    assert exc.value.status_code == 401


def test_verify_token_rechaza_sub_no_numerico():
    """Si el `sub` no se puede convertir a int, falla con 401 (cubre el
    `ValueError` capturado en `verify_token`)."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": "no-numero",
        "iat": now,
        "exp": now + timedelta(hours=1),
    }
    token = jwt.encode(payload, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)
    with pytest.raises(HTTPException) as exc:
        auth.verify_token(token)
    assert exc.value.status_code == 401


# ─── verify_password ────────────────────────────────────────────────────────

def test_verify_password_acepta_hash_correcto():
    hashed = bcrypt.hashpw(b"password123", bcrypt.gensalt()).decode()
    assert auth.verify_password("password123", hashed) is True


def test_verify_password_rechaza_hash_incorrecto():
    hashed = bcrypt.hashpw(b"password123", bcrypt.gensalt()).decode()
    assert auth.verify_password("otra-cosa", hashed) is False


# ─── get_current_user ───────────────────────────────────────────────────────

def _make_request(authorization: str | None, pool_row: dict | None) -> MagicMock:
    """Construye un `Request` mock con header opcional y un pool con fetchrow."""
    req = MagicMock()
    headers = {}
    if authorization is not None:
        headers["Authorization"] = authorization
    req.headers.get.side_effect = lambda key: headers.get(key)
    pool = MagicMock()
    pool.fetchrow = AsyncMock(return_value=pool_row)
    req.app.state.db_pool = pool
    return req


@pytest.mark.asyncio
async def test_get_current_user_sin_header_da_401():
    req = _make_request(authorization=None, pool_row=None)
    with pytest.raises(HTTPException) as exc:
        await auth.get_current_user(req)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_header_sin_bearer_da_401():
    req = _make_request(authorization="Token xxx", pool_row=None)
    with pytest.raises(HTTPException) as exc:
        await auth.get_current_user(req)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_token_invalido_da_401():
    req = _make_request(authorization="Bearer token-roto", pool_row=None)
    with pytest.raises(HTTPException) as exc:
        await auth.get_current_user(req)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_alumno_no_existe_da_401():
    """Token bien firmado pero el `sub` no existe en la tabla `alumnos`."""
    token = auth.create_token(9999)
    req = _make_request(authorization=f"Bearer {token}", pool_row=None)
    with pytest.raises(HTTPException) as exc:
        await auth.get_current_user(req)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_ok_construye_session_context():
    token = auth.create_token(7)
    row = {
        "id_alumno": 7,
        "nombre": "María",
        "apellido": "González",
        "legajo": "SIS-1001",
        "estado": "regular",
        "carrera": "Ingeniería en Sistemas",
    }
    req = _make_request(authorization=f"Bearer {token}", pool_row=row)
    ctx = await auth.get_current_user(req)
    assert ctx.id_alumno == 7
    assert ctx.perfil.legajo == "SIS-1001"
    assert ctx.perfil.carrera == "Ingeniería en Sistemas"
    assert ctx.perfil.estado == "regular"
