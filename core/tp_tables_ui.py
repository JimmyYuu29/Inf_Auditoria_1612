"""
Componente UI de Streamlit para tablas dinámicas de Transferencia de Precio.

Este módulo proporciona las funciones de renderizado para todas las tablas
específicas del informe de Transferencia de Precio.
"""
import streamlit as st
import pandas as pd
from typing import Dict, List, Any


def render_tp_tables_section(cfg_tab: dict, simple_inputs: dict) -> Dict[str, Any]:
    """
    Renderiza la sección de tablas para Transferencia de Precio en Streamlit.

    Args:
        cfg_tab: Configuración de tablas.yaml
        simple_inputs: Datos de variables simples (para ejercicios, etc.)

    Returns:
        Diccionario con {id_tabla: datos}
    """
    st.header("📊 Tablas")
    st.markdown("Completa los datos de las diferentes tablas del informe.")

    all_table_inputs = {}

    # 1. Tabla de análisis indirecto global (TNMM)
    st.subheader("1. Análisis Indirecto Global (TNMM)")
    tnmm_global = render_tnmm_global(cfg_tab)
    all_table_inputs["analisis_indirecto_global"] = tnmm_global

    # Preview de la tabla
    with st.expander("👁️ Previsualizar tabla", expanded=False):
        if tnmm_global and "rango_tnmm" in tnmm_global:
            preview_df = pd.DataFrame([tnmm_global["rango_tnmm"]])
            preview_df = preview_df.rename(columns={
                "min": "Mínimo",
                "lq": "Cuartil Inferior",
                "med": "Mediana",
                "uq": "Cuartil Superior",
                "max": "Máximo"
            })
            st.dataframe(preview_df, use_container_width=True)

    st.divider()

    # 2. Tabla de operaciones vinculadas
    st.subheader("2. Operaciones Vinculadas")
    operaciones = render_operaciones_vinculadas(cfg_tab)
    all_table_inputs["operaciones_vinculadas"] = operaciones

    # Preview de la tabla
    with st.expander("👁️ Previsualizar tabla", expanded=False):
        if operaciones:
            preview_df = pd.DataFrame(operaciones)
            preview_df = preview_df.rename(columns={
                "tipo_operacion": "Tipo de Operación",
                "entidad_vinculada": "Entidad Vinculada",
                "ingreso_local_file": "Ingreso (EUR)",
                "gasto_local_file": "Gasto (EUR)"
            })
            st.dataframe(preview_df, use_container_width=True)

    st.divider()

    # 3. Tablas TNMM por operación
    st.subheader("3. Análisis TNMM por Operación")
    st.markdown("Completa el análisis TNMM para cada operación vinculada.")

    num_operaciones = len(operaciones) if operaciones else 0

    if num_operaciones > 0:
        for i in range(num_operaciones):
            op_data = operaciones[i]
            tipo_op = op_data.get("tipo_operacion", f"Operación {i+1}")

            with st.expander(f"Operación {i+1}: {tipo_op}"):
                tnmm_op = render_tnmm_operacion(cfg_tab, i+1, tipo_op)
                all_table_inputs[f"analisis_indirecto_operacion_{i+1}"] = tnmm_op

                # Preview de la tabla TNMM de operación
                with st.expander("👁️ Previsualizar tabla TNMM", expanded=False):
                    if tnmm_op:
                        # Excluir 'nombre_operacion' del preview
                        preview_data = {k: v for k, v in tnmm_op.items() if k != "nombre_operacion"}
                        preview_df = pd.DataFrame([preview_data])
                        preview_df = preview_df.rename(columns={
                            "min": "Mínimo",
                            "lq": "Cuartil Inferior",
                            "med": "Mediana",
                            "uq": "Cuartil Superior",
                            "max": "Máximo"
                        })
                        st.dataframe(preview_df, use_container_width=True)
    else:
        st.info("Primero agrega operaciones en la tabla de 'Operaciones Vinculadas'")

    st.divider()

    # 4. Tabla de partidas contables
    st.subheader("4. Partidas Contables y Márgenes")
    partidas = render_partidas_contables(cfg_tab, simple_inputs)
    all_table_inputs["partidas_contables"] = partidas

    # Preview de la tabla
    with st.expander("👁️ Previsualizar tabla", expanded=False):
        if partidas:
            # Crear DataFrame para preview
            preview_data = []
            for row_id, values in partidas.items():
                row_data = {
                    "Concepto": row_id.replace("_", " ").title(),
                    "Ejercicio Actual": values.get("ejercicio_actual", 0),
                    "Ejercicio Anterior": values.get("ejercicio_anterior", 0)
                }
                preview_data.append(row_data)
            preview_df = pd.DataFrame(preview_data)
            st.dataframe(preview_df, use_container_width=True)

    st.divider()

    # 5. Tablas de cumplimiento inicial
    st.subheader("5. Cumplimiento Formal Inicial")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Local File (LF)**")
        cumpl_lf = render_cumplimiento_inicial(cfg_tab, "cumplimiento_inicial_LF")
        all_table_inputs["cumplimiento_inicial_LF"] = cumpl_lf

    with col2:
        st.markdown("**Master File (MF)**")
        cumpl_mf = render_cumplimiento_inicial(cfg_tab, "cumplimiento_inicial_MF")
        all_table_inputs["cumplimiento_inicial_MF"] = cumpl_mf

    st.divider()

    # 6. Tablas de cumplimiento formal detallado
    st.subheader("6. Cumplimiento Formal Detallado")

    with st.expander("Local File (LF) - Detallado"):
        cumpl_det_lf = render_cumplimiento_detallado(cfg_tab, "cumplimiento_formal_LF")
        all_table_inputs["cumplimiento_formal_LF"] = cumpl_det_lf

    with st.expander("Master File (MF) - Detallado"):
        cumpl_det_mf = render_cumplimiento_detallado(cfg_tab, "cumplimiento_formal_MF")
        all_table_inputs["cumplimiento_formal_MF"] = cumpl_det_mf

    st.divider()

    # 7. Tabla de riesgos
    st.subheader("7. Revisión de Riesgos PT")
    riesgos = render_riesgos(cfg_tab)
    all_table_inputs["riesgos_pt"] = riesgos

    # Preview de la tabla
    with st.expander("👁️ Previsualizar tabla", expanded=False):
        if riesgos:
            preview_df = pd.DataFrame(riesgos)
            preview_df = preview_df.rename(columns={
                "numero": "#",
                "elemento_riesgo": "Elemento de Riesgo",
                "impacto_compania": "Impacto",
                "nivel_afectacion_preliminar": "Nivel Prelim.",
                "mitigadores": "Mitigadores",
                "nivel_afectacion_final": "Nivel Final"
            })
            st.dataframe(preview_df, use_container_width=True)

    return all_table_inputs


