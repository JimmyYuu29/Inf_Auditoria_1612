"""Input widgets helpers for Streamlit forms.

Este módulo centraliza la creación de controles de entrada para distintas
categorías de datos, ofreciendo experiencias más intuitivas como el selector
calendario para fechas. De esta forma, añadir nuevos tipos de campos o ajustar
su comportamiento visual es más sencillo y reutilizable desde la UI.

PATCH NOTES (minimally invasive):
- Avoid widget "value/index" being recomputed on every rerun when a stable `key`
  is used. This was causing values to "bounce back" (e.g., select/radio needing
  two clicks) and inputs appearing to reset.
- Session state is treated as the single source of truth:
  - Initialize defaults only once (when `key` not present).
  - Then always render widgets using the value stored in `st.session_state[key]`.
- Function signatures are preserved to remain compatible with existing callers.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

import streamlit as st

from core.schema_models import SimpleField
from core.utils import setup_logger

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


def _field_key(field: SimpleField, key_prefix: Optional[str] = None) -> str:
    """Stable session key for a field.

    Args:
        field: The field to generate a key for
        key_prefix: Optional prefix to make the key unique (for multi-instance fields)

    Returns:
        A unique key string for session state
    """
    base = f"field_{field.id}"
    return f"{key_prefix}__{base}" if key_prefix else base


def render_text_input(field: SimpleField, current_value: Any = None, key_prefix: Optional[str] = None) -> Any:
    """Renderiza un campo de texto corto.

    Note: Uses key-based session state only, no value= parameter to prevent
    'strong control overwrite' issues per design specification.

    Args:
        field: Field definition
        current_value: Initial value (used only for first initialization)
        key_prefix: Optional prefix for multi-instance fields
    """
    key = _field_key(field, key_prefix)

    # One-time initialization only
    if key not in st.session_state:
        st.session_state[key] = current_value or ""

    # Do NOT pass value= when using key= to avoid "strong control overwrite"
    return st.text_input(
        label=field.nombre,
        placeholder=field.placeholder or "",
        help=field.ayuda,
        key=key,
    )


def render_long_text_input(field: SimpleField, current_value: Any = None, key_prefix: Optional[str] = None) -> Any:
    """Renderiza un área de texto para descripciones más largas.

    Note: Uses key-based session state only, no value= parameter to prevent
    'strong control overwrite' issues per design specification.

    Args:
        field: Field definition
        current_value: Initial value (used only for first initialization)
        key_prefix: Optional prefix for multi-instance fields
    """
    key = _field_key(field, key_prefix)

    # One-time initialization only
    if key not in st.session_state:
        st.session_state[key] = current_value or ""

    # Do NOT pass value= when using key= to avoid "strong control overwrite"
    return st.text_area(
        label=field.nombre,
        placeholder=field.placeholder or "",
        help=field.ayuda,
        key=key,
        height=150,
    )


def _is_integer_field(field: SimpleField) -> bool:
    """Determina si un campo debe ser tratado como entero (sin decimales).

    Criterios:
    - Campos cuyo ID contiene 'numero_nota' (notas de auditoría)
    - Campos cuyo ID contiene 'periodo' o 'ano_' (años/períodos)
    - Campos cuyo ID contiene 'dia_' (días)
    - Campos con min y max que son enteros (ej: día 1-31)
    """
    field_id = field.id.lower()

    # Nota fields - always integers
    if 'numero_nota' in field_id:
        return True

    # Period and year fields - always integers
    if 'periodo' in field_id or 'ano_' in field_id:
        return True

    # Day fields - always integers
    if 'dia_' in field_id:
        return True

    # Monto/amount fields that should be integers (thousands of euros)
    if 'monto_' in field_id:
        return True

    # Check if min/max are integers
    if field.min is not None and field.max is not None:
        min_is_int = float(field.min).is_integer()
        max_is_int = float(field.max).is_integer()
        if min_is_int and max_is_int:
            return True

    return False


def render_number_input(field: SimpleField, current_value: Any = None, key_prefix: Optional[str] = None) -> Any:
    """Renderiza un campo numérico con soporte para límites y decimales.

    Note: For number_input, we must pass value= for proper initialization,
    but this is only the initial value used when session_state is empty.
    Streamlit's number_input handles this correctly when key= is provided.

    Args:
        field: Field definition
        current_value: Initial value (used only for first initialization)
        key_prefix: Optional prefix for multi-instance fields
    """
    key = _field_key(field, key_prefix)

    # Determine if this should be an integer field
    use_integer = _is_integer_field(field)

    min_val = float(field.min) if field.min is not None else None
    max_val = float(field.max) if field.max is not None else None

    # One-time initialization only
    if key not in st.session_state:
        if current_value is not None:
            try:
                initial_value = float(current_value)
            except (TypeError, ValueError):
                initial_value = min_val if min_val is not None else 0.0
        elif min_val is not None:
            initial_value = min_val
        else:
            initial_value = 0.0

        # Convert to int for integer fields
        if use_integer:
            st.session_state[key] = int(initial_value)
        else:
            st.session_state[key] = float(initial_value)

    # Decide step based on field type
    if use_integer:
        step = 1
        # Ensure stored value is an integer
        current_stored = st.session_state.get(key, 0)
        if isinstance(current_stored, float):
            st.session_state[key] = int(current_stored)
    else:
        # Check for decimal values in min/max/current
        has_decimals = any(
            isinstance(val, float) and not float(val).is_integer()
            for val in (field.min, field.max, st.session_state.get(key))
            if val is not None
        )
        step = 0.01 if has_decimals else 1.0

    # Build number_input arguments - no value= to let session_state control
    if use_integer:
        number_input_args = {
            "label": field.nombre,
            "step": step,
            "help": field.ayuda,
            "key": key,
            "format": "%d",  # Integer format
        }
    else:
        number_input_args = {
            "label": field.nombre,
            "step": float(step),
            "help": field.ayuda,
            "key": key,
        }

    if min_val is not None:
        number_input_args["min_value"] = int(min_val) if use_integer else min_val
    if max_val is not None:
        number_input_args["max_value"] = int(max_val) if use_integer else max_val

    return st.number_input(**number_input_args)


def render_select_input(field: SimpleField, current_value: Any = None, key_prefix: Optional[str] = None) -> Any:
    """Renderiza un selector de opciones para campos de lista.

    Args:
        field: Field definition
        current_value: Initial value (used only for first initialization)
        key_prefix: Optional prefix for multi-instance fields
    """
    if not field.opciones:
        st.warning(f"Campo '{field.nombre}' no tiene opciones definidas")
        return None

    key = _field_key(field, key_prefix)
    options = field.opciones

    # One-time initialization only
    if key not in st.session_state:
        if current_value in options:
            st.session_state[key] = current_value
        else:
            st.session_state[key] = options[0]

    # No `index=` recomputation: Streamlit will pick the value from session_state[key]
    return st.selectbox(
        label=field.nombre,
        options=options,
        help=field.ayuda,
        key=key,
    )


def render_date_input(field: SimpleField, current_value: Any = None, key_prefix: Optional[str] = None) -> Optional[date]:
    """Renderiza un selector de fecha con calendario integrado.

    Note: Uses key-based session state only, no value= parameter to prevent
    'strong control overwrite' issues per design specification.

    Args:
        field: Field definition
        current_value: Initial value (used only for first initialization)
        key_prefix: Optional prefix for multi-instance fields
    """
    key = _field_key(field, key_prefix)

    # One-time initialization only
    if key not in st.session_state:
        st.session_state[key] = _ensure_date(current_value) or date.today()

    # Do NOT pass value= when using key= to avoid "strong control overwrite"
    return st.date_input(
        label=field.nombre,
        help=field.ayuda,
        key=key,
        format="YYYY-MM-DD",
    )


def render_date_group_input(
    fields_group: dict[str, SimpleField],
    current_values: dict[str, Any],
    group_name: str,
    group_label: str,
    key_prefix: Optional[str] = None,
) -> dict[str, Any]:
    """Renderiza un selector de fecha para un grupo de campos (dia, mes, ano).

    Args:
        fields_group: Diccionario con claves 'dia', 'mes', 'ano' y sus campos correspondientes
        current_values: Valores actuales de los campos
        group_name: Nombre del grupo (para generar key única)
        group_label: Etiqueta visible para el selector
        key_prefix: Optional prefix for multi-instance fields

    Returns:
        Diccionario con valores de dia, mes, ano extraídos de la fecha seleccionada
    """
    dia_field = fields_group.get("dia")
    mes_field = fields_group.get("mes")
    ano_field = fields_group.get("ano")

    # Build initial_date only for first initialization
    initial_date = None

    def _mes_num(mes_val: Any) -> Optional[int]:
        meses_es = {
            "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
            "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
            "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
        }
        return meses_es.get(str(mes_val).lower(), None) if mes_val is not None else None

    if dia_field and mes_field and ano_field:
        dia_val = current_values.get(dia_field.id)
        mes_val = current_values.get(mes_field.id)
        ano_val = current_values.get(ano_field.id)

        if dia_val and mes_val and ano_val:
            try:
                mes_num = _mes_num(mes_val)
                if mes_num:
                    initial_date = date(int(ano_val), mes_num, int(dia_val))
            except (ValueError, TypeError):
                logger.warning(
                    "No se pudo construir fecha desde %s/%s/%s",
                    dia_val, mes_val, ano_val
                )

    elif mes_field and ano_field:
        mes_val = current_values.get(mes_field.id)
        ano_val = current_values.get(ano_field.id)

        if mes_val and ano_val:
            try:
                mes_num = _mes_num(mes_val)
                if mes_num:
                    initial_date = date(int(ano_val), mes_num, 1)
            except (ValueError, TypeError):
                logger.warning(
                    "No se pudo construir fecha desde %s/%s",
                    mes_val, ano_val
                )

    if initial_date is None:
        initial_date = date.today()

    base_key = f"date_group_{group_name}"
    group_key = f"{key_prefix}__{base_key}" if key_prefix else base_key

    # One-time initialization only
    if group_key not in st.session_state:
        st.session_state[group_key] = initial_date

    # Do NOT pass value= when using key= to avoid "strong control overwrite"
    selected_date = st.date_input(
        label=group_label,
        help="Selecciona la fecha usando el calendario",
        key=group_key,
        format="DD/MM/YYYY",
    )

    meses_nombres = [
        "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
    ]

    result: dict[str, Any] = {}
    if dia_field:
        result[dia_field.id] = selected_date.day
    if mes_field:
        result[mes_field.id] = meses_nombres[selected_date.month - 1]
    if ano_field:
        result[ano_field.id] = selected_date.year

    return result
