-- La calidad ahora se calcula dentro del servidor (backend/calidad.py).
-- motivo_calidad: explica en palabras por que un reporte no quedo en "aceptar".
-- dimensiones_calidad: puntaje (0 a 1) de cada una de las seis dimensiones.
-- revisado: true cuando una persona del equipo decidio el estado a mano (el recalculo no lo cambia).
ALTER TABLE reportes ADD COLUMN IF NOT EXISTS motivo_calidad TEXT NOT NULL DEFAULT '';
ALTER TABLE reportes ADD COLUMN IF NOT EXISTS dimensiones_calidad JSONB;
ALTER TABLE reportes ADD COLUMN IF NOT EXISTS revisado BOOLEAN NOT NULL DEFAULT false;
CREATE INDEX IF NOT EXISTS idx_reportes_categoria_fecha ON reportes (categoria, fecha_dispositivo);
