"""
Utils - Utilidades generales de la plataforma

Funciones auxiliares para logging, manejo de paths y otras operaciones comunes.
"""

import logging
from pathlib import Path
from typing import Optional
import sys
import locale
from datetime import datetime


def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Configura y devuelve un logger con formato estándar.
    
    Args:
        name: Nombre del logger
        level: Nivel de logging (default: INFO)
    
    Returns:
        Logger configurado
    """
    logger = logging.getLogger(name)
    
    # Evitar duplicar handlers si ya existe
    if logger.handlers:
        return logger
    
    logger.setLevel(level)
    
    # Handler para consola
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    
    # Formato del log
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    
    return logger


def get_project_root() -> Path:
    """
    Obtiene el directorio raíz del proyecto.
    
    Returns:
        Path al directorio raíz (donde está report_platform/)
    """
    # Desde este archivo (core/utils.py), subir dos niveles
    return Path(__file__).parent.parent.parent


def get_reports_dir() -> Path:
    """
    Obtiene el directorio de plugins de informes.
    
    Returns:
        Path al directorio reports/
    """
    return get_project_root() / "report_platform" / "reports"


def get_outputs_dir() -> Path:
    """
    Obtiene (y crea si no existe) el directorio de salida.
    
    Returns:
        Path al directorio de outputs
    """
    output_dir = Path("/mnt/user-data/outputs")
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def safe_filename(filename: str) -> str:
    """
    Convierte un string en un nombre de archivo seguro.
    
    Args:
        filename: Nombre de archivo original
    
    Returns:
        Nombre de archivo sanitizado
    """
    # Reemplazar caracteres problemáticos
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Limitar longitud
    if len(filename) > 200:
        filename = filename[:200]
    
    return filename.strip()


def load_text_file(filepath: Path, encoding: str = 'utf-8') -> Optional[str]:
    """
    Carga un archivo de texto de forma segura.
    
    Args:
        filepath: Path al archivo
        encoding: Codificación del archivo
    
    Returns:
        Contenido del archivo o None si hay error
    """
    try:
        with open(filepath, 'r', encoding=encoding) as f:
            return f.read()
    except Exception as e:
        logger = setup_logger(__name__)
        logger.error(f"Error leyendo archivo {filepath}: {e}")
        return None


def ensure_directory(directory: Path) -> bool:
    """
    Asegura que un directorio existe, creándolo si es necesario.

    Args:
        directory: Path al directorio

    Returns:
        True si el directorio existe o fue creado exitosamente
    """
    try:
        directory.mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        logger = setup_logger(__name__)
        logger.error(f"Error creando directorio {directory}: {e}")
        return False


def set_spanish_locale() -> None:
    """
    Configura el locale del sistema a español para formato de fechas.

    Intenta varios identificadores según el sistema operativo.
    Esta función permite que las fechas se formateen correctamente
    con nombres de meses en español (enero, febrero, marzo, etc.).

    Uso:
        >>> set_spanish_locale()
        >>> datetime.now().strftime("%d de %B de %Y")
        '02 de diciembre de 2025'
    """
    spanish_locales = [
        "es_ES.UTF-8",      # Linux, macOS
        "es_ES.utf8",       # Linux (alternativo)
        "es_ES",            # Windows >= 10
        "Spanish_Spain",    # Windows antiguos
        "Spanish"           # Recurso final
    ]

    for loc in spanish_locales:
        try:
            locale.setlocale(locale.LC_TIME, loc)
            logger = setup_logger(__name__)
            logger.debug(f"Locale configurado a: {loc}")
            return
        except locale.Error:
            continue

    # Si no se pudo configurar ninguno, loguear advertencia
    logger = setup_logger(__name__)
    logger.warning("No se pudo configurar el locale a español. Las fechas podrían aparecer en inglés.")


def parse_date_string(date_string: str) -> datetime:
    """
    Convierte un string de fecha a objeto datetime.

    Intenta múltiples formatos de fecha comunes en español e inglés.
    Si no puede parsear la fecha, devuelve la fecha actual.

    Args:
        date_string: String con la fecha en diversos formatos posibles

    Returns:
        Objeto datetime parseado o fecha actual si falla

    Formatos soportados:
        - 31/12/2024
        - 2024-12-31
        - 31-12-2024
        - 31 de diciembre de 2024
        - 2024/12/31
        - 31.12.2024
        - Y más...

    Ejemplo:
        >>> fecha = parse_date_string("31/12/2024")
        >>> fecha.year
        2024
        >>> fecha = parse_date_string("invalid")
        >>> # Devuelve datetime.now()
    """
    if not date_string or not isinstance(date_string, str):
        return datetime.now()

    # Intentar varios formatos de fecha
    date_formats = [
        "%d/%m/%Y",              # 31/12/2024
        "%Y-%m-%d",              # 2024-12-31
        "%d-%m-%Y",              # 31-12-2024
        "%d de %B de %Y",        # 31 de diciembre de 2024
        "%Y/%m/%d",              # 2024/12/31
        "%d.%m.%Y",              # 31.12.2024
        "%Y.%m.%d",              # 2024.12.31
        "%m/%d/%Y",              # 12/31/2024 (formato americano)
        "%Y/%d/%m",              # 2024/31/12
        "%d %B %Y",              # 31 diciembre 2024
        "%B %d, %Y",             # diciembre 31, 2024
    ]

    # Asegurar que el locale español esté configurado para parsear meses
    set_spanish_locale()

    for fmt in date_formats:
        try:
            return datetime.strptime(date_string.strip(), fmt)
        except (ValueError, AttributeError):
            continue

    # Si no se pudo parsear, loguear warning y devolver fecha actual
    logger = setup_logger(__name__)
    logger.warning(f"No se pudo parsear la fecha '{date_string}'. Usando fecha actual.")
    return datetime.now()
