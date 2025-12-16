"""
Import Utils - Utilidades para importación de datos desde archivos

Funciones para importar datos desde archivos Excel (.xlsx, .xls) y Word (.docx)
para rellenar automáticamente formularios de generación de informes.

Formatos soportados:
    - Excel: Columna 1 = nombre de variable, Columna 2 = valor
    - Word: Formato "nombre_variable: valor" (uno por línea)
"""

import logging
from typing import Dict, Any, BinaryIO, Union
from datetime import datetime
import pandas as pd
from docx import Document

from .utils import setup_logger

logger = setup_logger(__name__)


def normalize_boolean_value(value: str) -> str:
    """
    Normaliza valores booleanos a 'sí' o 'no'.

    Convierte diferentes representaciones de sí/no a un formato estándar.

    Args:
        value: Valor a normalizar (puede ser 'SI', '1', 'SÍ', 'NO', '0', etc.)

    Returns:
        'sí' o 'no' según el valor de entrada

    Ejemplo:
        >>> normalize_boolean_value('SI')
        'sí'
        >>> normalize_boolean_value('0')
        'no'
        >>> normalize_boolean_value('true')
        'sí'
    """
    value_upper = str(value).strip().upper()

    # Valores que se consideran 'sí'
    yes_values = ['SI', 'SÍ', 'S', 'YES', 'Y', 'TRUE', 'T', '1', 'SÍ']

    # Valores que se consideran 'no'
    no_values = ['NO', 'N', 'FALSE', 'F', '0']

    if value_upper in yes_values:
        return 'sí'
    elif value_upper in no_values:
        return 'no'
    else:
        # Si no es reconocido como booleano, devolver el valor original
        return str(value).strip()


def normalize_variable_name(var_name: str) -> str:
    """
    Normaliza el nombre de una variable.

    Elimina acentos y espacios para estandarizar nombres de variables.

    Args:
        var_name: Nombre de variable a normalizar

    Returns:
        Nombre normalizado sin acentos

    Ejemplo:
        >>> normalize_variable_name('Comisión')
        'comision'
        >>> normalize_variable_name('Órgano de Administración')
        'organo_de_administracion'
    """
    # Mapeo de caracteres acentuados
    accent_map = {
        'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
        'Á': 'A', 'É': 'E', 'Í': 'I', 'Ó': 'O', 'Ú': 'U',
        'ñ': 'n', 'Ñ': 'N'
    }

    normalized = var_name.lower().strip()

    for accented, unaccented in accent_map.items():
        normalized = normalized.replace(accented, unaccented)

    # Reemplazar espacios por guiones bajos
    normalized = normalized.replace(' ', '_')

    return normalized


def process_excel_file(file: BinaryIO) -> Dict[str, Any]:
    """
    Procesa un archivo Excel y extrae variables y valores.

    Formato esperado:
        - Columna 1: Nombre de la variable
        - Columna 2: Valor de la variable
        - Las filas vacías se ignoran

    Args:
        file: Archivo Excel en formato binario (BinaryIO)

    Returns:
        Diccionario con nombres de variables y sus valores

    Ejemplo de Excel:
        | Nombre_Cliente | ABC S.A.           |
        | Fecha_de_hoy   | 31/12/2024         |
        | comision       | SI                 |
        | organo         | consejo            |

    Retorna:
        {
            'Nombre_Cliente': 'ABC S.A.',
            'Fecha_de_hoy': '31/12/2024',
            'comision': 'sí',
            'organo': 'consejo'
        }
    """
    extracted_data = {}

    try:
        # Leer Excel con pandas (sin encabezados)
        df = pd.read_excel(file, header=None, engine='openpyxl')

        # Verificar que tenga al menos 2 columnas
        if df.shape[1] < 2:
            logger.warning("El archivo Excel debe tener al menos 2 columnas")
            return {}

        # Iterar por las filas
        for index, row in df.iterrows():
            if pd.notna(row[0]) and pd.notna(row[1]):
                var_name = str(row[0]).strip()
                var_value = row[1]

                # Si es una fecha/datetime, convertirla a string
                if pd.api.types.is_datetime64_any_dtype(type(var_value)) or isinstance(var_value, datetime):
                    var_value = var_value.strftime("%d/%m/%Y")
                else:
                    var_value = str(var_value).strip()

                # Normalizar valores booleanos
                var_value = normalize_boolean_value(var_value)

                # Almacenar con el nombre original
                extracted_data[var_name] = var_value

        logger.info(f"Se importaron {len(extracted_data)} variables desde Excel")

    except Exception as e:
        logger.error(f"Error al procesar archivo Excel: {str(e)}")
        return {}

    return extracted_data


