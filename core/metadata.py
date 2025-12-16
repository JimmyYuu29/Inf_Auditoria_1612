"""
Metadata - Gestión de metadatos de informes generados

Este módulo permite guardar y recuperar metadatos de los informes generados,
facilitando la reproducción y modificación de informes anteriores.
"""

import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

from report_platform.core.utils import setup_logger

logger = setup_logger(__name__)


# ==============================================================================
# MODELOS DE METADATOS
# ==============================================================================

class ReportMetadata(BaseModel):
    """
    Metadatos de un informe generado.

    Contiene toda la información necesaria para reproducir o modificar
    un informe previamente generado.
    """
    id: str = Field(description="ID único del registro de metadata")
    report_id: str = Field(description="ID del plugin/tipo de informe")
    report_name: str = Field(description="Nombre visible del informe")
    timestamp: str = Field(description="Fecha y hora de generación (ISO format)")
    template_version: str = Field(description="Versión del template usado")
    input_data: Dict[str, Any] = Field(description="Datos de entrada del usuario")
    output_path: str = Field(description="Ruta del archivo generado")
    output_filename: str = Field(description="Nombre del archivo generado")
    generated_by: Optional[str] = Field(None, description="Usuario que generó el informe")
    description: Optional[str] = Field(None, description="Descripción opcional del informe")

    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()}
    )


# ==============================================================================
# CONFIGURACIÓN DE PATHS
# ==============================================================================

def get_metadata_dir() -> Path:
    """
    Obtiene el directorio donde se guardan los metadatos.

    Returns:
        Path al directorio de metadatos
    """
    # Usar directorio en la raíz del proyecto
    metadata_dir = Path(__file__).resolve().parents[2] / "metadata"

    # Crear directorio si no existe
    metadata_dir.mkdir(exist_ok=True)

    return metadata_dir


def get_metadata_file() -> Path:
    """
    Obtiene el path del archivo JSON de metadatos.

    Returns:
        Path al archivo metadata.json
    """
    return get_metadata_dir() / "metadata.json"


# ==============================================================================
# FUNCIONES DE PERSISTENCIA
# ==============================================================================

