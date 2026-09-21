Quiero que construyas el primer módulo de una aplicación para importar estados financieros desde archivos Excel.

OBJETIVO GENERAL

Crear un sistema que permita subir archivos Excel contables, analizar sus hojas, detectar cuentas contables, normalizar sus nombres, reconocer códigos, identificar su clasificación contable y preparar la información para almacenarla posteriormente en una base de datos.

El sistema NO debe importar automáticamente información dudosa. Cuando exista una cuenta desconocida, ambigua o con posible error ortográfico, debe mostrarla para revisión humana.

STACK TECNOLÓGICO

Frontend:

* React
* TypeScript
* Vite
* Tailwind CSS
* shadcn/ui
* TanStack Table
* react-dropzone

Backend:

* Python
* FastAPI
* Pydantic
* SQLAlchemy
* Alembic

Procesamiento Excel:

* pandas
* openpyxl
* RapidFuzz
* unicodedata
* re

Base de datos:

* PostgreSQL

Desarrollo:

* Docker
* Docker Compose
* pytest
* Ruff

No agregar Redis, Celery, Polars ni DuckDB todavía. La primera versión debe ser sencilla, modular y fácil de extender.

==================================================
PRIMER MÓDULO: IMPORTAR DATOS
=============================

Crear una pantalla principal llamada:

IMPORTAR ESTADOS FINANCIEROS

Debe tener aproximadamente esta estructura:

Empresa:
[ seleccionar empresa ]

Periodo:
[ seleccionar año o periodo ]

Archivo:
[ área drag and drop ]

Texto:

Arrastra aquí tu archivo Excel
o haz clic para seleccionar

Formatos inicialmente aceptados:
.xlsx
.xlsm

Botón:

[ Analizar archivo ]

No importar datos todavía al presionar este botón.

Primero se debe analizar el archivo.

==================================================
FLUJO DEL SISTEMA
=================

El proceso debe seguir este flujo:

SUBIR ARCHIVO
↓
LEER EXCEL
↓
DETECTAR HOJAS
↓
DETECTAR POSIBLES ESTADOS FINANCIEROS
↓
DETECTAR TABLAS
↓
DETECTAR ENCABEZADOS
↓
EXTRAER CUENTAS
↓
NORMALIZAR NOMBRES
↓
DETECTAR CÓDIGOS
↓
COMPARAR CON CATÁLOGO DE CUENTAS
↓
CLASIFICAR RESULTADOS
↓
MOSTRAR REVISIÓN
↓
CONFIRMACIÓN HUMANA
↓
IMPORTAR

Nunca saltarse la pantalla de revisión cuando existan advertencias.

==================================================
TIPOS DE HOJAS
==============

El sistema debe intentar reconocer estos tipos:

BALANCE_COMPROBACION

ESTADO_SITUACION_FINANCIERA

ESTADO_RESULTADOS

FLUJO_EFECTIVO

DESCONOCIDO

Debe normalizar también el nombre de la hoja.

Ejemplos equivalentes:

"Balance General"
"BALANCE GENERAL"
"Estado de Situación Financiera"
"Balance de Situación"

pueden clasificarse como:

ESTADO_SITUACION_FINANCIERA

Ejemplos:

"Estado de Resultados"
"Resultados"
"Pérdidas y Ganancias"

pueden clasificarse como:

ESTADO_RESULTADOS

No depender exclusivamente del nombre de la hoja.

También intentar identificar el tipo utilizando el contenido.

==================================================
NORMALIZACIÓN DE TEXTO
======================

Crear una función central reutilizable:

normalize_account_name(text: str) -> str

Debe:

1. convertir el texto a string
2. eliminar espacios al inicio y final
3. convertir a mayúsculas
4. eliminar tildes
5. convertir múltiples espacios en uno
6. limpiar caracteres invisibles
7. conservar caracteres relevantes como &, -, / cuando sean necesarios

