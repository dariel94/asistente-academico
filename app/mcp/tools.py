import json

import httpx

from app import config
from app.mcp.server import MCPServer, periodo_vigente
from app.models.schemas import SessionContext


def _json_result(data) -> str:
    return json.dumps(data, ensure_ascii=False, default=str)


# ─── 1. obtener_historia_academica ───────────────────────────────────────────

async def obtener_historia_academica(ctx: SessionContext, pool, **_kwargs) -> str:
    rows = await pool.fetch(
        """
        SELECT m.nombre AS materia, ha.estado,
               ha.nota_cursada AS nota_cursada,
               ha.nota_final AS nota_final,
               ha.periodo, c.nombre AS carrera
        FROM historia_academica ha
        JOIN materias m ON m.id_materia = ha.id_materia
        JOIN carreras c ON c.id_carrera = m.id_carrera
        WHERE ha.id_alumno = $1
        ORDER BY ha.fecha DESC
        """,
        ctx.id_alumno,
    )
    if not rows:
        return "No se encontraron registros académicos para este alumno."
    return _json_result([dict(r) for r in rows])


# ─── 2. obtener_materia ──────────────────────────────────────────────────────

async def obtener_materia(
    ctx: SessionContext, pool, nombre_materia: str = "", **_kwargs
) -> str:
    # Obtener carrera del alumno
    id_carrera = await pool.fetchval(
        "SELECT id_carrera FROM alumnos WHERE id_alumno = $1", ctx.id_alumno
    )

    # Buscar materias por coincidencia parcial dentro de la carrera
    materias = await pool.fetch(
        """
        SELECT id_materia, nombre, anio_plan, cuatrimestre, carga_horaria
        FROM materias
        WHERE id_carrera = $1 AND nombre ILIKE '%' || $2 || '%'
        """,
        id_carrera,
        nombre_materia,
    )
    if not materias:
        return "No se encontró ninguna materia con ese nombre en tu carrera."

    result = []
    for mat in materias:
        # Correlativas
        correlativas = await pool.fetch(
            """
            SELECT m.nombre, co.tipo
            FROM correlativas co
            JOIN materias m ON m.id_materia = co.id_correlativa
            WHERE co.id_materia = $1
            """,
            mat["id_materia"],
        )

        # Comisiones + horarios
        comisiones = await pool.fetch(
            """
            SELECT id_comision, nombre, periodo, aula, sede, profesor
            FROM comisiones
            WHERE id_materia = $1
            ORDER BY periodo DESC, nombre
            """,
            mat["id_materia"],
        )
        comisiones_list = []
        for com in comisiones:
            horarios = await pool.fetch(
                """
                SELECT dia_semana, hora_inicio::text, hora_fin::text
                FROM horarios
                WHERE id_comision = $1
                ORDER BY dia_semana
                """,
                com["id_comision"],
            )
            comisiones_list.append(
                {
                    "nombre": com["nombre"],
                    "periodo": com["periodo"],
                    "aula": com["aula"],
                    "sede": com["sede"],
                    "profesor": com["profesor"],
                    "horarios": [dict(h) for h in horarios],
                }
            )

        result.append(
            {
                "nombre": mat["nombre"],
                "anio_plan": mat["anio_plan"],
                "cuatrimestre": mat["cuatrimestre"],
                "carga_horaria": mat["carga_horaria"],
                "correlativas": [dict(c) for c in correlativas],
                "comisiones": comisiones_list,
            }
        )

    return _json_result(result)


# ─── 3. obtener_inscripciones ─────────────────────────────────────────────

async def obtener_inscripciones(ctx: SessionContext, pool, **_kwargs) -> str:
    periodo = periodo_vigente()
    rows = await pool.fetch(
        """
        SELECT h.dia_semana, h.hora_inicio::text, h.hora_fin::text,
               m.nombre AS materia, c.nombre AS comision,
               c.aula, c.sede, c.profesor
        FROM inscripciones i
        JOIN comisiones c ON c.id_comision = i.id_comision
        JOIN materias m ON m.id_materia = c.id_materia
        JOIN horarios h ON h.id_comision = c.id_comision
        WHERE i.id_alumno = $1 AND c.periodo = $2
        ORDER BY h.dia_semana, h.hora_inicio
        """,
        ctx.id_alumno,
        periodo,
    )
    if not rows:
        return "No se encontraron inscripciones para el período vigente."
    return _json_result([dict(r) for r in rows])


