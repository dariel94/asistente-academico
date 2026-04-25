"""Tests para `app.services.request_logger.RequestLog`.

Cubre la acumulación de tools y llamadas al LLM, los setters auxiliares y
la emisión final como una única línea JSON.
"""
import json
import logging
import re

import pytest

from app.services.request_logger import RequestLog, logger as req_logger


def test_estado_inicial():
    log = RequestLog(id_alumno=1, mensaje_usuario="hola")
    assert log.estado == "ok"
    assert log.error is None
    assert log.clasificacion is None
    assert log.tools == []
    assert log.llm_calls == []
    assert log.respuesta == ""
    # request_id debe ser un UUID v4 plausible
    assert re.match(r"^[0-9a-f-]{36}$", log.request_id)


def test_set_clasificacion_persiste_valor():
    log = RequestLog(1, "x")
    log.set_clasificacion("ACADEMICA")
    assert log.clasificacion == "ACADEMICA"


def test_record_llm_call_acumula_y_redondea():
    log = RequestLog(1, "x")
    log.record_llm_call(fase="clasificador", duracion_ms=482.27, prompt_tokens=313, eval_tokens=5)
    log.record_llm_call(fase="final_streaming", duracion_ms=1810.55, prompt_tokens=760, eval_tokens=98)
    assert len(log.llm_calls) == 2
    assert log.llm_calls[0]["fase"] == "clasificador"
    assert log.llm_calls[0]["duracion_ms"] == 482.3  # redondeo a 1 decimal
    assert log.llm_calls[1]["prompt_tokens"] == 760


def test_record_llm_call_acepta_tokens_none():
    log = RequestLog(1, "x")
    log.record_llm_call(fase="clasificador", duracion_ms=100.0)
    assert log.llm_calls[0]["prompt_tokens"] is None
    assert log.llm_calls[0]["eval_tokens"] is None


def test_record_tool_acumula_y_redondea():
    log = RequestLog(1, "x")
    log.record_tool(
        nombre="obtener_historia_academica",
        args={},
        duracion_ms=0.93,
        ok=True,
        resultado_chars=605,
    )
    assert log.tools[0]["nombre"] == "obtener_historia_academica"
    assert log.tools[0]["ok"] is True
    assert log.tools[0]["duracion_ms"] == 0.9
    assert log.tools[0]["error"] is None


def test_record_tool_con_error():
    log = RequestLog(1, "x")
    log.record_tool(
        nombre="obtener_inscripciones",
        args={"alumno": "X"},
        duracion_ms=2.0,
        ok=False,
        resultado_chars=0,
        error="TypeError: unexpected keyword 'alumno'",
    )
    assert log.tools[0]["ok"] is False
    assert "TypeError" in log.tools[0]["error"]


def test_set_respuesta_actualiza_contenido():
    log = RequestLog(1, "x")
    log.set_respuesta("¡Hola! ¿En qué puedo ayudarte?")
    assert log.respuesta == "¡Hola! ¿En qué puedo ayudarte?"


def test_set_error_marca_estado_y_formatea_mensaje():
    log = RequestLog(1, "x")
    log.set_error("ConnectError", "connection refused")
    assert log.estado == "error"
    assert log.error == "ConnectError: connection refused"


def test_emit_produce_una_unica_linea_json_valida(caplog):
    log = RequestLog(id_alumno=1, mensaje_usuario="hola")
    log.set_clasificacion("CONVERSACION")
    log.record_llm_call("clasificador", 100.0, 200, 5)
    log.set_respuesta("Hola!")

    with caplog.at_level(logging.INFO, logger=req_logger.name):
        log.emit()

    # Debe haber exactamente una línea de log
    assert len(caplog.records) == 1
    payload = json.loads(caplog.records[0].message)

    assert payload["id_alumno"] == 1
    assert payload["mensaje_usuario"] == "hola"
    assert payload["clasificacion"] == "CONVERSACION"
    assert payload["respuesta"] == "Hola!"
    assert payload["respuesta_chars"] == 5
    assert payload["estado"] == "ok"
    assert payload["error"] is None
    assert payload["llm_calls"][0]["fase"] == "clasificador"
    assert payload["request_id"] == log.request_id
    # duracion_total_ms debe ser >= 0
    assert payload["duracion_total_ms"] >= 0


def test_emit_serializa_unicode_sin_escapar(caplog):
    """`ensure_ascii=False` debe preservar caracteres en español."""
    log = RequestLog(1, "¿qué materias tengo?")
    log.set_respuesta("Tenés Álgebra y Análisis Matemático.")
    with caplog.at_level(logging.INFO, logger=req_logger.name):
        log.emit()
    msg = caplog.records[0].message
    assert "¿qué" in msg
    assert "Álgebra" in msg
    assert "\\u" not in msg  # nada escapado


def test_emit_propaga_estado_de_error(caplog):
    log = RequestLog(1, "x")
    log.set_error("TimeoutException", "Ollama no respondió")
    with caplog.at_level(logging.INFO, logger=req_logger.name):
        log.emit()
    payload = json.loads(caplog.records[0].message)
    assert payload["estado"] == "error"
    assert "TimeoutException" in payload["error"]
