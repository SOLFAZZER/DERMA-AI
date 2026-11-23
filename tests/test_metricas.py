"""CP025: las métricas se calculan bien. Se comparan con valores hechos a mano sobre 12 ejemplos controlados.

Se usan las mismas funciones de scikit-learn que el cuaderno de entrenamiento (classification_report,
accuracy_score y confusion_matrix).
"""
import pytest
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

CLASES = ["BCC", "MEL", "NV"]
# 6 NV, 4 MEL y 2 BCC. Errores: 1 NV dicho MEL, 1 MEL dicho NV y 1 BCC dicho NV.
REAL = ["NV"] * 6 + ["MEL"] * 4 + ["BCC"] * 2
PRED = ["NV"] * 5 + ["MEL"] + ["MEL"] * 3 + ["NV"] + ["BCC"] + ["NV"]


@pytest.fixture(scope="module")
def reporte():
    return classification_report(REAL, PRED, labels=CLASES, output_dict=True, zero_division=0)


def test_matriz_de_confusion():
    # filas = clase real y columnas = clase predicha, en el orden BCC, MEL, NV
    assert confusion_matrix(REAL, PRED, labels=CLASES).tolist() == [[1, 0, 1], [0, 3, 1], [0, 1, 5]]


def test_exactitud():
    assert accuracy_score(REAL, PRED) == pytest.approx(9 / 12)  # 9 aciertos de 12


def test_precision_sensibilidad_y_f1_por_clase(reporte):
    esperado = {  # (precisión, sensibilidad, F1) calculados a mano
        "BCC": (1 / 1, 1 / 2, 2 / 3),
        "MEL": (3 / 4, 3 / 4, 3 / 4),
        "NV": (5 / 7, 5 / 6, 10 / 13),
    }
    for clase, (p, r, f1) in esperado.items():
        assert reporte[clase]["precision"] == pytest.approx(p)
        assert reporte[clase]["recall"] == pytest.approx(r)
        assert reporte[clase]["f1-score"] == pytest.approx(f1)


def test_promedios_macro_y_ponderado(reporte):
    macro = reporte["macro avg"]
    assert macro["precision"] == pytest.approx((1 + 3 / 4 + 5 / 7) / 3)
    assert macro["recall"] == pytest.approx((1 / 2 + 3 / 4 + 5 / 6) / 3)
    assert macro["f1-score"] == pytest.approx((2 / 3 + 3 / 4 + 10 / 13) / 3)
    pond = reporte["weighted avg"]  # pesos 2, 4 y 6 de 12 imágenes
    assert pond["precision"] == pytest.approx((2 * 1 + 4 * 3 / 4 + 6 * 5 / 7) / 12)
    assert pond["recall"] == pytest.approx(9 / 12)  # la sensibilidad ponderada es igual a la exactitud
    assert pond["f1-score"] == pytest.approx((2 * 2 / 3 + 4 * 3 / 4 + 6 * 10 / 13) / 12)
