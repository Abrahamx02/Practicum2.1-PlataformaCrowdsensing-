-- Registro de las acciones del administrador (borrar, importar, descartar fotos...)
CREATE TABLE IF NOT EXISTS eventos (
    id SERIAL PRIMARY KEY,
    cuando TIMESTAMPTZ NOT NULL DEFAULT now(),
    rol TEXT NOT NULL,
    accion TEXT NOT NULL,
    detalle TEXT NOT NULL DEFAULT '',
    ip TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_eventos_cuando ON eventos (cuando);
