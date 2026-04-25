# Asistente Académico

Asistente conversacional académico de **ejecución íntegramente local**. Permite a los alumnos consultar en lenguaje natural su historial, inscripciones, plan de estudios, materias disponibles, avance hacia el título y normativa institucional. La identidad del alumno se inyecta desde el token JWT y nunca proviene del prompt del usuario, garantizando aislamiento estructural entre perfiles.

El proyecto fue desarrollado como tesis de grado y su documentación completa —diseño, implementación, evaluación empírica y resultados— está en [`tesis.md`](./tesis.md).

---

## Características

- **Ejecución 100 % local**: ningún dato del alumno sale de la infraestructura institucional.
- **Tool calling vía MCP**: el modelo invoca herramientas predefinidas para acceder a datos, sin acceso directo a la base.
- **Memoria conversacional híbrida**: ventana deslizante de mensajes recientes + resumen acumulado generado por el propio LLM.
- **RAG sobre documentos institucionales**: búsqueda semántica con embeddings y pgvector.
- **Streaming SSE token a token**: la respuesta se renderiza en el navegador a medida que se genera.
- **Seguridad multinivel**: autenticación JWT, rate limit por identidad, schemas vacíos en tools de datos personales, prompt hardening.

## Stack tecnológico

| Capa | Tecnología |
|---|---|
| Modelo de lenguaje | Llama 3.1 8B Instruct (cuantización Q5_K_M) |
| Servidor de inferencia | Ollama |
| Modelo de embeddings | nomic-embed-text (768 dimensiones) |
| Base de datos | PostgreSQL 18 + extensión pgvector |
| Backend | Python 3.11 · FastAPI · asyncpg · MCP Python SDK · PyJWT · bcrypt |
| Frontend | React 19 · TypeScript · Vite · Tailwind CSS · react-markdown |
| Tests | pytest + respx (backend) · Vitest + Testing Library (frontend) |

## Estructura del proyecto

```
asistente-academico/
├── app/                    # Backend FastAPI
│   ├── main.py             # Punto de entrada (lifespan, CORS, routers, logging)
│   ├── config.py           # Variables de configuración (DB, JWT, Ollama)
│   ├── models/             # Schemas Pydantic (Perfil, SessionContext, etc.)
│   ├── routers/            # Endpoints HTTP: auth.py, chat.py
│   ├── services/           # Lógica del agente
│   │   ├── agent.py            # Orquestador: clasificador, tools, streaming
│   │   ├── auth.py             # JWT + dependencia get_current_user
│   │   ├── memory.py           # MemoryManager híbrido (ventana + resumen)
│   │   ├── rate_limit.py       # 30 req/min por id_alumno
│   │   └── request_logger.py   # Logging estructurado por request
│   └── mcp/                # Servidor MCP in-process
│       ├── server.py           # FastMCP, dispatcher, TOOLS_CATALOG
│       └── tools.py            # Implementación SQL/RAG de las 7 tools
├── frontend/               # SPA React + Vite
│   └── src/
│       ├── App.tsx, main.tsx
│       ├── components/         # AuthGuard, LoginPage, ChatPage, …
│       ├── hooks/useChat.ts    # Reducer + suscripción SSE
│       ├── services/api.ts     # Cliente HTTP (login + sendMessage)
│       └── types/chat.ts
├── db/
│   ├── 01_schema.sql       # Esquema relacional + vectorial + índices HNSW
│   └── 02_seed.sql         # Datos de prueba (alumnos, materias, comisiones, etc.)
├── scripts/
│   ├── ingest.py           # Pipeline de ingesta de PDFs al corpus RAG
│   └── eval/               # Runners de evaluación funcional (Capítulo 6)
├── tests/                  # Suite de tests unitarios (pytest)
├── logs/                   # Logs rotativos: app.log, requests.log
├── tesis.md                # Documentación completa del trabajo
├── start.sh, start.bat     # Script de arranque unificado
├── requirements.txt        # Dependencias del backend
└── requirements-dev.txt    # + dependencias para correr tests
```

## Módulos funcionales

