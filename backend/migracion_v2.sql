-- Solo para bases que YA ejecutaron el schema.sql anterior.
-- Si la base es nueva, no hace falta: el schema.sql actual ya trae estas columnas.
ALTER TABLE reportes ADD COLUMN IF NOT EXISTS consentimiento_version TEXT NOT NULL DEFAULT 'v1';
ALTER TABLE reportes ADD COLUMN IF NOT EXISTS puntaje_calidad REAL;
ALTER TABLE reportes ADD COLUMN IF NOT EXISTS estado_calidad TEXT;
