"""Tests para `app.services.memory.MemoryManager`.

El pool `asyncpg` se mockea con `AsyncMock`. La llamada a Ollama (en
`_sumarizar_antiguos`) se intercepta con `respx`.
"""
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
import respx

from app import config
from app.services.memory import (
    MemoryManager,
    UMBRAL_SUMARIZACION,
    VENTANA_MENSAJES,
)


def _make_pool(
    fetchval_returns: list | None = None,
    fetch_returns: list | None = None,
):
    """Construye un pool mock cuya cola de retornos sigue el orden de las
    llamadas que hace `MemoryManager`."""
    pool = MagicMock()
    pool.fetchval = AsyncMock(side_effect=fetchval_returns or [])
    pool.fetch = AsyncMock(side_effect=fetch_returns or [])
    pool.execute = AsyncMock(return_value=None)
    return pool


# ─── obtener_contexto ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_obtener_contexto_sin_resumen_y_sin_mensajes():
    pool = _make_pool(fetchval_returns=[None], fetch_returns=[[]])
    mm = MemoryManager(pool)
    ctx = await mm.obtener_contexto(id_alumno=1)
    assert ctx == []


@pytest.mark.asyncio
async def test_obtener_contexto_solo_mensajes_literales():
    msgs = [
        {"rol": "user", "contenido": "hola"},
        {"rol": "assistant", "contenido": "¡Hola!"},
    ]
    pool = _make_pool(fetchval_returns=[None], fetch_returns=[msgs])
    mm = MemoryManager(pool)
    ctx = await mm.obtener_contexto(id_alumno=1)
    assert ctx == [
        {"role": "user", "content": "hola"},
        {"role": "assistant", "content": "¡Hola!"},
    ]


@pytest.mark.asyncio
async def test_obtener_contexto_con_resumen_va_primero():
    """El resumen acumulado debe entregarse como mensaje `system` antes que
    los mensajes literales."""
    pool = _make_pool(
        fetchval_returns=["resumen previo"],
        fetch_returns=[[{"rol": "user", "contenido": "siguiente"}]],
    )
    mm = MemoryManager(pool)
    ctx = await mm.obtener_contexto(id_alumno=1)
    assert len(ctx) == 2
    assert ctx[0]["role"] == "system"
    assert "Resumen de conversaciones anteriores:" in ctx[0]["content"]
    assert "resumen previo" in ctx[0]["content"]
    assert ctx[1] == {"role": "user", "content": "siguiente"}


@pytest.mark.asyncio
async def test_obtener_contexto_pasa_ventana_correcta_al_pool():
    """El SQL del segundo `fetch` debe usar `VENTANA_MENSAJES` como límite."""
    pool = _make_pool(fetchval_returns=[None], fetch_returns=[[]])
    mm = MemoryManager(pool)
    await mm.obtener_contexto(id_alumno=42)
    # El fetch de mensajes recibe (sql, id_alumno, VENTANA_MENSAJES)
    args = pool.fetch.await_args.args
    assert args[1] == 42
    assert args[2] == VENTANA_MENSAJES


# ─── guardar_intercambio ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_guardar_intercambio_inserta_user_y_assistant():
    pool = _make_pool(fetchval_returns=[5])  # count = 5, no dispara sumarización
    mm = MemoryManager(pool)
    await mm.guardar_intercambio(1, "preg", "resp")

    # Dos INSERTs
    assert pool.execute.await_count == 2
    primera = pool.execute.await_args_list[0].args
    segunda = pool.execute.await_args_list[1].args
    assert "'user'" in primera[0]
    assert primera[2] == "preg"
    assert "'assistant'" in segunda[0]
    assert segunda[2] == "resp"


@pytest.mark.asyncio
async def test_guardar_intercambio_no_sumariza_si_count_no_supera_umbral():
    pool = _make_pool(fetchval_returns=[UMBRAL_SUMARIZACION])
    mm = MemoryManager(pool)
    mm._sumarizar_antiguos = AsyncMock()
    await mm.guardar_intercambio(1, "x", "y")
    mm._sumarizar_antiguos.assert_not_awaited()


@pytest.mark.asyncio
async def test_guardar_intercambio_sumariza_al_superar_umbral():
    """count > UMBRAL_SUMARIZACION dispara `_sumarizar_antiguos`."""
    pool = _make_pool(fetchval_returns=[UMBRAL_SUMARIZACION + 2])
    mm = MemoryManager(pool)
    mm._sumarizar_antiguos = AsyncMock()
    await mm.guardar_intercambio(1, "x", "y")
    mm._sumarizar_antiguos.assert_awaited_once_with(1)


# ─── _sumarizar_antiguos ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sumarizar_antiguos_no_hace_nada_si_no_hay_mensajes_a_comprimir():
    """Si `len(rows) <= VENTANA_MENSAJES`, no hay nada para comprimir y la
    función retorna sin tocar Ollama ni `resumenes`."""
    pool = _make_pool(
        fetch_returns=[
            [{"rol": "user", "contenido": str(i)} for i in range(VENTANA_MENSAJES)]
        ]
    )
    mm = MemoryManager(pool)
    with respx.mock:
        await mm._sumarizar_antiguos(1)
    # No se llamó a Ollama ni a UPSERT de resumen
    pool.execute.assert_not_called()


@pytest.mark.asyncio
async def test_sumarizar_antiguos_invoca_ollama_y_upsertea_resumen(monkeypatch):
    """Verifica el ciclo completo de sumarización: 22 → recorte a 10 + upsert
    del resumen. Mockeamos `httpx.AsyncClient` con un transport que captura
    la request y devuelve el resumen sintético."""
    # 22 mensajes en la tabla → comprimir 22 - 10 = 12 más antiguos
    todos = [
        {"rol": "user" if i % 2 == 0 else "assistant", "contenido": f"msg{i}"}
        for i in range(UMBRAL_SUMARIZACION + 2)
    ]
    ids_a_borrar = [{"id_mensaje": i + 1} for i in range(12)]
    pool = _make_pool(fetch_returns=[todos, ids_a_borrar])

    captured_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        return httpx.Response(200, json={"message": {"content": "resumen generado"}})

    transport = httpx.MockTransport(handler)
    real_async_client = httpx.AsyncClient

    def fake_async_client(*args, **kwargs):
        kwargs["transport"] = transport
        return real_async_client(*args, **kwargs)

    monkeypatch.setattr("app.services.memory.httpx.AsyncClient", fake_async_client)

    mm = MemoryManager(pool)
    await mm._sumarizar_antiguos(7)

    # Se golpeó a Ollama una vez, contra la URL correcta
    assert len(captured_requests) == 1
    assert str(captured_requests[0].url) == f"{config.OLLAMA_BASE_URL}/api/chat"

    # UPSERT de resumen + DELETE de mensajes
    assert pool.execute.await_count == 2
    upsert_sql = pool.execute.await_args_list[0].args[0]
    upsert_resumen = pool.execute.await_args_list[0].args[2]
    delete_sql = pool.execute.await_args_list[1].args[0]
    delete_ids = pool.execute.await_args_list[1].args[1]

    assert "INSERT INTO resumenes" in upsert_sql
    assert upsert_resumen == "resumen generado"
    assert "DELETE FROM conversaciones" in delete_sql
    assert delete_ids == [r["id_mensaje"] for r in ids_a_borrar]
