"""
Plataforma de Generación de Informes

Sistema modular para generación automática de documentos basados en
plantillas Word, configuraciones YAML y lógica Python.

Versión: 1.2.0 (20251220)
"""

__version__ = "1.2.0"
__release_date__ = "20251220"
__author__ = "Jimmy - Forvis Mazars España"

# Exportar componentes principales del core
from core.config_loader import load_manifest, load_yaml_config
from core.schema_models import SimpleField, BlockDefinition, Manifest

__all__ = [
    "load_manifest",
    "load_yaml_config",
    "SimpleField",
    "BlockDefinition",
    "Manifest",
]
