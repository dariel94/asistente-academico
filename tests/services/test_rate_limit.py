"""Tests para `app.services.rate_limit`.

La política es una ventana deslizante por `id_alumno`: hasta
`MAX_REQUESTS` requests dentro de una ventana de `WINDOW_SECONDS`.
"""
from unittest.mock import patch

import pytest

from app.services import rate_limit


@pytest.fixture(autouse=True)
def _reset_state():
    """Cada test arranca con el diccionario interno limpio."""
    rate_limit._requests.clear()
    yield
    rate_limit._requests.clear()


def test_permite_primera_request():
    assert rate_limit.check_rate_limit(1) is True


def test_permite_hasta_max_requests_inclusive():
    """Las primeras MAX_REQUESTS deben pasar."""
    for _ in range(rate_limit.MAX_REQUESTS):
        assert rate_limit.check_rate_limit(1) is True


def test_request_max_mas_uno_es_rechazada():
    """La request número MAX+1 dentro de la ventana cae con False."""
    for _ in range(rate_limit.MAX_REQUESTS):
        rate_limit.check_rate_limit(1)
    assert rate_limit.check_rate_limit(1) is False


def test_segunda_request_excedida_sigue_rechazada():
    """Una vez excedido, los intentos siguientes siguen rechazados (no se
    suman al contador, se descartan)."""
    for _ in range(rate_limit.MAX_REQUESTS + 5):
        rate_limit.check_rate_limit(1)
    # Aún dentro de la ventana, debería rechazar
    assert rate_limit.check_rate_limit(1) is False


def test_aislamiento_entre_alumnos():
    """El cupo de un alumno no afecta al de otro."""
    for _ in range(rate_limit.MAX_REQUESTS):
        rate_limit.check_rate_limit(1)
    assert rate_limit.check_rate_limit(1) is False
    # Otro alumno empieza desde cero
    assert rate_limit.check_rate_limit(2) is True


def test_timestamps_viejos_se_descartan():
    """Cuando el reloj avanza más allá de la ventana, los timestamps
    antiguos se eliminan y el alumno vuelve a tener cupo completo."""
    base = 1_000_000.0
    with patch("app.services.rate_limit.time.time") as mock_time:
        # Llenar el cupo en t=base
        mock_time.return_value = base
        for _ in range(rate_limit.MAX_REQUESTS):
            rate_limit.check_rate_limit(7)
        assert rate_limit.check_rate_limit(7) is False

        # Avanzar el reloj más allá de la ventana
        mock_time.return_value = base + rate_limit.WINDOW_SECONDS + 1
        # Debería volver a aceptar
        assert rate_limit.check_rate_limit(7) is True


def test_timestamps_parcialmente_viejos():
    """Si la mitad de los timestamps caen fuera de la ventana, debe quedar
    espacio para nuevas requests."""
    base = 1_000_000.0
    with patch("app.services.rate_limit.time.time") as mock_time:
        # 10 requests en t=base
        mock_time.return_value = base
        for _ in range(10):
            rate_limit.check_rate_limit(3)

        # Avanzar el reloj para que las 10 anteriores queden afuera
        mock_time.return_value = base + rate_limit.WINDOW_SECONDS + 1
        # Cupo completo de nuevo
        for _ in range(rate_limit.MAX_REQUESTS):
            assert rate_limit.check_rate_limit(3) is True
        assert rate_limit.check_rate_limit(3) is False