Ejemplos:

" vehículos "
→
"VEHICULOS"

"Vehículos"
→
"VEHICULOS"

"VEHÍCULOS"
→
"VEHICULOS"

"Gastos   de   Administración"
→
"GASTOS DE ADMINISTRACION"

IMPORTANTE:

Nunca destruir el nombre original.

Guardar siempre:

original_name

normalized_name

Ejemplo:

original_name:
"Vehículos"

normalized_name:
"VEHICULOS"

==================================================
MODELO DE CUENTAS
=================

No utilizar solamente el nombre para identificar una cuenta.

Una cuenta debe tener al menos:

id

code

name

normalized_name

account_type

nature

level

parent_code

financial_statement

created_at

updated_at

Ejemplo:

{
"code": "12010203",
"name": "VEHICULOS",
"normalized_name": "VEHICULOS",
"account_type": "ACTIVO",
"nature": "DEUDORA",
"level": 6,
"parent_code": "120102",
"financial_statement": "ESTADO_SITUACION_FINANCIERA"
}

==================================================
TIPOS CONTABLES
===============

Crear un enum AccountType con:

ACTIVO
PASIVO
PATRIMONIO
INGRESO
COSTO
GASTO
OTRO

No tratar SALDO como tipo de cuenta.

SALDO es un valor asociado a una cuenta.

No tratar UTILIDAD automáticamente como una cuenta.

La utilidad puede ser un resultado calculado.

==================================================
CÓDIGOS JERÁRQUICOS
===================

Los códigos de las cuentas deben manejarse como strings, no como integers.

Esto es importante para evitar pérdida de ceros.

Ejemplo:

"01"

no debe convertirse a:

1

El sistema debe soportar estructuras como:

1
11
1101
110102
11010201
1101020102

Ejemplo:

1 ACTIVO

11 CORRIENTE

1101 EFECTIVO Y EQUIVALENTES

110102 BANCOS

11010201 CUENTAS CORRIENTES

1101020102 BANCO DAVIVIENDA SALVADOREÑO, S.A.

Cuando sea posible determinar el nivel por la estructura del catálogo, almacenar:

level

y:

parent_code

No asumir que todos los catálogos usarán exactamente las mismas longitudes.

Diseñar la lógica para que después podamos configurar esquemas diferentes.

==================================================
IDENTIFICACIÓN DE CUENTAS
=========================

El algoritmo debe buscar una cuenta siguiendo este orden:

1. código exacto
2. código + nombre normalizado
3. nombre normalizado + contexto jerárquico
4. alias conocido
5. coincidencia aproximada usando RapidFuzz
6. revisión humana

Nunca utilizar fuzzy matching como confirmación automática de una cuenta financiera.

RapidFuzz solo debe generar sugerencias.

Ejemplo:

Excel:

"VEICULOS"

Catálogo:

"VEHICULOS"

El sistema puede indicar:

Posible coincidencia:
VEHICULOS

pero debe marcarlo como:

NEEDS_REVIEW

si no existe otra evidencia suficiente.

==================================================
CUENTAS CON EL MISMO NOMBRE
===========================

Esta regla es MUY IMPORTANTE.

Puede existir el mismo nombre de cuenta en diferentes lugares del catálogo.

Ejemplo:

410415 HONORARIOS

puede pertenecer a:

COSTO DE PRODUCCIÓN

y:

420110 HONORARIOS

puede pertenecer a:

GASTOS DE ADMINISTRACIÓN

Por lo tanto:

"HONORARIOS"

NO identifica una cuenta de forma única.

El código y el contexto jerárquico tienen prioridad.

Nunca crear una regla global:

HONORARIOS = código X

sin revisar contexto.

==================================================
ALIAS DE CUENTAS
================

Crear una tabla AccountAlias.

Campos:

id

account_id

alias

normalized_alias

created_at

Ejemplo:

Cuenta oficial:

