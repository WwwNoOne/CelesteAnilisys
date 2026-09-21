# Arquitectura inicial

**Estado:** propuesta aprobada para la estructura inicial  
**Fecha:** 2026-09-18

## Objetivo

Organizar una aplicación de escritorio para Windows que permita:

1. Seleccionar archivos financieros en formatos como XLS, XLSX y CSV.
2. Validar, normalizar y transformar su contenido a un modelo financiero común.
3. Guardar los datos en una base de datos.
4. Comparar períodos mensuales y anuales.
5. Presentar análisis financieros al usuario.

## Límites de la primera estructura

La estructura no fija todavía el lenguaje, el framework de interfaz, el motor de base de datos ni el mecanismo de distribución para Windows. Esas decisiones se tomarán después de revisar requisitos de instalación, volumen de datos, compatibilidad con Excel y necesidades de análisis.

## Capas previstas

- `src/ui`: ventanas, pantallas, navegación y presentación de resultados.
- `src/application`: casos de uso, orquestación de importaciones, comparaciones y análisis.
- `src/domain`: entidades, reglas financieras, períodos y contratos independientes de la tecnología.
- `src/infrastructure`: persistencia, acceso a archivos, configuración y servicios externos.
- `src/importers`: lectores de XLS, XLSX, CSV y futuros formatos; su salida debe ser un modelo común.

## Flujo conceptual

```text
Archivo financiero
        ↓
Importador por formato
        ↓
Validación y normalización
        ↓
Modelo financiero común
        ↓
Persistencia
        ↓
Consultas por período
        ↓
Comparaciones y análisis
        ↓
Interfaz de escritorio
```

## Principios iniciales

- Mantener separada la lógica financiera de la interfaz.
- No hacer que el análisis dependa de un formato de archivo específico.
- Registrar errores de importación de forma comprensible para el usuario.
- Conservar los archivos originales y separar los datos temporales de los datos procesados.
- Diseñar la persistencia detrás de interfaces para poder cambiar de base de datos si es necesario.
- Mantener el código portable durante el desarrollo en Fedora y el empaquetado para Windows.

## Fuera de alcance por ahora

- Implementación de pantallas.
- Selección definitiva de tecnología.
- Diseño final de tablas y migraciones.
- Autenticación, multiusuario y sincronización en la nube.
- Cálculos financieros específicos todavía no definidos.