def render_tnmm_global(cfg_tab: dict) -> dict:
    """Renderiza la tabla TNMM global."""
    cfg = cfg_tab["tables"]["analisis_indirecto_global"]

    st.markdown("Ingresa los valores del rango TNMM global (valores por defecto: 1%, 2%, 3%, 4%, 5%):")

    data = {}

    # Valores por defecto para min, lq, med, uq, max
    default_values = [1.0, 2.0, 3.0, 4.0, 5.0]

    cols = st.columns(5)
    for i, col_cfg in enumerate(cfg["columns"]):
        col_id = col_cfg["id"]
        header = col_cfg["header"]

        with cols[i]:
            value = st.number_input(
                header,
                key=f"tnmm_global_{col_id}",
                min_value=0.0,
                max_value=100.0,
                step=0.01,
                format="%.2f",
                value=default_values[i] if i < len(default_values) else 0.0
            )

        if "rango_tnmm" not in data:
            data["rango_tnmm"] = {}

        data["rango_tnmm"][col_id] = value

    return data


def render_tnmm_operacion(cfg_tab: dict, n: int, nombre: str) -> dict:
    """Renderiza tabla TNMM para una operación específica."""
    cfg = cfg_tab["tables"]["analisis_indirecto_operacion"]

    st.markdown("Valores por defecto: 1%, 2%, 3%, 4%, 5%")

    data = {"nombre_operacion": nombre}

    # Valores por defecto para min, lq, med, uq, max
    default_values = [1.0, 2.0, 3.0, 4.0, 5.0]

    # Filtrar columnas para excluir 'nombre_operacion' ya que se proporciona como parámetro
    numeric_columns = [col for col in cfg["columns"] if col["id"] != "nombre_operacion"]

    cols = st.columns(len(numeric_columns))
    for i, col_cfg in enumerate(numeric_columns):
        col_id = col_cfg["id"]
        header = col_cfg["header"]

        with cols[i]:
            value = st.number_input(
                header,
                key=f"tnmm_op_{n}_{col_id}",
                min_value=0.0,
                max_value=100.0,
                step=0.01,
                format="%.2f",
                value=default_values[i] if i < len(default_values) else 0.0
            )

        data[col_id] = value

    return data


