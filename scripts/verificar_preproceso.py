"""Verifica que el servidor prepare las imágenes igual que el entrenamiento y mide el acierto real.

Uso (con el entorno activo, desde la raíz del repositorio):
    python -m scripts.verificar_preproceso --carpeta RUTA_DE_IMAGENES --csv split_test.csv --n 200

- `--carpeta`: carpeta con las imágenes .jpg de HAM10000 (se buscan también en subcarpetas).
- `--csv`: `split_test.csv` que guardó el cuaderno (columnas image_id, lesion_id, dx). Es opcional:
  sin él solo se compara servidor contra entrenamiento, sin calcular el acierto.
- `--n`: cuántas imágenes usar (por defecto 200, elegidas al azar con semilla fija).
"""
import argparse
import os
import random
import sys
from pathlib import Path

import numpy as np
from PIL import Image

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--carpeta", required=True)
    ap.add_argument("--csv")
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--semilla", type=int, default=42)
    a = ap.parse_args()

    import tensorflow as tf
    from tensorflow.keras.applications.mobilenet_v2 import preprocess_input

    from app.imagenes.preprocesamiento import preprocesar
    from app.inferencia.fabrica import crear_modelo

    modelo = crear_modelo("keras")
    clases = [c.lower() for c in modelo.clases]
    rutas = {p.stem: p for p in Path(a.carpeta).rglob("*") if p.suffix.lower() in (".jpg", ".jpeg", ".png")}
    if not rutas:
        print("No se encontraron imágenes en la carpeta.")
        return 1

    etiquetas = {}
    if a.csv:
        import csv
        with open(a.csv, encoding="utf-8") as f:
            etiquetas = {fila["image_id"]: fila["dx"].lower() for fila in csv.DictReader(f)}
        ids = sorted(i for i in etiquetas if i in rutas)
        if not ids:
            print("Ninguna imagen de la carpeta aparece en el CSV.")
            return 1
    else:
        ids = sorted(rutas)
    random.Random(a.semilla).shuffle(ids)
    ids = ids[:a.n]
    print(f"Usando {len(ids)} imágenes" + (" con etiqueta real." if etiquetas else " (sin etiquetas)."))

    difs, distintas, aciertos_srv, aciertos_ent, dif_prob = [], 0, 0, 0, []
    for i in ids:
        ruta = str(rutas[i])
        # Servidor: lo que hace la aplicación al recibir una imagen
        t_srv = preprocesar(Image.open(ruta))
        # Entrenamiento: exactamente lo que hacía el cuaderno
        img = tf.image.resize(tf.io.decode_jpeg(tf.io.read_file(ruta), channels=3), (224, 224))
        t_ent = preprocess_input(tf.cast(tf.round(img), tf.uint8).numpy().astype("float32"))[None]
        difs.append(float(np.abs(t_srv - t_ent).mean()))
        p_srv, p_ent = modelo.predecir(t_srv), modelo.predecir(t_ent)
        dif_prob.append(float(np.abs(p_srv - p_ent).max()) * 100)
        c_srv, c_ent = clases[int(np.argmax(p_srv))], clases[int(np.argmax(p_ent))]
        distintas += c_srv != c_ent
        if etiquetas:
            aciertos_srv += c_srv == etiquetas[i]
            aciertos_ent += c_ent == etiquetas[i]

    n = len(ids)
    print("\n=== RESULTADO ===")
    print(f"Diferencia media de píxeles (escala -1 a 1): {np.mean(difs):.4f}  (0 = idénticos)")
    print(f"Diferencia máxima en una probabilidad:       {np.max(dif_prob):.2f} puntos porcentuales "
          f"(media {np.mean(dif_prob):.2f})")
    print(f"Imágenes donde servidor y entrenamiento dan distinta categoría: {distintas} de {n}")
    if etiquetas:
        print(f"Acierto con el preprocesamiento del servidor:       {aciertos_srv / n:.1%}")
        print(f"Acierto con el preprocesamiento del entrenamiento:  {aciertos_ent / n:.1%}")
        print("(Referencia: exactitud del cuaderno en la partición de prueba = 79,9 %.)")
    ok = distintas / n <= 0.02 and np.mean(dif_prob) < 3.0
    print("(Quedan diferencias de 1 a 3 puntos por el decodificador JPEG de Pillow frente al de TensorFlow: es normal.)")
    print("\nCONCLUSIÓN:", "el servidor prepara las imágenes igual que el entrenamiento." if ok
          else "HAY una diferencia relevante: avísame y la corregimos.")
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
