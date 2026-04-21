"""Runner de evaluación de memoria conversacional híbrida (sección 6.5 de la tesis).

Ejecuta los diálogos multi-turno definidos en scripts/eval/memory_dataset.jsonl y
captura, por cada turno, el estado observable del sistema de memoria:
- filas totales en `conversaciones` para el alumno,
- existencia y longitud del resumen en `resumenes`,
- tools invocadas (vía logs/requests.log),
- keywords presentes/ausentes en la respuesta,
- latencia de extremo a extremo.

Al finalizar MEM-B (que cruza UMBRAL_SUMARIZACION) se captura además un snapshot
del resumen persistido, que se usa en la sección 6.5 para analizar la calidad de
la compresión (propiedad f).

Precondiciones (idénticas a run_eval.py):
- Backend corriendo en http://localhost:8000.
- PostgreSQL en localhost:5432 con la base asistente_academico seedeada.
- Ollama en localhost:11434 con el modelo pull-eado.

Uso:
    python scripts/eval/run_memory_eval.py
    python scripts/eval/run_memory_eval.py --only MEM-A

Output:
    scripts/eval/memory_results.jsonl   (una línea por turno)
    scripts/eval/memory_summary.json    (snapshot del resumen final de MEM-B + metadatos)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

import asyncpg
import httpx


REPO_ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = REPO_ROOT / "scripts" / "eval" / "memory_dataset.jsonl"
RESULTS_PATH = REPO_ROOT / "scripts" / "eval" / "memory_results.jsonl"
SUMMARY_PATH = REPO_ROOT / "scripts" / "eval" / "memory_summary.json"
LOG_PATH = REPO_ROOT / "logs" / "requests.log"

BASE_URL = "http://localhost:8000"
PASSWORD = "password123"
DB_DSN = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:admin@localhost:5432/asistente_academico",
)

LOG_SETTLE_SLEEP = 0.3
LOG_RETRY_ATTEMPTS = 5
LOG_RETRY_SLEEP = 0.4
HTTP_TIMEOUT = 180.0
SLEEP_ENTRE_REQUESTS = 0.6
SUMARIZACION_SETTLE_SLEEP = 1.5  # la sumarización dispara tras guardar; esperar a que Ollama responda


def cargar_dataset() -> list[dict]:
    with DATASET_PATH.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def login(client: httpx.Client, legajo: str) -> tuple[str, int]:
    r = client.post(
        f"{BASE_URL}/api/auth/login",
        json={"legajo": legajo, "password": PASSWORD},
    )
    r.raise_for_status()
    data = r.json()
    return data["token"], data["perfil"]["id_alumno"]


def enviar_chat(client: httpx.Client, token: str, mensaje: str) -> tuple[str, str | None]:
    chunks: list[str] = []
    error: str | None = None
    try:
        with client.stream(
            "POST",
            f"{BASE_URL}/api/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"mensaje": mensaje},
            timeout=HTTP_TIMEOUT,
        ) as resp:
            resp.raise_for_status()
            for raw_line in resp.iter_lines():
                if not raw_line or not raw_line.startswith("data: "):
                    continue
                payload = json.loads(raw_line[len("data: "):])
                tipo = payload.get("tipo")
                if tipo == "chunk":
                    chunks.append(payload.get("contenido", ""))
                elif tipo == "error":
                    error = payload.get("mensaje", "error sin mensaje")
                elif tipo == "fin":
                    break
    except httpx.HTTPError as exc:
        error = f"HTTPError: {exc}"
    return "".join(chunks), error


def offset_log_actual() -> int:
    return LOG_PATH.stat().st_size if LOG_PATH.exists() else 0


def leer_log_correlado(offset_inicial: int, mensaje: str, id_alumno_esperado: int) -> dict | None:
    for _ in range(LOG_RETRY_ATTEMPTS):
        time.sleep(LOG_SETTLE_SLEEP)
        if not LOG_PATH.exists():
            continue
        with LOG_PATH.open("rb") as fh:
            fh.seek(offset_inicial)
            data = fh.read()
        if not data:
            time.sleep(LOG_RETRY_SLEEP)
            continue
        candidato = None
        for line in data.decode("utf-8", errors="replace").splitlines():
            idx = line.find("{")
            if idx < 0:
                continue
            try:
                payload = json.loads(line[idx:])
            except json.JSONDecodeError:
                continue
            if (
                payload.get("mensaje_usuario") == mensaje
                and payload.get("id_alumno") == id_alumno_esperado
            ):
                candidato = payload
        if candidato is not None:
            return candidato
        time.sleep(LOG_RETRY_SLEEP)
    return None


async def inspeccionar_memoria(pool: asyncpg.Pool, id_alumno: int) -> dict:
    """Lee contadores y estado del resumen directamente de la DB."""
    count = await pool.fetchval(
        "SELECT count(*) FROM conversaciones WHERE id_alumno = $1", id_alumno
    )
    resumen_row = await pool.fetchrow(
        "SELECT contenido, actualizado FROM resumenes WHERE id_alumno = $1", id_alumno
    )
    resumen_contenido = resumen_row["contenido"] if resumen_row else None
    return {
        "filas_conversaciones": int(count),
        "resumen_presente": resumen_row is not None,
        "resumen_chars": len(resumen_contenido) if resumen_contenido else 0,
        "resumen_contenido": resumen_contenido,
    }


def evaluar_respuesta(respuesta: str, debe_contener: list[str], no_debe_contener: list[str]) -> dict:
    respuesta_lower = respuesta.lower()
    presentes = [k for k in debe_contener if k.lower() in respuesta_lower]
    faltantes = [k for k in debe_contener if k.lower() not in respuesta_lower]
    prohibidos_presentes = [k for k in (no_debe_contener or []) if k.lower() in respuesta_lower]
    return {
        "keywords_presentes": presentes,
        "keywords_faltantes": faltantes,
        "prohibidos_presentes": prohibidos_presentes,
        "respuesta_correcta": (not faltantes) and (not prohibidos_presentes),
    }


async def ejecutar_dialogo(
    dialogo: dict,
    pool: asyncpg.Pool,
    client: httpx.Client,
    out_fh,
) -> dict:
    """Ejecuta un diálogo completo y devuelve un resumen ejecutivo para memory_summary.json."""
    dialogo_id = dialogo["dialogo_id"]
    legajo = dialogo["alumno_legajo"]

    # Login (limpia memoria del alumno)
    token, id_alumno = login(client, legajo)

    # Confirmar limpieza post-login
    estado_inicial = await inspeccionar_memoria(pool, id_alumno)
    assert estado_inicial["filas_conversaciones"] == 0, (
        f"[{dialogo_id}] memoria no limpia tras login: {estado_inicial}"
    )
    assert not estado_inicial["resumen_presente"], (
        f"[{dialogo_id}] resumen residual tras login: {estado_inicial}"
    )
    print(f"[{dialogo_id}] login OK (id_alumno={id_alumno}, memoria limpia)")

    ultimo_chat = 0.0
    turnos_registrados: list[dict] = []

    for turno_cfg in dialogo["turnos"]:
        turno = turno_cfg["turno"]
        mensaje = turno_cfg["mensaje"]
        debe = turno_cfg.get("debe_contener", [])
        no_debe = turno_cfg.get("no_debe_contener", [])

        # Pacing rate_limit
        transcurrido = time.time() - ultimo_chat
        if transcurrido < SLEEP_ENTRE_REQUESTS:
            time.sleep(SLEEP_ENTRE_REQUESTS - transcurrido)

        # Leer estado ANTES del turno
        estado_previo = await inspeccionar_memoria(pool, id_alumno)

        t0 = time.time()
        offset = offset_log_actual()
        respuesta, error = enviar_chat(client, token, mensaje)
        duracion_turno_s = time.time() - t0
        ultimo_chat = time.time()

        # Dar margen para que la sumarización asíncrona termine (si fue disparada)
        time.sleep(SUMARIZACION_SETTLE_SLEEP)

        log_entry = leer_log_correlado(offset, mensaje, id_alumno)
        tools_invocadas = (
            sorted({t["nombre"] for t in log_entry.get("tools", [])})
            if log_entry else []
        )
        clasificacion = log_entry.get("clasificacion") if log_entry else None
        duracion_log_ms = log_entry.get("duracion_total_ms") if log_entry else None

        # Estado DESPUÉS del turno
        estado_post = await inspeccionar_memoria(pool, id_alumno)
        # No persistimos el contenido del resumen por turno, sólo tamaño (evita inflar el jsonl)
        dispara_sumarizacion = (
            estado_post["resumen_presente"] and not estado_previo["resumen_presente"]
        )

        metricas = evaluar_respuesta(respuesta, debe, no_debe)

        fila = {
            "dialogo_id": dialogo_id,
            "turno": turno,
            "mensaje": mensaje,
            "respuesta": respuesta,
            "error": error,
            "clasificacion": clasificacion,
            "tools_invocadas": tools_invocadas,
            "duracion_turno_s": round(duracion_turno_s, 2),
            "duracion_log_ms": duracion_log_ms,
            "filas_conversaciones_previas": estado_previo["filas_conversaciones"],
            "filas_conversaciones_post": estado_post["filas_conversaciones"],
            "resumen_presente_previo": estado_previo["resumen_presente"],
            "resumen_presente_post": estado_post["resumen_presente"],
            "resumen_chars_post": estado_post["resumen_chars"],
            "dispara_sumarizacion_en_este_turno": dispara_sumarizacion,
            "debe_contener": debe,
            "no_debe_contener": no_debe,
            **metricas,
        }
        out_fh.write(json.dumps(fila, ensure_ascii=False) + "\n")
        out_fh.flush()
        turnos_registrados.append(fila)

        marca = "OK" if metricas["respuesta_correcta"] else "--"
        sum_marca = "SUM" if dispara_sumarizacion else "   "
        print(
            f"  [{dialogo_id}] T{turno:02d} resp={marca} {sum_marca} "
            f"conv={estado_previo['filas_conversaciones']}->{estado_post['filas_conversaciones']} "
            f"({duracion_turno_s:.1f}s) tools={tools_invocadas or '-'}"
        )

    # Snapshot final del resumen (para calidad — propiedad f)
    estado_final = await inspeccionar_memoria(pool, id_alumno)

    # Verificación de keywords esperadas en el resumen
    resumen_keywords_check = None
    if "resumen_debe_contener" in dialogo and estado_final["resumen_contenido"]:
        resumen_lower = estado_final["resumen_contenido"].lower()
        kw = dialogo["resumen_debe_contener"]
        resumen_keywords_check = {
            "esperadas": kw,
            "presentes": [k for k in kw if k.lower() in resumen_lower],
            "faltantes": [k for k in kw if k.lower() not in resumen_lower],
        }

    return {
        "dialogo_id": dialogo_id,
        "alumno_legajo": legajo,
        "id_alumno": id_alumno,
        "turnos_ejecutados": len(turnos_registrados),
        "turnos_correctos": sum(1 for t in turnos_registrados if t["respuesta_correcta"]),
        "sumarizacion_disparada": any(t["dispara_sumarizacion_en_este_turno"] for t in turnos_registrados),
        "turno_sumarizacion": next(
            (t["turno"] for t in turnos_registrados if t["dispara_sumarizacion_en_este_turno"]),
            None,
        ),
        "estado_final": {
            "filas_conversaciones": estado_final["filas_conversaciones"],
            "resumen_presente": estado_final["resumen_presente"],
            "resumen_chars": estado_final["resumen_chars"],
            "resumen_contenido": estado_final["resumen_contenido"],
        },
        "resumen_keywords_check": resumen_keywords_check,
    }


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", type=str, default=None, help="IDs de diálogo (ej: MEM-A)")
    parser.add_argument("--output", type=str, default=str(RESULTS_PATH))
    args = parser.parse_args()

    dialogos = cargar_dataset()
    if args.only:
        ids = {x.strip() for x in args.only.split(",") if x.strip()}
        dialogos = [d for d in dialogos if d["dialogo_id"] in ids]
        if not dialogos:
            print(f"[!] Ningún diálogo matchea {ids}", file=sys.stderr)
            return 2

    total_turnos = sum(len(d["turnos"]) for d in dialogos)
    print(f"[i] Diálogos: {len(dialogos)} | turnos totales: {total_turnos}")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    pool = await asyncpg.create_pool(DB_DSN, min_size=1, max_size=2)
    summaries: list[dict] = []
    try:
        with output_path.open("w", encoding="utf-8") as out, httpx.Client(timeout=30.0) as client:
            for dialogo in dialogos:
                resumen = await ejecutar_dialogo(dialogo, pool, client, out)
                summaries.append(resumen)
    finally:
        await pool.close()

    SUMMARY_PATH.write_text(
        json.dumps({"dialogos": summaries}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[i] Resultados por turno en {output_path}")
    print(f"[i] Snapshot ejecutivo en {SUMMARY_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
