# Arquitectura de la Plataforma de Generación de Informes

## Resumen

Esta plataforma implementa un sistema modular para generación de documentos Word basado en:

1. **Arquitectura de plugins** - Cada tipo de informe es un plugin independiente
2. **Configuración declarativa** - YAML para definir campos, condiciones y texto
3. **Motor de condiciones seguro** - Evaluación basada en AST (sin `eval()`)
4. **Renderizado dual** - Jinja2 estándar o motor XML avanzado

## Diagrama de Arquitectura

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         CAPA DE PRESENTACIÓN                            │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                   ui/app.py (Streamlit)                          │   │
│  │  ┌───────────┐ ┌────────────┐ ┌──────────┐ ┌────────────────┐   │   │
│  │  │ Sidebar   │ │  Tabs      │ │ Forms    │ │ Generation     │   │   │
│  │  │ Selection │ │  Layout    │ │ Widgets  │ │ Button         │   │   │
│  │  └───────────┘ └────────────┘ └──────────┘ └────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                 │                                       │
│                                 ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                     ui/router.py                                 │   │
│  │              Plugin Discovery & Loading                          │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           CAPA CORE                                     │
│                                                                         │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐  │
│  │  config_loader   │  │  schema_models   │  │  conditions_engine   │  │
│  │                  │  │                  │  │                      │  │
│  │ • load_manifest  │  │ • Manifest       │  │ • SafeConditionEval  │  │
│  │ • load_yaml      │  │ • SimpleField    │  │ • evaluate_condition │  │
│  │ • load_fields    │  │ • Conditional    │  │ • AST parsing        │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────────┘  │
│                                                                         │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐  │
│  │   word_engine    │  │ xml_word_engine  │  │     ui_runtime       │  │
│  │                  │  │                  │  │                      │  │
│  │ • Jinja2 render  │  │ • XML parsing    │  │ • render_field       │  │
│  │ • docxtpl        │  │ • <<markers>>    │  │ • validate_form      │  │
│  │ • output files   │  │ • Dynamic tables │  │ • Dependencies       │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────────┘  │
│                                                                         │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐  │
│  │  input_widgets   │  │    metadata      │  │       utils          │  │
│  │                  │  │                  │  │                      │  │
│  │ • text_input     │  │ • save_metadata  │  │ • setup_logger       │  │
│  │ • select_input   │  │ • load_metadata  │  │ • get_outputs_dir    │  │
│  │ • date_input     │  │ • ReportMetadata │  │ • safe_filename      │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         CAPA DE PLUGINS                                 │
│                                                                         │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │              reports/informe_auditoria/                         │    │
│  │  ┌──────────────┐  ┌───────────────────────────────────────┐   │    │
│  │  │ manifest.yaml│  │            logic.py                    │   │    │
│  │  │              │  │                                        │   │    │
│  │  │ id, nombre,  │  │  BloquesTextoProcessor                 │   │    │
│  │  │ version,     │  │  build_context(data_in, config_dir)    │   │    │
│  │  │ paths        │  │                                        │   │    │
│  │  └──────────────┘  └───────────────────────────────────────┘   │    │
│  │                                                                 │    │
│  │  ┌─────────────────────────────────────────────────────────┐   │    │
│  │  │                    config/                               │   │    │
│  │  │  ┌─────────────────┐ ┌─────────────────────┐            │   │    │
│  │  │  │ variables_      │ │ variables_          │            │   │    │
│  │  │  │ simples.yaml    │ │ condicionales.yaml  │            │   │    │
│  │  │  └─────────────────┘ └─────────────────────┘            │   │    │
│  │  │  ┌─────────────────┐                                     │   │    │
│  │  │  │ bloques_        │                                     │   │    │
│  │  │  │ texto.yaml      │                                     │   │    │
│  │  │  └─────────────────┘                                     │   │    │
│  │  └─────────────────────────────────────────────────────────┘   │    │
│  │                                                                 │    │
│  │  ┌─────────────────────────────────────────────────────────┐   │    │
│  │  │              templates/plantilla_informe.docx            │   │    │
│  │  └─────────────────────────────────────────────────────────┘   │    │
│  └────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
```

## Flujo de Datos

```
ENTRADA (Usuario)                PROCESAMIENTO                    SALIDA
─────────────────                ─────────────                    ──────

┌──────────────┐
│   Formulario │
│   Streamlit  │
└──────┬───────┘
       │
       ▼
