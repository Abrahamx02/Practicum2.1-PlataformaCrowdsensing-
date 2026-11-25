-- Datos extra de la ubicacion (para juzgar mejor su calidad) y encuesta de experiencia de usuario.
ALTER TABLE reportes ADD COLUMN IF NOT EXISTS ubicacion_ajustada BOOLEAN NOT NULL DEFAULT false;   -- el participante movio el pin en el mapa
ALTER TABLE reportes ADD COLUMN IF NOT EXISTS velocidad_ms REAL;                                   -- velocidad del celular al capturar (m/s)
CREATE INDEX IF NOT EXISTS idx_reportes_participante ON reportes (participante_id, fecha_dispositivo);

CREATE TABLE IF NOT EXISTS encuestas (
    id SERIAL PRIMARY KEY,
    creada_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    participante_id TEXT NOT NULL,
    respuestas SMALLINT[] NOT NULL,
    indice REAL NOT NULL,
    comentario TEXT NOT NULL DEFAULT ''
);
