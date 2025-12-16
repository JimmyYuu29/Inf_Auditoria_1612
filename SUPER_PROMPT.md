# Super Prompt: Sistema de Generación de Documentos

## Contexto del Sistema

Este es un sistema de generación automática de documentos Word basado en plantillas y configuración YAML. El sistema está diseñado para ser:

- **Modular**: Arquitectura de plugins independientes
- **Configurable**: Todo se define en archivos YAML
- **Seguro**: Evaluación de condiciones sin `eval()`
- **Extensible**: Fácil agregar nuevos tipos de informes

---

## Estructura del Proyecto

```
[NOMBRE_PROYECTO]/
├── core/                           # Núcleo genérico (NO MODIFICAR DIRECTAMENTE)
│   ├── __init__.py                 # Exporta componentes principales
│   ├── config_loader.py            # Carga de manifests y YAML
│   ├── schema_models.py            # Modelos Pydantic de validación
│   ├── conditions_engine.py        # Evaluador seguro de condiciones (AST)
│   ├── word_engine.py              # Motor de renderizado Jinja2/docxtpl
│   ├── xml_word_engine.py          # Motor XML avanzado para Word
│   ├── ui_runtime.py               # Generación dinámica de UI Streamlit
│   ├── input_widgets.py            # Widgets especializados
│   ├── metadata.py                 # Persistencia de metadatos
│   ├── utils.py                    # Utilidades (logging, paths)
│   ├── import_utils.py             # Importación Excel/Word
│   ├── tables_engine.py            # Motor de tablas genérico
│   ├── tp_tables_engine.py         # Tablas especializadas
│   └── tp_tables_ui.py             # UI de tablas especializadas
│
├── ui/                             # Capa de interfaz
│   ├── __init__.py
│   ├── app.py                      # Aplicación Streamlit principal
│   ├── router.py                   # Descubrimiento y carga de plugins
│   └── table_design_ui.py          # UI de diseño de tablas
│
├── reports/                        # Directorio de plugins
│   ├── __init__.py
│   └── [nombre_plugin]/            # Cada plugin es un directorio
│       ├── __init__.py             # Exporta build_context
│       ├── manifest.yaml           # Metadatos del plugin
│       ├── logic.py                # Lógica de negocio
│       ├── config/
│       │   ├── variables_simples.yaml
│       │   ├── variables_condicionales.yaml
│       │   └── bloques_texto.yaml
│       └── templates/
│           └── plantilla.docx
│
├── outputs/                        # Documentos generados
├── metadata/                       # Metadatos guardados (JSON)
├── README.md
├── ARCHITECTURE.md
└── requirements.txt
```

---

## Componentes del Core

### 1. config_loader.py

**Responsabilidad**: Carga y valida archivos de configuración YAML.

**Funciones clave**:
```python
load_manifest(plugin_dir: Path) → Manifest
load_yaml_config(filepath: Path) → Dict
load_simple_fields(config_dir: Path) → List[SimpleField]
load_conditional_variables(config_dir: Path) → List[ConditionalVariable]
load_text_blocks(config_dir: Path) → List[BlockDefinition]
load_plugin_config(plugin_dir: Path) → Dict  # Carga completa
get_fields_by_section(fields: List) → Dict[str, List]
get_general_config(config_dir: Path) → Dict
```

### 2. schema_models.py

**Responsabilidad**: Define modelos Pydantic para validación de datos.

**Modelos principales**:

