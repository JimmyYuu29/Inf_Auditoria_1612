"""
Plugin: Informe de Auditoría

Este plugin genera informes de auditoría de cuentas anuales según
normativa española y europea.

Características:
- Múltiples tipos de opinión (favorable, salvedades, desfavorable, denegada)
- Soporte para cuentas consolidadas y abreviadas
- Entidades de Interés Público (EIP)
- Cuestiones clave de auditoría (KAM/AMRA)
- Bloques de texto condicionales según normativa
"""

from .logic import build_context

__all__ = ["build_context"]