def process_word_file(file: BinaryIO) -> Dict[str, Any]:
    """
    Procesa un archivo Word y extrae variables y valores.

    Formato esperado:
        Cada párrafo debe seguir el formato: "nombre_variable: valor"
        Las líneas que no sigan este formato se ignoran.

    Args:
        file: Archivo Word en formato binario (BinaryIO)

    Returns:
        Diccionario con nombres de variables y sus valores

    Ejemplo de Word:
        Nombre_Cliente: ABC S.A.
        Fecha_de_hoy: 31/12/2024
        comision: SI
        organo: consejo

    Retorna:
        {
            'Nombre_Cliente': 'ABC S.A.',
            'Fecha_de_hoy': '31/12/2024',
            'comision': 'sí',
            'organo': 'consejo'
        }
    """
    extracted_data = {}

    try:
        # Leer documento Word
        doc = Document(file)

        # Extraer texto de todos los párrafos
        for paragraph in doc.paragraphs:
            text = paragraph.text.strip()
            if text and ':' in text:
                # Dividir por el primer ':' encontrado
                parts = text.split(':', 1)
                if len(parts) == 2:
                    var_name = parts[0].strip()
                    var_value = parts[1].strip()

                    # Normalizar valores booleanos
                    var_value = normalize_boolean_value(var_value)

                    # Almacenar con el nombre original
                    extracted_data[var_name] = var_value

        logger.info(f"Se importaron {len(extracted_data)} variables desde Word")

    except Exception as e:
        logger.error(f"Error al procesar archivo Word: {str(e)}")
        return {}

    return extracted_data


def process_uploaded_file(file: BinaryIO, file_type: str) -> Dict[str, Any]:
    """
    Procesa un archivo subido (Excel o Word) y extrae variables.

    Esta es la función principal que delega al procesador apropiado
    según el tipo de archivo.

    Args:
        file: Archivo en formato binario
        file_type: Tipo de archivo ('excel' o 'word')

    Returns:
        Diccionario con las variables extraídas y sus valores

    Ejemplo:
        >>> with open('datos.xlsx', 'rb') as f:
        ...     datos = process_uploaded_file(f, 'excel')
        >>> print(datos)
        {'Nombre_Cliente': 'ABC S.A.', 'comision': 'sí', ...}
    """
    if file_type.lower() == 'excel':
        return process_excel_file(file)
    elif file_type.lower() == 'word':
        return process_word_file(file)
    else:
        logger.error(f"Tipo de archivo no soportado: {file_type}")
        return {}


def map_imported_data_to_fields(
    imported_data: Dict[str, Any],
    field_definitions: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Mapea datos importados a campos definidos en el formulario.

    Permite mapear nombres de variables alternativos o normalizados
    a los nombres exactos esperados por el sistema.

    Args:
        imported_data: Datos importados del archivo
        field_definitions: Definiciones de campos del formulario (IDs válidos)

    Returns:
        Diccionario con variables mapeadas correctamente

    Ejemplo:
        >>> imported = {'comisión': 'sí', 'órgano': 'consejo'}
        >>> fields = {'comision': ..., 'organo': ...}
        >>> mapped = map_imported_data_to_fields(imported, fields)
        >>> print(mapped)
        {'comision': 'sí', 'organo': 'consejo'}
    """
    mapped_data = {}

    # Crear un mapeo de nombres normalizados a nombres originales
    field_map = {}
    for field_id in field_definitions.keys():
        normalized = normalize_variable_name(field_id)
        field_map[normalized] = field_id
        field_map[field_id] = field_id  # También mantener el original

    # Mapear los datos importados
    for var_name, var_value in imported_data.items():
        # Intentar primero con el nombre original
        if var_name in field_map:
            mapped_name = field_map[var_name]
            mapped_data[mapped_name] = var_value
        else:
            # Intentar con el nombre normalizado
            normalized = normalize_variable_name(var_name)
            if normalized in field_map:
                mapped_name = field_map[normalized]
                mapped_data[mapped_name] = var_value
            else:
                # Si no coincide con ningún campo, mantener el nombre original
                mapped_data[var_name] = var_value
                logger.warning(f"Variable '{var_name}' no coincide con ningún campo definido")

    return mapped_data
