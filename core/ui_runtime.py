"""
UI Runtime - Motor de generación dinámica de controles UI

Genera automáticamente controles de interfaz Streamlit basándose en
definiciones de campos YAML, permitiendo formularios completamente dinámicos.
"""

import streamlit as st
from typing import Dict, Any, List, Optional
from core.utils import setup_logger
from core.schema_models import SimpleField, ConditionalVariable
from core.conditions_engine import evaluate_condition
from core.input_widgets import (
    render_date_input,
    render_date_group_input,
    render_long_text_input,
    render_number_input,
    render_select_input,
    render_text_input,
)

logger = setup_logger(__name__)

# ==============================================================================
# HELPERS - ESTADO ESTABLE PARA WIDGETS
# ==============================================================================
def _get_state_value(field_id: str, fallback: Any = None) -> Any:
    """Obtiene un valor desde st.session_state con tolerancia a distintas claves.

    En proyectos reales, los widgets a veces usan key=field.id, key=f"field_{id}", etc.
    Esta función intenta varias variantes para minimizar 'rebotes' y pérdida de estado.
    """
    candidates = [
        field_id,
        f"field_{field_id}",
        f"input_{field_id}",
        f"w_{field_id}",
    ]
    for k in candidates:
        if k in st.session_state:
            return st.session_state.get(k)
    return fallback


def _set_state_value(field_id: str, value: Any) -> None:
    """Guarda un valor en session_state bajo una clave 'canónica' y, si existe, también bajo field_id."""
    canonical = f"field_{field_id}"
    st.session_state[canonical] = value
    # Si el proyecto ya usa field_id como key de widget, mantenerlo sincronizado sin pisar otros tipos
    if field_id in st.session_state and not isinstance(st.session_state.get(field_id), (dict, list, tuple, set)):
        st.session_state[field_id] = value



# ==============================================================================
# IDENTIFICACIÓN DE GRUPOS DE FECHAS
# ==============================================================================

def identify_date_groups(fields: List[SimpleField]) -> Dict[str, Dict[str, SimpleField]]:
    """
    Identifica grupos de campos que deben renderizarse como selectores de fecha.

    Busca campos con:
    - Mismo valor en el atributo 'grupo'
    - O campos con IDs que sigan el patrón dia_*, mes_*, ano_* con el mismo sufijo

    Args:
        fields: Lista de campos

    Returns:
        Diccionario {group_name: {'dia': field, 'mes': field, 'ano': field}}
    """
    date_groups = {}

    # Primero buscar por atributo 'grupo'
    for field in fields:
        grupo = getattr(field, 'grupo', None)
        if grupo:
            if grupo not in date_groups:
                date_groups[grupo] = {}

            # Identificar si es dia, mes o ano
            field_id = field.id
            if field_id.startswith('dia_'):
                date_groups[grupo]['dia'] = field
            elif field_id.startswith('mes_'):
                date_groups[grupo]['mes'] = field
            elif field_id.startswith('ano_'):
                date_groups[grupo]['ano'] = field

    # Filtrar solo grupos que tengan al menos 2 componentes (mes+ano, dia+mes, o dia+mes+ano)
    valid_groups = {}
    for group_name, components in date_groups.items():
        if len(components) >= 2:
            valid_groups[group_name] = components

    return valid_groups


def get_date_group_label(fields_group: Dict[str, SimpleField], config_dir) -> str:
    """
    Obtiene la etiqueta para un grupo de fechas desde la configuración.

    Args:
        fields_group: Grupo de campos de fecha
        config_dir: Directorio de configuración

    Returns:
        Etiqueta del grupo o etiqueta por defecto
    """
    # Intentar obtener la etiqueta desde la configuración
    from core.config_loader import get_general_config

    # Buscar el nombre del grupo en alguno de los campos
    group_name = None
    for field in fields_group.values():
        group_name = getattr(field, 'grupo', None)
        if group_name:
            break

    if group_name:
        general_config = get_general_config(config_dir)
        agrupaciones = general_config.get('agrupaciones_fecha', [])

        for agrupacion in agrupaciones:
            if agrupacion.get('grupo') == group_name:
                return agrupacion.get('etiqueta', group_name)

    # Etiqueta por defecto
    return "Fecha"


