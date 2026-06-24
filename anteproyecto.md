# Anteproyecto de Tesis

## 1) Título

**Asistente Académico: Agente Conversacional con Tool Calling** — David Diaz.

## 2) Tutores

Federico D'Angiolo, Lucas Cabot.

## 3) Resumen

El presente trabajo propone el diseño e implementación de un agente conversacional académico que permite a los estudiantes universitarios acceder a su información académica e institucional (historia académica, materias, inscripciones, grilla horaria, plan de estudios, avance de carrera y normativa) mediante lenguaje natural, eliminando la fricción de navegar sistemas de gestión tradicionales.

En el estado actual de la tecnología, los Modelos de Lenguaje Grandes (LLM) han incorporado la capacidad de **Tool Calling** (uso de herramientas), que les permite actuar como agentes capaces de invocar funciones externas para recuperar datos verificables. El sistema combina cuatro pilares: (i) un LLM de **ejecución local** (Llama 3.1 8B cuantizado), que garantiza soberanía tecnológica, privacidad y costo cero por consulta frente a las APIs propietarias de nube; (ii) el **Model Context Protocol (MCP)** como capa de abstracción estandarizada que desacopla el modelo de las fuentes de datos y blinda el aislamiento de identidad; (iii) una **base de datos híbrida** PostgreSQL + pgvector que unifica datos relacionales (consultas determinísticas) y vectoriales (RAG sobre documentos institucionales) bajo una misma transacción; y (iv) un sistema de **memoria conversacional híbrida** (ventana deslizante + sumarización dinámica) que sostiene el contexto en diálogos extensos.

El resultado es una arquitectura portable, replicable en instituciones con presupuesto acotado y exigencias de privacidad, validado en precisión de tool calling, latencia, seguridad y memoria.

## 4) Estado del Arte

La transición de interfaces gráficas (GUI) hacia interfaces de lenguaje natural (LUI) se consolidó a partir de la arquitectura **Transformer** y su mecanismo de auto-atención (Vaswani et al., 2017), base de los LLM actuales. El refinamiento mediante aprendizaje por refuerzo con retroalimentación humana (RLHF) habilitó que estos modelos sigan instrucciones complejas e interactúen con APIs externas (Ouyang et al., 2022), dando origen al comportamiento agéntico.

Para mitigar las limitaciones conocidas de los LLM, como alucinaciones o conocimiento desactualizado, la técnica de **Generación Aumentada por Recuperación (RAG)** incorpora conocimiento de fuentes externas en tiempo de inferencia (Lewis et al., 2020). Los relevamientos recientes sistematizan su evolución (Gao et al., *Retrieval-Augmented Generation for Large Language Models: A Survey*, 2024) y, más aún, la convergencia entre RAG y agentes autónomos con uso de herramientas (Singh et al., *Agentic RAG: A Survey*, 2025).

En el dominio educativo específico, existe un cuerpo creciente de trabajos que aplican LLM + RAG a la asistencia universitaria. Se han propuesto **agentes tutores con RAG para cursos de educación superior** que recuperan información de material curricular curado para ofrecer asistencia personalizada (Modran et al., *LLM Intelligent Agent Tutoring in Higher Education Courses using a RAG Approach*, Springer, 2024); **chatbots con RAG para atención institucional** (jornadas de puertas abiertas, consultas administrativas); y soluciones de **memoria aumentada** integradas a sistemas de gestión del aprendizaje (LMS) para enriquecer el servicio conversacional (*Memory-Augmented LLM for Enhanced Chatbot Services in University LMS*, Applied Sciences, MDPI, 2025). Particularmente cercano es **NOVA**, un asistente educativo en español que combina RAG con bases de datos vectoriales y relacionales.

La mayoría de estos trabajos, presentan dos brechas que este proyecto aborda: (a) dependen de **APIs propietarias en la nube** (con el consiguiente costo y exposición de datos sensibles), mientras que aquí se prioriza la **ejecución local** y la privacidad *local-first*; y (b) resuelven la integración de datos con código a medida o frameworks específicos (p. ej. LangChain), mientras que este trabajo adopta el **Model Context Protocol (MCP)** como contrato estandarizado y agnóstico al Sistema de Información Académica, reforzando la portabilidad y el aislamiento de identidad por diseño. La combinación específica de *tool calling* local + MCP + base híbrida PostgreSQL/pgvector + memoria híbrida, evaluada bajo un modelo de amenazas explícito (autenticación, *prompt injection*, *SQL injection*, *rate limit*), constituye el aporte diferencial frente al estado del arte relevado.

