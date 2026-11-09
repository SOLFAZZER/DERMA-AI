-- Esquema físico de Derma-AI (C08). Tomado del documento "Diseño de base de datos";
-- se agregó IF NOT EXISTS para poder ejecutarlo más de una vez sin errores.

CREATE TABLE IF NOT EXISTS clase_lesion (
  id_clase INTEGER PRIMARY KEY AUTOINCREMENT,
  codigo TEXT NOT NULL UNIQUE,
  nombre_clase TEXT NOT NULL,
  descripcion TEXT NOT NULL,
  nivel_riesgo TEXT NOT NULL
    CHECK (nivel_riesgo IN ('benigno', 'premaligno', 'maligno'))
);

CREATE TABLE IF NOT EXISTS version_modelo (
  id_version INTEGER PRIMARY KEY AUTOINCREMENT,
  nombre_arquitectura TEXT NOT NULL,
  fecha_entrenamiento TEXT NOT NULL,
  num_epoca INTEGER NOT NULL CHECK (num_epoca > 0),
  hiperparametros TEXT,
  ruta_archivo TEXT NOT NULL,
  estado TEXT NOT NULL DEFAULT 'activo'
    CHECK (estado IN ('activo', 'archivado'))
);

CREATE TABLE IF NOT EXISTS metrica_evaluacion (
  id_metrica INTEGER PRIMARY KEY AUTOINCREMENT,
  id_version INTEGER NOT NULL,
  id_clase INTEGER,
  exactitud REAL CHECK (exactitud BETWEEN 0 AND 1),
  precision REAL CHECK (precision BETWEEN 0 AND 1),
  sensibilidad REAL CHECK (sensibilidad BETWEEN 0 AND 1),
  f1 REAL CHECK (f1 BETWEEN 0 AND 1),
  fecha_calculo TEXT NOT NULL,
  FOREIGN KEY (id_version) REFERENCES version_modelo (id_version) ON DELETE CASCADE,
  FOREIGN KEY (id_clase) REFERENCES clase_lesion (id_clase) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS registro_prueba (
  id_prueba INTEGER PRIMARY KEY AUTOINCREMENT,
  id_version INTEGER NOT NULL,
  id_clase INTEGER NOT NULL,
  fecha_prueba TEXT NOT NULL,
  confianza REAL NOT NULL CHECK (confianza BETWEEN 0 AND 1),
  tiempo_respuesta INTEGER NOT NULL CHECK (tiempo_respuesta >= 0),
  mapa_calor INTEGER NOT NULL DEFAULT 1 CHECK (mapa_calor IN (0, 1)),
  FOREIGN KEY (id_version) REFERENCES version_modelo (id_version) ON DELETE CASCADE,
  FOREIGN KEY (id_clase) REFERENCES clase_lesion (id_clase) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_metrica_version ON metrica_evaluacion (id_version);
CREATE INDEX IF NOT EXISTS idx_metrica_clase ON metrica_evaluacion (id_clase);
CREATE INDEX IF NOT EXISTS idx_prueba_version ON registro_prueba (id_version);
CREATE INDEX IF NOT EXISTS idx_prueba_clase ON registro_prueba (id_clase);

CREATE VIEW IF NOT EXISTS vw_metricas_globales AS
SELECT v.id_version, v.nombre_arquitectura, v.estado,
       m.exactitud, m.precision, m.sensibilidad, m.f1, m.fecha_calculo
FROM version_modelo v
JOIN metrica_evaluacion m ON m.id_version = v.id_version
WHERE m.id_clase IS NULL;
