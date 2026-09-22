# Extracción canónica y validación matemática contable

## Objetivo

Mejorar la ingestión de estados financieros con formatos variables mediante reglas estructurales basadas en la secuencia de textos y números de cada fila. El nombre original del Excel se conservará como evidencia, pero la identidad y función matemática de cada saldo dependerán de la cuenta del catálogo que el contador confirme.

Antes de aprobar una importación, la aplicación comprobará ecuaciones contables básicas. Los componentes ausentes, las asignaciones duplicadas conflictivas y las diferencias matemáticas bloquearán la aprobación y se mostrarán en rojo para que el contador corrija cuenta, rol, clasificación o saldo.

## Principios

- La posición relativa `texto → número` importa más que una columna fija.
- Las celdas vacías entre un texto y su importe no rompen la asociación.
- Un nuevo texto cierra el bloque anterior e inicia otro bloque independiente.
- Una fila completamente vacía no genera candidatos, registros ni pendientes.
- Una secuencia de textos sin números funciona como contexto visual, no como saldo.
- Un valor cero explícito es información válida; la ausencia de un componente no equivale a cero.
- El nombre del Excel nunca reemplaza la clasificación confirmada por el contador.
- Los totales explícitos son autoritativos y sus detalles no se suman nuevamente.

## Modelo de identidad y trazabilidad

Cada línea financiera conservará cuatro conceptos separados:

1. `original_name`: texto literal leído del Excel.
2. `matched_account_id`: cuenta normalizada del catálogo de la empresa.
3. `canonical_role`: función de la cuenta dentro de las ecuaciones contables.
4. `ending_balance`: saldo leído o corregido por el contador.

Los roles canónicos iniciales serán:

- `ACTIVO`
- `PASIVO`
- `PATRIMONIO`
- `VENTAS`
- `COSTO_VENTAS`
- `UTILIDAD_BRUTA`
- `GASTOS`
- `IMPUESTOS`
- `RESULTADO_EJERCICIO`

El catálogo seguirá siendo específico por empresa. La asignación automática será una propuesta; el contador podrá cambiar la cuenta y, cuando corresponda, su rol canónico. Las validaciones usarán exclusivamente las asignaciones confirmadas, nunca coincidencias directas contra el nombre original.

La persistencia deberá distinguir entre saldo declarado y valor calculado. Un total declarado en el Excel conservará su origen —importación, hoja y fila—. Un valor calculado podrá mostrarse durante la revisión, pero no fingirá ser una declaración del contador.

## Extracción por bloques

### Tokenización de filas

Cada fila se recorrerá de izquierda a derecha:

- Un texto no vacío inicia un bloque.
- Los números posteriores pertenecen a ese bloque hasta encontrar otro texto.
- Las celdas vacías se omiten y no cierran el bloque.
- Un texto posterior inicia un nuevo bloque, aunque haya varias celdas vacías entre ambos.

Ejemplos:

```text
Ingresos | 12,000
```

Produce un bloque financiero: `Ingresos → 12,000`.

```text
Ingresos | vacío | vacío | 12,000 | Conciliación de impuestos
```

Produce `Ingresos → 12,000` y un bloque contextual `Conciliación de impuestos` sin saldo.

```text
Activo | vacío | vacío | Pasivo
```

Produce dos encabezados contextuales sin saldo. Ninguno genera cuenta pendiente.

```text
Activo corriente | 50,000 | vacío | Pasivo corriente | 30,000
```

Produce dos líneas financieras independientes.

### Filas ignoradas

Una fila sin texto ni números relevantes se ignora por completo. Firmas, metadatos superiores y notas identificadas por las reglas existentes continuarán fuera de los saldos, aunque podrán permanecer en la vista previa como contexto visual.

La interfaz solo contará como pendiente una línea que tenga un `import_row_id` real y una clasificación financiera revisable. Las filas visuales sin registro extraído no participarán en contadores ni bloquearán botones.

### Clasificación inicial

Una línea con texto y saldo será una línea financiera, aunque su etiqueta contenga palabras como “Activo”, “Ingresos” o “Total”. Su clasificación semántica podrá ser cuenta, total o subtotal, pero deberá conservar el valor para el renderizado y la validación.

Una línea con texto y sin saldo será encabezado o contexto y no se persistirá como balance.

## Normalización de totales y prevención de doble conteo

Variantes como `Activo`, `Activos`, `Total Activo` y `Total Activos` podrán apuntar al mismo concepto canónico `ACTIVO`, siempre mediante una cuenta del catálogo confirmada.

Reglas:

1. Si existe un total explícito para un rol, ese valor es autoritativo.
2. Las cuentas hijas se conservan para detalle y trazabilidad, pero no se vuelven a sumar al total autoritativo.
3. Si no existe total explícito, la aplicación puede calcular uno desde las cuentas hijas y marcarlo como calculado.
4. Un total calculado no satisface por sí solo el requisito de componente explícito para aprobar cuando la ecuación exige una declaración del contador.
5. Dos declaraciones del mismo concepto canónico y período con igual valor se tratan como representación duplicada y se conserva una fuente principal con advertencia informativa.
6. Dos declaraciones del mismo concepto con valores diferentes generan un conflicto bloqueante.

La selección de la fuente principal deberá ser determinista y conservar referencias a las demás filas duplicadas.

## Motor de validación matemática

La validación se ejecutará por empresa, importación, hoja, tipo de estado y período. No mezclará saldos de hojas ni fechas diferentes.

### Tolerancia

