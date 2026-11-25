-- Las categorias se definen solo en configuracion.json. Se quita la lista fija de la base de datos
-- para poder agregar una categoria nueva sin tocar la base (el servidor sigue validando cada reporte).
ALTER TABLE reportes DROP CONSTRAINT IF EXISTS reportes_categoria_check;