# ==============================================================================
# GENERACIÓN DE VARIABLES CONDICIONALES
# ==============================================================================

def render_conditional_variable(var: ConditionalVariable, 
                               current_value: Any = None) -> Any:
    """
    Renderiza una variable condicional (radio / select) de forma estable.

    Problema típico en Streamlit:
    - Cada interacción provoca un rerun.
    - Si en cada rerun recalculas `index` desde un `current_value` que puede estar desfasado,
      el control "rebota" al valor por defecto y el usuario siente que debe elegir dos veces.

    Estrategia:
    - Separar la clave del widget (UI) de la clave del valor lógico (VAL).
    - Inicializar el valor por defecto SOLO una vez.
    - En reruns, respetar el estado ya guardado en session_state.
    """
    if not var.opciones:
        st.warning(f"Variable '{var.nombre}' no tiene opciones definidas")
        return None

    options = [opt.valor for opt in var.opciones]
    labels = [opt.etiqueta for opt in var.opciones]
    label_to_value = {opt.etiqueta: opt.valor for opt in var.opciones}
    value_to_label = {opt.valor: opt.etiqueta for opt in var.opciones}

    # Claves separadas: UI guarda etiqueta; VAL guarda valor lógico
    val_key = f"cond_{var.id}"
    ui_key = f"cond_{var.id}__ui"

    # Determinar default (solo para inicialización)
    default_value = options[0]
    for opt in var.opciones:
        if opt.es_default:
            default_value = opt.valor
            break

    # Inicialización: priorizar current_value si es válido; si no, default
    if val_key not in st.session_state:
        if current_value is not None and current_value in options:
            st.session_state[val_key] = current_value
        else:
            st.session_state[val_key] = default_value

    # Mantener UI (etiqueta) coherente con el valor lógico
    if ui_key not in st.session_state:
        st.session_state[ui_key] = value_to_label.get(st.session_state[val_key], labels[0])

    help_text = getattr(var, "descripcion", None)

    if var.tipo_control == "radio":
        # Importante: NO forzar `index` si el widget ya tiene estado propio
        if ui_key in st.session_state:
            selected_label = st.radio(
                label=var.nombre,
                options=labels,
                help=help_text,
                key=ui_key,
            )
        else:
            selected_label = st.radio(
                label=var.nombre,
                options=labels,
                index=labels.index(st.session_state[ui_key]),
                help=help_text,
                key=ui_key,
            )

    elif var.tipo_control == "select":
        if ui_key in st.session_state:
            selected_label = st.selectbox(
                label=var.nombre,
                options=labels,
                help=help_text,
                key=ui_key,
            )
        else:
            selected_label = st.selectbox(
                label=var.nombre,
                options=labels,
                index=labels.index(st.session_state[ui_key]),
                help=help_text,
                key=ui_key,
            )
    else:
        st.warning(f"Tipo de control desconocido: {var.tipo_control}")
        selected_label = st.session_state[ui_key]

    # Guardar valor lógico
    selected_value = label_to_value.get(selected_label, default_value)
    st.session_state[val_key] = selected_value
    return selected_value


# ==============================================================================
# GENERACIÓN DE FORMULARIO COMPLETO
# ==============================================================================

def render_field(field: SimpleField, current_value: Any = None) -> Any:
    """
    Renderiza un campo según su tipo.
    
    Args:
        field: Definición del campo
        current_value: Valor actual
    
    Returns:
        Valor introducido por el usuario
    """
    # Renderizar según tipo
    if field.tipo == "texto":
        return render_text_input(field, current_value)

    elif field.tipo == "texto_largo":
        return render_long_text_input(field, current_value)

    elif field.tipo == "numero":
        return render_number_input(field, current_value)

    elif field.tipo == "lista":
        return render_select_input(field, current_value)

    elif field.tipo == "fecha":
        return render_date_input(field, current_value)
    
    else:
        st.warning(f"Tipo de campo no soportado: {field.tipo}")
        return None


