# Plataforma de Generación de Informes

Sistema modular para generación automática de documentos basados en plantillas Word, configuraciones YAML y lógica Python.

## Descripción

Esta plataforma permite crear aplicaciones de generación de documentos altamente configurables. Utiliza:

- **Plantillas Word (.docx)** con variables Jinja2 (`{{ variable }}`)
- **Configuraciones YAML** para definir campos, condiciones y bloques de texto
- **Motor de condiciones** basado en AST para evaluación segura de expresiones
- **Interfaz Streamlit** dinámica que se adapta a cada plugin

## Estructura del Proyecto

```
Inf_Auditoria_1612/
├── core/                           # Núcleo genérico de la plataforma
│   ├── config_loader.py            # Carga de manifests y YAML
│   ├── schema_models.py            # Modelos Pydantic de validación
│   ├── conditions_engine.py        # Evaluador seguro de condiciones
│   ├── word_engine.py              # Renderizado con Jinja2
│   ├── xml_word_engine.py          # Motor XML avanzado para Word
│   ├── ui_runtime.py               # Generación dinámica de UI
│   ├── input_widgets.py            # Widgets de Streamlit
│   ├── metadata.py                 # Persistencia de metadatos
│   ├── utils.py                    # Utilidades generales
│   ├── import_utils.py             # Importación desde Excel/Word
│   ├── tables_engine.py            # Motor de tablas
│   ├── tp_tables_engine.py         # Tablas de precios de transferencia
│   └── tp_tables_ui.py             # UI de tablas especializadas
├── ui/                             # Capa de interfaz de usuario
│   ├── app.py                      # Aplicación principal Streamlit
│   ├── router.py                   # Enrutador de plugins
│   └── table_design_ui.py          # UI de diseño de tablas
├── reports/                        # Directorio de plugins
│   └── informe_auditoria/          # Plugin de informe de auditoría
│       ├── manifest.yaml           # Metadatos del plugin
│       ├── logic.py                # Lógica de negocio
│       ├── config/                 # Archivos de configuración
│       │   ├── variables_simples.yaml
│       │   ├── variables_condicionales.yaml
│       │   └── bloques_texto.yaml
│       └── templates/              # Plantillas Word
│           └── plantilla_informe.docx
├── outputs/                        # Documentos generados
└── metadata/                       # Metadatos guardados
```

## Instalación

### Requisitos

- Python >= 3.11
- pip

### Dependencias

```bash
pip install streamlit pyyaml jinja2 python-docx pydantic lxml pandas openpyxl
```

### Instalación completa

```bash
# Clonar el repositorio
git clone <url-del-repositorio>
cd Inf_Auditoria_1612

# Crear entorno virtual (recomendado)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Instalar dependencias
pip install -r requirements.txt
```

## Uso

### Ejecutar la aplicación

```bash
cd Inf_Auditoria_1612
streamlit run ui/app.py
```

La aplicación se abrirá en `http://localhost:8501`

### Flujo de trabajo

1. **Seleccionar plugin**: Elige el tipo de informe en el menú lateral
2. **Completar formulario**: Rellena los campos organizados por pestañas
3. **Configurar condiciones**: Ajusta las variables condicionales
4. **Generar informe**: Haz clic en "Generar Informe"
5. **Descargar**: Descarga el documento Word generado

## Crear un nuevo plugin

1. Crear directorio en `reports/`:
   ```
   reports/mi_nuevo_informe/
   ├── manifest.yaml
   ├── logic.py
   ├── config/
   │   ├── variables_simples.yaml
   │   ├── variables_condicionales.yaml
   │   └── bloques_texto.yaml
   └── templates/
       └── plantilla.docx
   ```

2. Definir `manifest.yaml`:
   ```yaml
   id: mi_nuevo_informe
   nombre: Mi Nuevo Informe
   version: "1.0.0"
   descripcion: Descripción del informe
   autor: Tu Nombre
   paths:
     template: templates/plantilla.docx
     config_dir: config
   ```

3. Implementar `logic.py` con función `build_context()`:
   ```python
   def build_context(data_in: dict, config_dir: Path) -> dict:
       # Procesar datos y devolver contexto para plantilla
       return context
   ```

4. Crear archivos YAML de configuración y plantilla Word

## Archivos de configuración YAML

### variables_simples.yaml

Define los campos de entrada del usuario:

```yaml
variables_simples:
  - id: nombre_entidad
    nombre: "Nombre de la entidad"
    tipo: texto
    requerido: true
    placeholder: "Ej: ABC S.A."
    seccion: "Información general"
    ayuda: "Nombre completo de la entidad"
```

**Tipos soportados**: `texto`, `texto_area`, `numero`, `lista`, `fecha`, `checkbox`

### variables_condicionales.yaml

Define controles de lógica condicional:

```yaml
variables_condicionales:
  - id: tipo_opinion
    nombre: "Tipo de opinión"
    tipo_control: radio
    opciones:
      - valor: "favorable"
        etiqueta: "Opinión favorable"
        es_default: true
      - valor: "salvedades"
        etiqueta: "Con salvedades"
        variables_asociadas: [motivo_salvedades, num_salvedades]
      - valor: "desfavorable"
        etiqueta: "Opinión desfavorable"
        variables_asociadas: [descripcion_desfavorable, num_desfavorables]
```

### Soporte Multi-Issue (Múltiples Cuestiones)

Para opiniones con salvedades o desfavorables, el sistema soporta múltiples cuestiones:

```yaml
# En variables_simples.yaml - campos locales
- id: num_salvedades
  nombre: "Número de salvedades"
  tipo: numero
  min: 1
  max: 10
  ambito: local
  condicion_padre: "tipo_opinion == 'salvedades'"

- id: num_desfavorables
  nombre: "Número de cuestiones (desfavorable)"
  tipo: numero
  min: 1
  max: 10
  ambito: local
  condicion_padre: "tipo_opinion == 'desfavorable'"
```

**Características:**
- Cuando N > 1, se renderizan N expanders colapsados en la UI
- Cada expander contiene un conjunto completo de campos
- Los valores se almacenan con claves compuestas: `salvedad_1__numero_nota`, `salvedad_2__numero_nota`, etc.
- La generación de Word produce N párrafos en `parrafo_fundamento_calificacion`
- El sistema convierte automáticamente marcadores de plural: `la(s)` → `la`/`las`, `cuestión(es)` → `cuestión`/`cuestiones`

### bloques_texto.yaml

Define bloques de texto condicionales:

```yaml
bloques_texto:
  - id: parrafo_opinion
    descripcion: "Párrafo de opinión"
    reglas:
      - cuando: "tipo_opinion == 'favorable'"
        plantilla: "En nuestra opinión, las cuentas anuales..."
      - cuando: "True"
        plantilla: "Texto por defecto..."
```

## API del Core

### Evaluación de condiciones

```python
from core.conditions_engine import evaluate_condition

resultado = evaluate_condition("tipo_opinion == 'favorable'", context)
```

### Renderizado de documentos

```python
from core.word_engine import render_word_report

output_path = render_word_report(template_path, context, "nombre_archivo")
```

### Carga de configuración

```python
from core.config_loader import load_plugin_config

config = load_plugin_config(plugin_dir)
```

## Licencia

MIT License - Ver archivo LICENSE para más detalles.

## Autor

Jimmy - Forvis Mazars España

## Versión

1.0.0
