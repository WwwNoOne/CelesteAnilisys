# Celeste Anilisys

Aplicación de escritorio para importar archivos financieros (`.xls`, `.xlsx`, `.csv` y formatos relacionados), almacenarlos en una base de datos y comparar información por meses y años.

## Estado actual

El proyecto implementa el **Módulo 1: Ingesta y normalización de estados financieros** y el **Espacio de revisión de importaciones (Workspace)**:
- Detección automática y validación interactiva de períodos y conflictos por hojas (ej. balances con hojas 2024 y 2025).
- Compatibilidad con formato de reporte y formato de cuenta (bloques paralelos ACTIVO / PASIVO y PATRIMONIO).
- Extracción de códigos contables tanto en columnas dedicadas como integrados en la misma celda de descripción (`1101 EFECTIVO`).
- Descarte automático de metadatos superiores (empresa, título, notas de moneda) y firmas inferiores (representante legal, contador).
- Contador exacto de filas desconocidas (`UNKNOWN`), filas a revisar (`NEEDS_REVIEW`), cuentas nuevas y errores.
- Espacio de trabajo a pantalla completa con vista previa del Excel, lista de hojas, tabla navegable con números de fila originales y panel lateral de mapeo de cuentas e ignorado de filas.
- Historial de importaciones por empresa en la sección `Archivos`.

## Estructura

```text
assets/       Recursos visuales y archivos auxiliares de la aplicación
config/       Configuraciones por entorno
data/         Datos locales, ejemplos y archivos temporales
docs/         Documentación funcional y decisiones de arquitectura
scripts/      Utilidades de desarrollo, validación y empaquetado
src/          Código fuente organizado por responsabilidades
tests/        Pruebas unitarias, de integración y de aceptación
```

Consulta [docs/architecture/initial-architecture.md](docs/architecture/initial-architecture.md) para conocer los límites iniciales de cada módulo.

## Instalación local en Fedora

Requiere Node.js 22.12 o superior para las herramientas actuales de empaquetado:

```bash
sudo dnf install -y nodejs npm git
node --version
npm --version
npm install
```

Comandos de desarrollo:

```bash
npm test
npm run dev
```

Los archivos de prueba se encuentran en `data/examples/`.

## Backend local

El backend requiere Python 3.11 o superior. Para instalar las herramientas de desarrollo:

```bash
sudo dnf install -y python3-pip
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
pytest -q
ruff check .
```

Para levantar FastAPI y PostgreSQL con Docker Compose:

```bash
docker compose up --build
docker compose exec api alembic upgrade head
```

## Desarrollo en Fedora y distribución para Windows

El desarrollo se realizará en Fedora 44. La tecnología definitiva deberá permitir ejecutar las pruebas en Linux y generar un instalador o binario distribuible para Windows.
