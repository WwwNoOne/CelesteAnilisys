# Diseño: espacio de revisión de importaciones financieras

## Objetivo

Convertir la revisión de un Excel financiero en un flujo de pantalla completa, con suficiente espacio para visualizar hojas, filas, cuentas e importes, corregir el mapeo y confirmar la importación únicamente cuando el usuario haya validado los datos.

## Decisiones aprobadas

- `Archivos` será el punto de entrada para subir libros y consultar el historial de importaciones.
- La pantalla de carga no tendrá selector manual de período.
- El sistema intentará detectar el período a partir del nombre de la hoja, título del estado, nombre del archivo y contenido del libro.
- El período detectado se mostrará como una propuesta editable durante la revisión.
- La importación no se confirmará si el período no está validado o existen filas críticas pendientes.
- La revisión será un modo de trabajo temporal a pantalla completa, no una sección permanente del menú lateral.

## Flujo de usuario

1. El usuario entra a `Archivos` y pulsa `+ Importar datos`.
2. Selecciona uno o varios archivos `.xlsx` o `.xlsm`, sin elegir período.
3. El backend almacena el original y analiza hojas, encabezados, cuentas, importes y período sugerido.
4. La aplicación abre `Revisión de importación` ocupando la ventana completa.
5. El usuario revisa cada hoja, corrige cuentas o ignora filas no financieras y puede editar el período detectado.
6. El usuario pasa a confirmación cuando no quedan errores críticos.
7. El sistema guarda la importación aprobada y vuelve al historial de `Archivos`.

## Pantalla de revisión

La pantalla tendrá tres zonas principales:

- Panel izquierdo: listado de hojas, tipo detectado, estado y cantidad de filas.
- Área central: tabla amplia con la vista previa del libro, número de fila original, cuenta, código, importes y estado.
- Panel derecho: detalle de la fila seleccionada, cuenta sugerida, cuenta asignada, motivo de revisión y controles de corrección.

La barra superior mostrará empresa, archivo, período detectado y estado de la revisión. El período tendrá un control editable con indicador de origen: `Detectado` o `Editado por el usuario`.

La barra inferior tendrá `Volver`, `Guardar cambios` y `Continuar a confirmación`.

## Período

El período se representará con un año y, cuando exista información suficiente, un mes o fecha de cierre. La detección usará este orden de prioridad:

1. Título o encabezado explícito de la hoja.
2. Nombre de la hoja.
3. Nombre del archivo.
4. Metadatos o fechas presentes en el contenido.

Si hay conflicto entre fuentes, se mostrará una advertencia y el usuario deberá elegir el valor correcto. El período final usado por la importación será siempre el valor validado en la revisión, no el valor inicial enviado desde `Archivos`.

## Estados de filas

- `MATCHED`: cuenta identificada con evidencia suficiente.
- `NEEDS_REVIEW`: existe una sugerencia, pero requiere confirmación.
- `UNKNOWN`: no se encontró una cuenta compatible.
- `NEW_ACCOUNT`: posible cuenta nueva que requiere decisión explícita.
- `ERROR`: fila no procesable.
- `IGNORED`: fila descartada por el usuario.

Las filas `UNKNOWN`, `NEW_ACCOUNT` y `ERROR` bloquearán la confirmación hasta resolverse o marcarse explícitamente como ignoradas. Las sugerencias fuzzy seguirán siendo solo sugerencias.

## Contratos de backend

Se ampliará el API para:

- devolver el período detectado y sus fuentes de evidencia;
- actualizar el período validado de una importación;
- devolver una vista tabular de una hoja con valores originales y datos extraídos;
- actualizar el mapeo de una fila a una cuenta existente;
- marcar una fila como ignorada;
- devolver el resumen actualizado de la importación;
- aprobar la revisión sin importar saldos definitivos hasta que exista el paso de carga final.

## Fuera de alcance

- Generación final de estados financieros y ratios.
- Importación definitiva de saldos a `account_balances`.
- Creación automática de cuentas contables.
- Soporte inicial para `.xls`.
- Edición destructiva del archivo original; siempre se conservarán los valores fuente.

## Criterios de aceptación

- La pantalla de carga en `Archivos` no muestra selector de período.
- Un libro con períodos diferentes por hoja muestra una advertencia de conflicto.
- El usuario puede modificar el período desde la pantalla de revisión.
- La tabla puede mostrar más columnas y filas que el modal actual sin scroll horizontal de toda la aplicación.
- El usuario puede seleccionar una fila, cambiar su cuenta o ignorarla.
- La confirmación queda bloqueada mientras existan filas críticas pendientes o un período sin validar.
- El archivo original, valores originales y trazabilidad de cada fila se conservan.
