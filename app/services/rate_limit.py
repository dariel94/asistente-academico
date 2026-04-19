import os
import time

# Valores de producción por defecto. Pueden sobrescribirse con las variables
# de entorno RATE_LIMIT_MAX / RATE_LIMIT_WINDOW_SECONDS (útil para pruebas).
MAX_REQUESTS = int(os.getenv("RATE_LIMIT_MAX", "30"))
WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))

_requests: dict[int, list[float]] = {}


def check_rate_limit(id_alumno: int) -> bool:
    """Retorna True si la request está permitida, False si excede el límite."""
    now = time.time()
    cutoff = now - WINDOW_SECONDS

    timestamps = _requests.get(id_alumno, [])
    # Limpiar timestamps viejos
    timestamps = [t for t in timestamps if t > cutoff]

    if len(timestamps) >= MAX_REQUESTS:
        _requests[id_alumno] = timestamps
        return False

    timestamps.append(now)
    _requests[id_alumno] = timestamps
    return True
