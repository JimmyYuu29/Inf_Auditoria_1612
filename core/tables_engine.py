"""
Tables Engine - Motor de validación de estructuras de tabla

Valida datos tabulares según definiciones de esquema y proporciona
utilidades para trabajar con tablas dinámicas.
"""

from typing import Dict, Any, List, Optional
from report_platform.core.utils import setup_logger
from report_platform.core.schema_models import TableDefinition, TableColumn

logger = setup_logger(__name__)


# ==============================================================================
# VALIDACIÓN DE TABLAS
# ==============================================================================

def validate_table_data(table_def: TableDefinition, 
                       data: List[Dict[str, Any]]) -> tuple[bool, List[str]]:
    """
    Valida datos de tabla según su definición.
    
    Args:
        table_def: Definición de la tabla
        data: Lista de filas (cada fila es un diccionario)
    
    Returns:
        Tupla (es_válido, lista_de_errores)
    """
    errors = []
    
    # Validar número de filas
    num_rows = len(data)
    
    if num_rows < table_def.min_filas:
        errors.append(f"Tabla '{table_def.id}': se requieren al menos {table_def.min_filas} filas, "
                     f"pero solo hay {num_rows}")
    
    if table_def.max_filas and num_rows > table_def.max_filas:
        errors.append(f"Tabla '{table_def.id}': máximo {table_def.max_filas} filas permitidas, "
                     f"pero hay {num_rows}")
    
    # Validar cada fila
    for row_idx, row in enumerate(data):
        row_errors = validate_table_row(table_def, row, row_idx)
        errors.extend(row_errors)
    
    is_valid = len(errors) == 0
    return is_valid, errors


def validate_table_row(table_def: TableDefinition, row: Dict[str, Any], 
                       row_idx: int) -> List[str]:
    """
    Valida una fila de tabla.
    
    Args:
        table_def: Definición de la tabla
        row: Diccionario con los datos de la fila
        row_idx: Índice de la fila (para mensajes de error)
    
    Returns:
        Lista de mensajes de error
    """
    errors = []
    
    for column in table_def.columnas:
        # Verificar columnas requeridas
        if column.requerido and column.id not in row:
            errors.append(f"Tabla '{table_def.id}', fila {row_idx + 1}: "
                         f"falta columna requerida '{column.nombre}'")
            continue
        
        if column.id not in row:
            continue
        
        value = row[column.id]
        
        # Validar tipo de dato
        error = validate_column_value(column, value, row_idx)
        if error:
            errors.append(f"Tabla '{table_def.id}', fila {row_idx + 1}: {error}")
    
    return errors


def validate_column_value(column: TableColumn, value: Any, 
                         row_idx: int) -> Optional[str]:
    """
    Valida el valor de una columna.
    
    Args:
        column: Definición de la columna
        value: Valor a validar
        row_idx: Índice de la fila
    
    Returns:
        Mensaje de error o None si es válido
    """
    # Validar según tipo
    if column.tipo == "numero":
        try:
            float(value)
        except (ValueError, TypeError):
            return f"Columna '{column.nombre}' debe ser numérica, pero es '{value}'"
    
    elif column.tipo == "lista":
        if column.opciones and value not in column.opciones:
            return (f"Columna '{column.nombre}' debe ser una de {column.opciones}, "
                   f"pero es '{value}'")
    
    # TODO: Agregar validaciones para fecha y otros tipos
    
    return None


# ==============================================================================
# CONSTRUCCIÓN DE TABLAS
# ==============================================================================

def create_empty_table_row(table_def: TableDefinition) -> Dict[str, Any]:
    """
    Crea una fila vacía según la definición de tabla.
    
    Args:
        table_def: Definición de la tabla
    
    Returns:
        Diccionario con valores por defecto
    """
    row = {}
    for column in table_def.columnas:
        if column.tipo == "numero":
            row[column.id] = 0
        elif column.tipo == "lista" and column.opciones:
            row[column.id] = column.opciones[0]
        else:
            row[column.id] = ""
    
    return row


def create_table_template(table_def: TableDefinition, 
                         num_rows: int = 1) -> List[Dict[str, Any]]:
    """
    Crea una tabla template con filas vacías.
    
    Args:
        table_def: Definición de la tabla
        num_rows: Número de filas a crear
    
    Returns:
        Lista de filas vacías
    """
    return [create_empty_table_row(table_def) for _ in range(num_rows)]


# ==============================================================================
# CONVERSIÓN DE TABLAS
# ==============================================================================

