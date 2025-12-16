"""
UI - Interfaz de usuario unificada

Proporciona la interfaz web Streamlit que se adapta dinámicamente
a los plugins de informes disponibles.
"""

from .router import list_available_reports, load_report_plugin

__all__ = ["list_available_reports", "load_report_plugin"]
