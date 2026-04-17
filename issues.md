# Issues conocidos

## 1. Incompatibilidad entre `mcp` y FastAPI por versión de Starlette

**Fecha:** 2026-04-17

**Síntoma:** Al iniciar el backend, FastAPI falla con:
```
TypeError: Router.__init__() got an unexpected keyword argument 'on_startup'
```

**Causa:** El paquete `mcp` (v1.27.0) declara como dependencia `starlette>=0.27`, lo que permite que pip instale `starlette 1.0.0`. Esta versión elimina el parámetro `on_startup` de `Router.__init__()`, rompiendo FastAPI `0.115.12` que depende de ese parámetro.

**Solución:** Forzar una versión de Starlette compatible con FastAPI 0.115.x:
```bash
pip install "starlette<1.0.0"
```

**Versiones verificadas como compatibles:**
- `fastapi==0.115.12`
- `mcp>=1.0.0`
- `starlette==0.52.1`

**Prevención:** Si se actualiza FastAPI a una versión compatible con Starlette 1.x, esta restricción puede eliminarse.