## 5) Objetivos

**Objetivo general:** Diseñar e implementar un agente conversacional académico, basado en LLM de ejecución local, que centralice y agilice el acceso a información académica e institucional mediante uso de herramientas (Tool Calling). Este acceso, mediante consultas en lenguaje natural, permite obtener la **historia académica** del estudiante (materias aprobadas, en curso y notas), las **materias disponibles** para inscripción según las correlativas cumplidas, la **grilla horaria** y los **docentes** asignados, el **plan de estudios** y el **avance de carrera** (materias faltantes para egresar), así como **información institucional** (datos de la institución, reglamentos) a través de búsqueda documental.

**Objetivos específicos y herramientas:**

- **Capa de abstracción de datos (MCP):** desarrollar un servidor MCP que exponga un catálogo de herramientas académicas, permitiendo la interoperabilidad estandarizada con bases relacionales (SQL) y vectoriales (RAG). *Herramientas: MCP Python SDK.*
- **Motor de inferencia local:** implementar el modelo **Llama 3.1 8B** optimizado por cuantización (Q5_K_M) para respuestas de baja latencia sin dependencia de la nube. *Herramientas: Ollama, GGUF.*
- **Memoria híbrida:** integrar una ventana deslizante de mensajes recientes con sumarización dinámica para persistir el contexto en conversaciones extensas. *Herramientas: PostgreSQL.*
- **Interfaz y orquestación:** desplegar un frontend con autenticación y un backend orquestador del agente con respuesta en *streaming*. *Herramientas: React + Vite + TypeScript + Tailwind, FastAPI, SSE.*
- **Seguridad multinivel:** establecer autenticación de usuarios (JWT + bcrypt), filtrado por perfil en la capa MCP y *System Prompt Hardening* contra *Prompt Injection*.
- **Validación y análisis de resultados:** verificar precisión, latencia, seguridad y memoria mediante una suite de pruebas sobre datasets académicos simulados y documentos normativos, **obteniendo métricas cuantitativas** que permitan analizar el rendimiento del sistema y asi **derivar conclusiones** sobre su viabilidad y posibles líneas de mejora.

## 6) Alcance

**El desarrollo abarca:**

- Un sistema funcional extremo a extremo (frontend SPA + backend FastAPI + servidor MCP in-process + Ollama + PostgreSQL/pgvector) ejecutable en hardware de consumo (GPU de 12 GB de VRAM).
- Siete herramientas MCP que cubren la superficie de consulta académica prevista (historia, materias, inscripciones, materias disponibles, plan de estudios, materias faltantes y búsqueda documental RAG).
- Memoria conversacional híbrida por sesión (se reinicia en cada login).
- Modelo de seguridad de tres capas y su validación frente a escenarios adversos.
- Diseño orientado a la escalabilidad, uso de FastAPI en modo *stateless* (autenticación por JWT sin estado de sesión en servidor), *pool* de conexiones a PostgreSQL y aislamiento de la identidad por petición permitiendo a futuro replicar instancias del backend de forma horizontal (varios servidores gestionados por un balanceador que distribuye la carga + un servidor dedicado para la BD).
- Evaluación sobre un **entorno académico simulado** (datasets de prueba).

**Queda fuera del alcance:**

