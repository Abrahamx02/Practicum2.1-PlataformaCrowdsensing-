-- Tablas base. Se puede ejecutar sobre una base que ya tenia el esquema de la version 2.
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS fotos (
    id SERIAL PRIMARY KEY,
    tipo TEXT NOT NULL DEFAULT 'image/jpeg',
    datos BYTEA NOT NULL
);

CREATE TABLE IF NOT EXISTS reportes (
    id SERIAL PRIMARY KEY,
    recibido_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    participante_id TEXT NOT NULL,
    categoria TEXT NOT NULL CHECK (categoria IN ('bache', 'luminaria_danada', 'basura', 'otro')),
    descripcion TEXT NOT NULL DEFAULT '',
    lat DOUBLE PRECISION NOT NULL,
    lon DOUBLE PRECISION NOT NULL,
    precision_m REAL,
    ubicacion GEOGRAPHY(Point, 4326) NOT NULL,
    fecha_dispositivo TIMESTAMPTZ NOT NULL,
    plataforma TEXT NOT NULL DEFAULT 'otro',
    navegador TEXT NOT NULL DEFAULT '',
    consentimiento BOOLEAN NOT NULL,
    consentimiento_version TEXT NOT NULL DEFAULT 'v1',
    foto_id INTEGER REFERENCES fotos(id),
    puntaje_calidad REAL,
    estado_calidad TEXT
);

-- por si la base viene de la version 2 sin estas columnas
ALTER TABLE reportes ADD COLUMN IF NOT EXISTS consentimiento_version TEXT NOT NULL DEFAULT 'v1';
ALTER TABLE reportes ADD COLUMN IF NOT EXISTS puntaje_calidad REAL;
ALTER TABLE reportes ADD COLUMN IF NOT EXISTS estado_calidad TEXT;

CREATE INDEX IF NOT EXISTS idx_reportes_ubicacion ON reportes USING GIST (ubicacion);
