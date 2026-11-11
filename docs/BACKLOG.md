# Backlog inicial (cada punto puede ser una incidencia en GitHub)

Prioridad según la matriz de trazabilidad y el SRS. IDs entre paréntesis = requisitos DERMA-SRS.

## Must have
1. Esqueleto del backend y `GET /api/salud` (hecho en el esqueleto).
2. Datos: descarga de HAM10000, licencia, preprocesamiento y división sin fuga (3.1 a 3.5).
3. Modelo CNN: entrenar, evaluar y guardar versionado (4.1 a 4.4, 4.6, 8.1, 8.2, 8.6).
4. Capa de datos SQLite: catálogo de 7 clases y versiones del modelo (C08).
5. Autenticación C09: registro, login, logout, consulta de sesión (12.1 a 12.4).
6. Seguridad del login: hash bcrypt, vigencia 60 min, aviso Ley 1581 (12.5, 12.7).
7. Carga y validación de imágenes: formatos, 5 MB, legibilidad, errores 400/413/422 (6.1 a 6.3, 6.5, 6.6).
8. Servicio de inferencia detrás de una interfaz única (2.2, 4.3, 4.4).
9. `POST /api/analizar` con sesión obligatoria (12.4).
10. Grad-CAM y mapa de calor superpuesto (5.1 a 5.3).
11. Interfaz: inicio con aviso de prototipo, categoría, confianza y advertencia (7.1 a 7.5).
12. Publicación con HTTPS (9.6) y no almacenar imágenes (9.1).
13. Pruebas funcionales, de modelo y de manejo de archivos (8.5).

## Should have
- Bloqueo tras 5 intentos fallidos (12.8) y vencimiento de sesión (12.6).
- Vista previa, indicador de progreso, responsive, español, tiempo ≤ 30 s (6.4, 7.6, 7.9 a 7.12).
- Aumento de datos y ponderación de clases (3.6, 3.7); baja confianza (4.5); matriz de confusión (8.3).
- Guía de despliegue y manual de usuario (10.3, 10.4).

## Could have (si sobra tiempo)
- Alternar imagen original y mapa de calor (5.4), nueva consulta (7.7), descripción de clases (7.8).

## Cambio por documentar: exportar resultado en PDF (paso 8)
- Nuevo requisito: el usuario puede descargar el resultado en PDF (categoría, confianza, probabilidades de las 7 clases, imagen original y mapa Grad-CAM).
- Nueva interfaz I14: POST /api/exportar-pdf (requiere sesión; 400 datos inválidos, 401 sin sesión, 413 demasiado grande, 500 error).
- El PDF se arma en memoria y no se guarda nada (se mantiene SRS 9.1). Sin historial (SC-01).
- Nueva dependencia: reportlab.
