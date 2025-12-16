"""
Word Engine - Motor de renderizado de documentos Word

Genera documentos Word a partir de plantillas con variables Jinja2.
Implementación placeholder que puede extenderse para soportar
renderizado completo de Word con formato preservado.
"""

from pathlib import Path
from typing import Dict, Any, Optional
from jinja2 import Environment, FileSystemLoader, BaseLoader
from core.utils import setup_logger, get_outputs_dir, safe_filename

logger = setup_logger(__name__)


# ==============================================================================
# RENDERIZADO BÁSICO DE PLANTILLAS
# ==============================================================================

def render_template_string(template_content: str, context: Dict[str, Any]) -> str:
    """
    Renderiza una plantilla como string con Jinja2.
    
    Args:
        template_content: Contenido de la plantilla
        context: Diccionario con variables
    
    Returns:
        Texto renderizado
    """
    try:
        env = Environment(loader=BaseLoader())
        template = env.from_string(template_content)
        return template.render(**context)
    except Exception as e:
        logger.error(f"Error renderizando plantilla: {e}")
        return ""


# ==============================================================================
# RENDERIZADO DE DOCUMENTOS WORD (PLACEHOLDER)
# ==============================================================================

def render_word_report(template_path: Path, context: Dict[str, Any],
                      output_filename: str) -> Optional[Path]:
    """
    Renderiza un informe Word desde una plantilla.

    Soporta dos motores:
    1. Motor XML (para plantillas con marcadores <<>>): Usado cuando context["_use_xml_engine"] == True
    2. Motor Jinja2 (docxtpl): Para plantillas con variables {{}}

    Args:
        template_path: Path a la plantilla Word (.docx)
        context: Diccionario con todas las variables
        output_filename: Nombre del archivo de salida

    Returns:
        Path al archivo generado o None si hay error
    """
    logger.info(f"Renderizando informe desde: {template_path}")

    try:
        # Verificar que la plantilla existe
        if not template_path.exists():
            logger.error(f"Plantilla no encontrada: {template_path}")
            return None

        # Obtener directorio de salida
        output_dir = get_outputs_dir()

        # Nombre seguro del archivo
        safe_name = safe_filename(output_filename)
        if not safe_name.endswith('.docx'):
            safe_name += '.docx'

        output_path = output_dir / safe_name

        # Verificar si se debe usar el motor XML
        use_xml_engine = context.get("_use_xml_engine", False)

        if use_xml_engine:
            # Usar motor XML para procesamiento complejo
            logger.info("Usando motor XML de Word para renderizado")
            return _render_with_xml_engine(template_path, context, output_path)
        else:
            # Usar motor Jinja2 (docxtpl) por defecto
            return _render_with_jinja2(template_path, context, output_path)

    except Exception as e:
        logger.error(f"Error generando informe: {e}")
        return None


def _render_with_jinja2(template_path: Path, context: Dict[str, Any],
                        output_path: Path) -> Optional[Path]:
    """
    Renderiza un documento usando docxtpl (motor Jinja2).

    Args:
        template_path: Path a la plantilla
        context: Contexto de variables
        output_path: Path de salida

    Returns:
        Path al archivo generado o None si hay error
    """
    try:
        from docxtpl import DocxTemplate

        # Cargar plantilla
        doc = DocxTemplate(str(template_path))

        # Renderizar con contexto
        # Filtrar valores None y metadata especial
        clean_context = {
            k: (v if v is not None else '')
            for k, v in context.items()
            if not k.startswith('_')
        }
        doc.render(clean_context)

        # Guardar documento
        doc.save(str(output_path))

        logger.info(f"✅ Informe Word generado exitosamente: {output_path}")
        return output_path

    except ImportError:
        logger.error("docxtpl no está instalado. Instalarlo con: pip install docxtpl")
        return None


