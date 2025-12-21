# Core Modules - Módulos Centrales de la Plataforma

Esta carpeta contiene todos los módulos centrales de la plataforma de generación de informes. Estos módulos son completamente independientes de cualquier tipo de informe específico y proporcionan funcionalidad reutilizable para todos los plugins.

## 📋 Índice de Módulos

| Módulo | Líneas | Descripción |
|--------|--------|-------------|
| [config_loader.py](#config_loaderpy) | 311 | Carga y validación de manifests y archivos YAML |
| [schema_models.py](#schema_modelspy) | 218 | Modelos Pydantic para validación de datos |
| [conditions_engine.py](#conditions_enginepy) | 521 | Motor de evaluación de condiciones seguro (AST) |
| [word_engine.py](#word_enginepy) | 365 | Renderizado de documentos Word con Jinja2 |
| [xml_word_engine.py](#xml_word_enginepy) | 1148 | Motor avanzado de procesamiento XML para Word |
| [tp_tables_engine.py](#tp_tables_enginepy) | 314 | Motor de construcción de tablas dinámicas |
| [tables_engine.py](#tables_enginepy) | 350 | Validación y procesamiento de tablas |
| [ui_runtime.py](#ui_runtimepy) | 469 | Generación dinámica de UI Streamlit |
| [input_widgets.py](#input_widgetspy) | 240 | Biblioteca de widgets de entrada |
| [metadata.py](#metadatapy) | 398 | Gestión y persistencia de metadatos |
| [utils.py](#utilspy) | 239 | Utilidades generales (logging, paths, fechas) |
| [import_utils.py](#import_utilspy) | 280 | Importación desde Excel/Word |

**Total:** ~4,853 líneas de código

---

## 📦 Descripción Detallada de Módulos

### config_loader.py

**Propósito:** Carga y validación de archivos de configuración YAML para plugins.

**Funciones Principales:**

- `load_manifest(plugin_dir: Path) -> Manifest`
  - Carga el archivo manifest.yaml de un plugin
  - Valida la estructura usando Pydantic
  - Retorna objeto Manifest con metadata del plugin

- `load_variables_simples(config_dir: Path) -> List[SimpleField]`
  - Carga variables_simples.yaml
  - Parsea definiciones de campos de entrada
  - Retorna lista de objetos SimpleField

- `load_variables_condicionales(config_dir: Path) -> List[ConditionalVariable]`
  - Carga variables_condicionales.yaml
  - Parsea definiciones de opciones condicionales
  - Retorna lista de objetos ConditionalVariable

- `load_bloques_texto(config_dir: Path) -> List[BlockDefinition]`
  - Carga bloques_texto.yaml
  - Parsea definiciones de bloques de texto condicionales
  - Retorna lista de objetos BlockDefinition

- `load_tables_config(config_dir: Path) -> Dict`
  - Carga tablas.yaml (si existe)
  - Parsea definiciones de tablas dinámicas
  - Retorna diccionario con configuración de tablas

**Uso:**
```python
from report_platform.core.config_loader import load_manifest, load_variables_simples

manifest = load_manifest(plugin_dir)
variables = load_variables_simples(config_dir)
```

---

### schema_models.py

**Propósito:** Define modelos Pydantic para validación de datos estructurados.

**Clases Principales:**

- `Manifest`
  - Representa el manifest.yaml de un plugin
  - Campos: id, nombre, version, descripcion, paths, features, etc.

- `SimpleField`
  - Representa una variable simple de entrada
  - Campos: id, nombre, tipo, requerido, seccion, placeholder, etc.

- `FieldDependency`
  - Define dependencias entre campos
  - Campos: variable, valor (cuando mostrar el campo)

- `ConditionalVariable`
  - Representa una variable condicional (radio/checkbox)
  - Campos: id, nombre, tipo_control, opciones, etc.

- `ConditionalOption`
  - Opción dentro de una variable condicional
  - Campos: valor, etiqueta, descripcion, es_default

- `BlockDefinition`
  - Define un bloque de texto condicional
  - Campos: id, descripcion, reglas

- `BlockRule`
  - Regla dentro de un bloque de texto
  - Campos: cuando (condición), plantilla (template Jinja2)

**Uso:**
```python
from report_platform.core.schema_models import SimpleField

field = SimpleField(
    id="nombre_entidad",
    nombre="Nombre de la entidad",
    tipo="texto",
    requerido=True
)
```

---

### conditions_engine.py

**Propósito:** Motor seguro de evaluación de expresiones condicionales usando AST parsing.

**Funciones Principales:**

- `evaluate_condition(condition: str, context: Dict) -> bool`
  - Evalúa expresiones como `"tipo_opinion == 'favorable' and tipo_cuentas == 'normales'"`
  - Usa AST parsing para seguridad (no eval())
  - Soporta operadores: ==, !=, <, >, <=, >=, in, not in, and, or, not
  - Retorna True/False

**Operadores Soportados:**

- **Comparación:** `==`, `!=`, `<`, `>`, `<=`, `>=`, `in`, `not in`
- **Lógicos:** `and`, `or`, `not`
- **Agrupación:** Paréntesis `()`

**Restricciones de Seguridad:**

- ❌ No permite llamadas a funciones
- ❌ No permite acceso a atributos de objetos
- ❌ No permite operaciones aritméticas (solo comparaciones)
- ❌ No permite imports ni asignaciones

**Uso:**
```python
from report_platform.core.conditions_engine import evaluate_condition

context = {'tipo_opinion': 'favorable', 'tipo_cuentas': 'normales'}
result = evaluate_condition("tipo_opinion == 'favorable'", context)
# result = True
```

---

### word_engine.py

**Propósito:** Renderizado de documentos Word usando plantillas Jinja2.

**Funciones Principales:**

- `render_word_report(template_path: Path, context: Dict, output_path: Path) -> bool`
  - Renderiza una plantilla Word (.docx) con variables Jinja2
  - Reemplaza `{{ variable }}` con valores del contexto
  - Procesa bloques condicionales `{% if ... %}...{% endif %}`
  - Soporta loops `{% for item in items %}...{% endfor %}`
  - Guarda el documento renderizado

- `check_xml_engine_flag(context: Dict) -> bool`
  - Verifica si se debe usar el motor XML en lugar de Jinja2
  - Lee flag `_use_xml_engine` del contexto

**Motor de Renderizado:**

- Usa `python-docxtpl` para plantillas Jinja2
- Variables: `{{ nombre_variable }}`
- Condicionales: `{% if condicion %}...{% endif %}`
- Loops: `{% for item in lista %}...{% endfor %}`
- Filtros: `{{ numero|int }}`, `{{ texto|upper }}`

**Uso:**
```python
from report_platform.core.word_engine import render_word_report

context = {
    'nombre_entidad': 'ABC S.A.',
    'tipo_opinion': 'favorable'
}
render_word_report(template_path, context, output_path)
```

---

### xml_word_engine.py

**Propósito:** Motor avanzado de procesamiento XML para documentos Word con tablas dinámicas.

**Funciones Principales:**

- `render_word_with_xml_engine(template_path: Path, context: Dict, output_path: Path) -> bool`
  - Renderiza usando marcadores XML `<<variable>>`
  - Soporta tablas dinámicas con múltiples filas
  - Permite insertar imágenes de fondo
  - Procesamiento de bloques condicionales
  - Limpieza automática de marcadores no usados

- `replace_xml_markers(doc: Document, context: Dict) -> None`
  - Reemplaza marcadores `<<variable>>` en todo el documento
  - Procesa párrafos, tablas, encabezados, pies de página

- `process_dynamic_tables(doc: Document, table_definitions: Dict, context: Dict) -> None`
  - Genera tablas dinámicas basadas en configuración YAML
  - Soporta diferentes tipos de datos (text, number, percent, currency)
  - Permite formateo personalizado de celdas

- `process_conditional_blocks(doc: Document, context: Dict) -> None`
  - Procesa bloques `{% if condicion == 'sí' %}...{% endif %}`
  - Elimina contenido cuando condición es False
  - Mantiene contenido cuando condición es True

- `clean_unused_markers(doc: Document) -> None`
  - Elimina marcadores XML no procesados
  - Limpia el documento de residuos de plantilla

**Marcadores XML:**

- Variables: `<<nombre_variable>>`
- Condicionales: `{% if variable == 'sí' %}...{% endif %}`
- Tablas: `<<Tabla nombre_tabla>>`

**Uso:**
```python
from report_platform.core.xml_word_engine import render_word_with_xml_engine

context = {
    '_use_xml_engine': True,
    'nombre_entidad': 'ABC S.A.',
    'table_data': {...}
}
render_word_with_xml_engine(template_path, context, output_path)
```

---

### tp_tables_engine.py

**Propósito:** Motor especializado de construcción de tablas dinámicas.

**Funciones Principales:**

- `build_table_data(table_id: str, table_config: Dict, context: Dict) -> List[List]`
  - Construye datos de tabla desde configuración YAML
  - Valida tipos de datos (text, number, percent, currency)
  - Formatea valores según el tipo especificado
  - Retorna matriz de datos para insertar en Word

- `format_cell_value(value: Any, cell_type: str) -> str`
  - Formatea valores según el tipo de celda
  - Tipos: text, number, percent, currency
  - Aplica formato de moneda/porcentaje

**Uso:**
```python
from report_platform.core.tp_tables_engine import build_table_data

table_config = {
    'columns': [...],
    'rows': [...]
}
table_data = build_table_data('mi_tabla', table_config, context)
```

---

### tables_engine.py

**Propósito:** Validación y procesamiento general de tablas.

**Funciones Principales:**

- `validate_table_definition(table_def: Dict) -> bool`
  - Valida estructura de definición de tabla
  - Verifica campos requeridos (columns, rows)
  - Valida tipos de datos

- `process_table_data(table_def: Dict, user_input: Dict) -> List[List]`
  - Procesa datos de tabla desde entrada de usuario
  - Valida y formatea filas/columnas
  - Retorna datos listos para renderizar

**Uso:**
```python
from report_platform.core.tables_engine import validate_table_definition

is_valid = validate_table_definition(table_def)
```

---

### ui_runtime.py

**Propósito:** Generación dinámica de interfaz de usuario Streamlit basada en definiciones YAML.

**Funciones Principales:**

- `render_field(field: SimpleField, current_value: Any, key_prefix: str = None) -> Any`
  - Renderiza un campo de entrada según su tipo
  - Tipos: texto, numero, lista, fecha, texto_area, checkbox
  - Soporta `key_prefix` para múltiples instancias (evita DuplicateWidgetID)
  - Gestiona estado en Streamlit session_state
  - Retorna valor introducido por el usuario

- `render_conditional_variable(var: ConditionalVariable, session_state: Dict) -> str`
  - Renderiza variables condicionales (radio/checkbox)
  - Gestiona opciones múltiples
  - Retorna valor seleccionado

- `validate_form_data(data: Dict, field_definitions: List[SimpleField]) -> Tuple[bool, List[str]]`
  - Valida datos del formulario
  - Verifica campos requeridos
  - Valida tipos de datos
  - Retorna (es_valido, lista_errores)

- `organize_fields_by_section(fields: List[SimpleField]) -> Dict[str, List[SimpleField]]`
  - Organiza campos por sección
  - Permite mostrar formulario en pestañas/acordeones
  - Retorna diccionario {seccion: [campos]}

**Tipos de Campos Soportados:**

- **texto:** Input de texto simple
- **texto_area:** Área de texto multilínea
- **numero:** Input numérico
- **lista:** Dropdown/Selectbox
- **fecha:** Date picker
- **checkbox:** Checkbox booleano

**Uso:**
```python
from report_platform.core.ui_runtime import render_field, validate_form_data

value = render_field(field, st.session_state)
is_valid, errors = validate_form_data(data, fields)
```

---

### input_widgets.py

**Propósito:** Biblioteca de widgets personalizados de entrada para Streamlit.

**Funciones de Generación de Claves:**

- `_field_key(field: SimpleField, key_prefix: str = None) -> str`
  - Genera clave única para session_state
  - Soporta prefijo para múltiples instancias del mismo campo
  - Ejemplo: `_field_key(field, "salvedad_1")` → `"salvedad_1__field_numero_nota"`

**Widgets Disponibles (todos soportan key_prefix):**

- `render_text_input(field, current_value, key_prefix=None) -> str`
  - Input de texto con validación
  - Placeholder y ayuda contextual
  - Retorna string

- `render_long_text_input(field, current_value, key_prefix=None) -> str`
  - Área de texto multilínea
  - Altura ajustable
  - Retorna string multilínea

- `render_number_input(field, current_value, key_prefix=None) -> Union[int, float]`
  - Input numérico con validación
  - Min/max opcional
  - Retorna número

- `render_select_input(field, current_value, key_prefix=None) -> str`
  - Dropdown con opciones predefinidas
  - Búsqueda opcional
  - Retorna valor seleccionado

- `render_date_input(field, current_value, key_prefix=None) -> date`
  - Selector de fecha con calendario
  - Formato personalizable
  - Retorna fecha

- `render_date_group_input(fields_group, current_values, group_name, group_label, key_prefix=None) -> dict`
  - Agrupa campos día/mes/año en un solo selector de fecha
  - Retorna diccionario con valores separados

**Uso Multi-Issue:**
```python
from core.input_widgets import render_number_input

# Sin prefijo (instancia única)
value = render_number_input(field, current_value)

# Con prefijo (múltiples instancias)
for i in range(1, n_issues + 1):
    with st.expander(f"Salvedad {i}"):
        value = render_number_input(field, current_value, key_prefix=f"salvedad_{i}")
        # Almacenar como: data[f"salvedad_{i}__{field.id}"] = value
```

---

### metadata.py

**Propósito:** Gestión y persistencia de metadatos de informes generados.

**Funciones Principales:**

- `save_metadata(report_id: str, data: Dict, output_filename: str) -> Path`
  - Guarda metadatos de un informe generado
  - Almacena en formato JSON
  - Incluye timestamp y configuración
  - Retorna path al archivo de metadata

- `load_metadata(metadata_file: Path) -> Dict`
  - Carga metadatos de un archivo
  - Parsea JSON
  - Retorna diccionario con datos

- `list_metadata_files(report_type: str = None) -> List[Path]`
  - Lista archivos de metadatos disponibles
  - Filtro opcional por tipo de informe
  - Retorna lista de paths

- `get_report_history(report_type: str, limit: int = 10) -> List[Dict]`
  - Obtiene historial de informes generados
  - Ordenado por fecha (más reciente primero)
  - Límite configurable
  - Retorna lista de metadatos

**Estructura de Metadata:**

```json
{
  "report_type": "informe_auditoria",
  "generated_at": "2024-03-15T10:30:00",
  "output_filename": "Informe_ABC_20240315.docx",
  "configuration": {
    "nombre_entidad": "ABC S.A.",
    "tipo_opinion": "favorable",
    ...
  }
}
```

**Uso:**
```python
from report_platform.core.metadata import save_metadata, load_metadata

# Guardar
metadata_path = save_metadata('informe_auditoria', data, output_filename)

# Cargar
metadata = load_metadata(metadata_path)
```

---

### utils.py

**Propósito:** Utilidades generales (logging, paths, internacionalización, fechas).

**Funciones Principales:**

- `setup_logger(name: str, level: int = logging.INFO) -> logging.Logger`
  - Configura y retorna un logger con formato estándar
  - Previene duplicación de handlers
  - Retorna logger configurado

- `get_project_root() -> Path`
  - Obtiene el directorio raíz del proyecto
  - Retorna Path al directorio

- `get_reports_dir() -> Path`
  - Obtiene el directorio de plugins
  - Retorna Path a reports/

- `get_outputs_dir() -> Path`
  - Obtiene/crea el directorio de salida
  - Retorna Path a outputs/

- `safe_filename(filename: str) -> str`
  - Sanitiza nombres de archivos
  - Elimina caracteres inválidos
  - Retorna string seguro

- `load_text_file(filepath: Path, encoding: str = 'utf-8') -> Optional[str]`
  - Carga archivo de texto de forma segura
  - Manejo de errores
  - Retorna contenido o None

- `ensure_directory(directory: Path) -> bool`
  - Crea directorio si no existe
  - Retorna True si exitoso

- `set_spanish_locale() -> None`
  - **NUEVO:** Configura locale a español
  - Permite formato de fechas en español
  - Soporta múltiples sistemas operativos

- `parse_date_string(date_string: str) -> datetime`
  - **NUEVO:** Parsea strings de fecha en múltiples formatos
  - Soporta formatos españoles e ingleses
  - Retorna datetime o fecha actual si falla

**Uso:**
```python
from report_platform.core.utils import (
    setup_logger,
    set_spanish_locale,
    parse_date_string
)

logger = setup_logger(__name__)
set_spanish_locale()
fecha = parse_date_string("31/12/2024")
```

---

### import_utils.py

**Propósito:** Importación automatizada de datos desde archivos Excel y Word.

**Funciones Principales:**

- `process_excel_file(file: BinaryIO) -> Dict[str, Any]`
  - Importa datos desde archivo Excel
  - Formato: Columna 1 = variable, Columna 2 = valor
  - Retorna diccionario con datos

- `process_word_file(file: BinaryIO) -> Dict[str, Any]`
  - Importa datos desde archivo Word
  - Formato: `variable: valor` (uno por línea)
  - Retorna diccionario con datos

- `process_uploaded_file(file: BinaryIO, file_type: str) -> Dict[str, Any]`
  - Función principal de importación
  - Delega a procesador apropiado (Excel/Word)
  - Retorna diccionario con datos extraídos

- `normalize_boolean_value(value: str) -> str`
  - Normaliza valores booleanos a 'sí'/'no'
  - Soporta SI, 1, YES, TRUE, etc.
  - Retorna 'sí' o 'no'

- `normalize_variable_name(var_name: str) -> str`
  - Normaliza nombres de variables
  - Elimina acentos y espacios
  - Retorna nombre normalizado

- `map_imported_data_to_fields(imported_data: Dict, field_definitions: Dict) -> Dict`
  - Mapea datos importados a campos del formulario
  - Maneja nombres alternativos/normalizados
  - Retorna datos mapeados correctamente

**Formatos Soportados:**

**Excel (.xlsx, .xls):**
```
| Nombre_Cliente | ABC S.A.    |
| comision       | SI          |
| organo         | consejo     |
```

**Word (.docx):**
```
Nombre_Cliente: ABC S.A.
comision: SI
organo: consejo
```

**Uso:**
```python
from report_platform.core.import_utils import process_uploaded_file

with open('datos.xlsx', 'rb') as f:
    datos = process_uploaded_file(f, 'excel')
print(datos)
# {'Nombre_Cliente': 'ABC S.A.', 'comision': 'sí', 'organo': 'consejo'}
```

---

## 🔧 Flujo de Uso Típico

### 1. Cargar Configuración del Plugin

```python
from report_platform.core.config_loader import (
    load_manifest,
    load_variables_simples,
    load_variables_condicionales,
    load_bloques_texto
)

manifest = load_manifest(plugin_dir)
variables = load_variables_simples(config_dir)
conditionals = load_variables_condicionales(config_dir)
bloques = load_bloques_texto(config_dir)
```

### 2. Renderizar UI y Capturar Datos

```python
from report_platform.core.ui_runtime import render_field, validate_form_data

# Renderizar campos
for field in variables:
    value = render_field(field, st.session_state)
    user_data[field.id] = value

# Validar
is_valid, errors = validate_form_data(user_data, variables)
```

### 3. Procesar Lógica de Negocio

```python
from report_platform.reports.mi_plugin.logic import build_context

# Construir contexto
context = build_context(user_data, config_dir)
```

### 4. Generar Documento Word

```python
from report_platform.core.word_engine import render_word_report
# O para XML:
# from report_platform.core.xml_word_engine import render_word_with_xml_engine

# Renderizar
success = render_word_report(template_path, context, output_path)
```

### 5. Guardar Metadata

```python
from report_platform.core.metadata import save_metadata

metadata_path = save_metadata(
    report_id=manifest.id,
    data=user_data,
    output_filename=output_path.name
)
```

---

## 🚀 Añadir Nuevas Funcionalidades

### Para añadir un nuevo tipo de campo:

1. Actualizar `schema_models.py` con el nuevo tipo
2. Crear widget en `input_widgets.py`
3. Añadir renderizado en `ui_runtime.py`

### Para añadir un nuevo motor de renderizado:

1. Crear nuevo archivo en `core/` (ej: `pdf_engine.py`)
2. Implementar función principal `render_pdf_report()`
3. Actualizar `word_engine.py` para detectar el nuevo motor

### Para extender el sistema de metadata:

1. Modificar estructura en `metadata.py`
2. Actualizar funciones de save/load
3. Añadir validación con Pydantic si es necesario

---

## 📝 Notas Importantes

### Seguridad

- **Conditions Engine:** Usa AST parsing, no `eval()`, para prevenir inyección de código
- **File Upload:** Valida tipos de archivo antes de procesar
- **Path Traversal:** Todas las rutas se validan antes de usar

### Performance

- Los archivos YAML se cargan una sola vez por plugin
- Las metadata se almacenan en JSON para rapidez
- El renderizado de Word se optimiza reutilizando objetos

### Mantenibilidad

- Todos los módulos tienen docstrings completos
- Se sigue PEP 8 para estilo de código
- Logging extensivo para debugging
- Validación con Pydantic previene errores

---

## 🛠️ Dependencias

```python
# requirements.txt
pyyaml>=6.0
pydantic>=2.0
python-docx>=0.8.11
python-docxtpl>=0.16.7
lxml>=4.9.0
pandas>=2.0.0
openpyxl>=3.1.0
streamlit>=1.28.0
```

---

## 📞 Soporte

Para añadir nuevos módulos core o extender funcionalidad existente, consultar:

- Documentación de Pydantic: https://docs.pydantic.dev/
- Python-docx: https://python-docx.readthedocs.io/
- Streamlit: https://docs.streamlit.io/

---

**Última actualización:** Diciembre 2024
**Versión de la plataforma:** 1.0.0