def table_to_dict_list(table_data: List[List[Any]], 
                       column_ids: List[str]) -> List[Dict[str, Any]]:
    """
    Convierte tabla en formato lista de listas a lista de diccionarios.
    
    Args:
        table_data: Datos en formato [[val1, val2], [val3, val4], ...]
        column_ids: IDs de las columnas
    
    Returns:
        Lista de diccionarios [{col1: val1, col2: val2}, ...]
    """
    result = []
    for row in table_data:
        if len(row) != len(column_ids):
            logger.warning(f"Fila con número incorrecto de columnas: {row}")
            continue
        
        row_dict = {col_id: val for col_id, val in zip(column_ids, row)}
        result.append(row_dict)
    
    return result


def dict_list_to_table(data: List[Dict[str, Any]], 
                      column_ids: List[str]) -> List[List[Any]]:
    """
    Convierte lista de diccionarios a formato tabla (lista de listas).
    
    Args:
        data: Lista de diccionarios
        column_ids: IDs de las columnas a extraer
    
    Returns:
        Datos en formato [[val1, val2], [val3, val4], ...]
    """
    result = []
    for row_dict in data:
        row = [row_dict.get(col_id, "") for col_id in column_ids]
        result.append(row)
    
    return result


# ==============================================================================
# PROCESAMIENTO DE TABLAS
# ==============================================================================

def filter_table_rows(data: List[Dict[str, Any]], 
                     condition: str) -> List[Dict[str, Any]]:
    """
    Filtra filas de tabla según una condición.
    
    Args:
        data: Lista de filas
        condition: Condición de filtrado (expresión Python)
    
    Returns:
        Lista filtrada de filas
    """
    from report_platform.core.conditions_engine import evaluate_condition
    
    filtered = []
    for row in data:
        if evaluate_condition(condition, row):
            filtered.append(row)
    
    return filtered


def sort_table_rows(data: List[Dict[str, Any]], 
                   sort_by: str, reverse: bool = False) -> List[Dict[str, Any]]:
    """
    Ordena filas de tabla por una columna.
    
    Args:
        data: Lista de filas
        sort_by: ID de la columna para ordenar
        reverse: Si True, orden descendente
    
    Returns:
        Lista ordenada de filas
    """
    try:
        return sorted(data, key=lambda x: x.get(sort_by, ""), reverse=reverse)
    except Exception as e:
        logger.error(f"Error ordenando tabla: {e}")
        return data


def aggregate_table_column(data: List[Dict[str, Any]], 
                          column_id: str, operation: str) -> Any:
    """
    Agrega una columna de tabla (suma, promedio, etc.).
    
    Args:
        data: Lista de filas
        column_id: ID de la columna
        operation: Operación ('sum', 'avg', 'min', 'max', 'count')
    
    Returns:
        Resultado de la agregación
    """
    values = [row.get(column_id) for row in data if row.get(column_id) is not None]
    
    if not values:
        return None
    
    if operation == 'sum':
        return sum(values)
    elif operation == 'avg':
        return sum(values) / len(values)
    elif operation == 'min':
        return min(values)
    elif operation == 'max':
        return max(values)
    elif operation == 'count':
        return len(values)
    else:
        logger.warning(f"Operación desconocida: {operation}")
        return None


# ==============================================================================
# EXPORTACIÓN DE TABLAS
# ==============================================================================

def table_to_markdown(table_def: TableDefinition, 
                     data: List[Dict[str, Any]]) -> str:
    """
    Convierte tabla a formato Markdown.
    
    Args:
        table_def: Definición de la tabla
        data: Datos de la tabla
    
    Returns:
        String en formato Markdown
    """
    # Encabezados
    headers = [col.nombre for col in table_def.columnas]
    header_row = "| " + " | ".join(headers) + " |"
    separator = "| " + " | ".join(["---"] * len(headers)) + " |"
    
    # Filas de datos
    rows = []
    for row_dict in data:
        values = [str(row_dict.get(col.id, "")) for col in table_def.columnas]
        row = "| " + " | ".join(values) + " |"
        rows.append(row)
    
    # Combinar todo
    table = "\n".join([header_row, separator] + rows)
    return table


def table_to_html(table_def: TableDefinition, 
                 data: List[Dict[str, Any]]) -> str:
    """
    Convierte tabla a formato HTML.
    
    Args:
        table_def: Definición de la tabla
        data: Datos de la tabla
    
    Returns:
        String en formato HTML
    """
    html = "<table>\n"
    
    # Encabezados
    html += "  <thead>\n    <tr>\n"
    for col in table_def.columnas:
        html += f"      <th>{col.nombre}</th>\n"
    html += "    </tr>\n  </thead>\n"
    
    # Filas
    html += "  <tbody>\n"
    for row_dict in data:
        html += "    <tr>\n"
        for col in table_def.columnas:
            value = row_dict.get(col.id, "")
            html += f"      <td>{value}</td>\n"
        html += "    </tr>\n"
    html += "  </tbody>\n"
    
    html += "</table>"
    return html
