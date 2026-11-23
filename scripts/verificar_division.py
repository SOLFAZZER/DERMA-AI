"""CP026: comprueba que no hay fuga de datos entre entrenamiento, validación y prueba.

Repite la misma división del cuaderno (StratifiedGroupKFold, 7 grupos, semilla 42, agrupada por lesion_id)
y muestra, con números, que ninguna lesión ni imagen está en dos conjuntos a la vez.

Dos formas de usarlo:

A) Comprobar la división REAL con la que se entrenó el modelo (la recomendada):
    python -m scripts.verificar_division --division RUTA/tabla_con_division.csv
   El CSV debe tener `lesion_id` y una columna `division` (train/val/test) o `conjunto`. Si trae la columna
   `origen`, solo se revisan las filas de HAM10000 (origen que empieza por "ham").

B) Repetir la división del cuaderno desde el metadata original (necesita pandas y scikit-learn):
    python -m scripts.verificar_division --metadata RUTA/HAM10000_metadata.csv --salida division_ham10000.csv
   Ojo: según la versión de scikit-learn, los tamaños pueden diferir un poco de los del entrenamiento.

- `--salida`: opcional. Guarda image_id, lesion_id, dx y conjunto de cada imagen (evidencia).
Termina con código 0 si no hay fuga y con código 1 si la hay.
"""
import argparse
import sys

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold


def dividir(meta: pd.DataFrame, semilla: int = 42, grupos: int = 7) -> pd.DataFrame:
    """Misma división del cuaderno: prueba = grupo 0, validación = grupo 1, entrenamiento = el resto."""
    clases = sorted(meta["dx"].unique())
    y = meta["dx"].map({c: i for i, c in enumerate(clases)})
    sgkf = StratifiedGroupKFold(n_splits=grupos, shuffle=True, random_state=semilla)
    folds = [idx for _, idx in sgkf.split(meta, y, groups=meta["lesion_id"])]
    conjunto = np.full(len(meta), "entrenamiento", dtype=object)
    conjunto[folds[0]] = "prueba"
    conjunto[folds[1]] = "validacion"
    return meta.assign(conjunto=conjunto)


def leer_division(ruta: str) -> pd.DataFrame:
    """Lee una tabla que ya trae la división usada en el entrenamiento."""
    t = pd.read_csv(ruta)
    if "origen" in t.columns:
        t = t[t["origen"].astype(str).str.startswith("ham")]
    col = "division" if "division" in t.columns else "conjunto"
    nombres = {"train": "entrenamiento", "val": "validacion", "test": "prueba"}
    t = t.assign(conjunto=t[col].map(nombres))
    t = t[t["conjunto"].notna()]
    if "image_id" not in t.columns:
        t = t.assign(image_id=t["clave"] if "clave" in t.columns else t["archivo"])
    if "dx" not in t.columns:
        t = t.assign(dx="?")
    return t[["image_id", "lesion_id", "dx", "conjunto"]].reset_index(drop=True)


def comprobar(div: pd.DataFrame) -> list[str]:
    """Devuelve la lista de problemas (vacía = sin fuga)."""
    problemas = []
    nombres = ["entrenamiento", "validacion", "prueba"]
    for i, a in enumerate(nombres):
        for b in nombres[i + 1:]:
            lesiones = set(div.loc[div.conjunto == a, "lesion_id"]) & set(div.loc[div.conjunto == b, "lesion_id"])
            imagenes = set(div.loc[div.conjunto == a, "image_id"]) & set(div.loc[div.conjunto == b, "image_id"])
            if lesiones:
                problemas.append(f"{len(lesiones)} lesiones en {a} y {b}")
            if imagenes:
                problemas.append(f"{len(imagenes)} imágenes en {a} y {b}")
    if div["image_id"].duplicated().any():
        problemas.append("hay imágenes repetidas en la tabla")
    return problemas


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--metadata", default=None)
    ap.add_argument("--division", default=None)
    ap.add_argument("--salida", default=None)
    a = ap.parse_args()

    if bool(a.metadata) == bool(a.division):
        ap.error("usa --division (la real) o --metadata, pero no ambos")
    div = leer_division(a.division) if a.division else dividir(pd.read_csv(a.metadata))
    print(f"Total: {len(div)} imágenes, {div.lesion_id.nunique()} lesiones distintas\n")
    print(f"{'conjunto':<15}{'imágenes':>10}{'lesiones':>10}")
    for c in ["entrenamiento", "validacion", "prueba"]:
        d = div[div.conjunto == c]
        print(f"{c:<15}{len(d):>10}{d.lesion_id.nunique():>10}")
    print("\nProporción por clase (%):")
    print((pd.crosstab(div.dx, div.conjunto, normalize="columns") * 100).round(1).to_string())

    problemas = comprobar(div)
    print()
    if problemas:
        print("FUGA DETECTADA:", "; ".join(problemas))
        return 1
    print("RESULTADO: SIN FUGA. Ninguna lesión ni imagen aparece en dos conjuntos a la vez.")
    if a.salida:
        div[["image_id", "lesion_id", "dx", "conjunto"]].to_csv(a.salida, index=False)
        print(f"Evidencia guardada en {a.salida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
