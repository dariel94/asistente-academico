import time

MAX_REQUESTS = 120
WINDOW_SECONDS = 60

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
