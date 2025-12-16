"""
Config Loader - Carga de configuración desde YAML

Funciones para cargar y parsear archivos de configuración YAML,
incluyendo manifests, definiciones de campos y bloques de texto.
"""

import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from core.utils import setup_logger
from core.schema_models import (
    Manifest,
    SimpleField,
    ConditionalVariable,
    BlockDefinition,
    TableDefinition,
    validate_manifest_dict,
)

logger = setup_logger(__name__)


# ==============================================================================
# CARGA DE MANIFEST
# ==============================================================================

def load_manifest(plugin_dir: Path) -> Optional[Manifest]:
    """
    Carga y valida el manifest de un plugin.
    
    Args:
        plugin_dir: Directorio del plugin
    
    Returns:
        Manifest validado o None si hay error
    """
    manifest_path = plugin_dir / "manifest.yaml"
    
    if not manifest_path.exists():
        logger.error(f"No se encontró manifest.yaml en {plugin_dir}")
        return None
    
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        manifest = validate_manifest_dict(data)
        logger.info(f"Manifest cargado: {manifest.nombre} (v{manifest.version})")
        return manifest
    
    except Exception as e:
        logger.error(f"Error cargando manifest de {plugin_dir}: {e}")
        return None


# ==============================================================================
# CARGA DE ARCHIVOS YAML GENÉRICOS
# ==============================================================================

def load_yaml_config(filepath: Path) -> Optional[Dict[str, Any]]:
    """
    Carga un archivo YAML genérico.
    
    Args:
        filepath: Path al archivo YAML
    
    Returns:
        Diccionario con el contenido o None si hay error
    """
    if not filepath.exists():
        logger.warning(f"Archivo no encontrado: {filepath}")
        return None
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        logger.debug(f"YAML cargado: {filepath.name}")
        return data
    
    except Exception as e:
        logger.error(f"Error cargando YAML {filepath}: {e}")
        return None


# ==============================================================================
# CARGA DE CAMPOS SIMPLES
# ==============================================================================

def load_simple_fields(config_dir: Path) -> List[SimpleField]:
    """
    Carga las definiciones de campos simples.
    
    Args:
        config_dir: Directorio de configuración del plugin
    
    Returns:
        Lista de SimpleField
    """
    filepath = config_dir / "variables_simples.yaml"
    data = load_yaml_config(filepath)
    
    # Soportar ambas claves: 'variables_simples' (español) y 'simple_variables' (inglés)
    key = 'variables_simples' if 'variables_simples' in (data or {}) else 'simple_variables'

    if not data or key not in data:
        logger.warning(f"No se encontraron variables simples en {filepath}")
        return []

    fields = []
    for field_data in data[key]:
        try:
            field = SimpleField(**field_data)
            fields.append(field)
        except Exception as e:
            logger.warning(f"Error parseando campo {field_data.get('id', '?')}: {e}")
    
    logger.info(f"Cargados {len(fields)} campos simples")
    return fields


# ==============================================================================
# CARGA DE VARIABLES CONDICIONALES
# ==============================================================================

def load_conditional_variables(config_dir: Path) -> List[ConditionalVariable]:
    """
    Carga las definiciones de variables condicionales.
    
    Args:
        config_dir: Directorio de configuración del plugin
    
    Returns:
        Lista de ConditionalVariable
    """
    filepath = config_dir / "variables_condicionales.yaml"
    data = load_yaml_config(filepath)
    
    # Soportar ambas claves: 'variables_condicionales' (español) y 'conditions' (inglés)
    key = 'variables_condicionales' if 'variables_condicionales' in (data or {}) else 'conditions'

    if not data or key not in data:
        logger.warning(f"No se encontraron variables condicionales en {filepath}")
        return []

    variables = []
    for var_data in data[key]:
        try:
            variable = ConditionalVariable(**var_data)
            variables.append(variable)
        except Exception as e:
            logger.warning(f"Error parseando variable {var_data.get('id', '?')}: {e}")
    
    logger.info(f"Cargadas {len(variables)} variables condicionales")
    return variables


