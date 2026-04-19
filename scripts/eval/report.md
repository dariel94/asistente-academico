# Reporte de Evaluación — Sección 6.2

- **Casos:** 27
- **Corridas totales:** 81
- **Corridas válidas:** 80
- **Corridas con error de runner:** 1

## 1. Clasificador de Intent

| | Predicho ACADEMICA | Predicho CONVERSACION |
|---|---:|---:|
| **Real ACADEMICA** | 65 | 0 |
| **Real CONVERSACION** | 0 | 15 |

- Accuracy global: **100.0%**
- Precisión ACADEMICA: 100.0%  ·  Recall ACADEMICA: 100.0%
- Precisión CONVERSACION: 100.0%  ·  Recall CONVERSACION: 100.0%

## 2. Tool Calling (rama académica)

- Match exacto (mismo set de tools que el esperado): **100.0%**
- Al menos una tool esperada invocada: 100.0%
- Ninguna tool invocada: 0.0%
- Tools de más promedio por corrida académica: 0
- Conversaciones sin invocar tools: 100.0%

### Match exacto por tool esperada

| Tool | n corridas | match exacto |
|---|---:|---:|
| `buscar_en_documentos` | 9 | 100.0% |
| `consultar_materias_disponibles` | 9 | 100.0% |
| `obtener_historia_academica` | 12 | 100.0% |
| `obtener_inscripciones` | 8 | 100.0% |
| `obtener_materia` | 9 | 100.0% |
| `obtener_materias_faltantes` | 9 | 100.0% |
| `obtener_plan_de_estudios` | 9 | 100.0% |

## 3. Contenido de la Respuesta

- Respuesta correcta (todos los keywords requeridos + ningún prohibido): **88.8%**
- Largo promedio de respuesta: 445.4 chars

## 4. Consistencia entre Corridas

- Casos con intent consistente N-de-N: **100.0%**
- Casos con tools consistentes N-de-N: **100.0%**
- Casos con respuesta consistente N-de-N: **100.0%**

## 5. Latencia

- n: 80
- mín: 1040.2 ms · media: 3585.2 ms · mediana: 3022.7 ms · p95: 7961.1 ms · máx: 11383.4 ms

## 6. Filtrado por Perfil (caso FP-01)

- n corridas: 3
- Tasa de respuesta correcta: **100.0%**
- Sin invasiones de datos de otros alumnos.

## 7. Casos con Falla (detalle)

### Fallas de intent
Ninguna.

### Fallas de tool calling
Ninguna.

### Fallas de contenido

| Caso | Run | Keywords faltantes | Prohibidos presentes |
|---|---:|---|---|
| DI-01 | 0 | ['cursar'] | [] |
| DI-01 | 1 | ['cursar'] | [] |
| DI-01 | 2 | ['cursar'] | [] |
| DI-03 | 0 | ['correlativ'] | [] |
| DI-03 | 1 | ['correlativ'] | [] |
| DI-03 | 2 | ['correlativ'] | [] |
| FA-02 | 0 | ['porcentaje'] | [] |
| FA-02 | 1 | ['porcentaje'] | [] |
| FA-02 | 2 | ['porcentaje'] | [] |

### Errores de runner

- IN-01 run 1: Error interno del servidor: TypeError