┌──────────────┐     ┌────────────────────┐
│  form_data   │────►│  validate_form_data │
│  (dict)      │     └─────────┬──────────┘
└──────────────┘               │
                               ▼
                    ┌────────────────────┐
                    │   build_context()  │
                    │   (plugin logic)   │
                    └─────────┬──────────┘
                              │
                    ┌─────────▼──────────┐
                    │ BloquesTextoProc.  │
                    │ procesar_todos()   │
                    └─────────┬──────────┘
                              │
           ┌──────────────────┼──────────────────┐
           ▼                  ▼                  ▼
    ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
    │ Evaluar     │   │ Evaluar     │   │ Evaluar     │
    │ Condición 1 │   │ Condición 2 │   │ Condición N │
    └──────┬──────┘   └──────┬──────┘   └──────┬──────┘
           │                 │                  │
           ▼                 ▼                  ▼
    ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
    │ Renderizar  │   │ Renderizar  │   │ Renderizar  │
    │ Plantilla   │   │ Plantilla   │   │ Plantilla   │
    └──────┬──────┘   └──────┬──────┘   └──────┬──────┘
           │                 │                  │
           └────────────┬────┴──────────────────┘
                        ▼
              ┌──────────────────┐
              │  context (dict)  │
              │  completo        │
              └────────┬─────────┘
                       │
                       ▼
              ┌──────────────────┐     ┌─────────────────┐
              │ render_word_     │────►│ Documento Word  │
              │ report()         │     │ (.docx)         │
              └──────────────────┘     └─────────────────┘
                       │
                       ▼
              ┌──────────────────┐     ┌─────────────────┐
              │  save_metadata() │────►│ metadata.json   │
              └──────────────────┘     └─────────────────┘
```

## Módulos del Core

### 1. config_loader.py

**Propósito**: Carga y valida archivos de configuración YAML

**Funciones principales**:
- `load_manifest(plugin_dir)` → `Manifest`
- `load_yaml_config(filepath)` → `Dict`
- `load_simple_fields(config_dir)` → `List[SimpleField]`
- `load_conditional_variables(config_dir)` → `List[ConditionalVariable]`
- `load_text_blocks(config_dir)` → `List[BlockDefinition]`
- `load_plugin_config(plugin_dir)` → `Dict` (carga completa)

**Dependencias**: `yaml`, `schema_models`, `utils`

### 2. schema_models.py

**Propósito**: Define modelos Pydantic para validación de datos

**Clases principales**:

```python
class Manifest(BaseModel):
    id: str
    nombre: str
    version: str
    descripcion: Optional[str]
    autor: Optional[str]
    paths: ManifestPaths

class SimpleField(BaseModel):
    id: str
    nombre: str
    tipo: Literal["texto", "texto_area", "numero", "lista", "fecha", "checkbox"]
    requerido: bool = False
    placeholder: Optional[str]
    seccion: Optional[str]
    dependencia: Optional[FieldDependency]

class ConditionalVariable(BaseModel):
    id: str
    nombre: str
    tipo_control: Literal["radio", "checkbox", "derivado"]
    opciones: List[ConditionalOption]
    dependencia: Optional[FieldDependency]

class BlockDefinition(BaseModel):
    id: str
    descripcion: Optional[str]
    reglas: List[BlockRule]

class BlockRule(BaseModel):
    cuando: str  # Condición Python
    plantilla: str  # Template Jinja2
```

### 3. conditions_engine.py

**Propósito**: Evaluación segura de condiciones sin usar `eval()`

**Implementación**:
- Usa `ast.parse()` para analizar expresiones
- Implementa un visitor (`SafeConditionEvaluator`) que solo permite operaciones seguras
- Soporta: comparaciones, operadores lógicos, literales, variables del contexto

**Operadores soportados**:
```python
# Comparación
==, !=, <, >, <=, >=, in, not in

# Lógicos
and, or, not

# Paréntesis
(expresión)
```

**Ejemplo de uso**:
```python
from core.conditions_engine import evaluate_condition