# ==============================================================================
# CARGA DE BLOQUES DE TEXTO
# ==============================================================================

def load_text_blocks(config_dir: Path) -> List[BlockDefinition]:
    """
    Carga las definiciones de bloques de texto condicionales.
    
    Args:
        config_dir: Directorio de configuración del plugin
    
    Returns:
        Lista de BlockDefinition
    """
    filepath = config_dir / "bloques_texto.yaml"
    data = load_yaml_config(filepath)
    
    if not data or 'bloques_texto' not in data:
        logger.warning(f"No se encontraron bloques_texto en {filepath}")
        return []
    
    blocks = []
    for block_data in data['bloques_texto']:
        try:
            block = BlockDefinition(**block_data)
            blocks.append(block)
        except Exception as e:
            logger.warning(f"Error parseando bloque {block_data.get('id', '?')}: {e}")
    
    logger.info(f"Cargados {len(blocks)} bloques de texto")
    return blocks


# ==============================================================================
# CARGA DE TABLAS
# ==============================================================================

def load_tables(config_dir: Path) -> List[TableDefinition]:
    """
    Carga las definiciones de tablas dinámicas.
    
    Args:
        config_dir: Directorio de configuración del plugin
    
    Returns:
        Lista de TableDefinition
    """
    filepath = config_dir / "tablas.yaml"
    data = load_yaml_config(filepath)
    
    if not data or 'tablas' not in data:
        logger.debug(f"No se encontraron definiciones de tablas en {filepath}")
        return []
    
    tables = []
    for table_data in data['tablas']:
        try:
            table = TableDefinition(**table_data)
            tables.append(table)
        except Exception as e:
            logger.warning(f"Error parseando tabla {table_data.get('id', '?')}: {e}")
    
    logger.info(f"Cargadas {len(tables)} tablas")
    return tables


# ==============================================================================
# CARGA COMPLETA DE PLUGIN
# ==============================================================================

def load_plugin_config(plugin_dir: Path) -> Optional[Dict[str, Any]]:
    """
    Carga toda la configuración de un plugin.
    
    Args:
        plugin_dir: Directorio del plugin
    
    Returns:
        Diccionario con toda la configuración o None si hay error
    """
    # Cargar manifest
    manifest = load_manifest(plugin_dir)
    if not manifest:
        return None
    
    # Directorio de configuración
    config_dir = plugin_dir / manifest.paths.config_dir
    
    if not config_dir.exists():
        logger.error(f"Directorio de configuración no encontrado: {config_dir}")
        return None
    
    # Cargar todos los componentes
    config = {
        'manifest': manifest,
        'plugin_dir': plugin_dir,
        'config_dir': config_dir,
        'simple_fields': load_simple_fields(config_dir),
        'conditional_variables': load_conditional_variables(config_dir),
        'text_blocks': load_text_blocks(config_dir),
        'tables': load_tables(config_dir),
    }
    
    logger.info(f"Configuración completa cargada para plugin: {manifest.id}")
    return config


# ==============================================================================
# OBTENCIÓN DE CONFIGURACIÓN GENERAL
# ==============================================================================

def get_general_config(config_dir: Path) -> Dict[str, Any]:
    """
    Obtiene la configuración general del archivo de variables simples.
    
    Args:
        config_dir: Directorio de configuración
    
    Returns:
        Diccionario con configuración general
    """
    filepath = config_dir / "variables_simples.yaml"
    data = load_yaml_config(filepath)
    
    if data and 'configuracion' in data:
        return data['configuracion']
    
    return {}


# ==============================================================================
# ORDENAMIENTO DE CAMPOS POR SECCIÓN
# ==============================================================================

def get_fields_by_section(fields: List[SimpleField]) -> Dict[str, List[SimpleField]]:
    """
    Agrupa campos por sección.
    
    Args:
        fields: Lista de campos
    
    Returns:
        Diccionario {seccion: [campos]}
    """
    sections: Dict[str, List[SimpleField]] = {}
    
    for field in fields:
        section = field.seccion or "Sin sección"
        if section not in sections:
            sections[section] = []
        sections[section].append(field)
    
    return sections
