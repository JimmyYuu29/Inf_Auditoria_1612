"""
Schema Models - Modelos Pydantic para configuración

Define las estructuras de datos genéricas para campos, bloques de texto,
tablas y configuración general de la plataforma.
"""

from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, validator


# ==============================================================================
# MODELOS PARA CAMPOS SIMPLES
# ==============================================================================

class FieldDependency(BaseModel):
    """Dependencia de un campo respecto a otro."""
    variable: str = Field(description="Variable de la cual depende")
    valor: Optional[str] = Field(None, description="Valor esperado para activar")
    valor_no: Optional[str] = Field(None, description="Valor que NO debe tener")


class SimpleField(BaseModel):
    """
    Definición de un campo simple de entrada.

    Representa un campo que el usuario debe completar en el formulario.
    Soporta tanto campos en español (nombre/tipo) como en inglés (label/type).
    """
    id: str = Field(description="Identificador único del campo")
    nombre: str = Field(alias='label', description="Etiqueta visible para el usuario")
    tipo: str = Field(alias='type', description="Tipo de control UI")
    marker: Optional[str] = Field(None, description="Marcador en plantilla Word")
    requerido: bool = Field(False, alias='required', description="Si el campo es obligatorio")
    opcional: bool = Field(False, alias='optional', description="Si el campo es opcional")
    placeholder: Optional[str] = Field(None, description="Texto placeholder")
    ayuda: Optional[str] = Field(None, description="Texto de ayuda")
    seccion: Optional[str] = Field(None, description="Sección UI donde aparece")
    grupo: Optional[str] = Field(None, description="Grupo de campos relacionados")
    opciones: Optional[List[str]] = Field(None, description="Opciones para lista")
    min: Optional[float] = Field(None, description="Valor mínimo para números")
    max: Optional[float] = Field(None, description="Valor máximo para números")
    formula: Optional[str] = Field(None, description="Fórmula para campos calculados")
    calculado: bool = Field(False, description="Si el campo se calcula automáticamente")
    ambito: Optional[str] = Field("global", description="Ámbito del campo (global/local)")
    dependencia: Optional[FieldDependency] = Field(None, description="Dependencia condicional")
    condicion_padre: Optional[str] = Field(None, description="Condición para mostrar")

    class Config:
        populate_by_name = True  # Permite usar tanto el nombre como el alias


# ==============================================================================
# MODELOS PARA VARIABLES CONDICIONALES
# ==============================================================================

class ConditionalOption(BaseModel):
    """Opción de una variable condicional."""
    valor: str = Field(description="Valor de la opción")
    etiqueta: str = Field(description="Texto visible")
    descripcion: Optional[str] = Field(None, description="Descripción detallada")
    es_default: bool = Field(False, description="Si es la opción por defecto")
    titulo_informe: Optional[str] = Field(None, description="Título asociado")
    variables_asociadas: Optional[List[str]] = Field(None, description="Variables dependientes")


class ConditionalVariable(BaseModel):
    """Variable condicional que controla el flujo.
    Soporta tanto formato español como inglés."""
    id: str = Field(description="Identificador único")
    nombre: str = Field(alias='label', description="Nombre descriptivo")
    descripcion: Optional[str] = Field(None, description="Explicación de la variable")
    tipo_control: str = Field(default="radio", description="Tipo de control UI")
    marker: Optional[str] = Field(None, description="Marcador en plantilla Word")
    word_file: Optional[str] = Field(None, description="Archivo Word condicional")
    requerido: bool = Field(False, description="Si es obligatorio")
    seccion: Optional[str] = Field(None, description="Sección UI")
    opciones: Optional[List[ConditionalOption]] = Field(None, description="Opciones disponibles")
    dependencia: Optional[FieldDependency] = Field(None, description="Dependencia condicional")

    class Config:
        populate_by_name = True  # Permite usar tanto el nombre como el alias


# ==============================================================================
# MODELOS PARA BLOQUES DE TEXTO
# ==============================================================================

class BlockRule(BaseModel):
    """Regla de un bloque de texto."""
    cuando: str = Field(description="Condición a evaluar (expresión Python)")
    plantilla: str = Field(description="Plantilla Jinja2 si se cumple la condición")