def should_show_field_in_ui(field: SimpleField, context: Dict[str, Any]) -> bool:
    """
    Determina si un campo debe mostrarse según su dependencia.

    Nota: Para evitar "rebotes", intentamos leer el valor más reciente desde session_state
    cuando el `context` aún no lo refleja (por ejemplo, durante reruns).
    """
    # Si el campo es calculado, no se muestra
    if field.calculado:
        return False

    # Si tiene condición padre, evaluarla
    if field.condicion_padre:
        # Enriquecer contexto con posibles valores más recientes
        try:
            dep_vars = getattr(field.condicion_padre, "variables", None)
            if dep_vars:
                for v in dep_vars:
                    if v not in context:
                        context[v] = _get_state_value(v, context.get(v))
        except Exception:
            pass
        return evaluate_condition(field.condicion_padre, context)

    # Si tiene dependencia estructurada
    if field.dependencia:
        dep = field.dependencia
        parent_value = context.get(dep.variable, _get_state_value(dep.variable))

        if dep.valor:
            return parent_value == dep.valor
        elif dep.valor_no:
            return parent_value != dep.valor_no

    return True


def render_section_fields(
    section_name: str,
    fields: List[SimpleField],
    context: Dict[str, Any],
    config_dir=None,
) -> Dict[str, Any]:
    """
    Renderiza todos los campos de una sección.

    Args:
        section_name: Nombre de la sección
        fields: Lista de campos de la sección
        context: Contexto actual
        config_dir: Directorio de configuración (para obtener etiquetas de grupos)

    Returns:
        Diccionario con valores recolectados {field_id: value}
    """
    # Solo renderizar subheader si el nombre de sección no está vacío
    if section_name:
        st.subheader(section_name)

    values = {}

    # Sincronizar contexto con el estado más reciente de Streamlit para reducir 'rebotes'
    for _f in fields:
        if _f is None:
            continue
        try:
            if _f.id not in context:
                context[_f.id] = _get_state_value(_f.id, context.get(_f.id))
        except Exception:
            continue

    # Identificar grupos de fechas
    date_groups = identify_date_groups(fields)

    # Conjunto de IDs de campos que ya se procesaron como parte de un grupo
    processed_field_ids = set()

    # Renderizar grupos de fechas
    for group_name, fields_group in date_groups.items():
        # Verificar si algún campo del grupo debe mostrarse
        should_show = False
        for field in fields_group.values():
            if should_show_field_in_ui(field, context):
                should_show = True
                break

        if should_show:
            # Obtener etiqueta del grupo
            if config_dir:
                group_label = get_date_group_label(fields_group, config_dir)
            else:
                group_label = "Fecha"

            # Renderizar selector de fecha
            date_values = render_date_group_input(
                fields_group,
                context,
                group_name,
                group_label
            )

            # Agregar valores al contexto
            values.update(date_values)
            context.update(date_values)

            # Marcar campos como procesados
            for field in fields_group.values():
                processed_field_ids.add(field.id)

    # Renderizar campos individuales que no son parte de grupos
    for field in fields:
        # Saltar si ya fue procesado como parte de un grupo
        if field.id in processed_field_ids:
            continue

        # Verificar si debe mostrarse
        if not should_show_field_in_ui(field, context):
            continue

        # Renderizar el campo
        value = render_field(field, context.get(field.id))

        if value is not None:
            values[field.id] = value
            # Actualizar contexto para campos dependientes
            context[field.id] = value

    return values