```python
class Manifest(BaseModel):
    id: str                    # Identificador único del plugin
    nombre: str                # Nombre para mostrar
    version: str               # Versión semántica
    descripcion: Optional[str]
    autor: Optional[str]
    paths: ManifestPaths       # Rutas a template y config

class ManifestPaths(BaseModel):
    template: str              # Ruta relativa a plantilla .docx
    config_dir: str            # Directorio de configuración

class SimpleField(BaseModel):
    id: str                    # Identificador único
    nombre: str                # Etiqueta para UI
    tipo: Literal["texto", "texto_area", "numero", "lista", "fecha", "checkbox"]
    requerido: bool = False
    placeholder: Optional[str]
    opciones: Optional[List[str]]  # Para tipo "lista"
    seccion: Optional[str]     # Agrupación en UI
    ayuda: Optional[str]       # Texto de ayuda
    grupo: Optional[str]       # Grupo de fecha (día/mes/año)
    dependencia: Optional[FieldDependency]
    ambito: Literal["global", "local"] = "global"

class FieldDependency(BaseModel):
    variable: str              # ID de variable padre
    valor: Optional[str]       # Mostrar si padre == valor
    valor_no: Optional[str]    # Mostrar si padre != valor_no

class ConditionalVariable(BaseModel):
    id: str
    nombre: str
    descripcion: Optional[str]
    tipo_control: Literal["radio", "checkbox", "derivado"]
    seccion: Optional[str]
    opciones: List[ConditionalOption]
    dependencia: Optional[FieldDependency]

class ConditionalOption(BaseModel):
    valor: str                 # Valor interno
    etiqueta: str              # Texto mostrado
    descripcion: Optional[str]
    es_default: bool = False
    variables_asociadas: Optional[List[str]]  # IDs de campos dependientes

class BlockDefinition(BaseModel):
    id: str                    # Identificador para plantilla
    descripcion: Optional[str]
    reglas: List[BlockRule]

class BlockRule(BaseModel):
    cuando: str                # Expresión de condición Python
    plantilla: str             # Template Jinja2
```

### 3. conditions_engine.py

**Responsabilidad**: Evaluación segura de expresiones condicionales usando AST.

**Función principal**:
```python
def evaluate_condition(condition: str, context: Dict[str, Any]) -> bool
```

**Operadores soportados**:
- Comparación: `==`, `!=`, `<`, `>`, `<=`, `>=`, `in`, `not in`
- Lógicos: `and`, `or`, `not`
- Paréntesis: `()`
- Literales: strings, números, booleanos, listas, None

**Ejemplos válidos**:
```python
"tipo_opinion == 'favorable'"
"edad >= 18 and activo == True"
"'opcion1' in lista_opciones"
"not es_borrador and (tipo == 'A' or tipo == 'B')"
```

### 4. word_engine.py

**Responsabilidad**: Renderizado de documentos Word.

**Funciones principales**:
```python
render_word_report(template_path: Path, context: Dict, output_filename: str) → Path
render_template_string(template_content: str, context: Dict) → str
```

**Motores disponibles**:
1. **Motor Jinja2/docxtpl** (por defecto): Variables `{{ variable }}`
2. **Motor XML**: Variables `<<variable>>`, activado con `context['_use_xml_engine'] = True`

### 5. ui_runtime.py

**Responsabilidad**: Generación dinámica de controles Streamlit.

**Funciones principales**:
```python
render_field(field: SimpleField, session_state: Dict) → Any
render_conditional_variable(var: ConditionalVariable, current_value: Any) → Any
validate_form_data(fields: List, data: Dict) → Tuple[bool, List[str]]
render_section_fields(section_name: str, fields: List, context: Dict) → Dict
should_show_field_in_ui(field: SimpleField, context: Dict) → bool
identify_date_groups(fields: List) → Dict
```

### 6. metadata.py

**Responsabilidad**: Persistencia de metadatos de informes generados.

**Modelo**:
```python
class ReportMetadata(BaseModel):
    id: str                    # UUID
    report_id: str             # ID del plugin
    report_name: str
    timestamp: datetime
    template_version: str
    input_data: Dict           # Datos del formulario
    output_path: str
    output_filename: str
    generated_by: str
    description: Optional[str]
```

**Funciones**:
```python
create_metadata(...) → ReportMetadata
save_metadata(meta: ReportMetadata) → None
load_all_metadata() → List[ReportMetadata]
load_metadata_by_report_id(report_id: str) → List[ReportMetadata]
get_metadata_summary(meta: ReportMetadata) → str
```

---

## Archivos de Configuración YAML

### variables_simples.yaml

Define los campos de entrada del usuario.