# ─── 4. consultar_materias_disponibles ───────────────────────────────────────

async def consultar_materias_disponibles(
    ctx: SessionContext, pool, **_kwargs
) -> str:
    periodo = periodo_vigente()
    id_carrera = await pool.fetchval(
        "SELECT id_carrera FROM alumnos WHERE id_alumno = $1", ctx.id_alumno
    )

    rows = await pool.fetch(
        """
        WITH aprobadas AS (
            -- Materias con el mejor estado del alumno
            SELECT DISTINCT ON (id_materia) id_materia, estado
            FROM historia_academica
            WHERE id_alumno = $1
            ORDER BY id_materia,
                     CASE estado
                         WHEN 'aprobada' THEN 1
                         WHEN 'promocionada' THEN 2
                         WHEN 'regularizada' THEN 3
                         WHEN 'desaprobada' THEN 4
                         WHEN 'libre' THEN 5
                     END
        ),
        inscriptas AS (
            SELECT c.id_materia
            FROM inscripciones i
            JOIN comisiones c ON c.id_comision = i.id_comision
            WHERE i.id_alumno = $1 AND c.periodo = $2
        )
        SELECT m.id_materia, m.nombre, m.anio_plan, m.cuatrimestre, m.carga_horaria
        FROM materias m
        WHERE m.id_carrera = $3
          -- No aprobada ni promocionada
          AND NOT EXISTS (
              SELECT 1 FROM aprobadas a
              WHERE a.id_materia = m.id_materia
                AND a.estado IN ('aprobada', 'promocionada')
          )
          -- No inscripta actualmente
          AND NOT EXISTS (
              SELECT 1 FROM inscriptas ins WHERE ins.id_materia = m.id_materia
          )
          -- Todas las correlativas cumplidas
          AND NOT EXISTS (
              SELECT 1 FROM correlativas co
              WHERE co.id_materia = m.id_materia
                AND NOT EXISTS (
                    SELECT 1 FROM aprobadas a
                    WHERE a.id_materia = co.id_correlativa
                      AND (
                          (co.tipo = 'aprobada' AND a.estado IN ('aprobada', 'promocionada'))
                          OR
                          (co.tipo = 'regularizada' AND a.estado IN ('regularizada', 'aprobada', 'promocionada'))
                      )
                )
          )
        ORDER BY m.anio_plan, m.cuatrimestre, m.nombre
        """,
        ctx.id_alumno,
        periodo,
        id_carrera,
    )

    if not rows:
        return "No hay materias disponibles para cursar en este momento."

    result = []
    for mat in rows:
        comisiones = await pool.fetch(
            """
            SELECT id_comision, nombre, periodo, aula, sede, profesor
            FROM comisiones
            WHERE id_materia = $1 AND periodo = $2
            ORDER BY nombre
            """,
            mat["id_materia"],
            periodo,
        )
        comisiones_list = []
        for com in comisiones:
            horarios = await pool.fetch(
                """
                SELECT dia_semana, hora_inicio::text, hora_fin::text
                FROM horarios WHERE id_comision = $1 ORDER BY dia_semana
                """,
                com["id_comision"],
            )
            comisiones_list.append(
                {
                    "nombre": com["nombre"],
                    "periodo": com["periodo"],
                    "aula": com["aula"],
                    "sede": com["sede"],
                    "profesor": com["profesor"],
                    "horarios": [dict(h) for h in horarios],
                }
            )

        result.append(
            {
                "nombre": mat["nombre"],
                "anio_plan": mat["anio_plan"],
                "cuatrimestre": mat["cuatrimestre"],
                "carga_horaria": mat["carga_horaria"],
                "comisiones": comisiones_list,
            }
        )

    return _json_result(result)


# ─── 5. obtener_materias_faltantes ──────────────────────────────────────────

