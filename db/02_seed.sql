-- Datos de prueba para el Asistente Virtual Académico
-- Password de todos los alumnos: "password123"
-- Hash bcrypt: $2b$12$UohyYs4mmhP0oeAC42WG9.K4b1kE2UvgK3hD1AsYMn8LA/0qfQvri

-- ============================================
-- 1. Carreras
-- ============================================
INSERT INTO carreras (nombre, duracion_anios, resolucion) VALUES
('Ingeniería en Sistemas de Información', 5, 'RES-CD-2023-001'),   -- id 1
('Licenciatura en Administración de Empresas', 4, 'RES-CD-2022-015'); -- id 2

-- ============================================
-- 2. Alumnos
-- ============================================
INSERT INTO alumnos (legajo, nombre, apellido, password_hash, id_carrera, estado, fecha_ingreso) VALUES
-- Sistemas
('SIS-1001', 'María',    'González',  '$2b$12$UohyYs4mmhP0oeAC42WG9.K4b1kE2UvgK3hD1AsYMn8LA/0qfQvri', 1, 'regular',      '2023-03-01'),
('SIS-1002', 'Carlos',   'López',     '$2b$12$UohyYs4mmhP0oeAC42WG9.K4b1kE2UvgK3hD1AsYMn8LA/0qfQvri', 1, 'regular',      '2024-03-01'),
('SIS-1003', 'Ana',      'Martínez',  '$2b$12$UohyYs4mmhP0oeAC42WG9.K4b1kE2UvgK3hD1AsYMn8LA/0qfQvri', 1, 'condicional',  '2023-03-01'),
('SIS-1004', 'Pedro',    'Ramírez',   '$2b$12$UohyYs4mmhP0oeAC42WG9.K4b1kE2UvgK3hD1AsYMn8LA/0qfQvri', 1, 'regular',      '2022-03-01'),
-- Administración
('ADM-2001', 'Lucía',    'Fernández', '$2b$12$UohyYs4mmhP0oeAC42WG9.K4b1kE2UvgK3hD1AsYMn8LA/0qfQvri', 2, 'regular',      '2024-03-01'),
('ADM-2002', 'Martín',   'García',    '$2b$12$UohyYs4mmhP0oeAC42WG9.K4b1kE2UvgK3hD1AsYMn8LA/0qfQvri', 2, 'regular',      '2025-03-01');

-- ============================================
-- 3. Materias — Ingeniería en Sistemas (carrera 1)
-- ============================================
INSERT INTO materias (id_carrera, nombre, anio_plan, cuatrimestre, carga_horaria) VALUES
-- Primer año
(1, 'Análisis Matemático I',              1, 1, 8),   -- id 1
(1, 'Álgebra y Geometría Analítica',      1, 1, 6),   -- id 2
(1, 'Sistemas y Organizaciones',          1, 1, 4),   -- id 3
(1, 'Análisis Matemático II',             1, 2, 8),   -- id 4
(1, 'Física I',                           1, 2, 6),   -- id 5
(1, 'Algoritmos y Estructuras de Datos',  1, 2, 6),   -- id 6
-- Segundo año
(1, 'Física II',                          2, 1, 6),   -- id 7
(1, 'Sintaxis y Semántica de Lenguajes',  2, 1, 6),   -- id 8
(1, 'Paradigmas de Programación',         2, 1, 6),   -- id 9
(1, 'Diseño de Sistemas',                 2, 2, 6),   -- id 10
(1, 'Bases de Datos',                     2, 2, 6);   -- id 11

-- ============================================
-- 4. Materias — Administración de Empresas (carrera 2)
-- ============================================
INSERT INTO materias (id_carrera, nombre, anio_plan, cuatrimestre, carga_horaria) VALUES
-- Primer año
(2, 'Introducción a la Administración',   1, 1, 6),   -- id 12
(2, 'Contabilidad I',                     1, 1, 6),   -- id 13
(2, 'Derecho Empresarial',                1, 1, 4),   -- id 14
(2, 'Economía I',                         1, 2, 6),   -- id 15
(2, 'Matemática para Administración',     1, 2, 6),   -- id 16
(2, 'Contabilidad II',                    1, 2, 6),   -- id 17
-- Segundo año
(2, 'Economía II',                        2, 1, 6),   -- id 18
(2, 'Administración de Recursos Humanos', 2, 1, 4),   -- id 19
(2, 'Estadística Aplicada',               2, 1, 6),   -- id 20
(2, 'Marketing',                          2, 2, 6),   -- id 21
(2, 'Administración Financiera',          2, 2, 6);   -- id 22

