"""
App - Aplicación principal Streamlit

Interfaz web unificada que se adapta dinámicamente a los plugins disponibles.
Incluye funcionalidad de metadatos para guardar y cargar configuraciones.
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

import streamlit as st

# Ensure the project root is in the Python path when running directly with Streamlit
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.utils import setup_logger, get_outputs_dir, safe_filename
from core.config_loader import get_fields_by_section, get_general_config
from core.word_engine import render_word_report
from core.ui_runtime import (
    render_field,
    render_conditional_variable,
    should_show_field_in_ui,
    validate_form_data,
    show_validation_errors,
    show_success_message,
)
from core.metadata import (
    create_metadata,
    save_metadata,
    load_all_metadata,
    load_metadata_by_report_id,
    get_metadata_summary,
)
from ui.router import (
    list_available_reports,
    load_report_plugin,
    get_build_context_function,
    get_template_path,
    get_plugin_info,
)

logger = setup_logger(__name__)


# ==============================================================================
# CONFIGURACIÓN DE LA PÁGINA
# ==============================================================================

st.set_page_config(
    page_title="Plataforma de Generación de Informes",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ==============================================================================
# ESTADO DE SESIÓN
# ==============================================================================

def init_session_state():
    """Inicializa el estado de sesión de Streamlit."""
    # Leer query_params una vez al inicio
    query_params = st.query_params

    if 'selected_report' not in st.session_state:
        # Intentar leer desde query_params si no está en session_state
        report_from_url = query_params.get("report", None)
        st.session_state.selected_report = report_from_url

    if 'plugin_config' not in st.session_state:
        st.session_state.plugin_config = None

    if 'form_data' not in st.session_state:
        st.session_state.form_data = {}

    if 'work_mode' not in st.session_state:
        # Leer mode desde query_params si está disponible
        mode_from_url = query_params.get("mode", None)
        st.session_state.work_mode = mode_from_url if mode_from_url in ['nuevo', 'cargar'] else 'nuevo'

    if 'loaded_metadata_id' not in st.session_state:
        st.session_state.loaded_metadata_id = None

    if 'initialized' not in st.session_state:
        st.session_state.initialized = False


# ==============================================================================
# SELECCIÓN DE PLUGIN Y MODO DE TRABAJO
# ==============================================================================

def render_sidebar():
    """Renderiza el sidebar con selección de informe y modo de trabajo."""
    st.sidebar.title("📄 Plataforma de Informes")
    st.sidebar.markdown("---")

    # Selector de modo de trabajo
    st.sidebar.subheader("🔧 Modo de trabajo")

    # Determinar el índice por defecto basado en el work_mode actual
    current_work_mode = st.session_state.work_mode
    mode_index = 0 if current_work_mode == 'nuevo' else 1

    work_mode = st.sidebar.radio(
        "Selecciona el modo",
        options=['nuevo', 'cargar'],
        format_func=lambda x: "✨ Crear nuevo informe" if x == 'nuevo' else "📂 Cargar desde metadatos",
        index=mode_index,
        key="work_mode_selector"
    )

    # Actualizar modo si cambió
    if st.session_state.work_mode != work_mode:
        st.session_state.work_mode = work_mode
        # Solo limpiar y hacer rerun si ya estábamos inicializados (cambio manual por el usuario)
        if st.session_state.initialized:
            st.session_state.form_data = {}
            st.session_state.loaded_metadata_id = None
            st.session_state.selected_report = None
            st.session_state.plugin_config = None
            st.rerun()

    st.sidebar.markdown("---")

    # Obtener plugins disponibles
    available_reports = list_available_reports()

    if not available_reports:
        st.sidebar.error("No se encontraron plugins de informes")
        return None, None

    # Preselección de informe desde parámetros de la URL (?report=<id>)
    query_params = st.query_params
    preselected_report_id = query_params.get("report", None)

    # Modo: Crear nuevo informe
    if st.session_state.work_mode == 'nuevo':
        st.sidebar.subheader("📋 Seleccionar tipo de informe")

        report_names = [r.nombre for r in available_reports]
        report_ids = [r.id for r in available_reports]

        # Determinar índice por defecto usando la preselección o la selección previa
        default_report_id = preselected_report_id or st.session_state.selected_report
        default_index = 0
        if default_report_id in report_ids:
            default_index = report_ids.index(default_report_id)

        selected_name = st.sidebar.selectbox(
            "Tipo de informe",
            options=report_names,
            index=default_index,
            key="report_selector_nuevo"
        )

        selected_idx = report_names.index(selected_name)
        selected_id = report_ids[selected_idx]
        selected_manifest = available_reports[selected_idx]

        # Mostrar info del plugin
        with st.sidebar.expander("ℹ️ Información del plugin"):
            st.write(f"**ID:** {selected_manifest.id}")
            st.write(f"**Versión:** {selected_manifest.version}")
            if selected_manifest.descripcion:
                st.write(f"**Descripción:** {selected_manifest.descripcion}")
            if selected_manifest.autor:
                st.write(f"**Autor:** {selected_manifest.autor}")

        return selected_id, None

    # Modo: Cargar desde metadatos
    else:
        st.sidebar.subheader("📂 Cargar desde metadatos")

        # Cargar todos los metadatos
        all_metadata = load_all_metadata()

        if not all_metadata:
            st.sidebar.warning("No hay metadatos guardados")
            return None, None

        # Primero seleccionar tipo de informe
        report_ids_with_meta = list(set([m.report_id for m in all_metadata]))
        report_names_map = {r.id: r.nombre for r in available_reports}

        # Preselección basada en query param si aplica
        default_meta_index = 0
        if preselected_report_id in report_ids_with_meta:
            default_meta_index = report_ids_with_meta.index(preselected_report_id)

        selected_report_id = st.sidebar.selectbox(
            "Tipo de informe",
            options=report_ids_with_meta,
            format_func=lambda rid: report_names_map.get(rid, rid),
            index=default_meta_index,
            key="report_selector_cargar"
        )

        # Filtrar metadatos por tipo de informe
        filtered_metadata = [m for m in all_metadata if m.report_id == selected_report_id]

        if not filtered_metadata:
            st.sidebar.warning(f"No hay metadatos para '{selected_report_id}'")
            return None, None

        # Seleccionar registro específico
        metadata_options = {get_metadata_summary(m): m.id for m in filtered_metadata}

        selected_summary = st.sidebar.selectbox(
            "Seleccionar configuración",
            options=list(metadata_options.keys()),
            key="metadata_selector"
        )

        selected_metadata_id = metadata_options[selected_summary]

        # Encontrar el metadata completo
        selected_metadata = next((m for m in filtered_metadata if m.id == selected_metadata_id), None)

        if selected_metadata:
            with st.sidebar.expander("📊 Detalles del metadata"):
                st.write(f"**Generado:** {selected_metadata.timestamp}")
                st.write(f"**Por:** {selected_metadata.generated_by}")
                st.write(f"**Archivo:** {selected_metadata.output_filename}")
                if selected_metadata.description:
                    st.write(f"**Descripción:** {selected_metadata.description}")

        return selected_report_id, selected_metadata


# ==============================================================================
# RENDERIZADO DE FORMULARIO
# ==============================================================================

def render_conditional_variables_section(plugin_config: Dict[str, Any],
                                        context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Renderiza las variables condicionales y sus variables locales asociadas.

    Args:
        plugin_config: Configuración del plugin
        context: Contexto actual

    Returns:
        Diccionario con valores de variables condicionales y locales
    """
    st.header("⚙️ Configuración del Informe")

    conditional_vars = [
        var for var in plugin_config['conditional_variables']
        if getattr(var, "tipo_control", None) != "derivado"
    ]
    simple_fields = plugin_config.get('simple_fields', [])
    local_fields = [f for f in simple_fields if getattr(f, 'ambito', 'global') == 'local']
    values = {}
    processed_groups = set()
    # Track rendered local fields to prevent DuplicateWidgetID errors
    rendered_local_fields = set()
    from core.ui_runtime import identify_date_groups
    date_groups = identify_date_groups(local_fields)

    if not conditional_vars:
        st.info("Este informe no tiene variables condicionales")
        return values

    # Agrupar por sección
    vars_by_section = {}
    for var in conditional_vars:
        section = var.seccion or "General"
        if section not in vars_by_section:
            vars_by_section[section] = []
        vars_by_section[section].append(var)

    # Renderizar cada sección
    for section, variables in vars_by_section.items():
        with st.expander(f"📋 {section}", expanded=True):
            for var in variables:
                # Verificar dependencia
                if var.dependencia:
                    dep = var.dependencia
                    parent_value = context.get(dep.variable)

                    if dep.valor and parent_value != dep.valor:
                        continue
                    if dep.valor_no and parent_value == dep.valor_no:
                        continue

                # Renderizar variable condicional
                value = render_conditional_variable(var, context.get(var.id))
                if value is not None:
                    values[var.id] = value
                    context[var.id] = value

                # Buscar y renderizar campos locales asociados a esta variable
                local_values = render_local_fields_for_condition(
                    condition_var_id=var.id,
                    condition_value=value,
                    local_fields=local_fields,
                    context=context,
                    plugin_config=plugin_config,
                    processed_groups=processed_groups,
                    date_groups=date_groups,
                    rendered_local_fields=rendered_local_fields,
                )
                values.update(local_values)
                context.update(local_values)

    return values