```yaml
# Configuración general (opcional)
configuracion:
  secciones_orden:
    - "Sección 1"
    - "Sección 2"
    - "Sección 3"

# Definición de campos
variables_simples:
  # Campo de texto simple
  - id: nombre_entidad
    nombre: "Nombre de la entidad"
    tipo: texto
    requerido: true
    placeholder: "Ej: ABC S.A."
    seccion: "Sección 1"
    ayuda: "Nombre legal completo"

  # Campo de área de texto
  - id: descripcion
    nombre: "Descripción"
    tipo: texto_area
    requerido: false
    seccion: "Sección 1"

  # Campo numérico
  - id: cantidad
    nombre: "Cantidad"
    tipo: numero
    requerido: true
    placeholder: "0"
    seccion: "Sección 2"

  # Campo de lista/select
  - id: tipo_documento
    nombre: "Tipo de documento"
    tipo: lista
    opciones:
      - "Opción A"
      - "Opción B"
      - "Opción C"
    requerido: true
    seccion: "Sección 2"

  # Grupo de fecha (día/mes/año se combinan)
  - id: dia_fecha
    nombre: "Día"
    tipo: numero
    grupo: fecha_completa
    seccion: "Sección 3"
  - id: mes_fecha
    nombre: "Mes"
    tipo: texto
    grupo: fecha_completa
    seccion: "Sección 3"
  - id: ano_fecha
    nombre: "Año"
    tipo: numero
    grupo: fecha_completa
    seccion: "Sección 3"

  # Campo con dependencia
  - id: detalle_opcion_b
    nombre: "Detalle de opción B"
    tipo: texto
    seccion: "Sección 2"
    dependencia:
      variable: tipo_documento
      valor: "Opción B"  # Solo visible si tipo_documento == "Opción B"

  # Campo checkbox
  - id: acepto_terminos
    nombre: "Acepto los términos"
    tipo: checkbox
    requerido: true
    seccion: "Sección 3"

  # Campo local (vinculado a variable condicional)
  - id: campo_local
    nombre: "Campo local"
    tipo: texto
    ambito: local
    seccion: "Variables locales"
```

### variables_condicionales.yaml

Define controles que afectan la lógica del documento.

```yaml
variables_condicionales:
  # Control tipo radio
  - id: tipo_informe
    nombre: "Tipo de informe"
    descripcion: "Selecciona el tipo de informe a generar"
    tipo_control: radio
    seccion: "Configuración principal"
    opciones:
      - valor: "completo"
        etiqueta: "Informe completo"
        descripcion: "Incluye todas las secciones"
        es_default: true
      - valor: "resumido"
        etiqueta: "Informe resumido"
        descripcion: "Solo secciones principales"
      - valor: "detallado"
        etiqueta: "Informe detallado"
        descripcion: "Incluye anexos adicionales"
        variables_asociadas:
          - numero_anexos
          - descripcion_anexos

  # Control tipo checkbox
  - id: incluir_graficos
    nombre: "¿Incluir gráficos?"
    tipo_control: checkbox
    seccion: "Opciones adicionales"
    opciones:
      - valor: "si"
        etiqueta: "Sí"
        variables_asociadas:
          - tipo_graficos
      - valor: "no"
        etiqueta: "No"
        es_default: true

  # Control con dependencia
  - id: subtipo_detallado
    nombre: "Subtipo de informe detallado"
    tipo_control: radio
    seccion: "Configuración principal"
    dependencia:
      variable: tipo_informe
      valor: "detallado"  # Solo visible si tipo_informe == "detallado"
    opciones:
      - valor: "financiero"
        etiqueta: "Enfoque financiero"
        es_default: true
      - valor: "operativo"
        etiqueta: "Enfoque operativo"
```

### bloques_texto.yaml

Define bloques de texto condicionales para la plantilla.