Las ecuaciones aceptarán una diferencia absoluta máxima de `0.01` para contemplar redondeos monetarios. La aritmética usará `Decimal` en el backend.

### Balance general

Componentes obligatorios explícitos:

- `ACTIVO`
- `PASIVO`
- `PATRIMONIO`

Ecuación:

```text
ACTIVO = PASIVO + PATRIMONIO
```

### Estado de resultados

Componentes obligatorios explícitos:

- `VENTAS`
- `COSTO_VENTAS`
- `UTILIDAD_BRUTA`
- `GASTOS`
- `IMPUESTOS`
- `RESULTADO_EJERCICIO`

Ecuaciones:

```text
VENTAS - COSTO_VENTAS = UTILIDAD_BRUTA
UTILIDAD_BRUTA = RESULTADO_EJERCICIO + GASTOS + IMPUESTOS
```

`RESULTADO_EJERCICIO` será positivo para utilidad y negativo para pérdida. Los costos, gastos e impuestos se representarán como magnitudes positivas dentro de estas ecuaciones. Una cuenta obligatoria con saldo explícito `0` es válida; una cuenta ausente bloquea la aprobación.

### Resultado de validación

Cada ecuación producirá:

- identificador de regla;
- estado `VALID`, `MISMATCH` o `MISSING_COMPONENTS`;
- componentes y cuentas fuente;
- valor del lado izquierdo;
- valor del lado derecho;
- diferencia;
- tolerancia aplicada;
- filas involucradas.

La validación se recalculará después de corregir una cuenta, rol, clasificación o saldo.

## Flujo de revisión y aprobación

La tabla de revisión mostrará, para cada línea financiera:

- texto original;
- cuenta del catálogo asignada;
- rol canónico;
- clasificación de fila;
- saldo;
- origen de hoja y fila;
- errores contables asociados.

El flujo será:

1. Analizar el libro y generar bloques financieros.
2. Proponer cuentas y roles desde el catálogo.
3. Permitir al contador confirmar o corregir asignaciones y saldos.
4. Guardar los saldos de cada hoja.
5. Ejecutar las reglas aplicables mediante **Validar y aprobar**.
6. Si faltan componentes, hay duplicados conflictivos o una ecuación no cuadra, bloquear la aprobación.
7. Resaltar en rojo las filas involucradas y mostrar una tarjeta por ecuación con valores esperado, encontrado y diferencia.
8. Después de las correcciones, volver a validar.
9. Habilitar la aprobación final únicamente cuando todas las hojas necesarias estén guardadas y todas las reglas aplicables tengan estado `VALID`.

No existirá aprobación excepcional ni omisión manual de una regla bloqueante en esta primera versión.

## Límites de componentes

El extractor, el catálogo y el motor de ecuaciones serán unidades separadas:

- El extractor convierte celdas en bloques y líneas financieras sin decidir fórmulas.
- El servicio de catálogo resuelve cuentas y roles canónicos.
- El servicio de persistencia guarda saldos y fuentes sin calcular resultados de aprobación.
- El motor de validación recibe saldos canónicos y devuelve resultados explicables.
- La API coordina los servicios y bloquea la aprobación cuando corresponde.
- React presenta y corrige datos; no realiza aritmética contable autoritativa.

## Errores y seguridad de datos

- Una asignación incompleta no se convertirá silenciosamente en cero.
- Un número no se asociará con un texto que aparezca después de él.
- La corrección de una fila mantendrá su texto y ubicación originales.
- Los conflictos no sobrescribirán saldos existentes automáticamente.
- Las operaciones seguirán aisladas por empresa e importación.
- El backend repetirá todas las validaciones aunque la interfaz deshabilite el botón.

## Estrategia de pruebas

### Extracción

- Texto y número adyacentes.
- Texto y número separados por celdas vacías.
- Dos textos sin números en una fila.
- Dos bloques `texto–número` en una fila.
- Texto, número y segundo texto sin saldo.
- Fila completamente vacía.
- Metadatos y firmas.
- Valor cero explícito.

### Normalización y jerarquía

- Variantes de nombres que apuntan al mismo rol.
- Total autoritativo con cuentas hijas sin doble conteo.
- Total calculado cuando no existe declaración explícita.
- Duplicado con igual valor.
- Duplicado conflictivo.

### Validación matemática

- Balance cuadrado y descuadrado.
- Cada componente obligatorio ausente.
- Componentes explícitos con cero.
- Resultado bruto correcto e incorrecto.
- Resultado final con utilidad.
- Resultado final con pérdida negativa.
- Diferencias dentro y fuera de la tolerancia.
- Aislamiento por hoja, período y empresa.

### Integración y regresión

- La API bloquea la aprobación con errores explicables.
- La interfaz marca en rojo filas y ecuaciones involucradas.
- Corregir una asignación recalcula la validación.
- Las filas visuales sin `import_row_id` no cuentan como pendientes.
- Los libros reales de `data/examples` producen candidatos y resultados esperados.
- El flujo actual de carga, revisión, guardado por hoja, historial y comparaciones permanece operativo.

## Criterios de aceptación

La función estará completa cuando el contador pueda cargar un libro con columnas variables, revisar bloques `texto–saldo`, asignarlos al catálogo, corregir errores y aprobar únicamente después de que todas las cuentas obligatorias estén explícitas y las ecuaciones contables cuadren dentro de la tolerancia.

Ninguna fila vacía deberá bloquear el flujo, ningún nombre original deberá sustituir la clasificación canónica y ningún total explícito deberá contarse dos veces junto con sus detalles.