-- ============================================
-- 5. Correlativas — Sistemas
-- ============================================
INSERT INTO correlativas (id_materia, id_correlativa, tipo) VALUES
-- AM II requiere AM I aprobada
(4, 1, 'aprobada'),
-- Física I requiere AM I regularizada
(5, 1, 'regularizada'),
-- Algoritmos requiere Sist y Org regularizada
(6, 3, 'regularizada'),
-- Física II requiere Física I aprobada y AM II regularizada
(7, 5, 'aprobada'),
(7, 4, 'regularizada'),
-- Sintaxis requiere Algoritmos aprobada
(8, 6, 'aprobada'),
-- Paradigmas requiere Algoritmos aprobada
(9, 6, 'aprobada'),
-- Diseño de Sistemas requiere Sist y Org aprobada y Paradigmas regularizada
(10, 3, 'aprobada'),
(10, 9, 'regularizada'),
-- Bases de Datos requiere Algoritmos aprobada y Paradigmas regularizada
(11, 6, 'aprobada'),
(11, 9, 'regularizada');

-- ============================================
-- 6. Correlativas — Administración
-- ============================================
INSERT INTO correlativas (id_materia, id_correlativa, tipo) VALUES
-- Contabilidad II requiere Contabilidad I aprobada
(17, 13, 'aprobada'),
-- Economía II requiere Economía I aprobada
(18, 15, 'aprobada'),
-- RRHH requiere Intro Administración aprobada
(19, 12, 'aprobada'),
-- Estadística requiere Matemática regularizada
(20, 16, 'regularizada'),
-- Marketing requiere Intro Administración aprobada y Economía I regularizada
(21, 12, 'aprobada'),
(21, 15, 'regularizada'),
-- Admin Financiera requiere Contabilidad II aprobada y Economía I aprobada
(22, 17, 'aprobada'),
(22, 15, 'aprobada');

-- ============================================
-- 7. Comisiones — Sistemas (período 2026-1C)
-- ============================================
INSERT INTO comisiones (id_materia, nombre, periodo, aula, sede, profesor) VALUES
-- Primer año 1C
(1, 'C1', '2026-1C', 'Aula 101', 'Campus Centro', 'Dr. Martínez'),      -- id 1
(1, 'C2', '2026-1C', 'Aula 105', 'Campus Norte',  'Dra. Blanco'),       -- id 2
(2, 'C1', '2026-1C', 'Aula 102', 'Campus Centro', 'Ing. Ruiz'),         -- id 3
(3, 'C1', '2026-1C', 'Aula 201', 'Campus Centro', 'Lic. Fernández'),    -- id 4
-- Segundo año 1C
(7, 'C1', '2026-1C', 'Aula 301', 'Campus Centro', 'Dr. Sánchez'),       -- id 5
(8, 'C1', '2026-1C', 'Aula 302', 'Campus Centro', 'Ing. Torres'),       -- id 6
(9, 'C1', '2026-1C', 'Aula 303', 'Campus Centro', 'Dr. Pérez'),         -- id 7
(9, 'C2', '2026-1C', 'Aula 304', 'Campus Norte',  'Ing. Vega');         -- id 8

-- ============================================
-- 8. Comisiones — Administración (período 2026-1C)
-- ============================================
INSERT INTO comisiones (id_materia, nombre, periodo, aula, sede, profesor) VALUES
-- Primer año 1C
(12, 'C1', '2026-1C', 'Aula 401', 'Campus Centro', 'Lic. Morales'),     -- id 9
(13, 'C1', '2026-1C', 'Aula 402', 'Campus Centro', 'Cr. Domínguez'),    -- id 10
(14, 'C1', '2026-1C', 'Aula 403', 'Campus Centro', 'Dr. Peralta'),      -- id 11
-- Segundo año 1C
(18, 'C1', '2026-1C', 'Aula 404', 'Campus Centro', 'Dr. Aguirre'),      -- id 12
(19, 'C1', '2026-1C', 'Aula 405', 'Campus Centro', 'Lic. Herrera'),     -- id 13
(20, 'C1', '2026-1C', 'Aula 406', 'Campus Centro', 'Dr. Navarro');      -- id 14

-- ============================================
-- 9. Horarios — Sistemas
-- ============================================
INSERT INTO horarios (id_comision, dia_semana, hora_inicio, hora_fin) VALUES
-- AM I C1: Lunes y Miércoles 8:00-10:00
(1, 1, '08:00', '10:00'),
(1, 3, '08:00', '10:00'),
-- AM I C2: Martes y Jueves 18:00-20:00
(2, 2, '18:00', '20:00'),
(2, 4, '18:00', '20:00'),
-- Álgebra C1: Martes y Jueves 10:00-12:00
(3, 2, '10:00', '12:00'),
(3, 4, '10:00', '12:00'),
-- Sist y Org C1: Viernes 14:00-18:00
(4, 5, '14:00', '18:00'),
-- Física II C1: Lunes y Miércoles 14:00-16:00
(5, 1, '14:00', '16:00'),
(5, 3, '14:00', '16:00'),
-- Sintaxis C1: Martes y Jueves 8:00-10:00
(6, 2, '08:00', '10:00'),
(6, 4, '08:00', '10:00'),
-- Paradigmas C1: Lunes y Miércoles 10:00-12:00
(7, 1, '10:00', '12:00'),
(7, 3, '10:00', '12:00'),
-- Paradigmas C2: Martes y Jueves 14:00-16:00
(8, 2, '14:00', '16:00'),
(8, 4, '14:00', '16:00');

