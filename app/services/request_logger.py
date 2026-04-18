import json
import logging
import time
import uuid
from typing import Any

logger = logging.getLogger("asistente.request")


class RequestLog:
    """Acumula métricas de una request del agente y emite una línea JSON al cerrar."""

    def __init__(self, id_alumno: int | str, mensaje_usuario: str):
        self.request_id = str(uuid.uuid4())
        self.id_alumno = id_alumno
        self.mensaje_usuario = mensaje_usuario
        self.tools: list[dict[str, Any]] = []
        self.llm_calls: list[dict[str, Any]] = []
        self.respuesta: str = ""
        self.estado: str = "ok"
        self.error: str | None = None
        self.clasificacion: str | None = None
        self._t0 = time.perf_counter()

    def set_clasificacion(self, valor: str) -> None:
        self.clasificacion = valor

    def record_llm_call(
        self,
        fase: str,
        duracion_ms: float,
        prompt_tokens: int | None = None,
        eval_tokens: int | None = None,
    ) -> None:
        self.llm_calls.append(
            {
                "fase": fase,
                "duracion_ms": round(duracion_ms, 1),
                "prompt_tokens": prompt_tokens,
                "eval_tokens": eval_tokens,
            }
        )

    def record_tool(
        self,
        nombre: str,
        args: dict,
        duracion_ms: float,
        ok: bool,
        resultado_chars: int,
        error: str | None = None,
    ) -> None:
        self.tools.append(
            {
                "nombre": nombre,
                "args": args,
                "duracion_ms": round(duracion_ms, 1),
                "ok": ok,
                "resultado_chars": resultado_chars,
                "error": error,
            }
        )

    def set_respuesta(self, respuesta: str) -> None:
        self.respuesta = respuesta

    def set_error(self, tipo: str, mensaje: str) -> None:
        self.estado = "error"
        self.error = f"{tipo}: {mensaje}"

    def emit(self) -> None:
        payload = {
            "request_id": self.request_id,
            "id_alumno": self.id_alumno,
            "estado": self.estado,
            "clasificacion": self.clasificacion,
            "duracion_total_ms": round((time.perf_counter() - self._t0) * 1000, 1),
            "mensaje_usuario": self.mensaje_usuario,
            "tools": self.tools,
            "llm_calls": self.llm_calls,
            "respuesta": self.respuesta,
            "respuesta_chars": len(self.respuesta),
            "error": self.error,
        }
        logger.info(json.dumps(payload, ensure_ascii=False))