context = {"tipo_opinion": "favorable", "tipo_cuentas": "normales"}
resultado = evaluate_condition("tipo_opinion == 'favorable' and tipo_cuentas != 'consolidadas'", context)
# resultado = True
```

### 4. word_engine.py

**Propósito**: Renderizado de documentos Word usando Jinja2

**Funciones principales**:
- `render_word_report(template_path, context, output_filename)` → `Path`
- `render_template_string(template_content, context)` → `str`

**Motores disponibles**:
1. **Motor Jinja2 (docxtpl)**: Variables con `{{ variable }}`
2. **Motor XML (xml_word_engine)**: Marcadores con `<<variable>>`

**Selección de motor**:
```python
# Si el contexto tiene _use_xml_engine=True, usa motor XML
if context.get('_use_xml_engine'):
    return render_word_with_xml_engine(template_path, context)
```

### 5. xml_word_engine.py

**Propósito**: Procesamiento avanzado de documentos Word via XML

**Características**:
- Manipulación directa del XML interno de .docx
- Soporte para marcadores `<<variable>>`
- Tablas dinámicas
- Bloques condicionales en documento

**Clase principal**:
```python
class XMLWordEngineAdapter:
    def __init__(self, template_path: Path)
    def replace_variables(self, context: dict)
    def process_dynamic_tables(self, doc, table_definitions, context)
    def process_conditional_blocks(self, doc, context)
    def clean_unused_markers(self, doc)
    def save(self, output_path: Path)
```

### 6. ui_runtime.py

**Propósito**: Generación dinámica de controles Streamlit

**Funciones principales**:
- `render_field(field, session_state, key_prefix=None)` → Valor
- `render_conditional_variable(var, current_value)` → Valor
- `validate_form_data(fields, data)` → `(bool, List[str])`
- `render_section_fields(section_name, fields, context)` → `Dict`
- `should_show_field_in_ui(field, context)` → `bool`

**Manejo de dependencias**:
```python
# Campo con dependencia
field = SimpleField(
    id="motivo_salvedades",
    dependencia=FieldDependency(
        variable="tipo_opinion",
        valor="salvedades"  # Solo mostrar si tipo_opinion == salvedades
    )
)
```

**Soporte Multi-Issue (key_prefix)**:
```python
# Renderizado de múltiples instancias del mismo campo
for i in range(1, n_issues + 1):
    key_prefix = f"salvedad_{i}"
    with st.expander(f"Salvedad {i}"):
        value = render_field(field, current_value, key_prefix=key_prefix)
        # Valor almacenado como: salvedad_1__numero_nota
```

### 7. metadata.py

**Propósito**: Persistencia y gestión de metadatos de informes

**Modelo**:
```python
class ReportMetadata(BaseModel):
    id: str                    # UUID único
    report_id: str             # ID del plugin
    report_name: str           # Nombre del informe
    timestamp: datetime        # Fecha/hora generación
    template_version: str      # Versión de plantilla
    input_data: Dict           # Datos del formulario
    output_path: str           # Ruta del archivo generado
    output_filename: str       # Nombre del archivo
    generated_by: str          # Usuario que generó
    description: Optional[str] # Descripción opcional
```

**Funciones**:
- `save_metadata(meta)` → Guarda en JSON
- `load_all_metadata()` → `List[ReportMetadata]`
- `load_metadata_by_report_id(report_id)` → `List[ReportMetadata]`

## Estructura de un Plugin

### manifest.yaml (Obligatorio)

```yaml
id: mi_plugin                    # ID único del plugin
nombre: Mi Plugin de Informes    # Nombre para mostrar
version: "1.0.0"                 # Versión semántica
descripcion: >                   # Descripción multilínea
  Descripción detallada del plugin
autor: Nombre del Autor          # Autor/organización

paths:
  template: templates/plantilla.docx  # Ruta a plantilla
  config_dir: config                  # Directorio de configuración

features:                        # Lista de características
  - Característica 1
  - Característica 2

tags:                           # Etiquetas para búsqueda
  - etiqueta1
  - etiqueta2

requirements:                   # Requisitos
  python_version: ">=3.11"
  dependencies:
    - jinja2
    - pyyaml
```

### logic.py (Obligatorio)

```python
from pathlib import Path
from typing import Dict, Any
from core.conditions_engine import evaluate_condition

class BloquesTextoProcessor:
    """Procesa bloques de texto condicionales."""

    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
        self._load_config()

    def procesar_todos(self, contexto: Dict) -> Dict[str, str]:
        """Procesa todos los bloques y devuelve textos renderizados."""
        ...

