-- Ejecutar completo en el editor SQL de Neon (una sola vez por base de datos)

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
    foto_id INTEGER REFERENCES fotos(id)
);

CREATE INDEX IF NOT EXISTS idx_reportes_ubicacion ON reportes USING GIST (ubicacion);