def save_metadata(meta: ReportMetadata) -> None:
    """
    Guarda un registro de metadata al archivo JSON.

    Si el archivo existe, agrega el nuevo registro a la lista existente.
    Si no existe, crea el archivo con el primer registro.

    Args:
        meta: Metadatos del informe a guardar
    """
    metadata_file = get_metadata_file()

    try:
        # Leer metadatos existentes
        if metadata_file.exists():
            with open(metadata_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                records = data.get('reports', [])
        else:
            records = []

        # Agregar nuevo registro
        records.append(meta.model_dump())

        # Escribir de vuelta
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump({'reports': records}, f, ensure_ascii=False, indent=2)

        logger.info(f"Metadata guardado: {meta.id} ({meta.report_name})")

    except Exception as e:
        logger.error(f"Error guardando metadata: {e}")
        raise


def load_all_metadata() -> List[ReportMetadata]:
    """
    Carga todos los registros de metadata del archivo JSON.

    Returns:
        Lista de ReportMetadata, ordenada por timestamp descendente (más reciente primero)
    """
    metadata_file = get_metadata_file()

    try:
        if not metadata_file.exists():
            logger.info("No se encontró archivo de metadata")
            return []

        with open(metadata_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            records = data.get('reports', [])

        # Parsear a modelos Pydantic
        metadata_list = [ReportMetadata(**record) for record in records]

        # Ordenar por timestamp descendente (más reciente primero)
        metadata_list.sort(key=lambda m: m.timestamp, reverse=True)

        logger.info(f"Cargados {len(metadata_list)} registros de metadata")
        return metadata_list

    except Exception as e:
        logger.error(f"Error cargando metadata: {e}")
        return []


def load_metadata_by_report_id(report_id: str) -> List[ReportMetadata]:
    """
    Carga los registros de metadata de un tipo de informe específico.

    Args:
        report_id: ID del plugin/tipo de informe

    Returns:
        Lista de ReportMetadata filtrada por report_id
    """
    all_metadata = load_all_metadata()
    filtered = [m for m in all_metadata if m.report_id == report_id]

    logger.info(f"Encontrados {len(filtered)} registros para report_id '{report_id}'")
    return filtered


def load_metadata_by_id(metadata_id: str) -> Optional[ReportMetadata]:
    """
    Carga un registro específico de metadata por su ID.

    Args:
        metadata_id: ID único del registro

    Returns:
        ReportMetadata si se encuentra, None en caso contrario
    """
    all_metadata = load_all_metadata()

    for meta in all_metadata:
        if meta.id == metadata_id:
            return meta

    logger.warning(f"No se encontró metadata con id '{metadata_id}'")
    return None


def delete_metadata_by_id(metadata_id: str) -> bool:
    """
    Elimina un registro de metadata por su ID.

    Args:
        metadata_id: ID único del registro a eliminar

    Returns:
        True si se eliminó, False si no se encontró
    """
    metadata_file = get_metadata_file()

    try:
        if not metadata_file.exists():
            return False

        with open(metadata_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            records = data.get('reports', [])

        # Filtrar el registro a eliminar
        original_count = len(records)
        records = [r for r in records if r.get('id') != metadata_id]

        if len(records) == original_count:
            logger.warning(f"No se encontró metadata con id '{metadata_id}'")
            return False

        # Escribir de vuelta
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump({'reports': records}, f, ensure_ascii=False, indent=2)

        logger.info(f"Metadata eliminado: {metadata_id}")
        return True

    except Exception as e:
        logger.error(f"Error eliminando metadata: {e}")
        return False


# ==============================================================================
# UTILIDADES
# ==============================================================================

def generate_metadata_id() -> str:
    """
    Genera un ID único para un registro de metadata.

    Returns:
        String con timestamp + random suffix
    """
    from datetime import datetime
    import random
    import string

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

    return f"meta_{timestamp}_{suffix}"


def create_metadata(
    report_id: str,
    report_name: str,
    template_version: str,
    input_data: Dict[str, Any],
    output_path: Path,
    generated_by: Optional[str] = None,
    description: Optional[str] = None
) -> ReportMetadata:
    """
    Crea un objeto ReportMetadata a partir de los parámetros.

    Args:
        report_id: ID del plugin/tipo de informe
        report_name: Nombre visible del informe
        template_version: Versión del template
        input_data: Datos de entrada del usuario
        output_path: Path al archivo generado
        generated_by: Usuario que generó (opcional)
        description: Descripción del informe (opcional)

    Returns:
        ReportMetadata configurado
    """
    return ReportMetadata(
        id=generate_metadata_id(),
        report_id=report_id,
        report_name=report_name,
        timestamp=datetime.now().isoformat(),
        template_version=template_version,
        input_data=input_data,
        output_path=str(output_path),
        output_filename=output_path.name,
        generated_by=generated_by or "sistema",
        description=description
    )


def get_metadata_summary(meta: ReportMetadata) -> str:
    """
    Genera un resumen legible de un registro de metadata.

    Args:
        meta: Metadatos del informe

    Returns:
        String con resumen formateado
    """
    timestamp = datetime.fromisoformat(meta.timestamp)
    timestamp_str = timestamp.strftime("%d/%m/%Y %H:%M")

    summary = f"{meta.report_name} - {timestamp_str}"

    if meta.description:
        summary += f" - {meta.description}"

    return summary


# ==============================================================================
# EXPORT/IMPORT
# ==============================================================================

def export_metadata_to_file(metadata_list: List[ReportMetadata], output_path: Path) -> None:
    """
    Exporta una lista de metadata a un archivo JSON.

    Args:
        metadata_list: Lista de metadatos a exportar
        output_path: Path donde guardar el archivo
    """
    try:
        data = {'reports': [m.model_dump() for m in metadata_list]}

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"Exportados {len(metadata_list)} registros a {output_path}")

    except Exception as e:
        logger.error(f"Error exportando metadata: {e}")
        raise


def import_metadata_from_file(input_path: Path) -> List[ReportMetadata]:
    """
    Importa metadata desde un archivo JSON.

    Args:
        input_path: Path al archivo a importar

    Returns:
        Lista de ReportMetadata importados
    """
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            records = data.get('reports', [])

        metadata_list = [ReportMetadata(**record) for record in records]

        logger.info(f"Importados {len(metadata_list)} registros desde {input_path}")
        return metadata_list

    except Exception as e:
        logger.error(f"Error importando metadata: {e}")
        raise


# ==============================================================================
# TESTS
# ==============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("TESTS DE METADATA")
    print("=" * 70)

    # Crear metadata de prueba
    test_metadata = create_metadata(
        report_id="informe_auditoria",
        report_name="Informe de Auditoría de Cuentas Anuales",
        template_version="1.0.0",
        input_data={
            'tipo_opinion': 'favorable',
            'nombre_entidad': 'Test S.A.',
            'ano_cierre_ejercicio': 2024
        },
        output_path=Path("/tmp/test_informe_20240101.docx"),
        generated_by="test_user",
        description="Informe de prueba"
    )

    print("\n📄 Metadata creado:")
    print(f"   ID: {test_metadata.id}")
    print(f"   Informe: {test_metadata.report_name}")
    print(f"   Timestamp: {test_metadata.timestamp}")
    print(f"   Resumen: {get_metadata_summary(test_metadata)}")

    # Guardar
    print("\n💾 Guardando metadata...")
    save_metadata(test_metadata)

    # Cargar
    print("\n📖 Cargando metadata...")
    all_meta = load_all_metadata()
    print(f"   Total registros: {len(all_meta)}")

    # Filtrar por report_id
    print("\n🔍 Filtrando por report_id 'informe_auditoria'...")
    filtered = load_metadata_by_report_id("informe_auditoria")
    print(f"   Registros encontrados: {len(filtered)}")

    print("\n" + "=" * 70)