12010203
VEHICULOS

Alias:

VEHICULO

VEHÍCULOS

EQUIPO DE TRANSPORTE

VEHICULOS DE LA EMPRESA

La normalización debe ocurrir antes de buscar aliases.

==================================================
SALDOS
======

Separar completamente la definición de una cuenta de sus valores financieros.

Crear un modelo AccountBalance.

Campos iniciales:

id

company_id

period_id

account_id

opening_balance

debits

credits

ending_balance

source_import_id

source_sheet

source_row

Una cuenta puede existir durante muchos periodos.

No duplicar la cuenta por cada año.

Ejemplo:

Cuenta:

420109
PAPELERIA Y UTILES

Saldos:

2024 = X

2025 = Y

2026 = Z

==================================================
IMPORTACIONES
=============

Crear una entidad ImportJob o FinancialImport.

Campos sugeridos:

id

company_id

period_id

file_name

status

created_at

completed_at

total_rows

recognized_rows

review_rows

new_accounts

error_rows

Estados posibles:

UPLOADED

ANALYZING

READY_FOR_REVIEW

APPROVED

IMPORTED

FAILED

==================================================
TRAZABILIDAD
============

Cada fila importada debe mantener referencia a:

archivo

hoja

número de fila original

texto original

código original

nombre original

nombre normalizado

cuenta detectada

tipo de coincidencia

confianza

estado

Esto es importante para auditoría.

Crear una entidad ImportRow.

Ejemplo:

{
"sheet": "Balance de Comprobacion",
"excel_row": 44,
"original_code": "420112",
"original_name": "Combustibles y Lobricantes",
"normalized_name": "COMBUSTIBLES Y LOBRICANTES",
"matched_account_id": 321,
"match_type": "FUZZY",
"status": "NEEDS_REVIEW"
}

==================================================
ESTADOS DE UNA FILA
===================

Crear un enum:

MATCHED

NEEDS_REVIEW

UNKNOWN

NEW_ACCOUNT

ERROR

IGNORED

Y para match_type:

EXACT_CODE

CODE_AND_NAME

NORMALIZED_NAME

ALIAS

CONTEXT

FUZZY

NONE

==================================================
ANÁLISIS INICIAL DEL ARCHIVO
============================

Después de subir el Excel, mostrar una pantalla como:

ANÁLISIS DEL ARCHIVO

Archivo:
Balance de comprobacion BENGALA 2025.xlsx

Hojas encontradas: 4

Balance de Comprobación
Tipo detectado:
BALANCE_COMPROBACION

Balance General
Tipo detectado:
ESTADO_SITUACION_FINANCIERA

Estado de Resultados
Tipo detectado:
ESTADO_RESULTADOS

Hoja1
Tipo detectado:
DESCONOCIDO

Botones:

[ Atrás ]

[ Continuar ]

==================================================
CONFIGURACIÓN DE HOJA
=====================

Para cada hoja relevante mostrar:

Hoja:
[ selector ]

Tipo:
[ selector ]

Fila de encabezados:
[ número ]

Mapeo de columnas:

Columna Excel
→
Campo sistema

Ejemplo:

Código de cuenta
→
code

Nombre de cuenta
→
account_name

Saldo anterior
→
opening_balance

Cargos
→
debits

Abonos
→
credits

Saldo actual
→
ending_balance

Debe permitirse modificar manualmente el mapeo.

==================================================
DETECCIÓN DE ENCABEZADOS
========================

No asumir que la primera fila contiene encabezados.

Los Excel financieros pueden contener:

nombre de empresa

título

fecha

periodo

filas vacías

antes de la tabla.

Implementar una función que inspeccione las primeras filas y trate de encontrar posibles encabezados.

Buscar palabras como:

CODIGO

CUENTA

SALDO

SALDO ANTERIOR

CARGO

CARGOS

DEBE

ABONO

ABONOS

HABER

SALDO ACTUAL

