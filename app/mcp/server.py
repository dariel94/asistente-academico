from datetime import datetime
from typing import Any, Callable, Coroutine

from app.models.schemas import SessionContext


def periodo_vigente() -> str:
    now = datetime.now()
    sufijo = "1C" if now.month <= 7 else "2C"
    return f"{now.year}-{sufijo}"


# Catálogo de tools en formato OpenAI para enviar a Ollama
TOOLS_CATALOG = [
    {
        "type": "function",
        "function": {
            "name": "obtener_historia_academica",
            "description": (
                "Obtiene el historial académico completo del alumno autenticado: "
                "materias cursadas con su estado, notas y período. Usar cuando el alumno pregunte "
                "por notas, historial académico, historia académica, materias cursadas."
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
                "horarios. Usar cuando el alumno pregunte por una materia específica."
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
                "materia, comisión, día, horario, aula, sede y profesor. Usar cuando "
                "pregunte por sus horarios, agenda, qué materias está cursando (en curso), "
                "a qué se inscribió o qué tiene este cuatrimestre."
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
                "y que no tengan inscripción activa. Usar cuando el alumno pregunte "
                "qué materias tiene disponibles para cursar o a que materias puede inscribirse el proximo periodo."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "buscar_en_documentos",
            "description": (
                "Busca información en los documentos institucionales. Usar SOLO cuando el alumno haga preguntas "
                "sobre reglamentos o información institucional."
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
    {
        "type": "function",
        "function": {
            "name": "obtener_plan_de_estudios",
            "description": (
                "Obtiene el plan de estudios completo de la carrera del alumno: "
                "todas las materias con año, cuatrimestre y carga horaria, más el "
                "total de materias. Usar cuando el alumno pida el plan de estudios."
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
                "la cantidad pendiente. Usar cuando pregunte qué le falta para "
                "recibirse, para terminar la carrera, cuántas materias le quedan "
                "o su avance/porcentaje."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]


ToolFunc = Callable[..., Coroutine[Any, Any, Any]]


class MCPServer:
    def __init__(self):
        self._tools: dict[str, ToolFunc] = {}

    def register(self, name: str, func: ToolFunc) -> None:
        self._tools[name] = func

    def has(self, name: str) -> bool:
        return name in self._tools

    async def dispatch(
        self, tool_name: str, args: dict, ctx: SessionContext, pool
    ) -> str:
        func = self._tools.get(tool_name)
        if not func:
            return f"Herramienta '{tool_name}' no encontrada."
        return await func(ctx=ctx, pool=pool, **args)