-- ============================================
-- 10. Horarios — Administración
-- ============================================
INSERT INTO horarios (id_comision, dia_semana, hora_inicio, hora_fin) VALUES
-- Intro Admin C1: Lunes y Miércoles 8:00-10:00
(9,  1, '08:00', '10:00'),
(9,  3, '08:00', '10:00'),
-- Contabilidad I C1: Martes y Jueves 10:00-12:00
(10, 2, '10:00', '12:00'),
(10, 4, '10:00', '12:00'),
-- Derecho C1: Viernes 8:00-12:00
(11, 5, '08:00', '12:00'),
-- Economía II C1: Lunes y Miércoles 14:00-16:00
(12, 1, '14:00', '16:00'),
(12, 3, '14:00', '16:00'),
-- RRHH C1: Martes y Jueves 16:00-18:00
(13, 2, '16:00', '18:00'),
(13, 4, '16:00', '18:00'),
-- Estadística C1: Lunes y Miércoles 10:00-12:00
(14, 1, '10:00', '12:00'),
(14, 3, '10:00', '12:00');

-- ============================================
-- 11. Historia académica — María González (SIS-1001)
--     Alumna avanzada: aprobó todo 1er año, cursando 2do año
-- ============================================
INSERT INTO historia_academica (id_alumno, id_materia, estado, nota_cursada, nota_final, fecha, periodo) VALUES
(1, 1, 'aprobada',     8.00, 7.00, '2023-07-15', '2023-1C'),  -- AM I
(1, 2, 'aprobada',     7.00, 6.00, '2023-07-20', '2023-1C'),  -- Álgebra
(1, 3, 'aprobada',     9.00, 8.00, '2023-07-10', '2023-1C'),  -- Sist y Org
(1, 4, 'promocionada', 8.50, NULL, '2023-12-01', '2023-2C'),  -- AM II
(1, 5, 'aprobada',     6.00, 4.00, '2024-03-10', '2023-2C'),  -- Física I
(1, 6, 'aprobada',     7.50, 7.00, '2024-03-15', '2023-2C');  -- Algoritmos

-- ============================================
-- 12. Historia académica — Carlos López (SIS-1002)
--     Alumno con resultados mixtos, AM I regularizada, Álgebra desaprobada
-- ============================================
INSERT INTO historia_academica (id_alumno, id_materia, estado, nota_cursada, nota_final, fecha, periodo) VALUES
(2, 1, 'regularizada', 5.00, NULL, '2024-07-10', '2024-1C'),  -- AM I regularizada
(2, 2, 'desaprobada',  3.00, NULL, '2024-07-15', '2024-1C'),  -- Álgebra desaprobada
(2, 3, 'promocionada', 9.00, NULL, '2024-07-05', '2024-1C');  -- Sist y Org promocionada

-- ============================================
-- 13. Historia académica — Ana Martínez (SIS-1003)
--     Alumna condicional: recursó AM I, quedó libre en Álgebra
-- ============================================
INSERT INTO historia_academica (id_alumno, id_materia, estado, nota_cursada, nota_final, fecha, periodo) VALUES
-- Primer intento 2023-1C
(3, 1, 'desaprobada',  2.00, NULL, '2023-07-10', '2023-1C'),  -- AM I desaprobada
(3, 2, 'libre',        NULL, NULL, '2023-07-15', '2023-1C'),  -- Álgebra libre
(3, 3, 'regularizada', 5.50, NULL, '2023-07-05', '2023-1C'),  -- Sist y Org regularizada
-- Recursada 2024-1C
(3, 1, 'regularizada', 4.50, NULL, '2024-07-10', '2024-1C'),  -- AM I regularizada (recursada)
(3, 2, 'aprobada',     6.00, 4.00, '2024-07-20', '2024-1C'),  -- Álgebra aprobada (recursada)
-- 2024-2C
(3, 5, 'regularizada', 5.00, NULL, '2024-12-05', '2024-2C'),  -- Física I regularizada
(3, 6, 'desaprobada',  3.50, NULL, '2024-12-10', '2024-2C');  -- Algoritmos desaprobada

