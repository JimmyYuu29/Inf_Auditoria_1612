"""
Core - Núcleo genérico de la plataforma

Este módulo contiene toda la funcionalidad genérica y reutilizable
que es independiente de cualquier tipo específico de informe.

Módulos:
    - config_loader: Carga de manifests y archivos YAML
    - schema_models: Modelos Pydantic de datos
    - conditions_engine: Evaluación de expresiones condicionales
    - word_engine: Renderizado de documentos Word
    - tables_engine: Validación de tablas
    - ui_runtime: Generación dinámica de controles UI
    - utils: Utilidades generales
"""

from .config_loader import load_manifest, load_yaml_config
from .schema_models import SimpleField, BlockDefinition, Manifest

__all__ = [
    "load_manifest",
    "load_yaml_config",
    "SimpleField",
    "BlockDefinition",
    "Manifest",
]