SALDO FINAL

No depender de coincidencia exacta.

Normalizar primero.

La detección debe devolver también un nivel de confianza.

==================================================
PANTALLA DE REVISIÓN
====================

Crear una tabla con TanStack Table.

Columnas:

Estado

Código Excel

Cuenta Excel

Código sistema

Cuenta sistema

Tipo

Coincidencia

Confianza

Acciones

Ejemplo:

✓
12010203
Vehiculos
12010203
VEHICULOS
ACTIVO
EXACT_CODE
100%

Otro ejemplo:

## ?

Combustibles y Lobricantes
420112
COMBUSTIBLES Y LUBRICANTES
GASTO
FUZZY
96%

Otro ejemplo:

## !

## Honorarios

*
*

## AMBIGUOUS

La tabla debe permitir:

buscar

filtrar

ordenar

mostrar solo problemas

seleccionar una sugerencia

marcar como cuenta nueva

ignorar una fila

editar asignación

confirmar equivalencia

==================================================
RESUMEN DE REVISIÓN
===================

Mostrar arriba:

Registros encontrados

Cuentas reconocidas

Cuentas nuevas

Posibles errores

Cuentas ambiguas

Errores

Ejemplo:

Registros encontrados: 184

Reconocidos: 169

Nuevos: 8

Posibles errores: 4

Ambiguos: 3

==================================================
CREACIÓN DE CUENTA NUEVA
========================

Si una cuenta no existe permitir:

Crear nueva cuenta

Mostrar formulario:

Nombre original

Nombre normalizado

Código

Tipo

Naturaleza

Cuenta padre

Nivel

Estado financiero

No generar silenciosamente códigos arbitrarios como:

1001
1002
1003

si el catálogo utiliza estructura jerárquica.

Para el MVP, si no puede determinarse un código válido:

marcar la cuenta para configuración manual.

==================================================
VALIDACIONES FINANCIERAS
========================

Crear una arquitectura extensible llamada:

FinancialValidationService

Inicialmente implementar validaciones simples.

Por ejemplo, cuando corresponda:

ACTIVO = PASIVO + PATRIMONIO

y para resultados:

INGRESOS - COSTOS - GASTOS = RESULTADO

No bloquear automáticamente una importación por diferencias pequeñas.

Registrar:

expected_value

actual_value

difference

status

Preparar tolerancia configurable.

==================================================
SEGURIDAD DE DATOS
==================

No modificar los datos originales.

Mantener:

raw value

normalized value

resolved value

Ejemplo:

raw:
" Vehículos "

normalized:
"VEHICULOS"

resolved:
account_id = 123

Esto permitirá auditoría y depuración.

==================================================
ARQUITECTURA DEL BACKEND
========================

No poner toda la lógica en los endpoints.

Separar aproximadamente:

app/

api/

models/

schemas/

services/

repositories/

importers/

normalizers/

matchers/

validators/

tests/

Por ejemplo:

services/excel_import_service.py

services/account_matching_service.py

services/account_normalization_service.py

services/financial_validation_service.py

importers/excel_reader.py

matchers/account_matcher.py

normalizers/text_normalizer.py

validators/financial_validator.py

==================================================
API INICIAL
===========

Diseñar endpoints similares a:

POST
/api/imports

Subir archivo.

POST
/api/imports/{id}/analyze

Analizar Excel.

GET
/api/imports/{id}

Obtener estado.

GET
/api/imports/{id}/sheets

Obtener hojas detectadas.

GET
/api/imports/{id}/rows

Obtener filas analizadas.

GET
/api/imports/{id}/issues

Obtener solo filas con problemas.

PATCH
/api/imports/{id}/rows/{row_id}

Corregir asignación.

POST
/api/imports/{id}/approve

Aprobar revisión.

POST
/api/imports/{id}/commit

Guardar importación definitivamente.