```yaml
bloques_texto:
  # Bloque simple con múltiples reglas
  - id: titulo_documento
    descripcion: "Título según tipo de informe"
    reglas:
      - cuando: "tipo_informe == 'completo'"
        plantilla: "INFORME COMPLETO DE {{ nombre_entidad }}"
      - cuando: "tipo_informe == 'resumido'"
        plantilla: "RESUMEN EJECUTIVO - {{ nombre_entidad }}"
      - cuando: "tipo_informe == 'detallado'"
        plantilla: "INFORME DETALLADO DE {{ nombre_entidad }} - Versión {{ subtipo_detallado }}"
      - cuando: "True"  # Caso por defecto
        plantilla: "INFORME DE {{ nombre_entidad }}"

  # Bloque con Jinja2 complejo
  - id: parrafo_introduccion
    descripcion: "Párrafo de introducción"
    reglas:
      - cuando: "tipo_informe == 'completo'"
        plantilla: |
          El presente informe ha sido elaborado por {{ nombre_entidad }}
          con fecha {{ dia_fecha }} de {{ mes_fecha }} de {{ ano_fecha }}.

          Este documento presenta un análisis completo de la situación,
          incluyendo {{ cantidad }} elementos analizados.
      - cuando: "tipo_informe == 'resumido'"
        plantilla: |
          Resumen ejecutivo de {{ nombre_entidad }}.
          Fecha: {{ dia_fecha }}/{{ mes_fecha }}/{{ ano_fecha }}.
      - cuando: "True"
        plantilla: "Informe preparado para {{ nombre_entidad }}."

  # Bloque condicional (puede ser vacío)
  - id: seccion_anexos
    descripcion: "Sección de anexos (solo en informe detallado)"
    reglas:
      - cuando: "tipo_informe == 'detallado'"
        plantilla: |
          ANEXOS

          Se adjuntan {{ numero_anexos }} anexos con información adicional:
          {{ descripcion_anexos }}
      - cuando: "True"
        plantilla: ""  # Vacío para otros tipos

  # Bloque con condiciones compuestas
  - id: nota_especial
    descripcion: "Nota especial según múltiples condiciones"
    reglas:
      - cuando: "tipo_informe == 'detallado' and subtipo_detallado == 'financiero'"
        plantilla: |
          NOTA: Este informe incluye análisis financiero detallado.
          Los datos han sido verificados según normativa vigente.
      - cuando: "tipo_informe == 'detallado' and subtipo_detallado == 'operativo'"
        plantilla: |
          NOTA: Este informe incluye análisis operativo detallado.
          Se han evaluado {{ cantidad }} procesos operativos.
      - cuando: "incluir_graficos == 'si'"
        plantilla: |
          Este documento incluye representaciones gráficas
          de tipo {{ tipo_graficos }}.
      - cuando: "True"
        plantilla: ""

  # Bloque con acceso a variables auxiliares
  - id: pie_documento
    descripcion: "Pie del documento"
    reglas:
      - cuando: "True"
        plantilla: |
          {{ nombre_entidad }}
          Generado el {{ dia_fecha }} de {{ mes_fecha }} de {{ ano_fecha }}
          {% if descripcion %}
          Observaciones: {{ descripcion }}
          {% endif %}
```

---

## Plugin: logic.py

Cada plugin debe implementar la función `build_context()`.

