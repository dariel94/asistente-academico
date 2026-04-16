"""
Pipeline de ingestión RAG — §4.4 del TECNICAL_SPEC.

Lista los .pdf de docs/, extrae texto con PyMuPDF, los divide en chunks
(800 chars, 200 overlap, separadores jerárquicos), genera embeddings con
nomic-embed-text vía Ollama y los inserta en documentos_fragmentos.
Re-ingestión: DELETE previo por nombre de documento.

Uso:
    python scripts/ingest.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import asyncpg
import fitz  # PyMuPDF
import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import config  # noqa: E402

DOCS_DIR = ROOT / "docs"

CHUNK_SIZE = 800
CHUNK_OVERLAP = 200
SEPARATORS = ["\n\n", "\n", ". ", " "]


def extraer_texto(pdf_path: Path) -> str:
    with fitz.open(pdf_path) as doc:
        return "\n\n".join(page.get_text("text") for page in doc)


def _split_recursivo(texto: str, separadores: list[str]) -> list[str]:
    """Corte jerárquico hasta que cada pieza quepa en CHUNK_SIZE."""
    if len(texto) <= CHUNK_SIZE or not separadores:
        return [texto]

    sep, resto = separadores[0], separadores[1:]
    partes = texto.split(sep) if sep else list(texto)
    piezas: list[str] = []
    for parte in partes:
        if len(parte) <= CHUNK_SIZE:
            piezas.append(parte)
        else:
            piezas.extend(_split_recursivo(parte, resto))
    return piezas


def chunk_text(texto: str) -> list[str]:
    """Chunking con separadores jerárquicos §4.2 y overlap de 200 chars."""
    texto = texto.strip()
    if not texto:
        return []

    piezas = _split_recursivo(texto, SEPARATORS)

    chunks: list[str] = []
    actual = ""
    for pieza in piezas:
        pieza = pieza.strip()
        if not pieza:
            continue
        candidato = f"{actual}\n{pieza}" if actual else pieza
        if len(candidato) <= CHUNK_SIZE:
            actual = candidato
        else:
            if actual:
                chunks.append(actual)
            if len(pieza) > CHUNK_SIZE:
                # pieza individual aún demasiado larga → corte duro
                for i in range(0, len(pieza), CHUNK_SIZE - CHUNK_OVERLAP):
                    chunks.append(pieza[i : i + CHUNK_SIZE])
                actual = ""
            else:
                # arrancar el nuevo chunk con overlap del anterior
                overlap = chunks[-1][-CHUNK_OVERLAP:] if chunks else ""
                actual = f"{overlap} {pieza}".strip() if overlap else pieza
    if actual:
        chunks.append(actual)
    return chunks


async def generar_embedding(client: httpx.AsyncClient, texto: str) -> list[float]:
    resp = await client.post(
        f"{config.OLLAMA_BASE_URL}/api/embed",
        json={"model": config.OLLAMA_EMBED_MODEL, "input": texto},
    )
    resp.raise_for_status()
    return resp.json()["embeddings"][0]


async def ingestar_pdf(
    pdf_path: Path, pool: asyncpg.Pool, client: httpx.AsyncClient
) -> int:
    documento = pdf_path.stem
    print(f"[{documento}] extrayendo texto...", flush=True)
    try:
        texto = extraer_texto(pdf_path)
    except Exception as exc:
        print(f"[{documento}] ERROR leyendo PDF: {exc}", flush=True)
        return 0

    chunks = chunk_text(texto)
    if not chunks:
        print(f"[{documento}] sin contenido, se omite", flush=True)
        return 0

    print(f"[{documento}] {len(chunks)} chunks -> generando embeddings...", flush=True)

    filas: list[tuple[str, str, list[float]]] = []
    for i, chunk in enumerate(chunks, start=1):
        embedding = await generar_embedding(client, chunk)
        filas.append((documento, chunk, embedding))
        if i % 10 == 0 or i == len(chunks):
            print(f"[{documento}]   {i}/{len(chunks)}", flush=True)

    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "DELETE FROM documentos_fragmentos WHERE documento = $1",
                documento,
            )
            await conn.executemany(
                """
                INSERT INTO documentos_fragmentos (documento, contenido, embedding)
                VALUES ($1, $2, $3::vector)
                """,
                [(doc, cont, str(emb)) for doc, cont, emb in filas],
            )

    print(f"[{documento}] insertados {len(filas)} fragmentos", flush=True)
    return len(filas)


async def main() -> None:
    pdfs = sorted(DOCS_DIR.glob("*.pdf"))
    if not pdfs:
        print(f"No se encontraron PDFs en {DOCS_DIR}")
        return

    pool = await asyncpg.create_pool(config.DATABASE_URL, min_size=1, max_size=2)
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            total = 0
            for pdf in pdfs:
                total += await ingestar_pdf(pdf, pool, client)
        print(f"\nIngestión completa: {total} fragmentos en {len(pdfs)} documento(s).")
    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
