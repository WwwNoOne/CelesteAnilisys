# Estados financieros independientes por hoja

Fecha: 2026-09-22  
Estado: diseño aprobado en conversación; pendiente de revisión del documento

## Objetivo

Convertir cada hoja válida de un libro Excel en una unidad independiente de revisión y aprobación. El archivo seguirá siendo el contenedor y la fuente de trazabilidad, pero cada hoja tendrá su propio tipo de estado financiero, periodo, progreso, validación contable y estado de aprobación.

Al mismo tiempo, la cuadrícula de revisión dejará de tratar una fila física como una sola cuenta. Una fila podrá contener varios bloques financieros laterales y cada bloque `cuenta + saldo` será seleccionable y editable por separado.

## Reglas funcionales

1. Una hoja puede representar como máximo un estado financiero.
2. Solo se conserva una hoja si contiene una estructura financiera válida y al menos un bloque utilizable de cuenta y saldo.
3. Una hoja vacía, auxiliar, de firmas, notas o sin estructura `cuenta + saldo` se marca como descartada y no produce saldos.
4. Cada hoja válida mantiene de forma independiente:
   - tipo de estado financiero;
   - fecha de corte o intervalo de fechas;
   - etiqueta, año y periodicidad;
   - número de cuentas reconocidas, pendientes y erróneas;
   - validación matemática;
   - estado de revisión y aprobación.
5. La edición y aprobación se realizan hoja por hoja. Aprobar una hoja no cambia el estado de las demás.
6. Una hoja aprobada queda bloqueada para impedir que una edición posterior altere saldos ya publicados.
7. Un archivo termina cuando todas sus hojas están aprobadas o descartadas. Puede quedar parcialmente procesado mientras existan hojas válidas pendientes.
8. Si no existe ninguna hoja válida, el análisis del archivo termina como descartado/sin estados financieros y no crea periodos ni saldos.
9. Las validaciones matemáticas se ejecutan únicamente con las cuentas de la hoja seleccionada.
10. Los duplicados se comprueban por empresa, tipo de estado y fechas de la hoja, no usando un periodo general del libro.

## Modelo de datos

Se incorporará una entidad persistente `ImportedStatement` (nombre técnico sujeto a las convenciones finales del código) entre `FinancialImport` e `ImportRow`.

### FinancialImport

Representa el archivo cargado. Conserva empresa, nombre, ruta, fecha de carga y un resumen agregado. Deja de ser propietario del periodo contable general: `period_id` pasará a ser nullable y se conservará únicamente como campo legado durante la transición. La carga nueva recibirá empresa y archivo, sin exigir periodo. Su estado agregado se deriva de sus hojas:

- `ANALYZING`: análisis en curso;
- `READY_FOR_REVIEW`: al menos una hoja válida pendiente;
- `APPROVED`: todas las hojas válidas están aprobadas y las restantes descartadas;
- `FAILED`: no se pudo leer o analizar el archivo;
- `DISCARDED`: no se encontró ninguna hoja válida.

Los campos temporales globales existentes se conservarán durante la migración por compatibilidad, pero el flujo nuevo no los usará como autoridad.

### ImportedStatement

Una fila por hoja del libro, incluyendo hojas descartadas para explicar al usuario qué ocurrió. Campos principales:

- `id`, `source_import_id`, `sheet_name` y posición original;
- clasificación/tipo detectado y confianza;
- estado: `PENDING_REVIEW`, `APPROVED`, `DISCARDED`;
- razón de descarte;
- `period_id` nullable hasta la aprobación;
- etiqueta, año, mes, fecha de corte, inicio, fin y periodicidad detectados/editados;
- indicador de validación temporal;
- contadores propios;
- fecha de aprobación.

La combinación `(source_import_id, sheet_name)` será única.

### ImportRow

Cada candidato financiero pertenecerá a `ImportedStatement`, además de mantener temporalmente la referencia al archivo para compatibilidad y trazabilidad. Se persistirán:

- `source_text_column`;
- `source_amount_column`;

Estas posiciones identifican el bloque exacto dentro de la fila física. Dos cuentas laterales de la misma fila serán dos `ImportRow` distintos con columnas distintas.

### Period y AccountBalance

El periodo se crea o reutiliza al aprobar una hoja. Los saldos guardados apuntan al periodo y al archivo de origen como hasta ahora; se añadirá la referencia a la hoja importada cuando resulte necesaria para garantizar aprobación/reemplazo aislado.

## Detección y descarte de hojas

El análisis se realizará individualmente para cada hoja:

1. Clasificar el posible tipo de estado.
2. Detectar estructura y encabezados.
3. Extraer bloques financieros laterales.
4. Considerar válida la hoja si hay al menos un bloque con texto de cuenta y saldo numérico, y evidencia suficiente de reporte financiero.
5. Si no cumple, crear el registro de hoja como descartado con una razón concreta, sin crear `ImportRow`.
6. Detectar fechas usando exclusivamente nombre y contenido de esa hoja, con el nombre del archivo solo como respaldo.
7. Crear candidatos y hacer el mapeo contra el catálogo para esa hoja.

