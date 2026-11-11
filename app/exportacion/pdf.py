"""Generación del informe en PDF del resultado (en memoria; no se guarda nada en el servidor)."""
import base64
import binascii
import io
from xml.sax.saxutils import escape

from PIL import Image
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image as ImagenPDF
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

RIESGO = {"benigno": "Lesión benigna", "premaligno": "Lesión premaligna", "maligno": "Lesión maligna"}
LADO_MAX = 700          # px: las imágenes del informe se reducen a este lado
ANCHO_IMG = 7.6 * cm
MSG_BAJA = "La confianza del resultado es baja: tómalo con precaución y consulta a un profesional."


def _imagen_pil(origen: bytes | Image.Image) -> Image.Image:
    img = origen if isinstance(origen, Image.Image) else Image.open(io.BytesIO(origen))
    img = img.convert("RGB")
    img.thumbnail((LADO_MAX, LADO_MAX))
    return img


def decodificar_mapa(b64: str) -> Image.Image | None:
    """Decodifica el PNG del mapa de calor. Devuelve None si viene vacío o no es una imagen válida."""
    if not b64:
        return None
    try:
        return _imagen_pil(base64.b64decode(b64, validate=True))
    except (binascii.Error, ValueError, OSError):
        return None


def _flowable(img: Image.Image) -> ImagenPDF:
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=88)
    buf.seek(0)
    ancho, alto = img.size
    return ImagenPDF(buf, width=ANCHO_IMG, height=ANCHO_IMG * alto / ancho)


def construir_pdf(r: dict, original: Image.Image | None, fecha: str) -> bytes:
    """Arma el informe. `r` es el resultado de /api/analizar (ya validado)."""
    base = getSampleStyleSheet()
    normal = ParagraphStyle("n", parent=base["Normal"], fontSize=10.5, leading=15)
    chico = ParagraphStyle("c", parent=normal, fontSize=8.5, leading=11, textColor=colors.HexColor("#555555"))
    h1 = ParagraphStyle("h1", parent=base["Title"], fontSize=18, leading=22, alignment=0, spaceAfter=2)
    h2 = ParagraphStyle("h2", parent=base["Heading2"], fontSize=13, leading=16, spaceBefore=10, spaceAfter=8)
    aviso = ParagraphStyle("a", parent=normal, backColor=colors.HexColor("#FFF4D6"), borderPadding=6,
                           borderColor=colors.HexColor("#E0B84A"), borderWidth=0.6)

    def p(texto, estilo=normal):
        return Paragraph(escape(str(texto)), estilo)

    cat = r["categoria"]
    version = r.get("version_modelo") or {}
    historia = [
        p("Derma-AI · Informe de resultado experimental", h1),
        p(f"Fecha: {fecha or 'no indicada'} · Modelo: {version.get('arquitectura') or 'no indicado'}"
          + (f" (versión {version['id']})" if version.get("id") else ""), chico),
        Spacer(1, 12),
        p("Prototipo académico, resultado experimental. No es un diagnóstico médico ni reemplaza "
          "la valoración de un profesional de la salud.", aviso),
        Spacer(1, 6),
        p("Resultado principal", h2),
    ]
    etiqueta = ParagraphStyle("e", parent=normal, textColor=colors.HexColor("#555555"))
    filas_res = [
        [p("Categoría", etiqueta), p(cat["nombre"], ParagraphStyle("v", parent=normal, fontName="Helvetica-Bold"))],
    ]
    if cat.get("nivel_riesgo") in RIESGO:
        filas_res.append([p("Nivel de riesgo", etiqueta), p(RIESGO[cat["nivel_riesgo"]])])
    filas_res.append([p("Confianza del modelo", etiqueta), p(f"{r['confianza']:.1f} %")])
    if cat.get("descripcion"):
        filas_res.append([p("Descripción", etiqueta), p(cat["descripcion"])])
    res = Table(filas_res, colWidths=[4.2 * cm, 12.8 * cm], hAlign="LEFT")
    res.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                             ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                             ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    historia.append(res)
    if r.get("baja_confianza"):
        historia += [Spacer(1, 6), p(MSG_BAJA, ParagraphStyle("b", parent=normal, textColor=colors.HexColor("#8A5300")))]
    # El servidor ya incluye el aviso de baja confianza dentro de `mensaje`: no se repite.
    extra = (r.get("mensaje") or "").replace(MSG_BAJA, "").strip()
    if extra:
        historia += [Spacer(1, 4), p(extra, chico)]

    historia += [Spacer(1, 8), p("Probabilidad por categoría", h2)]
    filas = [["Categoría", "Probabilidad"]] + [[x["nombre"], f"{x['porcentaje']:.1f} %"] for x in r["probabilidades"]]
    tabla = Table(filas, colWidths=[10 * cm, 4 * cm], hAlign="LEFT")
    tabla.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8EEF4")),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#BBBBBB")),
        ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#F4F9F4")),
    ]))
    historia.append(tabla)

    mapa = decodificar_mapa(r.get("mapa_calor", ""))
    historia += [Spacer(1, 8), p("Explicación del resultado (Grad-CAM)", h2)]
    if mapa is not None:
        pares = [[_flowable(original) if original is not None else p("(imagen original no incluida)", chico),
                  _flowable(mapa)],
                 [p("Imagen original", chico), p("Zonas en las que se fijó el modelo", chico)]]
        figuras = Table(pares, colWidths=[8.2 * cm, 8.2 * cm], hAlign="LEFT")
        figuras.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
        historia.append(figuras)
        historia.append(Spacer(1, 4))
        historia.append(p(r.get("explicacion_mapa") or
                          "Las zonas más cálidas (rojo) son las que más influyeron en el resultado.", chico))
    else:
        historia.append(p("No hubo mapa de calor disponible para este resultado.", chico))

    historia += [Spacer(1, 10), p(r.get("aviso") or "Prototipo académico. No es un diagnóstico médico.", chico),
                 p("La imagen y el resultado no se guardan en el servidor: este archivo solo existe en tu equipo.", chico)]

    buf = io.BytesIO()
    SimpleDocTemplate(buf, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.8 * cm,
                      bottomMargin=1.8 * cm, title="Derma-AI · Resultado experimental",
                      author="Derma-AI").build(historia)
    return buf.getvalue()
