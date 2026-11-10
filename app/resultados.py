"""Módulo de resultados (C07): arma la respuesta de la operación I01."""
import sqlite3

from app.db import catalogo
from app.inferencia.servicio import Resultado

AVISO = ("Prototipo académico de apoyo a la detección e interpretación de lesiones cutáneas. "
         "Este resultado no es un diagnóstico médico ni reemplaza la valoración de un profesional de la salud.")
MSG_BAJA_CONFIANZA = ("La confianza del resultado es baja: tómalo con precaución y consulta a un profesional.")
MSG_PROVISIONAL = "MODELO PROVISIONAL DE DESARROLLO: este resultado no proviene de un modelo entrenado."
MSG_SIN_MAPA = "El mapa de calor aún no está disponible."


def armar_respuesta(r: Resultado, conn: sqlite3.Connection, mapa_calor: str = "", mensaje_mapa: str = MSG_SIN_MAPA) -> dict:
    nombres = {x["codigo"]: x for x in catalogo.listar_lesiones(conn)}
    lesion = nombres.get(r.categoria)
    mensajes = []
    if r.provisional:
        mensajes.append(MSG_PROVISIONAL)
    if r.baja_confianza:
        mensajes.append(MSG_BAJA_CONFIANZA)
    if not mapa_calor:
        mensajes.append(mensaje_mapa)
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
        "mensaje": " ".join(mensajes),
        "version_modelo": (
            {"id": version["id"], "arquitectura": version["arquitectura"]} if version
            else {"id": None, "arquitectura": r.modelo}
        ),
        "aviso": AVISO,
    }