def render_local_fields_for_condition(
    condition_var_id: str,
    condition_value: Any,
    local_fields: List[Any],
    context: Dict[str, Any],
    plugin_config: Dict[str, Any],
    processed_groups: set,
    date_groups: Dict[str, Any],
    rendered_local_fields: Optional[set] = None,
) -> Dict[str, Any]:
    """
    Renderiza los campos locales asociados a una variable condicional.

    Args:
        condition_var_id: ID de la variable condicional padre
        condition_value: Valor actual de la variable condicional
        local_fields: Lista de campos locales
        context: Contexto actual
        plugin_config: Configuración del plugin
        processed_groups: Conjunto de grupos de fecha ya procesados
        date_groups: Diccionario de grupos de fecha
        rendered_local_fields: Conjunto de campos locales ya renderizados (evita duplicados)

    Returns:
        Diccionario con valores de campos locales
    """
    from core.conditions_engine import evaluate_condition
    from core.ui_runtime import render_field

    values = {}
    if rendered_local_fields is None:
        rendered_local_fields = set()

    # Encontrar campos locales cuya condicion_padre involucra esta variable
    relevant_fields = []
    for field in local_fields:
        condicion_padre = getattr(field, 'condicion_padre', None)
        dependencia = getattr(field, 'dependencia', None)

        include_field = False

        # Verificar condiciones expresadas con condicion_padre
        if condicion_padre and condition_var_id in condicion_padre:
            try:
                if evaluate_condition(condicion_padre, context):
                    include_field = True
            except Exception:
                # Si la evaluación falla (variable no existe), ignorar
                pass

        # Verificar dependencias estructuradas sobre la variable condicional
        if not include_field and dependencia and getattr(dependencia, 'variable', None) == condition_var_id:
            parent_value = condition_value if condition_value is not None else context.get(condition_var_id)
            expected_value = getattr(dependencia, 'valor', None)
            not_value = getattr(dependencia, 'valor_no', None)

            if expected_value is not None:
                include_field = parent_value == expected_value
            elif not_value is not None:
                include_field = parent_value != not_value

        if include_field:
            relevant_fields.append(field)

    # Renderizar campos relevantes en un contenedor visual
    if relevant_fields:
        # Filter out already rendered fields to prevent DuplicateWidgetID
        new_fields = [f for f in relevant_fields if f.id not in rendered_local_fields]

        if new_fields:
            st.markdown("---")
            st.markdown(f"**📝 Campos asociados:**")

            # Agrupar por sección para mejor organización
            fields_by_section = {}
            for field in new_fields:
                section = getattr(field, 'seccion', 'Campos adicionales')
                if section not in fields_by_section:
                    fields_by_section[section] = []
                fields_by_section[section].append(field)

            for section, fields in fields_by_section.items():
                st.caption(f"*{section}*")
                for field in fields:
                    # Skip if already rendered
                    if field.id in rendered_local_fields:
                        continue

                    # Verificar si es un grupo de fecha
                    grupo = getattr(field, 'grupo', None)
                    if grupo:
                        if grupo in processed_groups:
                            continue

                        # Buscar todos los campos del grupo
                        from core.ui_runtime import get_date_group_label

                        if grupo in date_groups:
                            from core.input_widgets import render_date_group_input
                            group_fields = date_groups[grupo]
                            current_values = {f.id: context.get(f.id) for f in group_fields.values()}
                            group_label = get_date_group_label(group_fields, plugin_config['config_dir'])
                            result = render_date_group_input(
                                group_fields,
                                current_values,
                                grupo,
                                group_label,
                            )
                            values.update(result)
                            processed_groups.add(grupo)
                            # Mark all fields in the group as rendered
                            for gf in group_fields.values():
                                rendered_local_fields.add(gf.id)
                        continue

                    # Campo individual
                    value = render_field(field, context.get(field.id))
                    if value is not None:
                        values[field.id] = value
                    # Mark field as rendered
                    rendered_local_fields.add(field.id)

    return values