No se intentará dividir una misma hoja en dos estados financieros. Si el detector encuentra evidencia clara de más de un estado en una hoja, se descartará con la razón “más de un estado financiero”, en lugar de importar datos ambiguos.

## API

Las respuestas de hojas incluirán ID estable, validez, razón de descarte, estado, metadatos temporales y contadores propios.

Las operaciones de periodo, vista previa, validación y aprobación se dirigirán al ID de la hoja importada, no al nombre de hoja como identidad principal:

- listar hojas de un archivo;
- obtener vista previa de una hoja;
- actualizar periodo de una hoja;
- revisar un candidato financiero;
- validar matemáticamente una hoja;
- aprobar o reemplazar una hoja.

Las rutas antiguas basadas en nombre se podrán mantener de manera transitoria como adaptadores mientras se actualiza el frontend. La aprobación global del archivo dejará de publicar saldos; únicamente comprobará o reflejará que todas las hojas han alcanzado un estado terminal.

## Vista de revisión

### Navegación por hojas

El panel izquierdo mostrará todas las hojas con uno de estos estados:

- pendiente y número de líneas por resolver;
- lista para aprobar;
- aprobada;
- descartada y motivo.

Las hojas descartadas serán visibles para trazabilidad, pero no editables ni aprobables.

### Periodo individual

El formulario temporal se moverá de la cabecera global al contexto de la hoja seleccionada. Para balance general se editará la fecha de corte; para resultados y flujo, fecha inicial y final. La hoja deberá tener fechas validadas antes de aprobarse.

### Selección de bloques financieros

La cuadrícula dibujará cada fila del Excel una sola vez. Cada detalle de fila contendrá una colección de candidatos, y cada candidato indicará sus columnas de texto y saldo.

- Pulsar la celda de cuenta o la de saldo seleccionará el mismo candidato.
- Solo esas celdas se resaltarán.
- El panel lateral editará el nombre/cuenta del catálogo, rol canónico, clasificación y saldo de ese candidato.
- Dos bloques en la misma fila serán completamente independientes.
- Las celdas que no formen parte de un bloque no abrirán el editor.

El contador de pendientes se calculará a partir de candidatos persistidos de la hoja, nunca a partir del número de filas visuales.

### Aprobación

El botón será `Aprobar hoja`. Solo se habilitará cuando esa hoja tenga:

- periodo validado;
- cero candidatos pendientes o erróneos;
- todas las cuentas canónicas obligatorias presentes, incluso con saldo cero;
- ecuaciones contables válidas;
- ninguna ambigüedad o duplicado sin resolver.

Los errores resaltarán únicamente los bloques implicados. Tras aprobar, la hoja quedará en modo lectura y la interfaz seleccionará la siguiente hoja pendiente.

## Consistencia y transacciones

La aprobación de una hoja será una transacción atómica: validar, resolver/crear periodo, comprobar duplicados, reemplazar si fue autorizado, insertar saldos y marcar la hoja aprobada. Cualquier error revierte solo esa operación.

Editar una hoja aprobada será rechazado por el backend aunque se intente fuera de la interfaz. El resumen del archivo se recalculará después de analizar, revisar, descartar o aprobar una hoja.

## Migración y compatibilidad

Una migración Alembic creará la nueva tabla y columnas de posición. Para importaciones pendientes existentes se generará una entidad por cada `source_sheet` presente en `ImportRow`. Los datos temporales globales se copiarán como valor inicial, pero deberán confirmarse por hoja. Las importaciones ya aprobadas se migrarán como hojas aprobadas usando `approved_sheets` y sus saldos existentes.

No se eliminarán columnas antiguas en esta fase; su retirada podrá hacerse después de verificar la migración en datos reales.

## Pruebas

El desarrollo seguirá TDD y cubrirá, como mínimo:

- hoja válida y hoja auxiliar en el mismo libro;
- libro sin hojas válidas;
- dos hojas válidas con periodos distintos;
- aprobación de una hoja sin aprobar la otra;
- bloqueo de edición de una hoja aprobada;
- validación matemática aislada por hoja;
- detección de una hoja con más de un estado;
- dos bloques laterales en la misma fila con columnas e IDs distintos;
- vista previa con una sola fila física y dos candidatos seleccionables;
- edición independiente de cuenta y saldo;
- coincidencia entre resumen y contador del botón;
- migración de importaciones pendientes y aprobadas;
- pruebas con los libros reales de `data/examples`;
- suites completas de backend, frontend, Ruff y compilación Electron.

## Fuera de alcance

- Dividir automáticamente una hoja que contenga varios estados financieros.
- Permitir múltiples periodos dentro de una sola hoja.
- Modificar una hoja después de aprobada sin un flujo explícito de reversión o reemplazo.
- Eliminar en esta fase los campos globales antiguos de `FinancialImport`.