def render_operaciones_vinculadas(cfg_tab: dict) -> list:
    """Renderiza la tabla de operaciones vinculadas con filas dinámicas."""
    cfg = cfg_tab["tables"]["operaciones_vinculadas"]

    st.markdown("Añade las operaciones vinculadas (puedes añadir hasta 10 operaciones):")

    # Inicializar estado de sesión
    if "num_operaciones" not in st.session_state:
        st.session_state.num_operaciones = 3  # Empezar con 3 operaciones

    # Botones para añadir/quitar filas
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("➕ Añadir operación"):
            if st.session_state.num_operaciones < 10:
                st.session_state.num_operaciones += 1
                st.rerun()

    with col2:
        if st.button("➖ Quitar última"):
            if st.session_state.num_operaciones > 1:
                st.session_state.num_operaciones -= 1
                st.rerun()

    # Crear DataFrame para edición
    rows = []

    for i in range(st.session_state.num_operaciones):
        row = {}
        st.markdown(f"**Operación {i+1}**")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            row["tipo_operacion"] = st.text_input(
                "Tipo de operación",
                key=f"op_{i}_tipo",
                placeholder="Ej: Servicios de soporte"
            )

        with col2:
            row["entidad_vinculada"] = st.text_input(
                "Entidad vinculada",
                key=f"op_{i}_entidad",
                placeholder="Ej: Dell Technologies Inc."
            )

        with col3:
            row["ingreso_local_file"] = st.number_input(
                "Ingreso (EUR)",
                key=f"op_{i}_ingreso",
                min_value=0.0,
                step=1000.0,
                format="%.2f"
            )

        with col4:
            row["gasto_local_file"] = st.number_input(
                "Gasto (EUR)",
                key=f"op_{i}_gasto",
                min_value=0.0,
                step=1000.0,
                format="%.2f"
            )

        rows.append(row)

    return rows


def render_partidas_contables(cfg_tab: dict, simple_inputs: dict) -> dict:
    """Renderiza la tabla de partidas contables."""
    cfg = cfg_tab["tables"]["partidas_contables"]

    ejercicio_actual = simple_inputs.get("ejercicio_completo", "2023")
    ejercicio_anterior = simple_inputs.get("ejercicio_anterior", "2022")

    st.markdown(f"Completa las partidas contables para {ejercicio_actual} y {ejercicio_anterior}:")

    data = {}

    # Mostrar solo las filas manuales (las calculadas se computan automáticamente)
    manual_rows = [row for row in cfg["rows"] if row.get("input_mode") == "manual"]

    for row_cfg in manual_rows:
        row_id = row_cfg["id"]
        label = row_cfg["label"]

        st.markdown(f"**{label}**")

        col1, col2 = st.columns(2)

        with col1:
            ea = st.number_input(
                f"{ejercicio_actual}",
                key=f"partida_{row_id}_ea",
                step=1000.0,
                format="%.2f"
            )

        with col2:
            ep = st.number_input(
                f"{ejercicio_anterior}",
                key=f"partida_{row_id}_ep",
                step=1000.0,
                format="%.2f"
            )

        data[row_id] = {
            "ejercicio_actual": ea,
            "ejercicio_anterior": ep
        }

    # Calcular las filas calculadas
    calculated_rows = [row for row in cfg["rows"] if row.get("input_mode") == "calculated"]

    for row_cfg in calculated_rows:
        row_id = row_cfg["id"]
        label = row_cfg["label"]

        # Obtener valores necesarios para el cálculo
        if row_id == "operating_margin_om":
            ebit_ea = data.get("ebit", {}).get("ejercicio_actual", 0)
            ebit_ep = data.get("ebit", {}).get("ejercicio_anterior", 0)
            cn_ea = data.get("cifra_negocios", {}).get("ejercicio_actual", 1)
            cn_ep = data.get("cifra_negocios", {}).get("ejercicio_anterior", 1)

            om_ea = (ebit_ea / cn_ea * 100) if cn_ea != 0 else 0
            om_ep = (ebit_ep / cn_ep * 100) if cn_ep != 0 else 0

            data[row_id] = {
                "ejercicio_actual": om_ea,
                "ejercicio_anterior": om_ep
            }

        elif row_id == "net_cost_plus_ncp":
            ebit_ea = data.get("ebit", {}).get("ejercicio_actual", 0)
            ebit_ep = data.get("ebit", {}).get("ejercicio_anterior", 0)
            tco_ea = data.get("total_costes_operativos", {}).get("ejercicio_actual", 1)
            tco_ep = data.get("total_costes_operativos", {}).get("ejercicio_anterior", 1)

            ncp_ea = (ebit_ea / tco_ea * 100) if tco_ea != 0 else 0
            ncp_ep = (ebit_ep / tco_ep * 100) if tco_ep != 0 else 0

            data[row_id] = {
                "ejercicio_actual": ncp_ea,
                "ejercicio_anterior": ncp_ep
            }

    return data