async def obtener_materias_faltantes(ctx: SessionContext, pool, **_kwargs) -> str:
    id_carrera = await pool.fetchval(
        "SELECT id_carrera FROM alumnos WHERE id_alumno = $1", ctx.id_alumno
    )

    rows = await pool.fetch(
        """
        WITH aprobadas AS (
            SELECT DISTINCT id_materia
            FROM historia_academica
            WHERE id_alumno = $1
              AND estado IN ('aprobada', 'promocionada')
        )
        SELECT m.nombre, m.anio_plan, m.cuatrimestre, m.carga_horaria
        FROM materias m
        WHERE m.id_carrera = $2
          AND NOT EXISTS (
              SELECT 1 FROM aprobadas a WHERE a.id_materia = m.id_materia
          )
        ORDER BY m.anio_plan, m.cuatrimestre, m.nombre
        """,
        ctx.id_alumno,
        id_carrera,
    )

    total_plan = await pool.fetchval(
        "SELECT COUNT(*) FROM materias WHERE id_carrera = $1", id_carrera
    )

    faltantes = len(rows)
    aprobadas = (total_plan or 0) - faltantes
    porcentaje_completado = (
        round(aprobadas / total_plan * 100, 1) if total_plan else 0.0
    )

    return _json_result({
        "total_plan": total_plan,
        "aprobadas": aprobadas,
        "faltantes": faltantes,
        "porcentaje_completado": porcentaje_completado,
        "materias": [dict(r) for r in rows],
    })


# ─── 6. obtener_plan_de_estudios ────────────────────────────────────────────

async def obtener_plan_de_estudios(ctx: SessionContext, pool, **_kwargs) -> str:
    id_carrera = await pool.fetchval(
        "SELECT id_carrera FROM alumnos WHERE id_alumno = $1", ctx.id_alumno
    )
    rows = await pool.fetch(
        """
        SELECT nombre, anio_plan, cuatrimestre, carga_horaria
        FROM materias
        WHERE id_carrera = $1
        ORDER BY anio_plan, cuatrimestre, nombre
        """,
        id_carrera,
    )
    if not rows:
        return "No se encontró el plan de estudios para esta carrera."

    carrera = await pool.fetchval(
        "SELECT nombre FROM carreras WHERE id_carrera = $1", id_carrera
    )
    return _json_result({
        "carrera": carrera,
        "total_materias": len(rows),
        "materias": [dict(r) for r in rows],
    })


# ─── 7. buscar_en_documentos ─────────────────────────────────────────────────

async def buscar_en_documentos(
    ctx: SessionContext, pool, consulta_semantica: str = "", **_kwargs
) -> str:
    # Generar embedding de la consulta via Ollama
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{config.OLLAMA_BASE_URL}/api/embed",
            json={"model": config.OLLAMA_EMBED_MODEL, "input": consulta_semantica},
        )
        resp.raise_for_status()
        embedding = resp.json()["embeddings"][0]

    # Búsqueda vectorial con threshold
    rows = await pool.fetch(
        """
        SELECT documento, seccion, contenido,
               embedding <=> $1::vector AS distancia,
               metadata
        FROM documentos_fragmentos
        WHERE embedding <=> $1::vector <= 0.75
        ORDER BY embedding <=> $1::vector
        LIMIT 5
        """,
        str(embedding),
    )

    if not rows:
        return "No se encontró información relevante en los documentos institucionales."

    return _json_result(
        [
            {
                "documento": r["documento"],
                "seccion": r["seccion"],
                "contenido": r["contenido"],
                "distancia": float(r["distancia"]),
                "metadata": r["metadata"],
            }
            for r in rows
        ]
    )


# ─── Registro ────────────────────────────────────────────────────────────────

def register_tools(mcp: MCPServer) -> None:
    mcp.register("obtener_historia_academica", obtener_historia_academica)
    mcp.register("obtener_materia", obtener_materia)
    mcp.register("obtener_inscripciones", obtener_inscripciones)
    mcp.register("consultar_materias_disponibles", consultar_materias_disponibles)
    mcp.register("buscar_en_documentos", buscar_en_documentos)
    mcp.register("obtener_materias_faltantes", obtener_materias_faltantes)
    mcp.register("obtener_plan_de_estudios", obtener_plan_de_estudios)
