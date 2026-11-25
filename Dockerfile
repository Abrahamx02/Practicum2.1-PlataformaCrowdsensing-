# Imagen para correr la API, el formulario y el panel (en tu computador o en cualquier servidor)
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY configuracion.json .
COPY backend ./backend
COPY frontend ./frontend

# no corre como administrador: si alguien lograra entrar al contenedor, tendria permisos minimos
RUN useradd --system --no-create-home --uid 10001 mcs && chown -R mcs /app
USER mcs

EXPOSE 8000
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000} --no-server-header"]
