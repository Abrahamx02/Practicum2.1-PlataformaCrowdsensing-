-- Cada reporte lleva un identificador creado en el celular. Si el celular reenvia el mismo
-- reporte (por ejemplo porque se perdio la respuesta), el servidor no lo guarda dos veces.
ALTER TABLE reportes ADD COLUMN IF NOT EXISTS id_cliente UUID;
CREATE UNIQUE INDEX IF NOT EXISTS ux_reportes_id_cliente ON reportes (id_cliente);