class BlockDefinition(BaseModel):
    """
    Definición de un bloque de texto condicional.
    
    Un bloque evalúa múltiples reglas y devuelve el texto de la primera que coincida.
    """
    id: str = Field(description="Identificador único del bloque")
    descripcion: Optional[str] = Field(None, description="Explicación del propósito")
    reglas: List[BlockRule] = Field(description="Lista de reglas condicionales")


# ==============================================================================
# MODELOS PARA TABLAS
# ==============================================================================

class TableColumn(BaseModel):
    """Definición de una columna de tabla."""
    id: str = Field(description="Identificador de la columna")
    nombre: str = Field(description="Nombre visible")
    tipo: Literal["texto", "numero", "fecha", "lista"] = Field(description="Tipo de dato")
    requerido: bool = Field(False, description="Si es obligatoria")
    opciones: Optional[List[str]] = Field(None, description="Opciones para listas")


class TableDefinition(BaseModel):
    """Definición de una tabla dinámica."""
    id: str = Field(description="Identificador único de la tabla")
    nombre: str = Field(description="Nombre visible")
    descripcion: Optional[str] = Field(None, description="Explicación de la tabla")
    columnas: List[TableColumn] = Field(description="Definición de columnas")
    min_filas: int = Field(0, description="Mínimo de filas requeridas")
    max_filas: Optional[int] = Field(None, description="Máximo de filas permitidas")


# ==============================================================================
# MODELOS PARA MANIFEST
# ==============================================================================

class ManifestPaths(BaseModel):
    """Paths de recursos del plugin."""
    template: str = Field(description="Path relativo a la plantilla Word")
    config_dir: str = Field(description="Path relativo al directorio de configuración")


class Manifest(BaseModel):
    """
    Manifest de un plugin de informe.
    
    Define los metadatos y rutas de un tipo de informe.
    """
    id: str = Field(description="Identificador único del plugin")
    nombre: str = Field(description="Nombre visible del informe")
    version: str = Field(description="Versión del plugin")
    descripcion: Optional[str] = Field(None, description="Descripción detallada")
    autor: Optional[str] = Field(None, description="Autor del plugin")
    paths: ManifestPaths = Field(description="Rutas de recursos")
    
    @validator('id')
    def validate_id(cls, v):
        """Valida que el ID sea un identificador válido."""
        if not v.replace('_', '').isalnum():
            raise ValueError("El ID solo puede contener letras, números y guiones bajos")
        return v


# ==============================================================================
# MODELOS PARA CONFIGURACIÓN GENERAL
# ==============================================================================

class ValidationRule(BaseModel):
    """Regla de validación."""
    tipo: str = Field(description="Tipo de validación")
    mensaje: str = Field(description="Mensaje de error")
    regla: Optional[str] = Field(None, description="Expresión de la regla")


class GeneralConfig(BaseModel):
    """Configuración general del sistema."""
    version: str = Field(description="Versión de la configuración")
    validaciones: Optional[List[ValidationRule]] = Field(None, description="Reglas de validación")
    secciones_orden: Optional[List[str]] = Field(None, description="Orden de secciones en UI")


# ==============================================================================
# FUNCIONES DE UTILIDAD
# ==============================================================================

def validate_field_dict(data: Dict[str, Any]) -> SimpleField:
    """
    Valida y convierte un diccionario en un SimpleField.
    
    Args:
        data: Diccionario con datos del campo
    
    Returns:
        SimpleField validado
    """
    return SimpleField(**data)


def validate_block_dict(data: Dict[str, Any]) -> BlockDefinition:
    """
    Valida y convierte un diccionario en un BlockDefinition.
    
    Args:
        data: Diccionario con datos del bloque
    
    Returns:
        BlockDefinition validado
    """
    return BlockDefinition(**data)


def validate_manifest_dict(data: Dict[str, Any]) -> Manifest:
    """
    Valida y convierte un diccionario en un Manifest.
    
    Args:
        data: Diccionario con datos del manifest
    
    Returns:
        Manifest validado
    """
    return Manifest(**data)