-- ============================================
-- 14. Historia académica — Pedro Ramírez (SIS-1004)
--     Alumno avanzado: todo 1er año aprobado + parte de 2do
-- ============================================
INSERT INTO historia_academica (id_alumno, id_materia, estado, nota_cursada, nota_final, fecha, periodo) VALUES
-- 2022-1C
(4, 1, 'aprobada',     9.00, 9.00, '2022-07-10', '2022-1C'),
(4, 2, 'aprobada',     8.00, 7.00, '2022-07-15', '2022-1C'),
(4, 3, 'promocionada',10.00, NULL, '2022-07-05', '2022-1C'),
-- 2022-2C
(4, 4, 'aprobada',     7.00, 8.00, '2022-12-10', '2022-2C'),
(4, 5, 'aprobada',     8.00, 6.00, '2023-03-10', '2022-2C'),
(4, 6, 'aprobada',     9.00, 9.00, '2023-03-15', '2022-2C'),
-- 2023-1C
(4, 7, 'aprobada',     7.50, 6.00, '2023-07-20', '2023-1C'),
(4, 8, 'aprobada',     8.00, 7.00, '2023-07-25', '2023-1C'),
(4, 9, 'promocionada', 9.00, NULL, '2023-07-15', '2023-1C'),
-- 2023-2C
(4, 10, 'regularizada', 6.00, NULL, '2023-12-10', '2023-2C'),  -- Diseño regularizado, no rindió final
(4, 11, 'aprobada',     8.00, 7.00, '2024-03-10', '2023-2C');  -- Bases de Datos aprobada

-- ============================================
-- 15. Historia académica — Lucía Fernández (ADM-2001)
--     Alumna avanzada en Administración, cursando 2do año
-- ============================================
INSERT INTO historia_academica (id_alumno, id_materia, estado, nota_cursada, nota_final, fecha, periodo) VALUES
-- 2024-1C
(5, 12, 'aprobada',     8.00, 7.00, '2024-07-10', '2024-1C'),  -- Intro Admin
(5, 13, 'aprobada',     7.00, 6.00, '2024-07-15', '2024-1C'),  -- Contabilidad I
(5, 14, 'promocionada', 9.00, NULL, '2024-07-05', '2024-1C'),  -- Derecho
-- 2024-2C
(5, 15, 'aprobada',     6.50, 5.00, '2024-12-10', '2024-2C'),  -- Economía I
(5, 16, 'regularizada', 5.00, NULL, '2024-12-15', '2024-2C'),  -- Matemática regularizada
(5, 17, 'aprobada',     7.00, 6.00, '2025-03-10', '2024-2C');  -- Contabilidad II

-- ============================================
-- 16. Historia académica — Martín García (ADM-2002)
--     Alumno nuevo en Administración, sin historia (ingresó 2025)
-- ============================================
-- (sin registros — alumno nuevo)

-- ============================================
-- 17. Inscripciones actuales (período 2026-1C)
-- ============================================

-- María (SIS-1001): Física II, Sintaxis, Paradigmas C1
INSERT INTO inscripciones (id_alumno, id_comision, fecha) VALUES
(1, 5, '2026-03-01'),   -- Física II C1
(1, 6, '2026-03-01'),   -- Sintaxis C1
(1, 7, '2026-03-01');   -- Paradigmas C1

-- Carlos (SIS-1002): AM I C2 y Álgebra (recursando)
INSERT INTO inscripciones (id_alumno, id_comision, fecha) VALUES
(2, 2, '2026-03-01'),   -- AM I C2 (turno noche)
(2, 3, '2026-03-01');   -- Álgebra C1

-- Ana (SIS-1003): AM I C1 y Sist y Org (recursando Algoritmos no puede, le falta correlativa)
INSERT INTO inscripciones (id_alumno, id_comision, fecha) VALUES
(3, 1, '2026-03-01'),   -- AM I C1
(3, 4, '2026-03-01');   -- Sist y Org C1

-- Pedro (SIS-1004): sin inscripciones en 2026-1C (tiene Diseño pendiente de final)

-- Lucía (ADM-2001): Economía II, RRHH, Estadística
INSERT INTO inscripciones (id_alumno, id_comision, fecha) VALUES
(5, 12, '2026-03-01'),  -- Economía II C1
(5, 13, '2026-03-01'),  -- RRHH C1
(5, 14, '2026-03-01');  -- Estadística C1

-- Martín (ADM-2002): Intro Admin, Contabilidad I, Derecho
INSERT INTO inscripciones (id_alumno, id_comision, fecha) VALUES
(6, 9,  '2026-03-01'),  -- Intro Admin C1
(6, 10, '2026-03-01'),  -- Contabilidad I C1
(6, 11, '2026-03-01');  -- Derecho C1
