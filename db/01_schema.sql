-- Esquema completo del Asistente Virtual Académico
-- PostgreSQL 16+ con extensión pgvector

-- ============================================
-- Extensiones
-- ============================================
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================
-- 1. Dimensiones maestras
-- ============================================
CREATE TABLE carreras (
    id_carrera     SERIAL PRIMARY KEY,
    nombre         VARCHAR(120) NOT NULL UNIQUE,
    duracion_anios SMALLINT NOT NULL,
    resolucion     VARCHAR(50)
);

CREATE TABLE alumnos (
    id_alumno     SERIAL PRIMARY KEY,
    legajo        VARCHAR(20)  NOT NULL UNIQUE,
    nombre        VARCHAR(100) NOT NULL,
    apellido      VARCHAR(100) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    id_carrera    INT NOT NULL REFERENCES carreras(id_carrera),
    estado        VARCHAR(20) DEFAULT 'regular'
                  CHECK (estado IN ('regular', 'condicional', 'libre', 'egresado')),
    fecha_ingreso DATE NOT NULL
);

CREATE TABLE materias (
    id_materia    SERIAL PRIMARY KEY,
    id_carrera    INT NOT NULL REFERENCES carreras(id_carrera),
    nombre        VARCHAR(150) NOT NULL,
    anio_plan     SMALLINT NOT NULL,
    cuatrimestre  SMALLINT NOT NULL CHECK (cuatrimestre IN (1, 2)),
    carga_horaria SMALLINT NOT NULL,
    UNIQUE (id_carrera, nombre)
);

CREATE TABLE correlativas (
    id_materia     INT NOT NULL REFERENCES materias(id_materia),
    id_correlativa INT NOT NULL REFERENCES materias(id_materia),
    tipo           VARCHAR(20) NOT NULL
                   CHECK (tipo IN ('aprobada', 'regularizada')),
    PRIMARY KEY (id_materia, id_correlativa)
);

-- ============================================
-- 2. Operatividad de la cursada
-- ============================================
CREATE TABLE comisiones (
    id_comision   SERIAL PRIMARY KEY,
    id_materia    INT NOT NULL REFERENCES materias(id_materia),
    nombre        VARCHAR(20)  NOT NULL,
    periodo       VARCHAR(20)  NOT NULL CHECK (periodo ~ '^\d{4}-(1C|2C)$'),
    aula          VARCHAR(30),
    sede          VARCHAR(60),
    profesor      VARCHAR(120)
);

CREATE TABLE horarios (
    id_horario    SERIAL PRIMARY KEY,
    id_comision   INT NOT NULL REFERENCES comisiones(id_comision),
    dia_semana    SMALLINT NOT NULL CHECK (dia_semana BETWEEN 1 AND 7),
    hora_inicio   TIME NOT NULL,
    hora_fin      TIME NOT NULL
);

CREATE TABLE inscripciones (
    id_inscripcion SERIAL PRIMARY KEY,
    id_alumno      INT NOT NULL REFERENCES alumnos(id_alumno),
    id_comision    INT NOT NULL REFERENCES comisiones(id_comision),
    fecha          DATE NOT NULL DEFAULT CURRENT_DATE,
    UNIQUE (id_alumno, id_comision)
);

-- ============================================
-- 3. Historial académico
-- ============================================
CREATE TABLE historia_academica (
    id_registro    SERIAL PRIMARY KEY,
    id_alumno      INT NOT NULL REFERENCES alumnos(id_alumno),
    id_materia     INT NOT NULL REFERENCES materias(id_materia),
    estado         VARCHAR(20) NOT NULL
                   CHECK (estado IN ('regularizada', 'aprobada', 'promocionada',
                                     'desaprobada', 'libre')),
    nota_cursada   NUMERIC(4,2) CHECK (nota_cursada >= 0 AND nota_cursada <= 10),
    nota_final     NUMERIC(4,2) CHECK (nota_final   >= 0 AND nota_final   <= 10),
    fecha          DATE NOT NULL,
    periodo        VARCHAR(20) NOT NULL
);

-- ============================================
-- 4. Memoria conversacional
-- ============================================
CREATE TABLE conversaciones (
    id_mensaje  SERIAL PRIMARY KEY,
    id_alumno   INT NOT NULL REFERENCES alumnos(id_alumno),
    rol         VARCHAR(10) NOT NULL CHECK (rol IN ('user', 'assistant')),
    contenido   TEXT NOT NULL,
    fecha       TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE resumenes (
    id_resumen  SERIAL PRIMARY KEY,
    id_alumno   INT NOT NULL UNIQUE REFERENCES alumnos(id_alumno),
    contenido   TEXT NOT NULL,
    actualizado TIMESTAMP NOT NULL DEFAULT NOW()
);

-- ============================================
-- 5. Esquema vectorial (RAG)
-- ============================================
CREATE TABLE documentos_fragmentos (
    id_fragmento SERIAL PRIMARY KEY,
    documento    VARCHAR(200) NOT NULL,
    seccion      VARCHAR(200),
    contenido    TEXT NOT NULL,
    embedding    vector(768) NOT NULL,
    metadata     JSONB DEFAULT '{}'
);

-- ============================================
-- 6. Índices secundarios
-- ============================================
CREATE INDEX idx_historia_alumno       ON historia_academica(id_alumno, estado);
CREATE INDEX idx_conversaciones_alumno ON conversaciones(id_alumno, fecha);
CREATE INDEX idx_inscripciones_alumno  ON inscripciones(id_alumno);

CREATE INDEX idx_fragmentos_embedding
    ON documentos_fragmentos
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 200);
