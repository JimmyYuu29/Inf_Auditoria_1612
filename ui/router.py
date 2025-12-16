"""
Router - Descubrimiento y carga de plugins de informes

Este módulo proporciona funciones para:
- Listar plugins disponibles en el directorio reports/
- Cargar la configuración de un plugin específico
- Obtener información y funciones del plugin
"""

import sys
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable

# Asegurar que el directorio raíz del proyecto esté en sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.utils import setup_logger
from core.config_loader import load_manifest, load_plugin_config
from core.schema_models import Manifest

logger = setup_logger(__name__)


def get_reports_dir() -> Path:
    """Obtiene el directorio de plugins/reports."""
    return PROJECT_ROOT / "reports"


def list_available_reports() -> List[Manifest]:
    """
    Lista todos los plugins de informes disponibles.

    Busca directorios en reports/ que contengan manifest.yaml válido.

    Returns:
        Lista de objetos Manifest de los plugins encontrados
    """
    reports_dir = get_reports_dir()
    manifests = []

    if not reports_dir.exists():
        logger.warning(f"Directorio de reports no encontrado: {reports_dir}")
        return manifests

    for plugin_dir in reports_dir.iterdir():
        # Ignorar archivos y directorios especiales
        if not plugin_dir.is_dir():
            continue
        if plugin_dir.name.startswith('_') or plugin_dir.name.startswith('.'):
            continue

        # Verificar si tiene manifest.yaml
        manifest_path = plugin_dir / "manifest.yaml"
        if not manifest_path.exists():
            continue

        # Cargar manifest
        manifest = load_manifest(plugin_dir)
        if manifest:
            manifests.append(manifest)
            logger.debug(f"Plugin encontrado: {manifest.id}")

    logger.info(f"Encontrados {len(manifests)} plugins de informes")
    return manifests


def load_report_plugin(report_id: str) -> Optional[Dict[str, Any]]:
    """
    Carga la configuración completa de un plugin.

    Args:
        report_id: ID del plugin (coincide con nombre del directorio)

    Returns:
        Diccionario con la configuración del plugin o None si hay error
    """
    reports_dir = get_reports_dir()
    plugin_dir = reports_dir / report_id

    if not plugin_dir.exists():
        logger.error(f"Plugin no encontrado: {report_id}")
        return None

    config = load_plugin_config(plugin_dir)
    if config:
        logger.info(f"Plugin cargado: {report_id}")
    return config


def get_build_context_function(plugin_config: Dict[str, Any]) -> Optional[Callable]:
    """
    Obtiene la función build_context del plugin.

    Args:
        plugin_config: Configuración del plugin

    Returns:
        Función build_context o None si no existe
    """
    try:
        plugin_dir = plugin_config['plugin_dir']
        manifest = plugin_config['manifest']

        # Importar dinámicamente el módulo logic del plugin
        import importlib.util

        logic_path = plugin_dir / "logic.py"
        if not logic_path.exists():
            logger.error(f"No se encontró logic.py en {plugin_dir}")
            return None

        spec = importlib.util.spec_from_file_location(
            f"reports.{manifest.id}.logic",
            logic_path
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)

        if hasattr(module, 'build_context'):
            logger.debug(f"Función build_context encontrada en {manifest.id}")
            return module.build_context

        logger.error(f"No se encontró build_context en {plugin_dir}/logic.py")
        return None

    except Exception as e:
        logger.error(f"Error importando build_context: {e}")
        return None


def get_template_path(plugin_config: Dict[str, Any]) -> Optional[Path]:
    """
    Obtiene la ruta completa a la plantilla del plugin.

    Args:
        plugin_config: Configuración del plugin

    Returns:
        Path a la plantilla o None si no existe
    """
    try:
        plugin_dir = plugin_config['plugin_dir']
        manifest = plugin_config['manifest']

        template_path = plugin_dir / manifest.paths.template

        if not template_path.exists():
            logger.error(f"Plantilla no encontrada: {template_path}")
            return None

        return template_path

    except Exception as e:
        logger.error(f"Error obteniendo ruta de plantilla: {e}")
        return None


def get_plugin_info(plugin_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Obtiene información resumida del plugin para mostrar en UI.

    Args:
        plugin_config: Configuración del plugin

    Returns:
        Diccionario con información del plugin
    """
    manifest = plugin_config.get('manifest')
    if not manifest:
        return {
            'id': 'unknown',
            'nombre': 'Plugin desconocido',
            'version': '0.0.0',
            'descripcion': '',
            'autor': '',
            'num_campos': 0,
            'num_condicionales': 0,
            'num_bloques': 0,
        }

    return {
        'id': manifest.id,
        'nombre': manifest.nombre,
        'version': manifest.version,
        'descripcion': manifest.descripcion or '',
        'autor': manifest.autor or '',
        'num_campos': len(plugin_config.get('simple_fields', [])),
        'num_condicionales': len(plugin_config.get('conditional_variables', [])),
        'num_bloques': len(plugin_config.get('text_blocks', [])),
    }
