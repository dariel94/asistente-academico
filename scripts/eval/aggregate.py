"""Agregador de resultados de la evaluación.

Lee scripts/eval/results.jsonl y produce:
- scripts/eval/summary.json — métricas agregadas para citar en la tesis.
- scripts/eval/report.md   — reporte legible (matriz de confusión, casos con falla, etc.).

Uso:
    python scripts/eval/aggregate.py
"""

from __future__ import annotations

import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
RESULTS_PATH = REPO_ROOT / "scripts" / "eval" / "results.jsonl"
SUMMARY_PATH = REPO_ROOT / "scripts" / "eval" / "summary.json"
REPORT_PATH = REPO_ROOT / "scripts" / "eval" / "report.md"


def cargar_results() -> list[dict]:
    with RESULTS_PATH.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def matriz_confusion(rows: list[dict]) -> dict:
    counts = Counter()
    for r in rows:
        if r.get("error_runner"):
            continue
        esp = r["intent_esperado"]
        obs = r.get("clasificacion_observada")
        counts[(esp, obs)] += 1

    tp_aca = counts[("ACADEMICA", "ACADEMICA")]
    fn_aca = counts[("ACADEMICA", "CONVERSACION")]
    tp_con = counts[("CONVERSACION", "CONVERSACION")]
    fp_aca = counts[("CONVERSACION", "ACADEMICA")]
    total = tp_aca + fn_aca + tp_con + fp_aca

    accuracy = (tp_aca + tp_con) / total if total else 0.0
    prec_aca = tp_aca / (tp_aca + fp_aca) if (tp_aca + fp_aca) else 0.0
    rec_aca = tp_aca / (tp_aca + fn_aca) if (tp_aca + fn_aca) else 0.0
    prec_con = tp_con / (tp_con + fn_aca) if (tp_con + fn_aca) else 0.0
    rec_con = tp_con / (tp_con + fp_aca) if (tp_con + fp_aca) else 0.0

    return {
        "TP_academica": tp_aca,
        "FN_academica": fn_aca,
        "TP_conversacion": tp_con,
        "FP_academica": fp_aca,
        "total_corridas": total,
        "accuracy": round(accuracy, 4),
        "precision_academica": round(prec_aca, 4),
        "recall_academica": round(rec_aca, 4),
        "precision_conversacion": round(prec_con, 4),
        "recall_conversacion": round(rec_con, 4),
    }


def metricas_tool_calling(rows: list[dict]) -> dict:
    academicas = [r for r in rows if r["intent_esperado"] == "ACADEMICA" and not r.get("error_runner")]
    conversacionales = [r for r in rows if r["intent_esperado"] == "CONVERSACION" and not r.get("error_runner")]
    total_aca = len(academicas)
    total_con = len(conversacionales)

    return {
        "n_corridas_academicas": total_aca,
        "n_corridas_conversacionales": total_con,
        "match_exacto": round(sum(1 for r in academicas if r.get("tools_match_exacto")) / total_aca, 4) if total_aca else 0.0,
        "alguna_correcta": round(sum(1 for r in academicas if r.get("alguna_correcta")) / total_aca, 4) if total_aca else 0.0,
        "ninguna_invocada": round(sum(1 for r in academicas if r.get("no_invoco_tools")) / total_aca, 4) if total_aca else 0.0,
        "tools_de_mas_promedio": round(
            statistics.mean(len(r.get("tools_de_mas", [])) for r in academicas), 4
        ) if total_aca else 0.0,
        "no_invocaron_en_conversacion": round(
            sum(1 for r in conversacionales if r.get("no_invoco_tools")) / total_con, 4
        ) if total_con else 0.0,
    }


def metricas_por_tool(rows: list[dict]) -> dict:
    """Tasa de match_exacto por cada tool esperada."""
    por_tool: dict[str, list[bool]] = defaultdict(list)
    for r in rows:
        if r.get("error_runner") or r["intent_esperado"] != "ACADEMICA":
            continue
        for tool in r.get("tools_esperadas", []):
            por_tool[tool].append(bool(r.get("tools_match_exacto")))
    return {
        tool: {
            "n": len(vals),
            "match_exacto_rate": round(sum(vals) / len(vals), 4) if vals else 0.0,
        }
        for tool, vals in sorted(por_tool.items())
    }