def build_context(data_in: Dict[str, Any], config_dir: Path) -> Dict[str, Any]:
    """
    Función principal que construye el contexto para la plantilla.

    Args:
        data_in: Datos del formulario
        config_dir: Directorio de configuración del plugin

    Returns:
        Contexto completo para renderizar la plantilla
    """
    context = dict(data_in)

    # Calcular variables auxiliares
    # ...

    # Determinar número de issues para manejo de plurales
    n_issues = int(data_in.get('num_salvedades') or 1)
    context['_n_issues'] = n_issues

    # Procesar bloques de texto
    processor = BloquesTextoProcessor(config_dir)
    bloques = processor.procesar_todos(context)
    context.update(bloques)

    # Generar múltiples párrafos si N > 1
    if n_issues > 1:
        # Renderizar N instancias del template
        paragraphs = []
        for i in range(1, n_issues + 1):
            tmp_context = context.copy()
            # Mapear campos compuestos: salvedad_1__numero_nota -> numero_nota
            for key, value in data_in.items():
                if key.startswith(f"salvedad_{i}__"):
                    original_field = key[len(f"salvedad_{i}__"):]
                    tmp_context[original_field] = value
            rendered = processor._renderizar_plantilla(template, tmp_context)
            paragraphs.append(rendered)
        context['parrafo_fundamento_calificacion'] = '\n\n'.join(paragraphs)

    # Aplicar marcadores de plural
    context = apply_plural_markers(context, n_issues)

    return context

def apply_plural_markers(text: str, n: int) -> str:
    """
    Convierte marcadores de plural según el conteo.

    Ejemplos:
    - "la(s)" -> "la" (n=1) o "las" (n>1)
    - "cuestión(es)" -> "cuestión" (n=1) o "cuestiones" (n>1)
    - "una/varias incorrección(es)" -> "una incorrección" / "varias incorrecciones"
    """
    # Implementación con regex para cada patrón
    ...
```

### config/variables_simples.yaml

```yaml
# Configuración general (opcional)
configuracion:
  secciones_orden:
    - "Información general"
    - "Datos específicos"

# Definición de campos
variables_simples:
  - id: nombre_entidad
    nombre: "Nombre de la entidad"
    tipo: texto
    requerido: true
    placeholder: "Ej: ABC S.A."
    seccion: "Información general"
    ayuda: "Nombre completo de la entidad"

  - id: tipo_documento
    nombre: "Tipo de documento"
    tipo: lista
    opciones:
      - "Informe anual"
      - "Informe trimestral"
      - "Informe especial"
    requerido: true
    seccion: "Información general"

  - id: fecha_emision
    nombre: "Fecha de emisión"
    tipo: fecha
    requerido: true
    seccion: "Datos específicos"
    grupo: fecha_completa  # Agrupa día/mes/año

  - id: observaciones
    nombre: "Observaciones"
    tipo: texto_area
    requerido: false
    seccion: "Datos específicos"
    dependencia:
      variable: tipo_documento
      valor: "Informe especial"  # Solo visible si tipo_documento == "Informe especial"
```

### config/variables_condicionales.yaml

```yaml
variables_condicionales:
  - id: incluir_anexos
    nombre: "¿Incluir anexos?"
    descripcion: "Determina si el informe incluye sección de anexos"
    tipo_control: radio
    seccion: "Configuración"
    opciones:
      - valor: "si"
        etiqueta: "Sí, incluir anexos"
        descripcion: "Se añadirá sección de anexos al final"
        variables_asociadas:
          - numero_anexos
          - descripcion_anexos
      - valor: "no"
        etiqueta: "No incluir anexos"
        es_default: true

  - id: tipo_formato
    nombre: "Formato del informe"
    tipo_control: radio
    opciones:
      - valor: "completo"
        etiqueta: "Formato completo"
        es_default: true
      - valor: "resumido"
        etiqueta: "Formato resumido"
```

### config/bloques_texto.yaml

```yaml
bloques_texto:
  - id: titulo_documento
    descripcion: "Título del documento según tipo"
    reglas:
      - cuando: "tipo_documento == 'Informe anual'"
        plantilla: "INFORME ANUAL DE {{ nombre_entidad }}"
      - cuando: "tipo_documento == 'Informe trimestral'"
        plantilla: "INFORME TRIMESTRAL - {{ nombre_entidad }}"
      - cuando: "True"  # Caso por defecto
        plantilla: "INFORME DE {{ nombre_entidad }}"

  - id: parrafo_introduccion
    descripcion: "Párrafo de introducción"
    reglas:
      - cuando: "tipo_formato == 'completo'"
        plantilla: |
          El presente informe ha sido elaborado por {{ nombre_entidad }}
          con fecha {{ fecha_emision }}. Este documento presenta un análisis
          completo de la situación actual.
      - cuando: "tipo_formato == 'resumido'"
        plantilla: |
          Resumen ejecutivo de {{ nombre_entidad }} - {{ fecha_emision }}.

  - id: seccion_anexos
    descripcion: "Sección de anexos (solo si incluir_anexos == 'si')"
    reglas:
      - cuando: "incluir_anexos == 'si'"
        plantilla: |
          ANEXOS

          A continuación se presentan {{ numero_anexos }} anexos:
          {{ descripcion_anexos }}
      - cuando: "True"
        plantilla: ""  # Vacío si no hay anexos
