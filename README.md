# Derma-AI

Prototipo web académico (Universidad Santiago de Cali) que clasifica imágenes dermatoscópicas con una CNN (MobileNetV2) y explica la predicción con un mapa de calor Grad-CAM. **No es una herramienta de diagnóstico ni reemplaza a un profesional de la salud.**

## Estado
API FastAPI con `GET /api/salud`, `GET /api/lesiones` y `GET /api/modelo` (catálogo de las 7 clases y versión del modelo en SQLite) y el inicio de sesión con correo y contraseña (`/api/auth/registro`, `/login`, `/logout`, `/yo`). El resto se construye por pasos (ver `docs/BACKLOG.md`).

## Cómo correrlo en tu computador
Requiere Python 3.11 o superior.

```bash
python -m venv .venv
source .venv/bin/activate        # En Windows: .venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env             # En Windows: copy .env.example .env  (y cambia DERMA_SECRET_KEY)
uvicorn app.main:app --reload
```

Abre http://127.0.0.1:8000/api/salud o la documentación interactiva en http://127.0.0.1:8000/docs.

Datos iniciales (catálogo de las 7 clases y versión del modelo con sus métricas):

```bash
python -m scripts.inicializar_datos --metrics docs/modelo_v2/metrics.json --epocas 40
```

Crea `data/catalogo.db` (no se sube a Git). Se puede repetir sin duplicar datos.

Inicio de sesión: las cuentas se guardan en `data/usuarios.db` (no se sube a Git), con la contraseña en hash bcrypt y la sesión en una cookie firmada de 60 minutos. Para una cuenta de demostración que se crea al arrancar, define `DERMA_DEMO_EMAIL` y `DERMA_DEMO_PASSWORD` en `.env`. En producción (HTTPS) usa `DERMA_COOKIE_SECURE=true` y una `DERMA_SECRET_KEY` larga y aleatoria.

Modelo de clasificación: copia `dermaai_mobilenetv2_v1.keras` y `class_names.json` a `models/`. TensorFlow solo funciona con **Python 3.10 a 3.13** (no con 3.14): crea el entorno con `py -3.12 -m venv .venv` e instala `pip install -r requirements-ml.txt`. Para desarrollar sin TensorFlow, define `DERMA_MODELO=provisional` en `.env` (modelo falso, solo para pruebas; la respuesta lo avisa).

Pruebas y estilo:

```bash
pytest -q
ruff check .
```

## Estructura
```
app/          Backend (FastAPI): API, autenticación, validación, inferencia
frontend/     Interfaz web (HTML, CSS y JS sin frameworks)
notebooks/    Cuaderno de Colab para entrenar y evaluar el modelo
models/       Modelo entrenado (.keras) — no se sube a Git, vive en Drive
data/         Datos locales y bases SQLite — no se suben a Git
tests/        Pruebas con pytest
docs/         Documentación del proyecto y backlog
scripts/      Utilidades (carga del catálogo, etc.)
```

## Flujo de trabajo con Git
- `main`: versión estable para la demostración.
- `develop`: integración del trabajo diario.
- Ramas por tarea: `feat/login`, `feat/carga-imagenes`, etc., y Pull Request hacia `develop`.
- Mensajes de commit cortos y en español: `feat: registro de usuarios`, `fix: error 413 en archivos grandes`.

## Entrenar el modelo
Abre `notebooks/01_entrenamiento_ham10000.ipynb` en Google Colab con GPU. Al terminar, el modelo y las métricas quedan en tu Drive (carpeta `derma-ai/modelo_v1`). Copia el `.keras` a `models/` para usarlo en local.