def metricas_contenido(rows: list[dict]) -> dict:
    validos = [r for r in rows if not r.get("error_runner")]
    n = len(validos)
    if not n:
        return {"n": 0, "respuesta_correcta": 0.0}
    return {
        "n": n,
        "respuesta_correcta": round(sum(1 for r in validos if r.get("respuesta_correcta")) / n, 4),
        "promedio_chars_respuesta": round(statistics.mean(r.get("respuesta_chars", 0) for r in validos), 1),
    }


def consistencia_por_caso(rows: list[dict]) -> dict:
    """Por cada caso_id, evalúa si las N corridas coinciden en intent / tools / respuesta."""
    por_caso: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        if r.get("error_runner"):
            continue
        por_caso[r["caso_id"]].append(r)

    intent_consistente = 0
    tools_consistente = 0
    respuesta_consistente = 0
    detalle: dict[str, dict] = {}
    for caso_id, runs in sorted(por_caso.items()):
        intents = {r.get("clasificacion_observada") for r in runs}
        tools_sets = {tuple(sorted(r.get("tools_invocadas") or [])) for r in runs}
        respuestas = {bool(r.get("respuesta_correcta")) for r in runs}
        intent_ok = len(intents) == 1
        tools_ok = len(tools_sets) == 1
        resp_ok = len(respuestas) == 1
        if intent_ok:
            intent_consistente += 1
        if tools_ok:
            tools_consistente += 1
        if resp_ok:
            respuesta_consistente += 1
        detalle[caso_id] = {
            "n_runs": len(runs),
            "intent_consistente": intent_ok,
            "tools_consistentes": tools_ok,
            "respuesta_consistente": resp_ok,
        }

    n_casos = len(por_caso)
    return {
        "n_casos": n_casos,
        "intent_consistente_n_de_n": round(intent_consistente / n_casos, 4) if n_casos else 0.0,
        "tools_consistentes_n_de_n": round(tools_consistente / n_casos, 4) if n_casos else 0.0,
        "respuesta_consistente_n_de_n": round(respuesta_consistente / n_casos, 4) if n_casos else 0.0,
        "detalle": detalle,
    }


def metricas_latencia(rows: list[dict]) -> dict:
    valores = [r.get("duracion_total_ms") for r in rows
               if not r.get("error_runner") and r.get("duracion_total_ms") is not None]
    if not valores:
        return {"n": 0}
    valores_ord = sorted(valores)
    p95_idx = max(0, int(round(0.95 * len(valores_ord))) - 1)
    return {
        "n": len(valores),
        "min_ms": round(min(valores), 1),
        "media_ms": round(statistics.mean(valores), 1),
        "mediana_ms": round(statistics.median(valores), 1),
        "p95_ms": round(valores_ord[p95_idx], 1),
        "max_ms": round(max(valores), 1),
    }


def fallas(rows: list[dict]) -> dict:
    """Lista de runs con alguna falla, agrupados por tipo."""
    fallas_intent = []
    fallas_tools = []
    fallas_contenido = []
    fallas_runner = []
    for r in rows:
        if r.get("error_runner"):
            fallas_runner.append({"caso_id": r["caso_id"], "run_idx": r["run_idx"], "error": r["error_runner"]})
            continue
        if not r.get("intent_correcto"):
            fallas_intent.append({
                "caso_id": r["caso_id"], "run_idx": r["run_idx"],
                "esperado": r["intent_esperado"], "observado": r.get("clasificacion_observada"),
                "mensaje": r["mensaje"],
            })
        if not r.get("tools_match_exacto"):
            fallas_tools.append({
                "caso_id": r["caso_id"], "run_idx": r["run_idx"],
                "esperadas": r["tools_esperadas"], "invocadas": r.get("tools_invocadas"),
                "faltantes": r.get("tools_faltantes"), "de_mas": r.get("tools_de_mas"),
                "mensaje": r["mensaje"],
            })
        if not r.get("respuesta_correcta"):
            fallas_contenido.append({
                "caso_id": r["caso_id"], "run_idx": r["run_idx"],
                "keywords_faltantes": r.get("keywords_faltantes"),
                "prohibidos_presentes": r.get("prohibidos_presentes"),
                "mensaje": r["mensaje"],
            })
    return {
        "intent": fallas_intent,
        "tools": fallas_tools,
        "contenido": fallas_contenido,
        "runner": fallas_runner,
    }


def caso_filtrado_perfil(rows: list[dict]) -> dict:
    runs = [r for r in rows if r["caso_id"] == "FP-01"]
    if not runs:
        return {}
    invasiones = [r for r in runs if r.get("prohibidos_presentes")]
    return {
        "n_runs": len(runs),
        "respuesta_correcta_rate": round(sum(1 for r in runs if r.get("respuesta_correcta")) / len(runs), 4),
        "invasiones_otros_perfiles": [
            {"run_idx": r["run_idx"], "prohibidos_filtrados": r.get("prohibidos_presentes")}
            for r in invasiones
        ],
    }


