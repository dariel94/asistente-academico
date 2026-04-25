"""Tests para `app.mcp.server`.

Cubre:
- `periodo_vigente()` — la convención meses 1-7 → 1C, 8-12 → 2C.
- `mcp_tool` — el decorador inscribe la función en el dict de despacho.
- `dispatch` — tool inexistente, propagación de `ContextVar` y de argumentos.
- `has` — chequeo de existencia.
"""
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from app.mcp import server as mcp_server_mod
from app.mcp.server import dispatch, has, mcp_tool, periodo_vigente, request_ctx, request_pool
from app.models.schemas import Perfil, SessionContext


def _ctx(id_alumno: int = 1) -> SessionContext:
    return SessionContext(
        id_alumno=id_alumno,
        perfil=Perfil(
            id_alumno=id_alumno,
            nombre="Test",
            apellido="Test",
            legajo="T-001",
            carrera="Ingeniería",
            estado="regular",
        ),
    )


# ─── periodo_vigente ────────────────────────────────────────────────────────

@pytest.mark.parametrize("mes,sufijo", [(1, "1C"), (3, "1C"), (7, "1C")])
def test_periodo_vigente_primer_cuatrimestre(mes, sufijo):
    fake = datetime(2026, mes, 15)
    with patch("app.mcp.server.datetime") as mock_dt:
        mock_dt.now.return_value = fake
        assert periodo_vigente() == f"2026-{sufijo}"


@pytest.mark.parametrize("mes,sufijo", [(8, "2C"), (10, "2C"), (12, "2C")])
def test_periodo_vigente_segundo_cuatrimestre(mes, sufijo):
    fake = datetime(2026, mes, 15)
    with patch("app.mcp.server.datetime") as mock_dt:
        mock_dt.now.return_value = fake
        assert periodo_vigente() == f"2026-{sufijo}"


def test_periodo_vigente_borde_julio_agosto():
    """Julio cae en 1C, agosto en 2C — corte exacto en el límite."""
    with patch("app.mcp.server.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2026, 7, 31)
        assert periodo_vigente().endswith("1C")
        mock_dt.now.return_value = datetime(2026, 8, 1)
        assert periodo_vigente().endswith("2C")


# ─── mcp_tool y has ─────────────────────────────────────────────────────────

def test_mcp_tool_registra_en_dispatch_y_devuelve_la_funcion(monkeypatch):
    """El decorador inscribe la función en `_dispatch` bajo el nombre
    indicado y devuelve la función original sin envolverla."""
    # Backup del dispatch para no contaminar otros tests
    backup = dict(mcp_server_mod._dispatch)
    try:
        monkeypatch.setattr(mcp_server_mod.mcp_server, "tool", lambda name: lambda f: f)

        @mcp_tool("test_tool_unica")
        async def _impl():
            return "ok"

        assert has("test_tool_unica") is True
        assert mcp_server_mod._dispatch["test_tool_unica"] is _impl
    finally:
        mcp_server_mod._dispatch.clear()
        mcp_server_mod._dispatch.update(backup)


def test_has_devuelve_false_para_tool_inexistente():
    assert has("herramienta_no_registrada") is False


# ─── dispatch ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_dispatch_tool_inexistente_devuelve_mensaje_de_error():
    res = await dispatch("nope_no_existe", {}, _ctx(), MagicMock())
    assert "no encontrada" in res


@pytest.mark.asyncio
async def test_dispatch_setea_contextvars_antes_de_invocar(monkeypatch):
    """`request_ctx` y `request_pool` deben estar accesibles desde dentro
    de la tool."""
    backup = dict(mcp_server_mod._dispatch)
    try:
        captured = {}
        monkeypatch.setattr(mcp_server_mod.mcp_server, "tool", lambda name: lambda f: f)

        @mcp_tool("captura_ctx")
        async def _impl():
            captured["ctx"] = request_ctx.get()
            captured["pool"] = request_pool.get()
            return "ok"

        ctx = _ctx(id_alumno=42)
        pool = MagicMock()
        res = await dispatch("captura_ctx", {}, ctx, pool)

        assert res == "ok"
        assert captured["ctx"].id_alumno == 42
        assert captured["pool"] is pool
    finally:
        mcp_server_mod._dispatch.clear()
        mcp_server_mod._dispatch.update(backup)


@pytest.mark.asyncio
async def test_dispatch_propaga_args_a_la_tool(monkeypatch):
    """Los `**args` se pasan tal cual a la tool."""
    backup = dict(mcp_server_mod._dispatch)
    try:
        monkeypatch.setattr(mcp_server_mod.mcp_server, "tool", lambda name: lambda f: f)

        @mcp_tool("eco")
        async def _impl(texto: str = ""):
            return texto.upper()

        res = await dispatch("eco", {"texto": "algebra"}, _ctx(), MagicMock())
        assert res == "ALGEBRA"
    finally:
        mcp_server_mod._dispatch.clear()
        mcp_server_mod._dispatch.update(backup)


# ─── TOOLS_CATALOG ──────────────────────────────────────────────────────────

def test_tools_catalog_tiene_siete_herramientas():
    assert len(mcp_server_mod.TOOLS_CATALOG) == 7


def test_tools_catalog_nombres_alineados_con_dispatch():
    """Cada tool del catálogo debe estar registrada en `_dispatch`."""
    # Forzar registro de las tools reales importando el módulo
    import app.mcp.tools  # noqa: F401
    nombres_catalogo = {t["function"]["name"] for t in mcp_server_mod.TOOLS_CATALOG}
    nombres_dispatch = set(mcp_server_mod._dispatch.keys())
    assert nombres_catalogo.issubset(nombres_dispatch), (
        "Todas las tools del catálogo deben estar registradas en _dispatch"
    )


def test_tools_catalog_sin_argumentos_tienen_schema_vacio():
    """Las cinco tools que operan sobre datos personales del alumno
    declaran `properties: {}` y `required: []` (defensa estructural
    contra argumentos generados por el LLM, ver tesis §4.5.4)."""
    tools_sin_args = {
        "obtener_historia_academica",
        "obtener_inscripciones",
        "consultar_materias_disponibles",
        "obtener_plan_de_estudios",
        "obtener_materias_faltantes",
    }
    for t in mcp_server_mod.TOOLS_CATALOG:
        if t["function"]["name"] in tools_sin_args:
            params = t["function"]["parameters"]
            assert params["properties"] == {}
            assert params["required"] == []
