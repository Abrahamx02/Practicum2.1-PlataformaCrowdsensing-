# MCS Loja - Prototipo de Mobile Crowdsensing

Proyecto del Practicum 2.1 (UTPL). Plataforma para recopilar reportes urbanos georreferenciados
desde el celular, evaluar su calidad y visualizarlos.

Equipo: Emilio Cueva, Abraham Ayala, Carlos Correa.

## Carpetas
- `backend/`  API con FastAPI y script SQL de la base (PostgreSQL + PostGIS en Neon)
- `frontend/` formulario web para el celular (HTML, CSS, JavaScript)
- `analisis/` reglas de calidad (pandas) y dashboard (Streamlit)
- `docs/`     bitacora, contrato de datos, manual y capturas

## Como correrlo en el computador
1. Copiar `.env.example` a `.env` y poner los datos reales (nunca subir `.env` a Git).
2. Crear y activar el entorno virtual, e instalar: `pip install -r requirements-local.txt`
3. API y formulario: `uvicorn backend.main:app --reload` y abrir http://127.0.0.1:8000
4. Dashboard: `streamlit run analisis/dashboard.py`
5. Pruebas: `python -m pytest -v`

## Roles de acceso a la API
- Participante: `CLAVE_ESCRITURA` (solo enviar reportes).
- Analista: `CLAVE_LECTURA` (leer y exportar).
- Administrador: `CLAVE_ADMIN` (todo: importar, calidad, fotos, retiro de participantes).

## Con Docker (entorno reproducible)
`docker compose up --build` levanta la base con PostGIS, la API y el formulario en http://localhost:8000
(las claves se leen del archivo `.env`).

Ver la guia paso a paso para el detalle de cada paso.