def construir_summary(rows: list[dict]) -> dict:
    casos_unicos = sorted({r["caso_id"] for r in rows})
    n_corridas = len(rows)
    n_validas = sum(1 for r in rows if not r.get("error_runner"))
    return {
        "n_casos": len(casos_unicos),
        "n_corridas_totales": n_corridas,
        "n_corridas_validas": n_validas,
        "n_corridas_con_error_runner": n_corridas - n_validas,
        "clasificador": matriz_confusion(rows),
        "tool_calling": metricas_tool_calling(rows),
        "tool_calling_por_tool": metricas_por_tool(rows),
        "contenido": metricas_contenido(rows),
        "consistencia": consistencia_por_caso(rows),
        "latencia": metricas_latencia(rows),
        "filtrado_perfil": caso_filtrado_perfil(rows),
    }


def fmt_pct(x: float) -> str:
    return f"{x*100:.1f}%"


def construir_reporte(summary: dict, fallas_dict: dict) -> str:
    cl = summary["clasificador"]
    tc = summary["tool_calling"]
    co = summary["contenido"]
    co_consist = summary["consistencia"]
    lat = summary["latencia"]
    fp = summary["filtrado_perfil"]

    lines = []
    lines.append("# Reporte de Evaluación — Sección 6.2")
    lines.append("")
    lines.append(f"- **Casos:** {summary['n_casos']}")
    lines.append(f"- **Corridas totales:** {summary['n_corridas_totales']}")
    lines.append(f"- **Corridas válidas:** {summary['n_corridas_validas']}")
    if summary["n_corridas_con_error_runner"]:
        lines.append(f"- **Corridas con error de runner:** {summary['n_corridas_con_error_runner']}")
    lines.append("")

    lines.append("## 1. Clasificador de Intent")
    lines.append("")
    lines.append("| | Predicho ACADEMICA | Predicho CONVERSACION |")
    lines.append("|---|---:|---:|")
    lines.append(f"| **Real ACADEMICA** | {cl['TP_academica']} | {cl['FN_academica']} |")
    lines.append(f"| **Real CONVERSACION** | {cl['FP_academica']} | {cl['TP_conversacion']} |")
    lines.append("")
    lines.append(f"- Accuracy global: **{fmt_pct(cl['accuracy'])}**")
    lines.append(f"- Precisión ACADEMICA: {fmt_pct(cl['precision_academica'])}  ·  Recall ACADEMICA: {fmt_pct(cl['recall_academica'])}")
    lines.append(f"- Precisión CONVERSACION: {fmt_pct(cl['precision_conversacion'])}  ·  Recall CONVERSACION: {fmt_pct(cl['recall_conversacion'])}")
    lines.append("")

    lines.append("## 2. Tool Calling (rama académica)")
    lines.append("")
    lines.append(f"- Match exacto (mismo set de tools que el esperado): **{fmt_pct(tc['match_exacto'])}**")
    lines.append(f"- Al menos una tool esperada invocada: {fmt_pct(tc['alguna_correcta'])}")
    lines.append(f"- Ninguna tool invocada: {fmt_pct(tc['ninguna_invocada'])}")
    lines.append(f"- Tools de más promedio por corrida académica: {tc['tools_de_mas_promedio']}")
    lines.append(f"- Conversaciones sin invocar tools: {fmt_pct(tc['no_invocaron_en_conversacion'])}")
    lines.append("")
    lines.append("### Match exacto por tool esperada")
    lines.append("")
    lines.append("| Tool | n corridas | match exacto |")
    lines.append("|---|---:|---:|")
    for tool, m in summary["tool_calling_por_tool"].items():
        lines.append(f"| `{tool}` | {m['n']} | {fmt_pct(m['match_exacto_rate'])} |")
    lines.append("")

    lines.append("## 3. Contenido de la Respuesta")
    lines.append("")
    lines.append(f"- Respuesta correcta (todos los keywords requeridos + ningún prohibido): **{fmt_pct(co['respuesta_correcta'])}**")
    lines.append(f"- Largo promedio de respuesta: {co['promedio_chars_respuesta']} chars")
    lines.append("")

    lines.append("## 4. Consistencia entre Corridas")
    lines.append("")
    lines.append(f"- Casos con intent consistente N-de-N: **{fmt_pct(co_consist['intent_consistente_n_de_n'])}**")
    lines.append(f"- Casos con tools consistentes N-de-N: **{fmt_pct(co_consist['tools_consistentes_n_de_n'])}**")
    lines.append(f"- Casos con respuesta consistente N-de-N: **{fmt_pct(co_consist['respuesta_consistente_n_de_n'])}**")
    lines.append("")

    lines.append("## 5. Latencia")
    lines.append("")
    if lat.get("n"):
        lines.append(f"- n: {lat['n']}")
        lines.append(f"- mín: {lat['min_ms']} ms · media: {lat['media_ms']} ms · mediana: {lat['mediana_ms']} ms · p95: {lat['p95_ms']} ms · máx: {lat['max_ms']} ms")
    else:
        lines.append("- (sin datos)")
    lines.append("")

    lines.append("## 6. Filtrado por Perfil (caso FP-01)")
    lines.append("")
    if fp:
        lines.append(f"- n corridas: {fp['n_runs']}")
        lines.append(f"- Tasa de respuesta correcta: **{fmt_pct(fp['respuesta_correcta_rate'])}**")
        if fp["invasiones_otros_perfiles"]:
            lines.append("- **Invasiones detectadas (datos de otro alumno filtrados):**")
            for inv in fp["invasiones_otros_perfiles"]:
                lines.append(f"  - run #{inv['run_idx']}: {inv['prohibidos_filtrados']}")
        else:
            lines.append("- Sin invasiones de datos de otros alumnos.")
    lines.append("")

    lines.append("## 7. Casos con Falla (detalle)")
    lines.append("")
    lines.append("### Fallas de intent")
    if fallas_dict["intent"]:
        lines.append("")
        lines.append("| Caso | Run | Esperado | Observado | Mensaje |")
        lines.append("|---|---:|---|---|---|")
        for f in fallas_dict["intent"]:
            lines.append(f"| {f['caso_id']} | {f['run_idx']} | {f['esperado']} | {f['observado']} | {f['mensaje']} |")
    else:
        lines.append("Ninguna.")
    lines.append("")

    lines.append("### Fallas de tool calling")
    if fallas_dict["tools"]:
        lines.append("")
        lines.append("| Caso | Run | Esperadas | Invocadas | Faltantes | De más |")
        lines.append("|---|---:|---|---|---|---|")
        for f in fallas_dict["tools"]:
            lines.append(f"| {f['caso_id']} | {f['run_idx']} | {f['esperadas']} | {f['invocadas']} | {f['faltantes']} | {f['de_mas']} |")
    else:
        lines.append("Ninguna.")
    lines.append("")

    lines.append("### Fallas de contenido")
    if fallas_dict["contenido"]:
        lines.append("")
        lines.append("| Caso | Run | Keywords faltantes | Prohibidos presentes |")
        lines.append("|---|---:|---|---|")
        for f in fallas_dict["contenido"]:
            lines.append(f"| {f['caso_id']} | {f['run_idx']} | {f['keywords_faltantes']} | {f['prohibidos_presentes']} |")
    else:
        lines.append("Ninguna.")
    lines.append("")

    if fallas_dict["runner"]:
        lines.append("### Errores de runner")
        lines.append("")
        for f in fallas_dict["runner"]:
            lines.append(f"- {f['caso_id']} run {f['run_idx']}: {f['error']}")
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    rows = cargar_results()
    if not rows:
        print("[!] results.jsonl está vacío. Corré primero scripts/eval/run_eval.py")
        return 1

    summary = construir_summary(rows)
    fallas_dict = fallas(rows)

    SUMMARY_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    REPORT_PATH.write_text(construir_reporte(summary, fallas_dict), encoding="utf-8")

    print(f"[i] {SUMMARY_PATH.relative_to(REPO_ROOT)} escrito")
    print(f"[i] {REPORT_PATH.relative_to(REPO_ROOT)} escrito")
    print()
    cl = summary["clasificador"]
    tc = summary["tool_calling"]
    print(f"  Clasificador accuracy: {fmt_pct(cl['accuracy'])}  (TP_aca={cl['TP_academica']}, FN_aca={cl['FN_academica']}, TP_con={cl['TP_conversacion']}, FP_aca={cl['FP_academica']})")
    print(f"  Tool calling match exacto: {fmt_pct(tc['match_exacto'])}")
    print(f"  Respuesta correcta: {fmt_pct(summary['contenido']['respuesta_correcta'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
