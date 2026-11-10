"""Módulo de resultados (C07): arma la respuesta de la operación I01."""
import logging
import sqlite3

import numpy as np

from app.db import catalogo
from app.explicabilidad.superposicion import crear_png_base64, tensor_a_imagen
from app.inferencia.servicio import Resultado

AVISO = ("Prototipo académico de apoyo a la detección e interpretación de lesiones cutáneas. "
         "Este resultado no es un diagnóstico médico ni reemplaza la valoración de un profesional de la salud.")
MSG_BAJA_CONFIANZA = ("La confianza del resultado es baja: tómalo con precaución y consulta a un profesional.")
MSG_PROVISIONAL = "MODELO PROVISIONAL DE DESARROLLO: este resultado no proviene de un modelo entrenado."
MSG_SIN_MAPA = "Este modelo no ofrece mapa de calor."
MSG_MAPA_FALLO = ("No se pudo generar el mapa de calor, pero la categoría y la confianza sí están disponibles.")
EXPLICACION_MAPA = ("Las zonas más cálidas (rojo) son las que más influyeron en el resultado del modelo. "
                    "Es una ayuda visual: no marca con precisión los bordes de la lesión ni confirma un diagnóstico.")
log = logging.getLogger("derma.resultados")


def armar_respuesta(r: Resultado, conn: sqlite3.Connection, entrada: np.ndarray | None = None) -> dict:
    nombres = {x["codigo"]: x for x in catalogo.listar_lesiones(conn)}
    lesion = nombres.get(r.categoria)
    mensajes = []
    if r.provisional:
        mensajes.append(MSG_PROVISIONAL)
    if r.baja_confianza:
        mensajes.append(MSG_BAJA_CONFIANZA)
    mapa_calor = ""
    if r.mapa is not None and entrada is not None:
        try:
            mapa_calor = crear_png_base64(tensor_a_imagen(entrada), r.mapa)
        except Exception:
            log.exception("No se pudo dibujar el mapa de calor")
    if not mapa_calor:
        mensajes.append(MSG_MAPA_FALLO if r.mapa_fallo or r.mapa is not None else MSG_SIN_MAPA)
    version = catalogo.version_activa(conn)
    return {
        "categoria": {
            "codigo": r.categoria,
            "nombre": lesion["nombre"] if lesion else r.categoria,
            "nivel_riesgo": lesion["nivel_riesgo"] if lesion else None,
            "descripcion": lesion["descripcion"] if lesion else None,
        },
        "confianza": round(r.confianza * 100, 1),
        "baja_confianza": r.baja_confianza,
        "probabilidades": [
            {"codigo": c, "nombre": nombres[c]["nombre"] if c in nombres else c, "porcentaje": round(p * 100, 1)}
            for c, p in r.probabilidades.items()
        ],
        "mapa_calor": mapa_calor,
        "explicacion_mapa": EXPLICACION_MAPA if mapa_calor else "",
        "mensaje": " ".join(mensajes),
        "version_modelo": (
            {"id": version["id"], "arquitectura": version["arquitectura"]} if version
            else {"id": None, "arquitectura": r.modelo}
        ),
        "aviso": AVISO,
    }