def render_cumplimiento_inicial(cfg_tab: dict, table_id: str) -> list:
    """Renderiza tabla de cumplimiento inicial."""
    cfg = cfg_tab["tables"][table_id]

    # Filas predefinidas según el artículo (simplificado)
    if "LF" in table_id:
        secciones = [
            "Identificación de la entidad",
            "Descripción del negocio",
            "Operaciones vinculadas",
            "Información financiera",
            "Acuerdos de precios de transferencia"
        ]
    else:  # MF
        secciones = [
            "Estructura organizativa",
            "Descripción del negocio",
            "Activos intangibles",
            "Actividades financieras",
            "Situación financiera y fiscal"
        ]

    rows = []

    for i, seccion in enumerate(secciones):
        col1, col2 = st.columns([3, 1])

        with col1:
            st.markdown(f"**{seccion}**")

        with col2:
            cumplimiento = st.selectbox(
                "Cumplimiento",
                options=["Sí", "No", "Ver comentario"],
                key=f"{table_id}_{i}",
                label_visibility="collapsed"
            )

        rows.append({
            "numero": i + 1,
            "seccion": seccion,
            "cumplimiento": cumplimiento
        })

    return rows


def render_cumplimiento_detallado(cfg_tab: dict, table_id: str) -> list:
    """Renderiza tabla de cumplimiento formal detallado."""
    cfg = cfg_tab["tables"][table_id]

    # Requisitos predefinidos (simplificado)
    if "LF" in table_id:
        requisitos = [
            "Identificación completa de la entidad local",
            "Descripción detallada de las actividades",
            "Listado completo de operaciones vinculadas",
            "Análisis funcional de las operaciones",
            "Información sobre comparables utilizados"
        ]
    else:  # MF
        requisitos = [
            "Estructura organizativa del grupo",
            "Descripción del negocio y estrategias",
            "Intangibles del grupo y su propiedad",
            "Actividades financieras intragrupo",
            "Situación financiera consolidada"
        ]

    rows = []

    for requisito in requisitos:
        st.markdown(f"**{requisito}**")

        col1, col2 = st.columns([1, 2])

        with col1:
            cumplimiento = st.selectbox(
                "Cumplimiento",
                options=["Sí", "No", "Ver comentario"],
                key=f"{table_id}_det_{requisito[:20]}",
                label_visibility="collapsed"
            )

        with col2:
            comentario = ""
            if cumplimiento == "Ver comentario":
                comentario = st.text_input(
                    "Comentario",
                    key=f"{table_id}_com_{requisito[:20]}",
                    label_visibility="collapsed"
                )

        rows.append({
            "requisito": requisito,
            "cumplimiento": cumplimiento,
            "comentario": comentario
        })

    return rows


def render_riesgos(cfg_tab: dict) -> list:
    """Renderiza tabla de riesgos."""
    cfg = cfg_tab["tables"]["riesgos_pt"]

    # Elementos de riesgo predefinidos
    elementos_riesgo = [
        "Operaciones con entidades en paraísos fiscales",
        "Transferencia de intangibles sin remuneración adecuada",
        "Servicios intragrupo sin documentación suficiente",
        "Financiación intragrupo con tipos no de mercado",
        "Reestructuraciones empresariales sin compensación",
        "Operaciones con pérdidas sistemáticas",
        "Falta de análisis de comparabilidad",
        "Ausencia de documentación contemporánea"
    ]

    rows = []

    for i, elemento in enumerate(elementos_riesgo):
        st.markdown(f"**{i+1}. {elemento}**")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            impacto = st.selectbox(
                "Impacto",
                options=["No", "Sí", "Posible"],
                key=f"riesgo_{i}_impacto",
                label_visibility="collapsed"
            )

        with col2:
            nivel_prelim = st.selectbox(
                "Nivel Prelim.",
                options=["No", "Sí", "Posible"],
                key=f"riesgo_{i}_prelim",
                label_visibility="collapsed"
            )

        with col3:
            mitigadores = st.text_input(
                "Mitigadores",
                key=f"riesgo_{i}_mitig",
                label_visibility="collapsed",
                placeholder="Describe mitigadores..."
            )

        with col4:
            nivel_final = st.selectbox(
                "Nivel Final",
                options=["No", "Sí", "Posible"],
                key=f"riesgo_{i}_final",
                label_visibility="collapsed"
            )

        rows.append({
            "numero": i + 1,
            "elemento_riesgo": elemento,
            "impacto_compania": impacto,
            "nivel_afectacion_preliminar": nivel_prelim,
            "mitigadores": mitigadores,
            "nivel_afectacion_final": nivel_final
        })

    return rows