No es obligatorio usar exactamente estos endpoints si propones una estructura REST mejor.

==================================================
FRONTEND
========

Crear inicialmente estas rutas:

/imports/new

/imports/:id/analyze

/imports/:id/review

/imports/:id/result

Componentes sugeridos:

ExcelDropzone

ImportSummary

SheetDetector

ColumnMapper

AccountReviewTable

AccountMatchBadge

NewAccountDialog

ImportIssuesFilter

FinancialValidationSummary

==================================================
DISEÑO
======

La interfaz debe ser profesional y sencilla.

No crear un dashboard visualmente recargado.

Priorizar:

legibilidad

tablas

alertas claras

estados claros

acciones explícitas

Los colores deben utilizarse principalmente para:

correcto

advertencia

error

información

==================================================
IMPORTANTE SOBRE EL EXCEL REAL
==============================

El sistema debe estar preparado para archivos donde una fila pueda contener algo conceptualmente parecido a:

11010201 CUENTAS CORRIENTES

o donde código y nombre estén separados en diferentes columnas.

También debe soportar jerarquías como:

1 ACTIVO

11 CORRIENTE

1101 EFECTIVO Y EQUIVALENTES

110102 BANCOS

11010201 CUENTAS CORRIENTES

1101020102 BANCO DAVIVIENDA SALVADOREÑO, S.A.

El archivo puede contener filas de agrupación y filas de cuentas finales.

No asumir que todas las filas representan cuentas transaccionales.

Preparar un campo:

is_group

o equivalente.

==================================================
PRUEBAS
=======

Crear tests al menos para:

normalización de nombres

eliminación de tildes

espacios múltiples

códigos como string

cuentas con nombres iguales y códigos diferentes

aliases

fuzzy matching

detección de encabezados

detección de hojas

clasificación de filas

cuentas desconocidas

cuentas ambiguas

Ejemplos obligatorios:

# normalize_account_name(" Vehículos ")

"VEHICULOS"

# normalize_account_name("VEHÍCULOS")

"VEHICULOS"

Las cuentas:

410415 HONORARIOS

y:

420110 HONORARIOS

deben poder coexistir sin conflictos.

==================================================
REGLAS IMPORTANTES
==================

1.

Nunca identificar una cuenta únicamente porque su texto se parece a otra.

2.

Código exacto tiene prioridad.

3.

Conservar siempre datos originales.

4.

Normalización no significa modificación del archivo original.

5.

Los códigos de cuentas son strings.

6.

No crear automáticamente cuentas ambiguas.

7.

Fuzzy matching solamente genera sugerencias.

8.

La revisión humana forma parte del flujo normal.

9.

Separar cuenta de saldo.

10.

Separar lógica contable de lógica de lectura de Excel.

11.

Diseñar el sistema para soportar en el futuro catálogos contables diferentes por empresa.

12.

No sobreingenierizar el MVP.

==================================================
FORMA DE TRABAJAR
=================

Antes de programar:

1. revisa la arquitectura solicitada
2. propone una estructura de carpetas
3. identifica decisiones importantes
4. crea un plan de implementación por etapas

Después implementa en pequeñas etapas.

Prioridad inicial:

FASE 1

Proyecto base

Docker

FastAPI

React

PostgreSQL

modelos principales

subida de archivo

FASE 2

lector Excel

detección de hojas

detección de encabezados

normalización

FASE 3

catálogo de cuentas

matching

aliases

RapidFuzz

FASE 4

pantalla de revisión

correcciones manuales

FASE 5

confirmación e importación

FASE 6

validaciones financieras

No implementar funcionalidades que no sean necesarias para estas fases sin justificar primero por qué son necesarias.

Escribe código mantenible, tipado y testeable.

Evita funciones gigantes.

Mantén separada la lógica de negocio de la interfaz y de la base de datos.

Si encuentras una decisión ambigua, favorece una arquitectura simple que podamos extender posteriormente.
