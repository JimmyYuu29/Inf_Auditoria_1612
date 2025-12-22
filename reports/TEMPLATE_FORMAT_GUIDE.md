# Guía de Formato de Plantillas YAML para Nuevos Proyectos

## Versión: 2.0
## Fecha: Diciembre 2025
## Objetivo: Estandarización de formatos YAML para compatibilidad con UI unificada

---

## Índice

1. [Introducción](#introducción)
2. [Estructura de Archivos](#estructura-de-archivos)
3. [Formato de variables_simples.yaml](#formato-de-variables_simplesyaml)
4. [Formato de variables_condicionales.yaml](#formato-de-variables_condicionalesyaml)
5. [Formato de bloques_texto.yaml](#formato-de-bloques_textoyaml)
6. [Ejemplos Completos](#ejemplos-completos)
7. [Migración de Proyectos Existentes](#migración-de-proyectos-existentes)

---

## Introducción

Este documento define el formato estándar para la configuración YAML de nuevos informes en la plataforma. El objetivo es garantizar la compatibilidad con la interfaz de usuario unificada y facilitar el mantenimiento.

### Proyectos de Referencia

- **informe_auditoria**: Implementación de referencia completa
- **transferencia_precio**: Ejemplo de migración desde formato antiguo

---

## Estructura de Archivos

Cada proyecto de informe debe contener los siguientes archivos YAML en su carpeta `config/`:

```
reports/
└── [nombre_proyecto]/
    ├── config/
    │   ├── variables_simples.yaml       # Definición de variables de entrada
    │   ├── variables_condicionales.yaml # Definición de condiciones lógicas
    │   ├── bloques_texto.yaml          # Definición de bloques de texto condicionales
    │   └── tablas.yaml                 # (Opcional) Definición de tablas
    ├── template.docx                    # Plantilla Word del informe
    └── manifest.yaml                    # Metadatos del proyecto
```

---

## Formato de variables_simples.yaml

### Estructura General

```yaml
# Variables Simples - [Nombre del Sistema]
# Configuración de variables que el usuario debe completar
# Versión: 2.0 - Estandarizada para compatibilidad con UI unificada

variables_simples:

  # ==================== [CATEGORÍA DE VARIABLES] ====================

  - id: nombre_variable
    nombre: "Nombre descriptivo para el usuario"
    tipo: texto | texto_largo | numero | lista
    requerido: true | false
    placeholder: "Texto de ejemplo"
    seccion: "Nombre de la sección en UI"
    ayuda: "Texto de ayuda para el usuario (opcional)"
    grupo: nombre_grupo  # (opcional) para agrupar variables relacionadas

# ==================== CONFIGURACIÓN GENERAL ====================

configuracion:
  version: "2.0"
  compatible_con: "informe_auditoria"

  validaciones:
    - tipo: "campos_requeridos"
      mensaje: "Todos los campos marcados como requeridos deben completarse"

  secciones_orden:
    - "Sección 1"
    - "Sección 2"

  marcadores:  # (opcional) para compatibilidad con plantillas existentes
    nombre_variable: "<<Marcador en plantilla Word>>"
```

### Tipos de Variables Soportados

| Tipo | Descripción | Ejemplo UI |
|------|-------------|------------|
| `texto` | Campo de texto corto | Input de una línea |
| `texto_largo` | Campo de texto largo | Textarea multilínea |
| `numero` | Campo numérico | Input numérico |
| `lista` | Selección de opciones | Dropdown/Select |
| `email` | Campo de correo electrónico | Input con validación email |

### Ejemplo Completo

```yaml
variables_simples:

  - id: nombre_entidad
    nombre: "Nombre de la entidad"
    tipo: texto
    requerido: true
    placeholder: "Ej: ABC Sociedad Anónima"
    seccion: "Información de la entidad"
    ayuda: "Nombre legal completo de la entidad"

  - id: ejercicio_fiscal
    nombre: "Ejercicio fiscal"
    tipo: numero
    requerido: true
    placeholder: "2024"
    seccion: "Información general"

  - id: descripcion_actividad
    nombre: "Descripción de la actividad"
    tipo: texto_largo
    requerido: true
    placeholder: "Descripción detallada..."
    seccion: "Información de la entidad"

  - id: tipo_informe
    nombre: "Tipo de informe"
    tipo: lista
    requerido: true
    seccion: "Información general"
    opciones:
      - "Informe estándar"
      - "Informe especial"
      - "Informe resumido"
```

---

## Formato de variables_condicionales.yaml

### Estructura General

```yaml
# Variables Condicionales - [Nombre del Sistema]
# Define todas las condiciones que modifican el contenido del informe
# Versión: 2.0 - Estandarizada para compatibilidad con UI unificada

variables_condicionales:

  # ==================== CONDICIÓN: [NOMBRE DESCRIPTIVO] ====================

  - id: nombre_condicion
    nombre: "Nombre descriptivo para el usuario"
    descripcion: "Explicación detallada del propósito"
    tipo_control: radio
    requerido: true | false
    seccion: "Nombre de la sección en UI"
    opciones:
      - valor: "opcion1"
        etiqueta: "Etiqueta visible para el usuario"
        descripcion: "Descripción de esta opción"
        es_default: true | false  # (opcional) marca la opción por defecto

      - valor: "opcion2"
        etiqueta: "Otra opción"
        descripcion: "Descripción de la segunda opción"
        variables_asociadas:  # (opcional) variables que se muestran solo con esta opción
          - variable_dependiente_1
          - variable_dependiente_2

    dependencia:  # (opcional) muestra esta condición solo si se cumple
      variable: otra_condicion
      valor: "valor_esperado"

# ==================== CONFIGURACIÓN GENERAL ====================

configuracion:
  version: "2.0"
  motor_condicional: "Jinja2"
  compatible_con: "informe_auditoria"

  sintaxis_jinja2:
    inicio_condicion: "{% if"
    fin_condicion: "{% endif %}"
    else: "{% else %}"
    elif: "{% elif"

  marcadores:  # (opcional) para compatibilidad
    nombre_condicion: "<<Marcador en plantilla>>"
```

### Ejemplo Completo

```yaml
variables_condicionales:

  - id: tipo_opinion
    nombre: "Tipo de opinión de auditoría"
    descripcion: "Determina la naturaleza de la opinión del auditor"
    tipo_control: radio
    requerido: true
    seccion: "Opinión de auditoría"
    opciones:
      - valor: "favorable"
        etiqueta: "Opinión favorable (limpia)"
        descripcion: "Las cuentas expresan la imagen fiel sin salvedades"
        es_default: true

      - valor: "salvedades"
        etiqueta: "Opinión con salvedades"
        descripcion: "Excepto por ciertos aspectos"
        variables_asociadas:
          - descripcion_salvedades
          - numero_nota_salvedades

      - valor: "desfavorable"
        etiqueta: "Opinión desfavorable"
        descripcion: "Las cuentas no expresan la imagen fiel"

  - id: incluir_anexos
    nombre: "¿Incluir anexos adicionales?"
    descripcion: "Permite agregar documentación adicional al informe"
    tipo_control: radio
    requerido: false
    seccion: "Configuración del informe"
    opciones:
      - valor: "si"
        etiqueta: "Sí, incluir anexos"

      - valor: "no"
        etiqueta: "No incluir anexos"
        es_default: true
```

---

## Formato de bloques_texto.yaml

### Estructura General

```yaml
# ==============================================================================
# BLOQUES DE TEXTO CONDICIONALES - [Nombre del Sistema]
# ==============================================================================
# Este archivo define todos los bloques de texto que dependen de condiciones.
# Versión: 2.0 - Compatible con sistema unificado
# ==============================================================================

bloques_texto:

  - id: nombre_bloque
    descripcion: "Propósito del bloque de texto"
    reglas:
      - cuando: "condicion_python_evaluable"
        plantilla: |
          Texto con variables Jinja2: {{ variable_simple }}
          Puede ser multilínea.
        marcador: "<<Marcador en Word>>"  # (opcional)

      - cuando: "condicion_python_evaluable"
        documento: "ruta/al/documento.docx"  # (opcional) para incluir contenido de archivo
        marcador: "<<Marcador en Word>>"

      - cuando: "True"  # default / fallback
        plantilla: ""

# ==============================================================================
# CONFIGURACIÓN DEL MOTOR DE BLOQUES
# ==============================================================================

configuracion_bloques:
  version: "2.0"
  esquema: "A - Lógica externa"
  compatible_con: "informe_auditoria"

  evaluador:
    tipo: "python_eval"
    contexto_requerido:
      - variable_condicional_1
      - variable_condicional_2

  orden_evaluacion: "primera_coincidente"
  valor_default: ""
```

### Ejemplo Completo

```yaml
bloques_texto:

  - id: parrafo_opinion
    descripcion: "Párrafo de opinión según el tipo seleccionado"
    reglas:
      - cuando: "tipo_opinion == 'favorable'"
        plantilla: |
          En nuestra opinión, las cuentas anuales de {{ nombre_entidad }} expresan,
          en todos los aspectos significativos, la imagen fiel del patrimonio y de la
          situación financiera a {{ fecha_cierre }}.
        marcador: "<<Párrafo opinión>>"

      - cuando: "tipo_opinion == 'salvedades'"
        plantilla: |
          En nuestra opinión, excepto por los efectos de las cuestiones descritas
          en {{ descripcion_salvedades }}, las cuentas anuales de {{ nombre_entidad }}
          expresan la imagen fiel.
        marcador: "<<Párrafo opinión>>"

      - cuando: "tipo_opinion == 'desfavorable'"
        plantilla: |
          En nuestra opinión, debido a la significatividad de las cuestiones descritas,
          las cuentas anuales NO expresan la imagen fiel.
        marcador: "<<Párrafo opinión>>"

      - cuando: "True"
        plantilla: ""

  - id: seccion_anexos
    descripcion: "Sección de anexos si se incluyen"
    reglas:
      - cuando: "incluir_anexos == 'si'"
        documento: "anexos/anexo_template.docx"
        marcador: "<<Sección anexos>>"

      - cuando: "True"
        plantilla: ""
```

---

## Ejemplos Completos

### Proyecto Mínimo

Un proyecto mínimo debe incluir:

#### variables_simples.yaml

```yaml
variables_simples:
  - id: nombre_proyecto
    nombre: "Nombre del proyecto"
    tipo: texto
    requerido: true
    seccion: "Información básica"

  - id: descripcion
    nombre: "Descripción"
    tipo: texto_largo
    requerido: true
    seccion: "Información básica"

configuracion:
  version: "2.0"
  secciones_orden:
    - "Información básica"
```

#### variables_condicionales.yaml

```yaml
variables_condicionales:
  - id: incluir_resumen
    nombre: "¿Incluir resumen ejecutivo?"
    descripcion: "Agrega un resumen al inicio del documento"
    tipo_control: radio
    requerido: false
    seccion: "Configuración"
    opciones:
      - valor: "si"
        etiqueta: "Sí"
      - valor: "no"
        etiqueta: "No"
        es_default: true

configuracion:
  version: "2.0"
  motor_condicional: "Jinja2"
```

#### bloques_texto.yaml

```yaml
bloques_texto:
  - id: texto_resumen
    descripcion: "Resumen ejecutivo"
    reglas:
      - cuando: "incluir_resumen == 'si'"
        plantilla: |
          RESUMEN EJECUTIVO

          Proyecto: {{ nombre_proyecto }}
          {{ descripcion }}

      - cuando: "True"
        plantilla: ""

configuracion_bloques:
  version: "2.0"
  orden_evaluacion: "primera_coincidente"
```

---

## Migración de Proyectos Existentes

### Pasos para Migrar un Proyecto Antiguo

1. **Identificar el formato actual**
   - Revisa los archivos YAML existentes
   - Identifica las diferencias con el formato estándar

2. **Crear variables_simples.yaml estandarizado**
   - Convierte `label` → `nombre`
   - Convierte `marker` → añade a sección `configuracion.marcadores`
   - Convierte `type` → `tipo` (usando nombres en español)
   - Añade `seccion` para todas las variables
   - Añade `requerido` explícitamente

3. **Crear variables_condicionales.yaml estandarizado**
   - Convierte condiciones booleanas simples a formato `radio` con opciones "si"/"no"
   - Si usas `boolean_include_doc`, convierte a `radio` con referencia a documento en `bloques_texto.yaml`
   - Añade `seccion` para todas las condiciones

4. **Crear bloques_texto.yaml**
   - Para cada condición, crea un bloque de texto correspondiente
   - Si el contenido está en archivos `.docx`, referéncialos usando `documento`
   - Si es texto simple, usa `plantilla`

5. **Actualizar manifest.yaml**
   - Añade `format_version: "2.0"`
   - Añade `compatible_ui: true`

### Ejemplo de Migración

**Formato Antiguo:**

```yaml
# variables_simples.yaml (antiguo)
simple_variables:
  - id: company_name
    label: "Company Name"
    marker: "<<Company>>"
    type: "text"
```

**Formato Nuevo:**

```yaml
# variables_simples.yaml (nuevo)
variables_simples:
  - id: company_name
    nombre: "Nombre de la compañía"
    tipo: texto
    requerido: true
    placeholder: "Ej: ABC S.A."
    seccion: "Información de la entidad"

configuracion:
  version: "2.0"
  marcadores:
    company_name: "<<Company>>"
```

---

## Validación de Formato

### Checklist de Validación

- [ ] Todos los archivos YAML usan la clave raíz correcta:
  - `variables_simples:` (no `simple_variables:`)
  - `variables_condicionales:` (no `conditions:`)
  - `bloques_texto:` (no `text_blocks:`)

- [ ] Todas las variables simples tienen:
  - [x] `id`
  - [x] `nombre` (no `label`)
  - [x] `tipo` (no `type`)
  - [x] `requerido`
  - [x] `seccion`

- [ ] Todas las variables condicionales tienen:
  - [x] `id`
  - [x] `nombre`
  - [x] `tipo_control: radio`
  - [x] `seccion`
  - [x] `opciones` (lista con al menos 2 opciones)

- [ ] Todos los bloques de texto tienen:
  - [x] `id`
  - [x] `descripcion`
  - [x] `reglas` (lista con al menos una regla)
  - [x] Cada regla tiene `cuando` y (`plantilla` o `documento`)

- [ ] La sección `configuracion:` existe y contiene:
  - [x] `version: "2.0"`
  - [x] `secciones_orden` (lista ordenada de secciones)

---

## Soporte y Recursos

### Documentación Adicional

- **Sintaxis Jinja2**: https://jinja.palletsprojects.com/
- **Formato YAML**: https://yaml.org/spec/

### Proyectos de Referencia

- **informe_auditoria**: `/report_platform/reports/informe_auditoria/`
  - Implementación completa y detallada
  - Múltiples tipos de variables
  - Condiciones complejas
  - Bloques de texto extensos

- **transferencia_precio**: `/report_platform/reports/transferencia_precio/`
  - Ejemplo de migración
  - Uso de documentos Word externos
  - Tablas dinámicas

### Contacto

Para dudas o problemas con la migración, consultar la documentación del proyecto o contactar al equipo de desarrollo.

---

---

## Soporte Multi-Issue (Múltiples Cuestiones)

### Descripción

El sistema soporta la entrada de múltiples cuestiones para opiniones con salvedades o desfavorables. Cuando el usuario indica N > 1 cuestiones:

1. **UI**: Se renderizan N expanders colapsados, cada uno con un conjunto completo de campos
2. **Almacenamiento**: Los valores se guardan con claves compuestas: `salvedad_1__numero_nota`, `salvedad_2__numero_nota`, etc.
3. **Generación**: Se producen N párrafos en el documento Word
4. **Plurales**: Se convierten automáticamente los marcadores de plural

### Configuración en variables_simples.yaml

```yaml
variables_simples:
  # Campo para especificar el número de cuestiones
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

### Configuración en variables_condicionales.yaml

```yaml
variables_condicionales:
  - id: tipo_opinion
    opciones:
      - valor: "salvedades"
        variables_asociadas:
          - motivo_calificacion
          - num_salvedades  # Añadir el campo de conteo

      - valor: "desfavorable"
        variables_asociadas:
          - descripcion_desfavorable
          - num_desfavorables  # Añadir el campo de conteo
```

### Marcadores de Plural en Plantillas

Use marcadores de plural que el sistema convertirá automáticamente:

```yaml
bloques_texto:
  - id: parrafo_opinion
    reglas:
      - cuando: "tipo_opinion == 'salvedades'"
        plantilla: |
          Excepto por la(s) cuestión(es) descrita(s) en la sección "Fundamento de la
          opinión con salvedades", expresamos que...
```

**Marcadores soportados:**

| Marcador | Singular (N=1) | Plural (N>1) |
|----------|----------------|--------------|
| `la(s)` | la | las |
| `cuestión(es)` | cuestión | cuestiones |
| `descrita(s)` | descrita | descritas |
| `indicada(s)` | indicada | indicadas |
| `incorrección(es)` | incorrección | incorrecciones |
| `material(es)` | material | materiales |
| `limitación(es)` | limitación | limitaciones |
| `una/varias incorrección(es) material(es)` | una incorrección material | varias incorrecciones materiales |
| `una/varias limitación(es) al alcance` | una limitación al alcance | varias limitaciones al alcance |

---

## Historial de Cambios

| Versión | Fecha | Cambios |
|---------|-------|---------|
| 2.1 | Dic 2025 | Añadido soporte multi-issue y marcadores de plural |
| 2.0 | Dic 2025 | Estandarización completa del formato |
| 1.0 | - | Formato inicial (deprecado) |

---

**Fin del documento**
