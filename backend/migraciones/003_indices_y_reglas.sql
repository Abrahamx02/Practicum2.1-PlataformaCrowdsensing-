-- Indices para las consultas mas usadas y reglas minimas de los datos
CREATE INDEX IF NOT EXISTS idx_reportes_recibido_en ON reportes (recibido_en);
CREATE INDEX IF NOT EXISTS idx_reportes_participante ON reportes (participante_id);
CREATE INDEX IF NOT EXISTS idx_reportes_categoria ON reportes (categoria);
CREATE INDEX IF NOT EXISTS idx_reportes_estado ON reportes (estado_calidad);

-- NOT VALID: se aplican a los datos nuevos sin revisar los viejos
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_reportes_precision') THEN
        ALTER TABLE reportes ADD CONSTRAINT ck_reportes_precision
            CHECK (precision_m IS NULL OR (precision_m >= 0 AND precision_m <= 100000)) NOT VALID;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_reportes_estado') THEN
        ALTER TABLE reportes ADD CONSTRAINT ck_reportes_estado
            CHECK (estado_calidad IS NULL OR estado_calidad IN ('aceptar', 'revisar', 'descartar')) NOT VALID;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_reportes_puntaje') THEN
        ALTER TABLE reportes ADD CONSTRAINT ck_reportes_puntaje
            CHECK (puntaje_calidad IS NULL OR (puntaje_calidad >= 0 AND puntaje_calidad <= 100)) NOT VALID;
    END IF;
END
$$;
