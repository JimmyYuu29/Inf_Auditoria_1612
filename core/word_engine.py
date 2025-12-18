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
# AJUSTE DE FORMATO - LIMPIEZA DE LÍNEAS EN BLANCO
# ==============================================================================

def clean_blank_lines(text: str) -> str:
    """
    Limpia líneas en blanco excesivas de un texto.

    Garantiza que entre párrafos haya como máximo una línea en blanco.
    Elimina líneas en blanco al inicio y al final.

    Args:
        text: Texto a limpiar

    Returns:
        Texto limpio con formato ajustado
    """
    if not text or not isinstance(text, str):
        return text or ""

    import re

    # Normalizar saltos de línea
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    # Eliminar espacios en blanco al final de cada línea
    lines = [line.rstrip() for line in text.split('\n')]

    # Colapsar múltiples líneas en blanco a máximo una
    cleaned_lines = []
    prev_blank = False

    for line in lines:
        is_blank = len(line.strip()) == 0

        if is_blank:
            if not prev_blank:
                # Mantener una línea en blanco
                cleaned_lines.append('')
            prev_blank = True
        else:
            cleaned_lines.append(line)
            prev_blank = False

    # Eliminar líneas en blanco al inicio y al final
    while cleaned_lines and cleaned_lines[0] == '':
        cleaned_lines.pop(0)
    while cleaned_lines and cleaned_lines[-1] == '':
        cleaned_lines.pop()

    return '\n'.join(cleaned_lines)


