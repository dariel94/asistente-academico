import httpx

from app import config

VENTANA_MENSAJES = 10
UMBRAL_SUMARIZACION = 20

PROMPT_SUMARIZACION = """Resume la siguiente conversación entre un alumno y un asistente académico.
Preserva: datos académicos mencionados, decisiones tomadas, y preferencias expresadas.
Descarta: saludos, repeticiones y detalles irrelevantes.
Máximo 300 palabras.

Conversación:
{mensajes}"""


class MemoryManager:
    def __init__(self, pool):
        self._pool = pool

    async def obtener_contexto(self, id_alumno: int) -> list[dict]:
        messages: list[dict] = []

        # Resumen acumulado (si existe)
        resumen = await self._pool.fetchval(
            "SELECT contenido FROM resumenes WHERE id_alumno = $1",
            id_alumno,
        )
        if resumen:
            messages.append(
                {
                    "role": "system",
                    "content": f"Resumen de conversaciones anteriores:\n{resumen}",
                }
            )

        # Últimos N mensajes literales
        rows = await self._pool.fetch(
            """
            SELECT rol, contenido FROM (
                SELECT rol, contenido, fecha
                FROM conversaciones
                WHERE id_alumno = $1
                ORDER BY fecha DESC
                LIMIT $2
            ) sub ORDER BY fecha ASC
            """,
            id_alumno,
            VENTANA_MENSAJES,
        )
        for row in rows:
            messages.append({"role": row["rol"], "content": row["contenido"]})

        return messages

    async def guardar_intercambio(
        self, id_alumno: int, pregunta: str, respuesta: str
    ) -> None:
        await self._pool.execute(
            "INSERT INTO conversaciones (id_alumno, rol, contenido) VALUES ($1, 'user', $2)",
            id_alumno,
            pregunta,
        )
        await self._pool.execute(
            "INSERT INTO conversaciones (id_alumno, rol, contenido) VALUES ($1, 'assistant', $2)",
            id_alumno,
            respuesta,
        )

        # Verificar si hay que sumarizar
        count = await self._pool.fetchval(
            "SELECT count(*) FROM conversaciones WHERE id_alumno = $1",
            id_alumno,
        )
        if count > UMBRAL_SUMARIZACION:
            await self._sumarizar(id_alumno)

    async def _sumarizar(self, id_alumno: int) -> None:
        # Obtener mensajes fuera de la ventana (los más antiguos)
        rows = await self._pool.fetch(
            """
            SELECT rol, contenido FROM conversaciones
            WHERE id_alumno = $1
            ORDER BY fecha ASC
            """,
            id_alumno,
        )

        # Mensajes a comprimir: todos menos los últimos VENTANA_MENSAJES
        a_comprimir = rows[: len(rows) - VENTANA_MENSAJES]
        if not a_comprimir:
            return

        texto = "\n".join(
            f"{'Alumno' if r['rol'] == 'user' else 'Asistente'}: {r['contenido']}"
            for r in a_comprimir
        )
        prompt = PROMPT_SUMARIZACION.format(mensajes=texto)

        # Llamada no-streaming a Ollama para sumarizar
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{config.OLLAMA_BASE_URL}/api/chat",
                json={
                    "model": config.OLLAMA_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                    "web_search": False,
                },
            )
            resp.raise_for_status()
            resumen = resp.json()["message"]["content"]

        # UPSERT resumen
        await self._pool.execute(
            """
            INSERT INTO resumenes (id_alumno, contenido, actualizado)
            VALUES ($1, $2, NOW())
            ON CONFLICT (id_alumno) DO UPDATE
            SET contenido = $2, actualizado = NOW()
            """,
            id_alumno,
            resumen,
        )

        # Eliminar mensajes comprimidos de conversaciones
        ids_a_borrar = await self._pool.fetch(
            """
            SELECT id_mensaje FROM conversaciones
            WHERE id_alumno = $1
            ORDER BY fecha ASC
            LIMIT $2
            """,
            id_alumno,
            len(a_comprimir),
        )
        await self._pool.execute(
            "DELETE FROM conversaciones WHERE id_mensaje = ANY($1)",
            [r["id_mensaje"] for r in ids_a_borrar],
        )
