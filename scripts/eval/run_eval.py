"""Runner de evaluación para la sección 6.2 de la tesis.

Precondiciones (responsabilidad del operador):
- Backend corriendo en http://localhost:8000 (uvicorn app.main:app --port 8000).
- PostgreSQL escuchando en localhost:5432 con la base asistente_academico seedeada.
- Ollama escuchando en localhost:11434 con los modelos pull-eados.

Uso:
    python scripts/eval/run_eval.py                        # corrida completa (todos los casos, N=3)
    python scripts/eval/run_eval.py --runs 1               # smoke test (N=1)
    python scripts/eval/run_eval.py --only HA-01,CO-01     # subset de casos
    python scripts/eval/run_eval.py --runs 1 --only HA-01  # smoke test mínimo

Output: scripts/eval/results.jsonl (una línea por corrida individual).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import httpx


REPO_ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = REPO_ROOT / "scripts" / "eval" / "dataset.jsonl"
RESULTS_PATH = REPO_ROOT / "scripts" / "eval" / "results.jsonl"
LOG_PATH = REPO_ROOT / "logs" / "requests.log"

BASE_URL = "http://localhost:8000"
PASSWORD = "password123"
DEFAULT_RUNS_PER_CASE = 3
LOG_SETTLE_SLEEP = 0.3      # margen para que RequestLog.emit() flushee
LOG_RETRY_ATTEMPTS = 5      # reintentos al leer el log (por si tarda)
LOG_RETRY_SLEEP = 0.4
HTTP_TIMEOUT = 180.0        # generoso: tools + LLM streaming pueden tardar
SLEEP_ENTRE_REQUESTS = 0.6  # 120 req/60s por alumno (rate_limit.py) → 0.5s mínimo, 0.6s da margen


def cargar_dataset() -> list[dict]:
    with DATASET_PATH.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def login(client: httpx.Client, legajo: str) -> str:
    r = client.post(
        f"{BASE_URL}/api/auth/login",
        json={"legajo": legajo, "password": PASSWORD},
    )
    r.raise_for_status()
    return r.json()["token"]


def enviar_chat(client: httpx.Client, token: str, mensaje: str) -> tuple[str, str | None]:
    """Devuelve (respuesta_completa, error). error=None si todo ok."""
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


def leer_log_correlado(offset_inicial: int, mensaje: str, id_alumno_esperado: int) -> dict | None:
    """Lee las líneas nuevas del log y devuelve la entrada que matchea
    mensaje_usuario + id_alumno. Reintenta para acomodar el flush asíncrono.
    """
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
        # Cada línea: "<timestamp> INFO asistente.request <json>"
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
                candidato = payload  # quedarse con la última coincidencia
        if candidato is not None:
            return candidato
        time.sleep(LOG_RETRY_SLEEP)
    return None


def offset_log_actual() -> int:
    return LOG_PATH.stat().st_size if LOG_PATH.exists() else 0


def evaluar_corrida(caso: dict, log_entry: dict | None, respuesta: str, error: str | None) -> dict:
    """Computa métricas booleanas/numéricas para una corrida individual."""
    tools_esperadas = set(caso.get("tools_esperadas", []))
    tools_prohibidas = caso.get("tools_prohibidas", [])
    no_tools_permitidas = tools_prohibidas == ["*"]

    if log_entry is None or error is not None:
        return {
            "error_runner": error or "log_entry_no_encontrada",
            "intent_correcto": False,
            "tools_match_exacto": False,
            "respuesta_correcta": False,
        }

    clasificacion = log_entry.get("clasificacion")
    tools_invocadas = {t["nombre"] for t in log_entry.get("tools", [])}
    duracion_ms = log_entry.get("duracion_total_ms")
    llm_calls = log_entry.get("llm_calls", [])

    intent_correcto = clasificacion == caso["intent_esperado"]
    tools_match_exacto = tools_invocadas == tools_esperadas
    tools_faltantes = sorted(tools_esperadas - tools_invocadas)
    tools_de_mas = sorted(tools_invocadas - tools_esperadas)
    alguna_correcta = bool(tools_invocadas & tools_esperadas) if tools_esperadas else (
        len(tools_invocadas) == 0 if no_tools_permitidas else True
    )

    respuesta_lower = respuesta.lower()
    debe = caso.get("respuesta_debe_contener", []) or []
    no_debe = caso.get("respuesta_no_debe_contener", []) or []
    keywords_presentes = [k for k in debe if k.lower() in respuesta_lower]
    keywords_faltantes = [k for k in debe if k.lower() not in respuesta_lower]
    prohibidos_presentes = [k for k in no_debe if k.lower() in respuesta_lower]

    respuesta_correcta = (not keywords_faltantes) and (not prohibidos_presentes)

    return {
        "error_runner": None,
        "clasificacion_observada": clasificacion,
        "intent_correcto": intent_correcto,
        "tools_invocadas": sorted(tools_invocadas),
        "tools_match_exacto": tools_match_exacto,
        "tools_faltantes": tools_faltantes,
        "tools_de_mas": tools_de_mas,
        "alguna_correcta": alguna_correcta,
        "no_invoco_tools": len(tools_invocadas) == 0,
        "respeta_tools_prohibidas": (not no_tools_permitidas) or (len(tools_invocadas) == 0),
        "keywords_presentes": keywords_presentes,
        "keywords_faltantes": keywords_faltantes,
        "prohibidos_presentes": prohibidos_presentes,
        "respuesta_correcta": respuesta_correcta,
        "respuesta_chars": len(respuesta),
        "duracion_total_ms": duracion_ms,
        "llm_calls": llm_calls,
        "request_id": log_entry.get("request_id"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--runs", type=int, default=DEFAULT_RUNS_PER_CASE,
                        help=f"corridas por caso (default {DEFAULT_RUNS_PER_CASE})")
    parser.add_argument("--only", type=str, default=None,
                        help="lista de IDs de caso separados por coma (ej: HA-01,CO-01)")
    parser.add_argument("--output", type=str, default=str(RESULTS_PATH),
                        help="ruta del jsonl de salida")
    args = parser.parse_args()

    casos = cargar_dataset()
    if args.only:
        ids = {x.strip() for x in args.only.split(",") if x.strip()}
        casos = [c for c in casos if c["id"] in ids]
        if not casos:
            print(f"[!] Ningún caso matchea {ids}", file=sys.stderr)
            return 2

    print(f"[i] Casos: {len(casos)} | corridas por caso: {args.runs} | total: {len(casos) * args.runs}")
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Pacing por alumno para respetar el rate limit (10 req/60s en rate_limit.py)
    ultimo_chat_por_alumno: dict[str, float] = {}

    with output_path.open("w", encoding="utf-8") as out, httpx.Client(timeout=30.0) as client:
        for caso_idx, caso in enumerate(casos, 1):
            for run_idx in range(args.runs):
                t_inicio = time.time()
                # Esperar para respetar rate limit del alumno
                legajo = caso["alumno_legajo"]
                ultimo = ultimo_chat_por_alumno.get(legajo)
                if ultimo is not None:
                    transcurrido = time.time() - ultimo
                    if transcurrido < SLEEP_ENTRE_REQUESTS:
                        time.sleep(SLEEP_ENTRE_REQUESTS - transcurrido)
                # Login antes de cada corrida (limpia memoria — ver auth.py:28-29)
                try:
                    login_resp = client.post(
                        f"{BASE_URL}/api/auth/login",
                        json={"legajo": caso["alumno_legajo"], "password": PASSWORD},
                    )
                    login_resp.raise_for_status()
                    login_data = login_resp.json()
                    token = login_data["token"]
                    id_alumno = login_data["perfil"]["id_alumno"]
                except httpx.HTTPError as exc:
                    print(f"[!] {caso['id']} run {run_idx}: login falló: {exc}", file=sys.stderr)
                    out.write(json.dumps({
                        "caso_id": caso["id"], "run_idx": run_idx,
                        "error_runner": f"login_failed: {exc}",
                    }, ensure_ascii=False) + "\n")
                    continue

                offset = offset_log_actual()
                respuesta, error = enviar_chat(client, token, caso["mensaje"])
                ultimo_chat_por_alumno[legajo] = time.time()
                log_entry = leer_log_correlado(offset, caso["mensaje"], id_alumno)

                metricas = evaluar_corrida(caso, log_entry, respuesta, error)
                fila = {
                    "caso_id": caso["id"],
                    "categoria": caso["categoria"],
                    "alumno_legajo": caso["alumno_legajo"],
                    "mensaje": caso["mensaje"],
                    "intent_esperado": caso["intent_esperado"],
                    "tools_esperadas": caso["tools_esperadas"],
                    "tools_prohibidas": caso.get("tools_prohibidas", []),
                    "respuesta_debe_contener": caso.get("respuesta_debe_contener", []),
                    "respuesta_no_debe_contener": caso.get("respuesta_no_debe_contener", []),
                    "run_idx": run_idx,
                    "respuesta": respuesta,
                    **metricas,
                }
                out.write(json.dumps(fila, ensure_ascii=False) + "\n")
                out.flush()

                t_total = time.time() - t_inicio
                marca_intent = "OK" if metricas.get("intent_correcto") else "--"
                marca_tools = "OK" if metricas.get("tools_match_exacto") else "--"
                marca_resp = "OK" if metricas.get("respuesta_correcta") else "--"
                err_extra = f" [ERR={metricas.get('error_runner')}]" if metricas.get("error_runner") else ""
                print(f"[{caso_idx:>2}/{len(casos)}][{caso['id']}#{run_idx}] "
                      f"intent={marca_intent} tools={marca_tools} resp={marca_resp} "
                      f"({t_total:.1f}s){err_extra}")

    print(f"[i] Resultados escritos en {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