def clean_context_formatting(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Limpia el formato de todos los valores de texto en el contexto.

    Aplica clean_blank_lines a todos los valores string para:
    - Eliminar líneas en blanco excesivas
    - Normalizar el espaciado entre párrafos
    - Eliminar espacios en blanco innecesarios

    Args:
        context: Diccionario de contexto

    Returns:
        Contexto con valores de texto formateados
    """
    cleaned = {}

    for key, value in context.items():
        if key.startswith('_'):
            # Preservar metadatos internos
            cleaned[key] = value
        elif isinstance(value, str):
            # Limpiar valores de texto
            cleaned[key] = clean_blank_lines(value)
        elif value is None:
            # Convertir None a string vacío
            cleaned[key] = ''
        else:
            # Preservar otros tipos
            cleaned[key] = value

    return cleaned


def remove_empty_paragraphs_from_docx(doc_path: Path, max_consecutive_empty: int = 1) -> bool:
    """
    Elimina párrafos vacíos consecutivos de un documento Word.

    Esta función procesa el documento después de la generación para limpiar
    los párrafos vacíos que pueden quedar cuando secciones condicionales
    no se muestran.

    Args:
        doc_path: Path al documento Word a procesar
        max_consecutive_empty: Máximo número de párrafos vacíos consecutivos permitidos

    Returns:
        True si se procesó correctamente, False si hubo error
    """
    try:
        from docx import Document
        from docx.oxml.ns import qn

        doc = Document(str(doc_path))
        body = doc.element.body

        # Lista para almacenar párrafos a eliminar
        paragraphs_to_remove = []
        consecutive_empty_count = 0

        for element in body:
            # Solo procesar elementos de párrafo (<w:p>)
            if element.tag == qn('w:p'):
                # Verificar si el párrafo está vacío
                text = ''.join(node.text or '' for node in element.iter(qn('w:t')))
                is_empty = len(text.strip()) == 0

                # También verificar si tiene contenido de tabla o imagen (preservar estos)
                has_table = element.find('.//' + qn('w:tbl')) is not None
                has_drawing = element.find('.//' + qn('w:drawing')) is not None
                has_picture = element.find('.//' + qn('w:pict')) is not None

                if is_empty and not has_table and not has_drawing and not has_picture:
                    consecutive_empty_count += 1
                    if consecutive_empty_count > max_consecutive_empty:
                        paragraphs_to_remove.append(element)
                else:
                    consecutive_empty_count = 0
            else:
                # Resetear contador para elementos no-párrafo (tablas, etc.)
                consecutive_empty_count = 0

        # Eliminar los párrafos marcados
        for para in paragraphs_to_remove:
            body.remove(para)

        # Guardar el documento procesado
        doc.save(str(doc_path))

        logger.info(f"Eliminados {len(paragraphs_to_remove)} párrafos vacíos excesivos de {doc_path.name}")
        return True

    except ImportError:
        logger.warning("python-docx no está instalado. No se puede limpiar párrafos vacíos.")
        return False
    except Exception as e:
        logger.error(f"Error limpiando párrafos vacíos: {e}")
        return False


def clean_document_spacing(doc_path: Path) -> bool:
    """
    Limpia el espaciado del documento de forma integral.

    Realiza las siguientes operaciones:
    1. Elimina párrafos vacíos consecutivos excesivos
    2. Elimina párrafos vacíos al inicio del documento
    3. Elimina párrafos vacíos al final del documento

    Args:
        doc_path: Path al documento Word a procesar

    Returns:
        True si se procesó correctamente, False si hubo error
    """
    try:
        from docx import Document
        from docx.oxml.ns import qn

        doc = Document(str(doc_path))
        body = doc.element.body

        def is_paragraph_empty(element) -> bool:
            """Verifica si un párrafo está vacío."""
            if element.tag != qn('w:p'):
                return False
            text = ''.join(node.text or '' for node in element.iter(qn('w:t')))
            has_table = element.find('.//' + qn('w:tbl')) is not None
            has_drawing = element.find('.//' + qn('w:drawing')) is not None
            has_picture = element.find('.//' + qn('w:pict')) is not None
            return len(text.strip()) == 0 and not has_table and not has_drawing and not has_picture

        def is_section_break(element) -> bool:
            """Verifica si el párrafo contiene un salto de sección."""
            return element.find('.//' + qn('w:sectPr')) is not None

        elements = list(body)
        paragraphs_to_remove = []

        # Fase 1: Eliminar párrafos vacíos al inicio (excepto si tienen salto de sección)
        for element in elements:
            if element.tag == qn('w:p'):
                if is_paragraph_empty(element) and not is_section_break(element):
                    paragraphs_to_remove.append(element)
                else:
                    break
            elif element.tag != qn('w:sectPr'):
                break

        # Fase 2: Eliminar párrafos vacíos consecutivos en el medio
        consecutive_empty = []
        for element in elements:
            if element in paragraphs_to_remove:
                continue

            if element.tag == qn('w:p'):
                if is_paragraph_empty(element) and not is_section_break(element):
                    consecutive_empty.append(element)
                else:
                    # Mantener máximo 1 párrafo vacío entre contenido
                    if len(consecutive_empty) > 1:
                        paragraphs_to_remove.extend(consecutive_empty[1:])
                    consecutive_empty = []
            else:
                # Para elementos no-párrafo (tablas), eliminar todos los párrafos vacíos antes
                if len(consecutive_empty) > 1:
                    paragraphs_to_remove.extend(consecutive_empty[1:])
                consecutive_empty = []

        # Fase 3: Eliminar párrafos vacíos al final
        reversed_elements = list(reversed(elements))
        for element in reversed_elements:
            if element in paragraphs_to_remove:
                continue

            if element.tag == qn('w:p'):
                if is_paragraph_empty(element) and not is_section_break(element):
                    paragraphs_to_remove.append(element)
                else:
                    break
            elif element.tag not in [qn('w:sectPr')]:
                break

        # Eliminar los párrafos marcados
        for para in paragraphs_to_remove:
            try:
                body.remove(para)
            except ValueError:
                pass  # Ya fue eliminado

        # Guardar el documento procesado
        doc.save(str(doc_path))

        logger.info(f"Limpieza de espaciado completada: {len(paragraphs_to_remove)} párrafos eliminados de {doc_path.name}")
        return True

    except ImportError:
        logger.warning("python-docx no está instalado. No se puede limpiar espaciado.")
        return False
    except Exception as e:
        logger.error(f"Error limpiando espaciado del documento: {e}")
        return False


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

        # Aplicar limpieza de formato al contexto
        # Esto elimina líneas en blanco excesivas de los bloques de texto
        formatted_context = clean_context_formatting(context)

        # Filtrar valores None y metadata especial
        clean_context = {
            k: (v if v is not None else '')
            for k, v in formatted_context.items()
            if not k.startswith('_')
        }

        logger.info("Aplicando ajuste de formato (limpieza de líneas en blanco)")
        doc.render(clean_context)

        # Guardar documento
        doc.save(str(output_path))

        # Post-procesamiento: limpiar párrafos vacíos excesivos del documento
        # Esto elimina espacios en blanco dejados por secciones condicionales no mostradas
        logger.info("Aplicando limpieza de espaciado del documento...")
        clean_document_spacing(output_path)

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