```python
"""
Plugin Logic - Motor de contexto para [NOMBRE DEL INFORME]

Este módulo implementa la lógica de negocio del plugin:
- Carga archivos YAML de configuración
- Evalúa condiciones de cada bloque de texto
- Renderiza plantillas Jinja2
- Construye el contexto final para la plantilla Word
"""

import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from jinja2 import Environment, BaseLoader
import logging

# Importar el evaluador de condiciones del core
from core.conditions_engine import evaluate_condition

logger = logging.getLogger(__name__)


class BloquesTextoProcessor:
    """
    Procesador de bloques de texto condicionales.

    Lee la configuración YAML, evalúa condiciones y renderiza plantillas.
    """

    def __init__(self, config_dir: Optional[Path] = None):
        """
        Args:
            config_dir: Directorio de archivos YAML de configuración.
        """
        self.config_dir = config_dir or Path(__file__).parent / "config"
        self.jinja_env = Environment(loader=BaseLoader())
        self.bloques_texto: List[Dict] = []
        self._load_config()

    def _load_config(self) -> None:
        """Carga archivos bloques_texto*.yaml del directorio de configuración."""
        yaml_files = list(self.config_dir.glob("bloques_texto*.yaml"))

        for yaml_file in sorted(yaml_files):
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    content = yaml.safe_load(f)
                    if content and 'bloques_texto' in content:
                        self.bloques_texto.extend(content['bloques_texto'])
            except Exception as e:
                logger.error(f"Error cargando {yaml_file}: {e}")

    def _evaluar_condicion(self, condicion: str, contexto: Dict[str, Any]) -> bool:
        """Evalúa una condición usando el motor seguro del core."""
        return evaluate_condition(condicion, contexto)

    def _renderizar_plantilla(self, plantilla: str, contexto: Dict[str, Any]) -> str:
        """Renderiza una plantilla Jinja2."""
        try:
            template = self.jinja_env.from_string(plantilla)
            return template.render(**contexto).strip()
        except Exception as e:
            logger.error(f"Error renderizando plantilla: {e}")
            return ""

    def procesar_bloque(self, bloque: Dict, contexto: Dict[str, Any]) -> str:
        """
        Procesa un bloque de texto evaluando sus reglas en orden.

        La primera regla cuya condición sea True se utiliza.
        """
        reglas = bloque.get('reglas', [])

        for regla in reglas:
            condicion = regla.get('cuando', 'True')
            plantilla = regla.get('plantilla', '')

            if self._evaluar_condicion(condicion, contexto):
                return self._renderizar_plantilla(plantilla, contexto)

        return ""

    def procesar_todos(self, contexto: Dict[str, Any]) -> Dict[str, str]:
        """Procesa todos los bloques y devuelve diccionario id→texto."""
        resultados = {}
        for bloque in self.bloques_texto:
            bloque_id = bloque.get('id')
            if bloque_id:
                resultados[bloque_id] = self.procesar_bloque(bloque, contexto)
        return resultados


def calcular_variables_auxiliares(data_in: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calcula variables auxiliares derivadas de los datos de entrada.

    Estas variables simplifican las plantillas evitando lógica repetitiva.

    Args:
        data_in: Datos de entrada del usuario

    Returns:
        Diccionario con variables auxiliares calculadas
    """
    aux = {}

    # Ejemplo: Calcular nombre completo
    nombre = data_in.get('nombre_entidad', '')
    tipo = data_in.get('tipo_documento', '')

    aux['nombre_completo'] = f"{nombre} ({tipo})" if tipo else nombre

    # Ejemplo: Calcular año anterior
    ano = data_in.get('ano_fecha')
    if ano:
        aux['ano_anterior'] = ano - 1

    # Ejemplo: Calcular texto según condición
    if data_in.get('tipo_informe') == 'detallado':
        aux['texto_tipo'] = 'análisis detallado'
    else:
        aux['texto_tipo'] = 'análisis general'

    return aux


def build_context(data_in: Dict[str, Any], config_dir: Optional[Path] = None) -> Dict[str, Any]:
    """
    Construye el contexto completo para la plantilla Word.

    Esta es la función principal del plugin que:
    1. Toma los datos de entrada del usuario
    2. Calcula las variables auxiliares
    3. Procesa todos los bloques de texto condicionales
    4. Devuelve un contexto unificado para Jinja2

    Args:
        data_in: Diccionario con valores del formulario
        config_dir: Directorio de configuración (opcional)

    Returns:
        Diccionario con todas las variables listas para la plantilla
    """
    # 1. Iniciar con los datos de entrada
    context = dict(data_in)

    # 2. Calcular variables auxiliares
    auxiliares = calcular_variables_auxiliares(data_in)
    context.update(auxiliares)

    # 3. Procesar todos los bloques de texto
    processor = BloquesTextoProcessor(config_dir)
    bloques_renderizados = processor.procesar_todos(context)
    context.update(bloques_renderizados)

    logger.info(f"Contexto construido con {len(context)} variables")
    return context
```

---

## Plantilla Word (.docx)

La plantilla usa sintaxis Jinja2 para variables y control de flujo.

### Variables simples
```
{{ nombre_variable }}
```

### Bloques condicionales en plantilla
```
{% if condicion %}
Texto condicional
{% endif %}

{% if var == 'valor1' %}
Texto para valor1
{% elif var == 'valor2' %}
Texto para valor2
{% else %}
Texto por defecto
{% endif %}
```

### Bucles
```
{% for item in lista %}
- {{ item }}
{% endfor %}
```

### Ejemplo de plantilla completa

```
{{ titulo_documento }}

INFORMACIÓN GENERAL

Entidad: {{ nombre_entidad }}
Fecha: {{ dia_fecha }} de {{ mes_fecha }} de {{ ano_fecha }}
Tipo de documento: {{ tipo_documento }}

{{ parrafo_introduccion }}

{% if descripcion %}
OBSERVACIONES
{{ descripcion }}
{% endif %}

{{ seccion_anexos }}

{{ nota_especial }}

---

{{ pie_documento }}
```

---

## Flujo de Ejecución