| Módulo | Responsabilidad |
|---|---|
| **Backend (FastAPI)** | Expone `/api/auth/login` y `/api/chat`, valida JWT, aplica rate limit, orquesta el flujo del agente. |
| **Servidor MCP** | Define el catálogo de 7 herramientas académicas. Inyecta la identidad del alumno desde el token JWT vía `ContextVar`, nunca desde el prompt. |
| **Orquestador del agente** | Clasifica la intención del mensaje (`ACADEMICA` vs `CONVERSACION`), invoca tools si corresponde y genera la respuesta final en streaming. |
| **MemoryManager** | Persiste el historial en `conversaciones`, mantiene una ventana de 10 mensajes literales y comprime los más antiguos en un resumen al superar los 20. |
| **Pipeline RAG** | Ingesta PDFs institucionales, los fragmenta jerárquicamente (800 chars, 200 de overlap), embebe cada fragmento con `nomic-embed-text` y los almacena con índice HNSW. |
| **Frontend SPA** | Captura credenciales, mantiene el JWT en memoria, renderiza la conversación con streaming progresivo y expone indicadores de estado del agente. |

---

## Instalación en Windows

### 1. Software base requerido

Antes de levantar el proyecto necesitás los siguientes binarios instalados y disponibles en `PATH` (los instaladores oficiales suelen agregarlos automáticamente):

| Software | Versión sugerida | Notas |
|---|---|---|
| **Python** | 3.11 (mínimo 3.10) | https://www.python.org/downloads/windows/ — marcar *"Add Python to PATH"* en el instalador. |
| **Node.js + npm** | LTS (≥ 20.x) | https://nodejs.org/ — incluye `npm`. |
| **PostgreSQL** | 18 | Instalador EnterpriseDB: https://www.postgresql.org/download/windows/ — anotá la contraseña del usuario `postgres`. |
| **pgvector** | 0.7+ | Extensión para PostgreSQL. Ver paso 3. |
| **Ollama** | última estable | https://ollama.com/download/windows |
| **Git** + **Git Bash** | última estable | https://git-scm.com/download/win — Git Bash es necesario para correr `start.sh` desde `start.bat`. |

### 2. Clonar el repositorio

```bash
git clone <URL-del-repo>
cd asistente-academico
```

### 3. PostgreSQL: habilitar pgvector

