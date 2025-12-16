"""
Table Design UI - Interfaz de diseño de tablas

Proporciona una interfaz para diseñar y configurar tablas dinámicas
que se insertarán en los documentos generados.
"""

import streamlit as st
from typing import Dict, Any, List, Optional


def render_table_design_window() -> Dict[str, Any]:
    """
    Renderiza la ventana de diseño de tablas.

    Permite al usuario configurar:
    - Columnas de la tabla
    - Estilos de formato
    - Datos de ejemplo

    Returns:
        Configuración de diseño de tabla
    """
    st.subheader("Diseño de tablas")

    st.info(
        "Esta sección permite diseñar tablas personalizadas para el documento. "
        "La funcionalidad completa está en desarrollo."
    )

    config = {}

    # Configuración básica de tabla
    with st.expander("Configuración básica", expanded=True):
        config['nombre_tabla'] = st.text_input(
            "Nombre de la tabla",
            placeholder="Ej: tabla_resumen"
        )

        config['titulo_tabla'] = st.text_input(
            "Título para mostrar",
            placeholder="Ej: Resumen de datos"
        )

        config['num_columnas'] = st.number_input(
            "Número de columnas",
            min_value=1,
            max_value=10,
            value=3
        )

    # Definición de columnas
    with st.expander("Definición de columnas", expanded=False):
        columnas = []
        for i in range(int(config.get('num_columnas', 3))):
            col1, col2 = st.columns(2)
            with col1:
                nombre_col = st.text_input(
                    f"Nombre columna {i+1}",
                    key=f"col_nombre_{i}"
                )
            with col2:
                tipo_col = st.selectbox(
                    f"Tipo columna {i+1}",
                    options=["texto", "numero", "fecha", "moneda"],
                    key=f"col_tipo_{i}"
                )
            columnas.append({
                'nombre': nombre_col,
                'tipo': tipo_col
            })
        config['columnas'] = columnas

    # Estilos
    with st.expander("Estilos", expanded=False):
        config['estilo_cabecera'] = st.selectbox(
            "Estilo de cabecera",
            options=["Negrita", "Normal", "Mayúsculas"]
        )

        config['alineacion'] = st.selectbox(
            "Alineación de datos",
            options=["Izquierda", "Centro", "Derecha", "Justificado"]
        )

        config['bordes'] = st.checkbox(
            "Mostrar bordes",
            value=True
        )

    return config


def render_table_preview(config: Dict[str, Any]) -> None:
    """
    Renderiza una vista previa de la tabla configurada.

    Args:
        config: Configuración de la tabla
    """
    if not config.get('columnas'):
        st.warning("Define las columnas para ver la vista previa")
        return

    st.subheader("Vista previa")

    # Crear datos de ejemplo
    import pandas as pd

    columnas = [c['nombre'] or f"Col {i+1}" for i, c in enumerate(config.get('columnas', []))]

    if not columnas:
        return

    # Datos de ejemplo
    datos = []
    for i in range(3):  # 3 filas de ejemplo
        fila = {}
        for j, col in enumerate(columnas):
            tipo = config['columnas'][j]['tipo'] if j < len(config['columnas']) else 'texto'
            if tipo == 'numero':
                fila[col] = (i + 1) * 100
            elif tipo == 'moneda':
                fila[col] = f"${(i + 1) * 1000:,.2f}"
            elif tipo == 'fecha':
                fila[col] = f"2024-0{i+1}-01"
            else:
                fila[col] = f"Ejemplo {i+1}"
        datos.append(fila)

    df = pd.DataFrame(datos)
    st.dataframe(df, use_container_width=True)