- *Fine-tuning* del modelo como agente académico (se prioriza el aprendizaje en contexto).
- Compresión **semántica** de la memoria que preserve preferencias narrativas del usuario (memoria episódica / tabla de "hechos singulares") — limitación documentada del modelo de 8B utilizado.
- Refuerzo del *hardening* contra exfiltración del propio system prompt (filtro de salida).
- Integración real contra un Sistema de Información Académica productivo como el SIU.
- Despliegue productivo a gran escala, con multiples instancias, balanceador y pruebas de carga/*stress* con concurrencia masiva real (la arquitectura se diseña para escalar, pero su validación bajo alta demanda queda como línea de trabajo futuro).

## 7) Cronograma (≈ 12 meses)

| Fase | Período aprox. | Actividades |
|---|---|---|
| **1. Búsqueda de material y marco teórico** | Mes 1 – Mes 2 | Relevamiento de papers (LLM, RAG, MCP, agentes), estado del arte, definición de objetivos y alcance. |
| **2. Análisis y diseño de arquitectura** | Mes 3 – Mes 4 | Requerimientos funcionales y no funcionales; diseño de la base híbrida (3NF + pgvector), del servidor MCP y del modelo de seguridad. |
| **3. Desarrollo del núcleo de datos e inferencia** | Mes 4 – Mes 6 | Implementación de PostgreSQL/pgvector, pipeline RAG (chunking, embeddings, HNSW), despliegue de Ollama con Llama 3.1 8B cuantizado y servidor MCP con sus herramientas. |
| **4. Desarrollo del orquestador y la interfaz** | Mes 6 – Mes 8 | Backend FastAPI (clasificación de intención, tool calling, streaming), autenticación JWT, memoria híbrida y frontend SPA. |
| **5. Integración, seguridad y pruebas** | Mes 8 – Mes 10 | Hardening del prompt, rate limit, pruebas unitarias e integración extremo a extremo. |
| **6. Evaluación y resultados** | Mes 10 – Mes 11 | Métricas de precisión y tool calling, latencia/tokens, validación de seguridad (auth, SQLi, prompt injection) y de memoria. |
| **7. Redacción final y conclusiones** | Mes 11 – Mes 12 | Documentación, análisis de resultados, conclusiones y líneas futuras; entrega y defensa. |

## 8) Referencias

**Modelos de lenguaje y fundamentos**
- Vaswani, A. et al. *Attention Is All You Need.* arXiv:1706.03762, 2017. https://arxiv.org/abs/1706.03762
- Ouyang, L. et al. *Training language models to follow instructions with human feedback.* arXiv:2203.02155, 2022. https://arxiv.org/abs/2203.02155
- Meta AI. *Introducing Llama 3.1: Our most capable models to date.* 2024. https://ai.meta.com/blog/meta-llama-3-1/

**RAG, agentes y aplicaciones educativas (estado del arte)**
- Lewis, P. et al. *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks.* arXiv:2005.11401, 2020. https://arxiv.org/abs/2005.11401
- Gao, Y. et al. *Retrieval-Augmented Generation for Large Language Models: A Survey.* arXiv:2312.10997, 2024. https://arxiv.org/abs/2312.10997
- Singh, A. et al. *Agentic Retrieval-Augmented Generation: A Survey on Agentic RAG.* arXiv:2501.09136, 2025. https://arxiv.org/abs/2501.09136
- Modran, H. et al. *LLM Intelligent Agent Tutoring in Higher Education Courses using a RAG Approach.* Springer, 2024. https://link.springer.com/chapter/10.1007/978-3-031-83520-9_54
- *Memory-Augmented Large Language Model for Enhanced Chatbot Services in University Learning Management Systems.* Applied Sciences, MDPI, 2025. https://www.mdpi.com/2076-3417/15/17/9775
- *Retrieval Augmented Large Language Model Chatbots in Higher Education: A Study on University Open Days.* 2025. https://www.researchgate.net/publication/387786519

**Protocolo MCP**
- Anthropic. *Model Context Protocol — Specification.* https://modelcontextprotocol.io/

**Embeddings, búsqueda vectorial e infraestructura**
- Malkov, Y. A. y Yashunin, D. A. *Efficient and robust approximate nearest neighbor search using HNSW graphs.* arXiv:1603.09320, 2016. https://arxiv.org/abs/1603.09320
- Nussbaum, Z. et al. *Nomic Embed: Training a Reproducible Long Context Text Embedder.* arXiv:2402.01613, 2024. https://arxiv.org/abs/2402.01613
- pgvector. *Open-source vector similarity search for Postgres.* https://github.com/pgvector/pgvector
- Ollama. *Sitio oficial.* https://ollama.com/

**Backend, frontend y seguridad**
- Ramírez, S. *FastAPI — Documentación oficial.* https://fastapi.tiangolo.com/
- Jones, M., Bradley, J. y Sakimura, N. *JSON Web Token (JWT).* RFC 7519, IETF, 2015. https://datatracker.ietf.org/doc/html/rfc7519
- Provos, N. y Mazières, D. *A Future-Adaptable Password Scheme (bcrypt).* USENIX, 1999.
- OWASP Foundation. *OWASP Top 10.* https://owasp.org/www-project-top-ten/