def render_simple_fields_section(
    plugin_config: Dict[str, Any],
    context: Dict[str, Any],
    fields: Optional[List[Any]] = None,
    header_title: str = "📝 Datos del Informe",
    default_expanded: bool = True,
    exclude_local: bool = True,
) -> Dict[str, Any]:
    """
    Renderiza los campos simples organizados por secciones.

    Args:
        plugin_config: Configuración del plugin
        context: Contexto actual con variables condicionales
        fields: Lista de campos a renderizar (opcional)
        header_title: Título de la sección
        default_expanded: Si los expanders deben estar expandidos por defecto
        exclude_local: Si debe excluir campos locales (mostrados en condiciones)

    Returns:
        Diccionario con valores de campos
    """
    st.header(header_title)

    simple_fields = fields if fields is not None else plugin_config['simple_fields']

    if not simple_fields:
        st.info("Este informe no tiene campos simples")
        return {}

    # Excluir campos locales si se solicita (se muestran en condiciones)
    if exclude_local:
        simple_fields = [f for f in simple_fields if getattr(f, 'ambito', 'global') != 'local']

    if not simple_fields:
        st.info("Todos los campos de este informe están asociados a condiciones")
        return {}

    # Agrupar por sección
    fields_by_section = get_fields_by_section(simple_fields)

    # Obtener orden de secciones si está definido
    config_dir = plugin_config['config_dir']
    general_config = get_general_config(config_dir)
    sections_order = general_config.get('secciones_orden', [])

    # Determinar orden
    if sections_order:
        sections = [s for s in sections_order if s in fields_by_section]
        sections.extend([s for s in fields_by_section.keys() if s not in sections])
    else:
        sections = list(fields_by_section.keys())

    # Renderizar campos usando render_section_fields que soporta date groups
    all_values = {}

    # Importar funciones necesarias para verificar visibilidad
    from core.ui_runtime import render_section_fields, should_show_field_in_ui, identify_date_groups

    for section in sections:
        if section not in fields_by_section:
            continue

        section_fields = fields_by_section[section]

        # Verificar si al menos un campo de la sección debe mostrarse
        # Considerar también los grupos de fechas
        date_groups = identify_date_groups(section_fields)
        has_visible_fields = False

        # Verificar campos individuales (no en grupos de fecha)
        grouped_field_ids = set()
        for group_fields in date_groups.values():
            for field in group_fields.values():
                grouped_field_ids.add(field.id)

        for field in section_fields:
            if field.id in grouped_field_ids:
                continue  # Se verificará como parte del grupo
            if should_show_field_in_ui(field, context):
                has_visible_fields = True
                break

        # Verificar grupos de fecha
        if not has_visible_fields:
            for group_name, group_fields in date_groups.items():
                for field in group_fields.values():
                    if should_show_field_in_ui(field, context):
                        has_visible_fields = True
                        break
                if has_visible_fields:
                    break

        # Solo crear el expander si hay campos visibles
        if not has_visible_fields:
            continue

        with st.expander(f"📋 {section}", expanded=default_expanded):
            section_values = render_section_fields(
                section_name="",  # No mostrar subheader porque ya tenemos el expander
                fields=section_fields,
                context=context,
                config_dir=config_dir,
            )
            all_values.update(section_values)

    return all_values