```

### templates/plantilla.docx

La plantilla Word debe contener variables Jinja2:

```
{{ titulo_documento }}

{{ parrafo_introduccion }}

Información de la entidad:
- Nombre: {{ nombre_entidad }}
- Fecha: {{ fecha_emision }}

{% if observaciones %}
Observaciones:
{{ observaciones }}
{% endif %}

{{ seccion_anexos }}
```

## Dependencias entre Módulos

```
┌─────────────────────────────────────────────────────────────────┐
│                         ui/app.py                               │
└──────────────────────────────┬──────────────────────────────────┘
                               │
       ┌───────────────────────┼───────────────────────┐
       │                       │                       │
       ▼                       ▼                       ▼
┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│ ui/router   │         │core/ui_     │         │core/word_   │
│             │         │runtime      │         │engine       │
└──────┬──────┘         └──────┬──────┘         └──────┬──────┘
       │                       │                       │
       ▼                       ▼                       ▼
┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│core/config_ │         │core/input_  │         │core/xml_    │
│loader       │         │widgets      │         │word_engine  │
└──────┬──────┘         └──────┬──────┘         └─────────────┘
       │                       │
       │                       ▼
       │                ┌─────────────┐
       │                │core/condit- │
       │                │ions_engine  │
       │                └──────┬──────┘
       │                       │
       ▼                       ▼
┌─────────────┐         ┌─────────────┐
│core/schema_ │         │core/utils   │
│models       │◄────────│             │
└─────────────┘         └─────────────┘
       ▲                       ▲
       │                       │
       └───────────────────────┘

Leyenda:
─────── = Dependencia directa
◄────── = Dependencia de validación
```

## Extensibilidad

### Agregar nuevo tipo de campo

1. Modificar `schema_models.py`:
```python
class SimpleField(BaseModel):
    tipo: Literal["texto", "numero", "lista", "fecha", "checkbox", "mi_nuevo_tipo"]
```

2. Agregar widget en `input_widgets.py`:
```python
def render_mi_nuevo_tipo_input(field: SimpleField, current_value: Any) -> Any:
    # Implementación del widget
    pass
```

3. Registrar en `ui_runtime.py`:
```python
WIDGET_RENDERERS = {
    # ...
    "mi_nuevo_tipo": render_mi_nuevo_tipo_input,
}
```

### Agregar nuevo motor de renderizado

1. Crear módulo en `core/`:
```python
# core/mi_motor.py
def render_with_mi_motor(template_path: Path, context: Dict) -> Path:
    # Implementación
    pass
```

2. Integrar en `word_engine.py`:
```python
def render_word_report(template_path, context, output_filename):
    if context.get('_use_mi_motor'):
        from core.mi_motor import render_with_mi_motor
        return render_with_mi_motor(template_path, context)
    # ...
```

## Seguridad

### Evaluación de condiciones

El motor de condiciones usa AST para prevenir inyección de código:

```python
# ✅ Permitido
"tipo_opinion == 'favorable'"
"edad > 18 and activo == True"
"'valor' in lista_valores"

# ❌ Rechazado (no evaluado)
"__import__('os').system('rm -rf /')"
"eval('malicious_code')"
"open('/etc/passwd').read()"
```

### Validación de datos

Todos los datos pasan por validación Pydantic antes de procesarse.

## Rendimiento

### Estrategias de optimización

1. **Carga lazy de plugins**: Los plugins se cargan solo cuando se seleccionan
2. **Caché de configuración**: La configuración se almacena en `session_state`
3. **Procesamiento paralelo**: Los bloques de texto se pueden procesar en paralelo

### Consideraciones de memoria

- Los documentos Word se procesan en memoria
- Para documentos muy grandes, considerar el motor XML con streaming
