"""Input widgets helpers for Streamlit forms.

Este módulo centraliza la creación de controles de entrada para distintas
categorías de datos, ofreciendo experiencias más intuitivas como el selector
calendario para fechas. De esta forma, añadir nuevos tipos de campos o ajustar
su comportamiento visual es más sencillo y reutilizable desde la UI.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

import streamlit as st

from report_platform.core.schema_models import SimpleField
from report_platform.core.utils import setup_logger

logger = setup_logger(__name__)


def _ensure_date(value: Any) -> Optional[date]:
    """Convert incoming values to ``date`` when posible."""
    if value is None:
        return None

    if isinstance(value, date):
        return value

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value).date()
        except ValueError:
            logger.warning("No se pudo convertir el valor '%s' a fecha", value)
            return None

    return None


def render_text_input(field: SimpleField, current_value: Any = None) -> Any:
    """Renderiza un campo de texto corto."""

    return st.text_input(
        label=field.nombre,
        value=current_value or "",
        placeholder=field.placeholder or "",
        help=field.ayuda,
        key=f"field_{field.id}",
    )


def render_long_text_input(field: SimpleField, current_value: Any = None) -> Any:
    """Renderiza un área de texto para descripciones más largas."""

    return st.text_area(
        label=field.nombre,
        value=current_value or "",
        placeholder=field.placeholder or "",
        help=field.ayuda,
        key=f"field_{field.id}",
        height=150,
    )


def render_number_input(field: SimpleField, current_value: Any = None) -> Any:
    """Renderiza un campo numérico con soporte para límites y decimales."""

    min_val = float(field.min) if field.min is not None else None
    max_val = float(field.max) if field.max is not None else None

    if current_value is not None:
        try:
            initial_value = float(current_value)
        except (TypeError, ValueError):
            initial_value = min_val or 0.0
    elif min_val is not None:
        initial_value = min_val
    else:
        initial_value = 0.0

    has_decimals = any(
        isinstance(val, float) and not float(val).is_integer()
        for val in (field.min, field.max, current_value)
    )
    step = 0.01 if has_decimals else 1.0

    number_input_args = {
        "label": field.nombre,
        "value": initial_value,
        "step": float(step),
        "help": field.ayuda,
        "key": f"field_{field.id}",
    }

    if min_val is not None:
        number_input_args["min_value"] = min_val
    if max_val is not None:
        number_input_args["max_value"] = max_val

    return st.number_input(**number_input_args)


def render_select_input(field: SimpleField, current_value: Any = None) -> Any:
    """Renderiza un selector de opciones para campos de lista."""

    if not field.opciones:
        st.warning(f"Campo '{field.nombre}' no tiene opciones definidas")
        return None

    options = field.opciones
    default_index = 0

    if current_value in options:
        default_index = options.index(current_value)

    return st.selectbox(
        label=field.nombre,
        options=options,
        index=default_index,
        help=field.ayuda,
        key=f"field_{field.id}",
    )


def render_date_input(field: SimpleField, current_value: Any = None) -> Optional[date]:
    """Renderiza un selector de fecha con calendario integrado."""

    initial_date = _ensure_date(current_value) or date.today()

    return st.date_input(
        label=field.nombre,
        value=initial_date,
        help=field.ayuda,
        key=f"field_{field.id}",
        format="YYYY-MM-DD",
    )


def render_date_group_input(
    fields_group: dict[str, SimpleField],
    current_values: dict[str, Any],
    group_name: str,
    group_label: str,
) -> dict[str, Any]:
    """Renderiza un selector de fecha para un grupo de campos (dia, mes, ano).

    Args:
        fields_group: Diccionario con claves 'dia', 'mes', 'ano' y sus campos correspondientes
        current_values: Valores actuales de los campos
        group_name: Nombre del grupo (para generar key única)
        group_label: Etiqueta visible para el selector

    Returns:
        Diccionario con valores de dia, mes, ano extraídos de la fecha seleccionada
    """
    # Obtener los IDs de los campos disponibles
    dia_field = fields_group.get("dia")
    mes_field = fields_group.get("mes")
    ano_field = fields_group.get("ano")

    # Construir fecha inicial desde valores actuales
    initial_date = None

    if dia_field and mes_field and ano_field:
        dia_val = current_values.get(dia_field.id)
        mes_val = current_values.get(mes_field.id)
        ano_val = current_values.get(ano_field.id)

        # Intentar construir fecha desde dia, mes, ano
        if dia_val and mes_val and ano_val:
            try:
                # Mapeo de nombres de meses en español
                meses_es = {
                    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
                    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
                    "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12
                }
                mes_num = meses_es.get(str(mes_val).lower(), None)
                if mes_num:
                    initial_date = date(int(ano_val), mes_num, int(dia_val))
            except (ValueError, TypeError):
                logger.warning(
                    "No se pudo construir fecha desde %s/%s/%s",
                    dia_val, mes_val, ano_val
                )
    elif mes_field and ano_field:
        # Solo mes y año, usar primer día del mes
        mes_val = current_values.get(mes_field.id)
        ano_val = current_values.get(ano_field.id)

        if mes_val and ano_val:
            try:
                meses_es = {
                    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
                    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
                    "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12
                }
                mes_num = meses_es.get(str(mes_val).lower(), None)
                if mes_num:
                    initial_date = date(int(ano_val), mes_num, 1)
            except (ValueError, TypeError):
                logger.warning(
                    "No se pudo construir fecha desde %s/%s",
                    mes_val, ano_val
                )

    if initial_date is None:
        initial_date = date.today()

    # Renderizar selector de fecha
    selected_date = st.date_input(
        label=group_label,
        value=initial_date,
        help=f"Selecciona la fecha usando el calendario",
        key=f"date_group_{group_name}",
        format="DD/MM/YYYY",
    )

    # Extraer componentes de la fecha
    result = {}

    # Mapeo inverso de números a nombres de meses
    meses_nombres = [
        "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
    ]

    if dia_field:
        result[dia_field.id] = selected_date.day

    if mes_field:
        result[mes_field.id] = meses_nombres[selected_date.month - 1]

    if ano_field:
        result[ano_field.id] = selected_date.year

    return result
