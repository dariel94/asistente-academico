from contextvars import ContextVar
from datetime import datetime
from typing import Any, Callable, Coroutine

from mcp.server.fastmcp import FastMCP

from app.models.schemas import SessionContext

# ─── Servidor MCP (SDK oficial) ─────────────────────────────────────────────
mcp_server = FastMCP("asistente-academico-mcp")

# Context variables para inyectar dependencias por request sin exponerlas
# como parámetros MCP.  Se setean en dispatch() antes de invocar la tool.
request_ctx: ContextVar[SessionContext] = ContextVar("request_ctx")
request_pool: ContextVar[Any] = ContextVar("request_pool")


def periodo_vigente() -> str:
    now = datetime.now()
    sufijo = "1C" if now.month <= 7 else "2C"
    return f"{now.year}-{sufijo}"


# ─── Registro y despacho in-process ─────────────────────────────────────────
# El orquestador llama a las herramientas directamente (sin transporte MCP),
# por lo que mantenemos un dict nombre→función para despacho rápido.

ToolFunc = Callable[..., Coroutine[Any, Any, str]]
_dispatch: dict[str, ToolFunc] = {}


def mcp_tool(name: str):
    """Decorador que registra una herramienta tanto en el servidor MCP (SDK)
    como en el dict de despacho interno para invocación in-process."""
    def decorator(func: ToolFunc) -> ToolFunc:
        mcp_server.tool(name=name)(func)
        _dispatch[name] = func
        return func
    return decorator


def has(name: str) -> bool:
    return name in _dispatch


async def dispatch(name: str, args: dict, ctx: SessionContext, pool) -> str:
    func = _dispatch.get(name)
    if not func:
        return f"Herramienta '{name}' no encontrada."
    request_ctx.set(ctx)
    request_pool.set(pool)
    return await func(**args)


# ─── Catálogo de tools en formato OpenAI para enviar a Ollama ───────────────
TOOLS_CATALOG = [
    {
        "type": "function",
        "function": {
            "name": "obtener_historia_academica",
            "description": (
                "Obtiene el historial académico completo del alumno autenticado: "
                "materias cursadas con su estado, notas y período. Usar SOLO cuando el alumno pregunte "
                "por notas, historial académico o materias cursadas."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "obtener_materia",
            "description": (
                "Busca información detallada de una materia por nombre: año del plan, "
                "cuatrimestre, carga horaria, correlativas y comisiones disponibles con "
                "horarios. Usar SOLO cuando el alumno pregunte por una materia específica."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "nombre_materia": {
                        "type": "string",
                        "description": "Nombre o parte del nombre de la materia a buscar",
                    }
                },
                "required": ["nombre_materia"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "obtener_inscripciones",
            "description": (
                "Devuelve las inscripciones vigentes del alumno: "
                "materia, comisión, día, horario, aula, sede y profesor. Usar SOLO cuando el alumno "
                "pregunte sus horarios de cursada, agenda académica semanal, materias que está cursando, "
                "inscripciones o materias a las que esta inscripto en el periodo actual."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_materias_disponibles",
            "description": (
                "Lista las materias que el alumno puede cursar en el próximo período: "
                "solo incluye materias no aprobadas cuyas correlativas estén cumplidas "
                "y que no tengan inscripción activa. Usar SOLO cuando el alumno pregunte "
                "qué materias tiene disponibles para cursar o a que materias puede inscribirse el proximo periodo."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "obtener_plan_de_estudios",
            "description": (
                "Obtiene el plan de estudios completo de la carrera del alumno: "
                "todas las materias con año, cuatrimestre y carga horaria, más el "
                "total de materias. Usar SOLO cuando el alumno pida informacion sobre el plan de estudios."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "obtener_materias_faltantes",
            "description": (
                "Devuelve las materias que el alumno aún no tiene aprobadas ni "
                "promocionadas en el plan de su carrera, más el total del plan y "
                "la cantidad pendiente. Usar SOLO cuando el alumno consulte por las materias que le faltan para "
                "recibirse, cuántas materias le quedan por cursar "
                "o su avance/porcentaje en la carrera."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "buscar_en_documentos",
            "description": (
                "Busca información institucional o sobre la universidad en documentos. Usar SOLO cuando el alumno haga una pregunta "
                "sobre un tema institucional/académico o sobre a la universidad que no puedas responder con otras herramientas. "
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "consulta_semantica": {
                        "type": "string",
                        "description": "Pregunta o tema a buscar en los documentos",
                    }
                },
                "required": ["consulta_semantica"],
            },
        },
    },
]