En Windows, pgvector se instala compilándolo o con un binario precompilado (consultar https://github.com/pgvector/pgvector#installation-notes para la versión específica de PostgreSQL). Una vez instalada la extensión a nivel del servidor, **no** hace falta crear la base ni habilitarla manualmente: el script `start.sh` se encarga en el primer arranque.

Por defecto el sistema asume:

- Host: `localhost` · Puerto: `5432`
- Usuario: `postgres` · Contraseña: `admin`
- Base: `asistente_academico` (se crea automáticamente si no existe)

Si tu instalación usa otra contraseña o credenciales, ajustá las variables en `app/config.py` o seteá la variable de entorno `DATABASE_URL` antes de arrancar.

### 4. Ollama: descargar los modelos

Una vez instalado Ollama (queda corriendo como servicio en `http://localhost:11434`), descargá los dos modelos que el sistema utiliza:

```bash
ollama pull llama3.1:8b-instruct-q5_K_M
ollama pull nomic-embed-text
```

La primera descarga puede tardar varios minutos. Verificá que ambos modelos quedaron disponibles con:

```bash
ollama list
```

### 5. Backend: entorno virtual de Python

Desde la raíz del proyecto:

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Si vas a correr los tests unitarios, usá `requirements-dev.txt` en su lugar (incluye `pytest`, `pytest-asyncio` y `respx`):

```bash
pip install -r requirements-dev.txt
```

### 6. Frontend: dependencias de Node

```bash
cd frontend
npm install
cd ..
```

### 7. (Opcional) Cargar documentos institucionales al pipeline RAG

Para que la herramienta `buscar_en_documentos` devuelva resultados, hace falta ingestar previamente los PDFs institucionales:

```bash
python scripts/ingest.py <ruta-al-pdf>
```

El script extrae el texto, lo fragmenta, genera los embeddings con `nomic-embed-text` y los inserta en la tabla `documentos_fragmentos`.

---

## Levantar el proyecto

Con todo lo anterior instalado, hay dos formas de arrancar el sistema completo.

### Opción A — Script unificado (recomendado)

Desde la raíz del proyecto:

```bash
start.bat
```

`start.bat` abre Git Bash y ejecuta `start.sh`, que se encarga de:

1. Verificar que PostgreSQL esté escuchando en `localhost:5432`.
2. Crear la base `asistente_academico` y aplicar `01_schema.sql` + `02_seed.sql` si la base aún no existe.
3. Activar el entorno virtual (`venv/` o `.venv/`).
4. Lanzar el backend con `uvicorn app.main:app --reload --port 8000`.
5. Lanzar el frontend con `npm run dev` en el puerto que asigne Vite (por defecto 5173).

Para detener todos los procesos: `Ctrl+C` en la terminal de Git Bash.

> **Nota**: el script asume que PostgreSQL y Ollama corren como servicios del sistema operativo, ya iniciados. No los gestiona como procesos hijos para evitar recargar pesos del LLM en cada arranque.

### Opción B — Procesos manuales

Si preferís levantar cada componente por separado, abrí cuatro terminales:

```bash
# Terminal 1 — PostgreSQL (asegurarse de que está corriendo como servicio)
# Terminal 2 — Ollama (queda como servicio tras instalarlo)
# Terminal 3 — Backend
venv\Scripts\activate
uvicorn app.main:app --reload --port 8000

# Terminal 4 — Frontend
cd frontend
npm run dev
```

### Acceso

Una vez levantados los cuatro procesos, abrí en el navegador:

```
http://localhost:5173
```

El frontend usa el proxy de Vite para reenviar las llamadas `/api` al backend en `localhost:8000`. Las credenciales de prueba están definidas en `db/02_seed.sql`; todos los alumnos seedeados comparten la contraseña `password123`.

---

## Tests

### Backend (Python)

```bash
venv\Scripts\activate
pip install -r requirements-dev.txt
pytest
```

Ejecuta 72 tests unitarios cubriendo `auth`, `memory`, `rate_limit`, `request_logger`, los helpers del orquestador y el servidor MCP. No requiere PostgreSQL ni Ollama (las dependencias externas están mockeadas).

### Frontend (TypeScript)

```bash
cd frontend
npm test
```

Ejecuta 28 tests con Vitest cubriendo el reducer de la conversación, el cliente HTTP y el parser SSE, y los indicadores de estado.

### Evaluación funcional (Capítulo 6 de la tesis)

Los runners en `scripts/eval/` ejercitan el sistema completo contra el dataset documentado en la tesis. Requieren todos los servicios levantados:

```bash
python scripts/eval/run_eval.py
python scripts/eval/run_memory_eval.py
python scripts/eval/run_security.py
python scripts/eval/aggregate.py   # consolida resultados en summary.json y report.md
```

---

## Variables de entorno

Todos los valores tienen defaults razonables en `app/config.py`. Solo es necesario sobreescribir si se cambia la infraestructura:

| Variable | Default | Descripción |
|---|---|---|
| `DATABASE_URL` | `postgresql://postgres:admin@localhost:5432/asistente_academico` | Cadena de conexión completa. |
| `JWT_SECRET` | (default de desarrollo) | Secreto HMAC-SHA256 para firmar los tokens. **Cambiar en producción.** |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | URL del servidor de inferencia. |
| `OLLAMA_MODEL` | `llama3.1:8b-instruct-q5_K_M` | Modelo de chat. |
| `OLLAMA_EMBED_MODEL` | `nomic-embed-text` | Modelo de embeddings. |
| `RATE_LIMIT_MAX` | `30` | Requests por ventana por alumno. |
| `RATE_LIMIT_WINDOW_SECONDS` | `60` | Tamaño de la ventana en segundos. |

---

## Documentación

La tesis completa —objetivos, marco teórico, requerimientos, diseño detallado de cada componente, decisiones arquitectónicas, evaluación empírica con métricas y conclusiones— está en [`tesis.md`](./tesis.md).