def render_all_fields(
    fields_by_section: Dict[str, List[SimpleField]],
    sections_order: Optional[List[str]] = None,
    initial_context: Optional[Dict[str, Any]] = None,
    config_dir=None,
) -> Dict[str, Any]:
    """
    Renderiza todos los campos organizados por secciones.

    Args:
        fields_by_section: Diccionario {seccion: [campos]}
        sections_order: Orden de las secciones (opcional)
        initial_context: Contexto inicial con valores
        config_dir: Directorio de configuración

    Returns:
        Diccionario con todos los valores recolectados
    """
    context = initial_context.copy() if initial_context else {}
    all_values = {}

    # Determinar orden de secciones
    if sections_order:
        sections = [s for s in sections_order if s in fields_by_section]
        # Agregar secciones no listadas al final
        sections.extend([s for s in fields_by_section.keys() if s not in sections])
    else:
        sections = list(fields_by_section.keys())

    # Renderizar cada sección
    for section in sections:
        if section not in fields_by_section:
            continue

        section_values = render_section_fields(
            section,
            fields_by_section[section],
            context,
            config_dir,
        )
        all_values.update(section_values)
        context.update(section_values)

    return all_values


# ==============================================================================
# VALIDACIÓN DE FORMULARIO
# ==============================================================================

def validate_form_data(fields: List[SimpleField], 
                      data: Dict[str, Any]) -> tuple[bool, List[str]]:
    """
    Valida datos del formulario.
    
    Args:
        fields: Lista de definiciones de campos
        data: Datos introducidos por el usuario
    
    Returns:
        Tupla (es_válido, lista_de_errores)
    """
    errors = []
    
    for field in fields:
        # Omitir campos calculados o no aplicables según dependencias
        if getattr(field, "calculado", False):
            continue

        if not should_show_field_in_ui(field, data):
            continue

        # Verificar campos requeridos
        if field.requerido and field.id not in data:
            errors.append(f"Campo requerido faltante: {field.nombre}")
            continue

        if field.id not in data:
            continue

        value = data[field.id]

        # Si el valor está vacío, solo marcar error si es requerido
        if value in (None, ""):
            if field.requerido:
                errors.append(f"Campo requerido faltante: {field.nombre}")
            continue

        # Validar rangos numéricos
        if field.tipo == "numero":
            try:
                num_value = float(value)
                if field.min is not None and num_value < field.min:
                    errors.append(f"{field.nombre}: valor mínimo es {field.min}")
                if field.max is not None and num_value > field.max:
                    errors.append(f"{field.nombre}: valor máximo es {field.max}")
            except (ValueError, TypeError):
                errors.append(f"{field.nombre}: debe ser un número")
        
        # Validar opciones de lista
        if field.tipo == "lista" and field.opciones:
            if value not in field.opciones:
                errors.append(f"{field.nombre}: valor no válido")
    
    is_valid = len(errors) == 0
    return is_valid, errors


# ==============================================================================
# UTILIDADES DE UI
# ==============================================================================

def show_validation_errors(errors: List[str]) -> None:
    """
    Muestra errores de validación en la UI.
    
    Args:
        errors: Lista de mensajes de error
    """
    if errors:
        st.error("**Errores de validación:**")
        for error in errors:
            st.write(f"- {error}")


def show_success_message(message: str) -> None:
    """
    Muestra mensaje de éxito en la UI.
    
    Args:
        message: Mensaje a mostrar
    """
    st.success(message)


def show_info_message(message: str) -> None:
    """
    Muestra mensaje informativo en la UI.
    
    Args:
        message: Mensaje a mostrar
    """
    st.info(message)


def create_download_button(file_path, button_label: str = "Descargar informe") -> None:
    """
    Crea un botón de descarga para un archivo.
    
    Args:
        file_path: Path al archivo
        button_label: Texto del botón
    """
    try:
        with open(file_path, 'rb') as f:
            file_data = f.read()
        
        st.download_button(
            label=button_label,
            data=file_data,
            file_name=file_path.name,
            mime='application/octet-stream'
        )
    except Exception as e:
        st.error(f"Error creando botón de descarga: {e}")
