"""Una sola instancia del servicio para toda la aplicación (patrón Singleton), cargada una vez."""
import logging
import threading

from app.inferencia.base import InferenciaNoDisponible
from app.inferencia.fabrica import crear_modelo
from app.inferencia.servicio import ServicioInferencia

log = logging.getLogger("derma.inferencia")
_servicio: ServicioInferencia | None = None
_cerrojo = threading.Lock()


def esta_cargado() -> bool:
    return _servicio is not None


def obtener_servicio() -> ServicioInferencia:
    """Carga el modelo la primera vez. Si falla, lanza InferenciaNoDisponible (y se reintenta después)."""
    global _servicio
    with _cerrojo:
        if _servicio is None:
            try:
                _servicio = ServicioInferencia(crear_modelo())
            except InferenciaNoDisponible:
                raise
            except Exception as e:  # cualquier fallo al cargar el modelo
                raise InferenciaNoDisponible(f"No se pudo cargar el modelo: {e}") from e
        return _servicio


def precargar() -> None:
    """Se llama al arrancar para que la primera solicitud no espere. Un fallo no detiene la API."""
    try:
        obtener_servicio()
        log.info("Modelo cargado.")
    except InferenciaNoDisponible as e:
        log.warning("El modelo no se cargó al arrancar: %s", e)


def reiniciar() -> None:
    """Solo para pruebas."""
    global _servicio
    _servicio = None