```
1. Usuario abre aplicación Streamlit
   └── ui/app.py → init_session_state()

2. Selección de plugin
   └── ui/router.py → list_available_reports()
   └── ui/router.py → load_report_plugin()
       └── core/config_loader.py → load_plugin_config()

3. Renderizado de formulario
   └── core/ui_runtime.py → render_field() para cada campo
   └── core/ui_runtime.py → render_conditional_variable()

4. Usuario completa formulario y genera

5. Validación
   └── core/ui_runtime.py → validate_form_data()

6. Construcción de contexto
   └── reports/[plugin]/logic.py → build_context()
       └── calcular_variables_auxiliares()
       └── BloquesTextoProcessor.procesar_todos()
           └── core/conditions_engine.py → evaluate_condition()
           └── Jinja2 → render template strings

7. Renderizado de documento
   └── core/word_engine.py → render_word_report()
       └── docxtpl o xml_word_engine

8. Guardado de metadatos
   └── core/metadata.py → save_metadata()

9. Descarga de documento
   └── Streamlit download_button
```

---

## Notas de Implementación

### Seguridad

- **Nunca usar `eval()`**: El motor de condiciones usa AST
- **Validar todos los datos**: Pydantic valida estructura de YAML
- **Sanitizar nombres de archivo**: `utils.safe_filename()`

### Extensibilidad

Para agregar un nuevo plugin:

1. Crear directorio `reports/mi_plugin/`
2. Crear `manifest.yaml` con metadatos
3. Crear `logic.py` con función `build_context()`
4. Crear archivos YAML en `config/`
5. Crear plantilla Word en `templates/`

### Depuración

- Logs en cada módulo vía `utils.setup_logger()`
- Los bloques de texto registran qué condición se cumplió
- Los metadatos guardan los datos de entrada para reproducir

### Mejores prácticas

1. Mantener bloques de texto pequeños y específicos
2. Usar variables auxiliares para cálculos repetitivos
3. Organizar campos por secciones lógicas
4. Documentar cada bloque con `descripcion`
5. Incluir siempre una regla `cuando: "True"` como fallback

---

## Ejemplo Completo de Plugin Mínimo

### reports/mi_informe/__init__.py
```python
from .logic import build_context
__all__ = ["build_context"]
```

### reports/mi_informe/manifest.yaml
```yaml
id: mi_informe
nombre: Mi Informe
version: "1.0.0"
descripcion: Informe de ejemplo
autor: Tu Nombre
paths:
  template: templates/plantilla.docx
  config_dir: config
```

### reports/mi_informe/config/variables_simples.yaml
```yaml
variables_simples:
  - id: titulo
    nombre: "Título"
    tipo: texto
    requerido: true
    seccion: "General"
  - id: contenido
    nombre: "Contenido"
    tipo: texto_area
    seccion: "General"
```

### reports/mi_informe/config/variables_condicionales.yaml
```yaml
variables_condicionales:
  - id: formato
    nombre: "Formato"
    tipo_control: radio
    seccion: "Configuración"
    opciones:
      - valor: "formal"
        etiqueta: "Formal"
        es_default: true
      - valor: "informal"
        etiqueta: "Informal"
```

### reports/mi_informe/config/bloques_texto.yaml
```yaml
bloques_texto:
  - id: saludo
    reglas:
      - cuando: "formato == 'formal'"
        plantilla: "Estimado/a:"
      - cuando: "True"
        plantilla: "Hola:"
```

### reports/mi_informe/logic.py
```python
from pathlib import Path
from typing import Dict, Any
from core.conditions_engine import evaluate_condition
from jinja2 import Environment, BaseLoader
import yaml

def build_context(data_in: Dict[str, Any], config_dir: Path) -> Dict[str, Any]:
    context = dict(data_in)

    # Cargar y procesar bloques
    yaml_path = config_dir / "bloques_texto.yaml"
    with open(yaml_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    jinja_env = Environment(loader=BaseLoader())

    for bloque in config.get('bloques_texto', []):
        for regla in bloque.get('reglas', []):
            if evaluate_condition(regla['cuando'], context):
                template = jinja_env.from_string(regla['plantilla'])
                context[bloque['id']] = template.render(**context)
                break

    return context
```

### reports/mi_informe/templates/plantilla.docx
```
{{ titulo }}

{{ saludo }}

{{ contenido }}
```

---

Este documento proporciona una guía completa para entender, mantener y extender el sistema de generación de documentos.