def _render_with_xml_engine(template_path: Path, context: Dict[str, Any],
                            output_path: Path) -> Optional[Path]:
    """
    Renderiza un documento usando el motor XML (para procesamiento complejo).

    Utiliza el motor XML que soporta:
    - Marcadores <<>> en lugar de {{}}
    - Inserción de tablas dinámicas
    - Bloques condicionales de Word
    - Procesamiento avanzado de XML

    Args:
        template_path: Path a la plantilla
        context: Contexto de variables
        output_path: Path de salida

    Returns:
        Path al archivo generado o None si hay error
    """
    try:
        from core.xml_word_engine import XMLWordEngineAdapter
        from core.tp_tables_engine import TableBuilder

        # Extraer metadatos del contexto
        config_dir = Path(context.get("_config_dir", "."))
        table_inputs = context.get("_table_inputs", {})
        simple_inputs = context.get("_simple_inputs", {})
        condition_inputs = context.get("_condition_inputs", {})
        docs_to_insert = context.get("_docs_to_insert", [])
        cfg_simple = context.get("_cfg_simple", {})
        cfg_cond = context.get("_cfg_cond", {})
        cfg_tab = context.get("_cfg_tab", {})

        # Crear motor XML
        engine = XMLWordEngineAdapter(template_path)

        # 1. Reemplazar variables simples
        engine.replace_variables(context)

        # 2. Construir e insertar tablas
        if cfg_tab and table_inputs:
            table_builder = TableBuilder(cfg_tab, simple_inputs)
            tables_data = table_builder.build_all_tables(table_inputs)

            # Formato de tablas (se puede personalizar)
            table_format_config = {
                "font_size": 10,
                "header_bold": True,
                "borders": True
            }

            engine.insert_tables(tables_data, cfg_tab, table_format_config)

        # 3. Insertar bloques condicionales
        if docs_to_insert:
            engine.insert_conditional_blocks(docs_to_insert, config_dir)

        # 4. Eliminar secciones específicas basadas en condiciones
        if condition_inputs.get("desarrollo_discrepancias_formales", "No") != "Sí":
            if hasattr(engine, 'remove_discrepancias_formales_section'):
                engine.remove_discrepancias_formales_section()

        # 5. Procesar marcadores especiales
        engine.process_salto_markers()

        # 6. Procesar tabla de contenidos
        engine.process_table_of_contents()

        # 7. Limpieza final
        engine.clean_unused_markers()
        engine.clean_empty_paragraphs()
        engine.remove_empty_lines_at_page_start()
        engine.remove_empty_pages()
        engine.preserve_headers_and_footers()

        # 8. Insertar imágenes de fondo si están configuradas
        first_page_image = context.get("first_page_image_path")
        if first_page_image:
            img_path = Path(first_page_image)
            if img_path.exists():
                engine.insert_background_image(img_path, page_type="first")

        last_page_image = context.get("last_page_image_path")
        if last_page_image:
            img_path = Path(last_page_image)
            if img_path.exists():
                engine.insert_background_image(img_path, page_type="last")

        # 9. Guardar documento
        engine.save(output_path)

        logger.info(f"✅ Informe Word generado exitosamente con motor XML: {output_path}")
        return output_path

    except ImportError as e:
        logger.error(f"Error importando módulos necesarios: {e}")
        return None
    except Exception as e:
        logger.error(f"Error en motor XML: {e}")
        import traceback
        traceback.print_exc()
        return None


# ==============================================================================
# RENDERIZADO AVANZADO (FUTURO)
# ==============================================================================

def render_word_with_docxtpl(template_path: Path, context: Dict[str, Any], 
                             output_path: Path) -> bool:
    """
    Renderiza documento Word usando docxtpl (implementación futura).
    
    Esta función es un placeholder para una implementación futura que use
    la biblioteca docxtpl para renderizado completo de Word con formato.
    
    Args:
        template_path: Path a la plantilla Word
        context: Diccionario con variables
        output_path: Path del archivo de salida
    
    Returns:
        True si se generó correctamente
    """
    logger.warning("render_word_with_docxtpl: Función no implementada aún")
    return False


def render_word_with_python_docx(template_path: Path, context: Dict[str, Any], 
                                 output_path: Path) -> bool:
    """
    Renderiza documento Word usando python-docx (implementación futura).
    
    Esta función es un placeholder para una implementación futura que use
    python-docx para manipulación directa del documento.
    
    Args:
        template_path: Path a la plantilla Word
        context: Diccionario con variables
        output_path: Path del archivo de salida
    
    Returns:
        True si se generó correctamente
    """
    logger.warning("render_word_with_python_docx: Función no implementada aún")
    return False


# ==============================================================================
# VALIDACIÓN DE PLANTILLAS
# ==============================================================================

def validate_template(template_path: Path) -> bool:
    """
    Valida que una plantilla Word sea accesible.
    
    Args:
        template_path: Path a la plantilla
    
    Returns:
        True si la plantilla es válida
    """
    if not template_path.exists():
        logger.error(f"Plantilla no encontrada: {template_path}")
        return False
    
    if not template_path.is_file():
        logger.error(f"La ruta no es un archivo: {template_path}")
        return False
    
    # TODO: Agregar validaciones adicionales (formato Word, sintaxis Jinja2, etc.)
    
    return True


def get_template_variables(template_path: Path) -> list:
    """
    Extrae las variables utilizadas en una plantilla.
    
    Args:
        template_path: Path a la plantilla
    
    Returns:
        Lista de nombres de variables encontradas
    """
    import re
    
    try:
        with open(template_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Pattern para {{ variable }}
        pattern = r'\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}'
        variables = set(re.findall(pattern, content))
        
        return sorted(list(variables))
    
    except Exception as e:
        logger.error(f"Error extrayendo variables de plantilla: {e}")
        return []


# ==============================================================================
# UTILIDADES
# ==============================================================================

def create_sample_template(output_path: Path, variables: list) -> bool:
    """
    Crea una plantilla de ejemplo con las variables proporcionadas.
    
    Args:
        output_path: Path donde guardar la plantilla
        variables: Lista de nombres de variables
    
    Returns:
        True si se creó correctamente
    """
    try:
        content = "# Plantilla de Ejemplo\n\n"
        for var in variables:
            content += f"{{ {var} }}\n\n"
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Plantilla de ejemplo creada: {output_path}")
        return True
    
    except Exception as e:
        logger.error(f"Error creando plantilla de ejemplo: {e}")
        return False