def render_tables_section(plugin_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """Renderiza el área de tablas dinámicas."""

    st.header("📊 Tablas dinámicas")

    # Obtener el ID del informe
    manifest = plugin_config.get('manifest')
    report_id = manifest.id if manifest else None

    # Si es el informe de transferencia de precio, usar el UI especializado
    if report_id == 'transferencia_precio':
        try:
            from core.tp_tables_ui import render_tp_tables_section
            import yaml

            # Cargar configuración de tablas
            config_dir = plugin_config['config_dir']
            tablas_path = Path(config_dir) / "tablas.yaml"

            if tablas_path.exists():
                with open(tablas_path, 'r', encoding='utf-8') as f:
                    cfg_tab = yaml.safe_load(f)

                # Extraer simple_inputs del contexto
                simple_inputs = {k: v for k, v in context.items() if not k.startswith('_')}

                # Renderizar tablas
                table_values = render_tp_tables_section(cfg_tab, simple_inputs)
                return table_values
            else:
                st.warning(f"No se encontró el archivo tablas.yaml en {config_dir}")
                return {}

        except ImportError as e:
            st.error(f"Error importando módulo de tablas: {e}")
            return {}
        except Exception as e:
            st.error(f"Error renderizando tablas de transferencia de precio: {e}")
            logger.error(f"Error en render_tables_section: {e}", exc_info=True)
            return {}

    # Para otros informes, usar el sistema genérico
    tables = plugin_config.get('tables') or []
    values: Dict[str, Any] = {}

    if not tables:
        st.info("Este informe no tiene tablas configuradas en config/tablas.yaml")
        return values

    for table in tables:
        with st.expander(f"📋 {table.nombre}", expanded=True):
            if table.descripcion:
                st.write(table.descripcion)

            st.info(
                "Sistema de captura de datos genérico para tablas dinámicas en desarrollo"
            )

    return values


# ==============================================================================
# GENERACIÓN DE INFORME
# ==============================================================================

def generate_report(plugin_config: Dict[str, Any], form_data: Dict[str, Any],
                   save_meta: bool = True) -> Optional[Path]:
    """
    Genera el informe usando el plugin y los datos del formulario.

    Args:
        plugin_config: Configuración del plugin
        form_data: Datos del formulario
        save_meta: Si debe guardar metadatos

    Returns:
        Path al archivo generado o None si hay error
    """
    try:
        # Obtener función build_context
        build_context = get_build_context_function(plugin_config)

        # Construir contexto
        logger.info("Construyendo contexto con build_context()...")
        context = build_context(form_data, plugin_config['config_dir'])

        # Obtener path de plantilla
        template_path = get_template_path(plugin_config)

        # Generar nombre de archivo
        manifest = plugin_config['manifest']
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"{manifest.id}_{timestamp}"

        # Renderizar informe
        logger.info("Renderizando informe...")
        output_path = render_word_report(template_path, context, output_filename)

        # Verificar si la generación fue exitosa
        if output_path is None:
            logger.error("render_word_report devolvió None - error en la generación")
            return None

        # Guardar metadatos si se solicita (solo si output_path es válido)
        if save_meta:
            metadata = create_metadata(
                report_id=manifest.id,
                report_name=manifest.nombre,
                template_version=manifest.version,
                input_data=form_data,
                output_path=output_path,
                generated_by="usuario",
                description=None
            )
            save_metadata(metadata)
            logger.info(f"Metadatos guardados: {metadata.id}")

        return output_path

    except Exception as e:
        logger.error(f"Error generando informe: {e}")
        st.error(f"Error generando informe: {e}")
        return None


# ==============================================================================
# INTERFAZ PRINCIPAL
# ==============================================================================

def render_html_selector():
    """Muestra el selector HTML de informes cuando no hay selección."""
    # Leer el archivo HTML
    html_path = Path(__file__).parent / "report_selector.html"

    if html_path.exists():
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()

        # Mostrar el HTML usando components
        import streamlit.components.v1 as components
        components.html(html_content, height=800, scrolling=True)
    else:
        st.error("No se encontró el archivo report_selector.html")
        st.info("Por favor, selecciona un tipo de informe en el menú lateral")


def main():
    """Función principal de la aplicación."""
    init_session_state()

    # Renderizar sidebar y obtener selección
    selected_report_id, selected_metadata = render_sidebar()

    # Marcar como inicializado después del primer render
    if not st.session_state.initialized:
        st.session_state.initialized = True

    if not selected_report_id:
        # Mostrar el selector HTML en lugar de un mensaje de advertencia
        render_html_selector()
        st.stop()

    # Cargar plugin si cambió la selección o es nueva
    if (st.session_state.selected_report != selected_report_id or
        st.session_state.plugin_config is None):

        with st.spinner(f"Cargando configuración de {selected_report_id}..."):
            plugin_config = load_report_plugin(selected_report_id)

        if not plugin_config:
            st.error(f"Error cargando plugin: {selected_report_id}")
            st.stop()

        st.session_state.selected_report = selected_report_id
        st.session_state.plugin_config = plugin_config

        # Si estamos en modo cargar y tenemos metadata, prellenar form_data
        if st.session_state.work_mode == 'cargar' and selected_metadata:
            st.session_state.form_data = selected_metadata.input_data.copy()
            st.session_state.loaded_metadata_id = selected_metadata.id
        else:
            st.session_state.form_data = {}
            st.session_state.loaded_metadata_id = None

        # Mostrar información del plugin
        plugin_info = get_plugin_info(plugin_config)
        st.success(f"✅ Plugin cargado: {plugin_info['nombre']} (v{plugin_info['version']})")

        with st.expander("📊 Estadísticas del plugin"):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Campos", plugin_info['num_campos'])
            with col2:
                st.metric("Variables condicionales", plugin_info['num_condicionales'])
            with col3:
                st.metric("Bloques de texto", plugin_info['num_bloques'])

    # Si estamos en modo cargar y el metadata cambió, actualizar form_data
    elif (st.session_state.work_mode == 'cargar' and selected_metadata and
          st.session_state.loaded_metadata_id != selected_metadata.id):
        st.session_state.form_data = selected_metadata.input_data.copy()
        st.session_state.loaded_metadata_id = selected_metadata.id
        st.info("✅ Datos cargados desde metadatos")

    plugin_config = st.session_state.plugin_config

    simple_fields = plugin_config['simple_fields']
    local_fields = [f for f in simple_fields if getattr(f, "ambito", "global") == "local"]
    global_fields = [f for f in simple_fields if f not in local_fields]

    # Mostrar indicador si estamos en modo cargar
    if st.session_state.work_mode == 'cargar' and st.session_state.loaded_metadata_id:
        st.info(f"📂 **Modo:** Cargado desde metadatos (ID: {st.session_state.loaded_metadata_id[:20]}...)")

    # Contexto para seguimiento de valores
    context = dict(st.session_state.form_data)

    # Check if tables exist for this plugin
    has_tables = bool(plugin_config.get('tables'))
    manifest = plugin_config.get('manifest')
    report_id = manifest.id if manifest else None
    # transferencia_precio uses specialized table UI
    is_tp_report = report_id == 'transferencia_precio'

    # Build tab list dynamically based on available content
    tab_names = ["📝 Variables simples", "⚙️ Variables condicionales"]
    if has_tables or is_tp_report:
        tab_names.append("📊 Tablas")
        tab_names.append("🎨 Diseño de Tablas")
    tab_names.append("📁 Archivos")

    # Create tabs dynamically
    tabs = st.tabs(tab_names)
    tab_index = 0

    # Tab: Variables simples
    with tabs[tab_index]:
        field_values = render_simple_fields_section(
            plugin_config,
            context,
            fields=global_fields,
            header_title="📝 Variables simples",
            default_expanded=True,
        )
        context.update(field_values)
    tab_index += 1

    # Tab: Variables condicionales
    with tabs[tab_index]:
        cond_values = render_conditional_variables_section(plugin_config, context)
        context.update(cond_values)
    tab_index += 1

    # Tab: Tablas (only if tables exist)
    if has_tables or is_tp_report:
        with tabs[tab_index]:
            table_values = render_tables_section(plugin_config, context)
            context.update(table_values)
        tab_index += 1

        # Tab: Diseño de Tablas
        with tabs[tab_index]:
            # Importar la función de diseño de tablas
            from ui.table_design_ui import render_table_design_window

            # Renderizar la ventana de diseño de tablas
            table_design_config = render_table_design_window()

            # Guardar la configuración de diseño en el contexto
            context['_table_design_config'] = table_design_config
        tab_index += 1

    # Tab: Archivos (always last)
    with tabs[tab_index]:
        st.header("📁 Archivos de configuración del informe")
        config_dir = plugin_config['config_dir']
        st.write(f"Directorio de configuración: `{config_dir}`")

        st.markdown("**Carga de YAML detectada:**")
        st.markdown(
            f"- `variables_simples.yaml`: { '✅' if plugin_config['simple_fields'] else '⚠️ Sin variables'}"
        )
        st.markdown(
            f"- `variables_condicionales.yaml`: { '✅' if plugin_config['conditional_variables'] else '⚠️ Sin variables'}"
        )
        st.markdown(
            f"- `tablas.yaml`: { '✅' if plugin_config.get('tables') else '⚠️ No hay tablas definidas'}"
        )
        st.markdown(
            f"- `bloques_texto.yaml`: { '✅' if plugin_config['text_blocks'] else '⚠️ No hay bloques configurados'}"
        )

        st.info(
            "Cada categoría se muestra en una pestaña independiente."
            " Si una variable simple es local, solo se mostrará cuando la condición correspondiente esté activa."
        )

    # Guardar datos en sesión
    st.session_state.form_data = context

    st.markdown("---")

    # Botón de generación
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        if st.button("🚀 Generar Informe", type="primary", use_container_width=True):

            # Validar formulario
            all_fields = plugin_config['simple_fields']
            is_valid, errors = validate_form_data(all_fields, context)

            if not is_valid:
                show_validation_errors(errors)
            else:
                # Generar informe
                with st.spinner("Generando informe..."):
                    output_path = generate_report(plugin_config, context, save_meta=True)

                if output_path:
                    show_success_message(f"✅ Informe generado exitosamente")

                    st.info(f"**Archivo:** `{output_path.name}`")
                    st.info(f"**Ubicación:** `{output_path}`")
                    st.success("💾 Metadatos guardados para futura reutilización")

                    # Botón de descarga
                    try:
                        with open(output_path, 'rb') as f:
                            file_data = f.read()

                        st.download_button(
                            label="📥 Descargar Informe",
                            data=file_data,
                            file_name=output_path.name,
                            mime='application/octet-stream',
                            use_container_width=True
                        )
                    except Exception as e:
                        st.error(f"Error al preparar descarga: {e}")

    # Footer
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: gray;'>"
        "Plataforma de Generación de Informes v2.0 | "
        "Desarrollado por Jimmy - Forvis Mazars España | "
        "Con funcionalidad de metadatos para reutilización"
        "</div>",
        unsafe_allow_html=True
    )


# ==============================================================================
# PUNTO DE ENTRADA
# ==============================================================================

if __name__ == "__main__":
    main()
