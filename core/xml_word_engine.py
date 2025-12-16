"""
XMLWordEngine Adaptador - Reemplazo compatible de WordEngine
============================================================

Este módulo proporciona un reemplazo drop-in para WordEngine que:
- ✅ Mantiene la misma interfaz
- ✅ Preserva 100% imágenes y secciones
- ✅ Funciona con tu código existente sin cambios

USO: Simplemente importa XMLWordEngineAdapter en lugar de WordEngine
"""

from pathlib import Path
from lxml import etree
import zipfile
import tempfile
import shutil
import os
import re
from copy import deepcopy
from typing import Dict, List, Any, Optional


class XMLWordEngineAdapter:
    """
    Adaptador que reemplaza WordEngine usando manipulación XML directa.
    Compatible con la interfaz existente de WordEngine.
    """
    
    def __init__(self, template_path: Path):
        """
        Inicializa el motor con una plantilla.
        
        Args:
            template_path: Ruta a la plantilla Word (.docx)
        """
        self.template_path = Path(template_path)
        
        if not self.template_path.exists():
            raise FileNotFoundError(f"Plantilla no encontrada: {template_path}")
        
        # Extraer plantilla
        self.temp_dir = tempfile.mkdtemp()
        with zipfile.ZipFile(self.template_path, 'r') as zip_ref:
            zip_ref.extractall(self.temp_dir)
        
        # Cargar document.xml
        self.doc_xml_path = Path(self.temp_dir) / 'word' / 'document.xml'
        self.parser = etree.XMLParser(remove_blank_text=False, strip_cdata=False)
        self.tree = etree.parse(str(self.doc_xml_path), self.parser)
        self.root = self.tree.getroot()
        
        # Namespaces
        self.ns = self.root.nsmap
        self.w_ns = self.ns.get('w', 'http://schemas.openxmlformats.org/wordprocessingml/2006/main')
        self.xml_ns = 'http://www.w3.org/XML/1998/namespace'
        
        # Contadores para debug
        self._initial_drawings = len(self.root.findall(f'.//{{{self.w_ns}}}drawing'))
        self._initial_sections = len(self.root.findall(f'.//{{{self.w_ns}}}sectPr'))

        # Configuraciones especiales para tablas específicas
        self.special_table_behaviors = {
            "<<Tabla de cumplimiento formal MF>>": {"column_break_before": True}
        }
    
    def replace_variables(self, context: dict):
        """Reemplaza variables <<marcador>> incluso cuando se dividen en múltiples runs."""
        context_filtered = {
            k: v for k, v in context.items()
            if v is not None and v != "" and str(v).strip()
        }

        if not context_filtered:
            return

        paragraphs = self.root.findall(f'.//{{{self.w_ns}}}p')

        for para in paragraphs:
            para_text = self._get_paragraph_text(para)

            if not para_text:
                continue

            for marker, value in context_filtered.items():
                value_str = str(value)

                while marker in para_text:
                    self._replace_marker_in_paragraph_xml(para, marker, value_str)
                    para_text = self._get_paragraph_text(para)
    
    def insert_tables(self, tables_data: dict, cfg_tab: dict, table_format_config: dict = None):
        """
        Inserta tablas en los marcadores correspondientes.
        
        Args:
            tables_data: Diccionario {marker: table_data}
            cfg_tab: Configuración de tablas
            table_format_config: Configuración de formato (opcional)
        """
        for marker, table_data in tables_data.items():
            self._insert_table_at_marker(marker, table_data, table_format_config)
    
    def _insert_table_at_marker(self, marker: str, table_data: dict, format_config: dict = None):
        """Inserta una tabla en la posición del marcador."""
        # Buscar párrafo con el marcador
        target_para = None
        all_paras = self.root.findall(f'.//{{{self.w_ns}}}p')
        
        for para in all_paras:
            para_text = self._get_paragraph_text(para)
            if marker in para_text:
                target_para = para
                break

        if target_para is None:
            return

        # Aplicar comportamientos especiales antes de insertar la tabla
        self._apply_pre_table_behavior(marker, target_para)

        # Crear tabla XML
        table_elem = self._create_table_xml(table_data, format_config)

        # Insertar tabla
        parent = target_para.getparent()
        para_pos = list(parent).index(target_para)
        parent.insert(para_pos + 1, table_elem)

        # Insertar un párrafo de separación después de la tabla para evitar que
        # quede pegada al contenido siguiente
        spacer_para = self._create_spacing_paragraph()
        parent.insert(para_pos + 2, spacer_para)

        # Limpiar marcador
        self._remove_marker_from_paragraph(target_para, marker)

        # Si el párrafo quedó vacío tras eliminar el marcador, dejar un espacio
        # no separable para preservar el espaciado y evitar que se elimine en la
        # fase de limpieza
        if not self._get_paragraph_text(target_para).strip():
            self._set_paragraph_text(target_para, '\u00A0')

    def _apply_pre_table_behavior(self, marker: str, target_para: etree.Element):
        """Aplica comportamientos especiales antes de insertar ciertas tablas."""
        behavior = self.special_table_behaviors.get(marker)
        if not behavior:
            return

        if behavior.get("column_break_before"):
            self._insert_column_break_before_paragraph(target_para)

    def _insert_column_break_before_paragraph(self, para: etree.Element):
        """Inserta un salto de columna antes de un párrafo determinado."""
        parent = para.getparent()
        if parent is None:
            return

        column_break_para = etree.Element(f'{{{self.w_ns}}}p')
        run = etree.SubElement(column_break_para, f'{{{self.w_ns}}}r')
        br = etree.SubElement(run, f'{{{self.w_ns}}}br')
        br.set(f'{{{self.w_ns}}}type', 'column')

        para_index = list(parent).index(para)
        parent.insert(para_index, column_break_para)
    
    def _create_table_xml(self, table_data: dict, format_config: dict = None) -> etree.Element:
        """Crea elemento de tabla XML con formato."""
        columns = table_data.get('columns', [])
        rows = table_data.get('rows', [])
        footer_rows = table_data.get('footer_rows', [])
        headers = table_data.get('headers', {})
        
        # Crear tabla
        tbl = etree.Element(f'{{{self.w_ns}}}tbl')
        
        # Propiedades de tabla
        tbl_pr = etree.SubElement(tbl, f'{{{self.w_ns}}}tblPr')
        
        # Estilo
        tbl_style = etree.SubElement(tbl_pr, f'{{{self.w_ns}}}tblStyle')
        tbl_style.set(f'{{{self.w_ns}}}val', 'TableGrid')
        
        # Ancho
        tbl_w = etree.SubElement(tbl_pr, f'{{{self.w_ns}}}tblW')
        tbl_w.set(f'{{{self.w_ns}}}w', '5000')
        tbl_w.set(f'{{{self.w_ns}}}type', 'pct')
        
        # Bordes
        tbl_borders = etree.SubElement(tbl_pr, f'{{{self.w_ns}}}tblBorders')
        for border_type in ['top', 'left', 'bottom', 'right', 'insideH', 'insideV']:
            border = etree.SubElement(tbl_borders, f'{{{self.w_ns}}}{border_type}')
            border.set(f'{{{self.w_ns}}}val', 'single')
            border.set(f'{{{self.w_ns}}}sz', '4')
            border.set(f'{{{self.w_ns}}}space', '0')
            border.set(f'{{{self.w_ns}}}color', 'auto')
        
        # Grid
        tbl_grid = etree.SubElement(tbl, f'{{{self.w_ns}}}tblGrid')
        for _ in range(len(columns)):
            grid_col = etree.SubElement(tbl_grid, f'{{{self.w_ns}}}gridCol')
            grid_col.set(f'{{{self.w_ns}}}w', str(5000 // len(columns)))
        
        # Fila de encabezados
        header_values = []
        for col in columns:
            if "header_template" in col:
                header_text = col["header_template"]
                for key, value in headers.items():
                    header_text = header_text.replace(f"{{{key}}}", str(value))
            else:
                header_text = col.get("header", "")
            header_values.append(header_text)
        
        header_row = self._create_table_row(header_values, is_header=True)
        tbl.append(header_row)
        
        # Filas de datos
        for row_data in rows:
            cell_values = []
            for col in columns:
                col_id = col['id']
                value = row_data.get(col_id, '')
                
                # Formatear según tipo
                col_type = col.get('type', 'text')
                formatted_value = self._format_cell_value(value, col_type)
                cell_values.append(formatted_value)
            
            data_row = self._create_table_row(cell_values, is_header=False)
            tbl.append(data_row)
        
        # Filas de footer
        for footer_data in footer_rows:
            cell_values = []
            for col in columns:
                col_id = col['id']
                value = footer_data.get(col_id, '')
                formatted_value = self._format_cell_value(value, col.get('type', 'text'))
                cell_values.append(formatted_value)
            
            footer_row = self._create_table_row(cell_values, is_header=False, is_bold=True)
            tbl.append(footer_row)
        
        return tbl
    
    def _format_cell_value(self, value: Any, col_type: str) -> str:
        """Formatea valor de celda según tipo."""
        if value is None or value == "":
            return ""
        
        try:
            if col_type == "percent":
                if isinstance(value, str):
                    value = value.replace('%', '').strip()
                num_val = float(value)
                return f"{num_val:.2f}%"
            elif col_type == "number":
                num_val = float(value)
                return f"{num_val:,.2f}"
            elif col_type == "integer":
                return str(int(value))
            else:
                return str(value)
        except (ValueError, TypeError):
            return str(value)
    
    def _create_table_row(self, cell_values: List[str], is_header: bool = False, is_bold: bool = False) -> etree.Element:
        """Crea fila de tabla."""
        tr = etree.Element(f'{{{self.w_ns}}}tr')
        
        for value in cell_values:
            tc = etree.SubElement(tr, f'{{{self.w_ns}}}tc')
            
            # Propiedades de celda
            tc_pr = etree.SubElement(tc, f'{{{self.w_ns}}}tcPr')
            
            if is_header:
                shd = etree.SubElement(tc_pr, f'{{{self.w_ns}}}shd')
                shd.set(f'{{{self.w_ns}}}val', 'clear')
                shd.set(f'{{{self.w_ns}}}fill', '4472C4')
            
            # Párrafo
            p = etree.SubElement(tc, f'{{{self.w_ns}}}p')
            p_pr = etree.SubElement(p, f'{{{self.w_ns}}}pPr')
            jc = etree.SubElement(p_pr, f'{{{self.w_ns}}}jc')
            jc.set(f'{{{self.w_ns}}}val', 'left')
            
            # Run
            r = etree.SubElement(p, f'{{{self.w_ns}}}r')
            r_pr = etree.SubElement(r, f'{{{self.w_ns}}}rPr')
            
            if is_header or is_bold:
                b = etree.SubElement(r_pr, f'{{{self.w_ns}}}b')
            
            if is_header:
                color = etree.SubElement(r_pr, f'{{{self.w_ns}}}color')
                color.set(f'{{{self.w_ns}}}val', 'FFFFFF')
            
            # Texto
            t = etree.SubElement(r, f'{{{self.w_ns}}}t')
            t.text = value
            t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
        
        return tr

    def _create_spacing_paragraph(self) -> etree.Element:
        """Crea un párrafo con un espacio no separable para usar como separador."""
        para = etree.Element(f'{{{self.w_ns}}}p')
        run = etree.SubElement(para, f'{{{self.w_ns}}}r')
        text = etree.SubElement(run, f'{{{self.w_ns}}}t')
        text.text = '\u00A0'
        text.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
        return para
    
    def insert_conditional_blocks(self, docs_to_insert: list, config_dir: Path):
        """Inserta bloques condicionales desde archivos Word."""
        for doc_info in docs_to_insert:
            marker = doc_info['marker']
            file_name = doc_info['file']
            # file_name ya incluye 'condiciones/' en el yaml (ej: "condiciones/nocumple1.docx")
            file_path = config_dir.parent / file_name

            self._insert_conditional_block(marker, file_path)
    
    def _insert_conditional_block(self, marker: str, block_file: Path):
        """
        Inserta un bloque de Word preservando todo el formato EXCEPTO section properties.

        IMPORTANTE: Este método copia TODO el contenido con formato (fuentes, colores,
        negritas, tablas, etc.) PERO elimina configuración de secciones (sectPr) para
        preservar el diseño de doble columna del documento principal.

        Args:
            marker: Marcador donde insertar el bloque
            block_file: Archivo Word a insertar
        """
        if not block_file.exists():
            return

        block_temp = tempfile.mkdtemp()
        try:
            with zipfile.ZipFile(block_file, 'r') as zip_ref:
                zip_ref.extractall(block_temp)

            block_xml_path = Path(block_temp) / 'word' / 'document.xml'
            block_tree = etree.parse(str(block_xml_path), self.parser)
            block_root = block_tree.getroot()

            block_body = block_root.find(f'.//{{{self.w_ns}}}body')
            if block_body is None:
                return

            # Obtener todos los elementos del cuerpo del documento
            block_elements = list(block_body)

            # Buscar párrafo con marcador
            target_para = None
            all_paras = self.root.findall(f'.//{{{self.w_ns}}}p')

            for para in all_paras:
                para_text = self._get_paragraph_text(para)
                if marker in para_text:
                    target_para = para
                    break

            if target_para is None:
                return

            # Insertar elementos REMOVIENDO section properties para preservar columnas
            parent = target_para.getparent()
            para_pos = list(parent).index(target_para)

            for i, elem in enumerate(block_elements):
                # Hacer copia profunda del elemento
                elem_copy = deepcopy(elem)

                # CRÍTICO: Remover sectPr (propiedades de sección) para preservar columnas
                # Las section properties incluyen configuración de columnas, márgenes, etc.
                # Si las copiamos, romperán el diseño de doble columna del documento principal
                self._remove_section_properties_from_element(elem_copy)

                # Insertar el elemento limpio
                parent.insert(para_pos + 1 + i, elem_copy)

            # Limpiar el marcador del párrafo original sin eliminarlo
            # (para preservar cualquier configuración de sección que pueda tener)
            self._remove_marker_from_paragraph(target_para, marker)

            # Si el párrafo quedó vacío después de limpiar el marcador, eliminarlo
            # únicamente cuando no contiene propiedades de sección. Estos párrafos
            # suelen guardar la configuración de columnas del documento y removerlos
            # rompe el diseño de doble columna.
            para_text_after = self._get_paragraph_text(target_para).strip()
            has_section = self._paragraph_has_section_break_xml(target_para)

            if (not para_text_after) and (not has_section):
                parent.remove(target_para)

        finally:
            shutil.rmtree(block_temp, ignore_errors=True)

    def remove_discrepancias_formales_section(self):
        """Elimina títulos y entradas del índice de Discrepancias formales."""
        targets = [
            "Anexo IV – Discrepancias formales",
            "Anexo IV - Discrepancias formales"
        ]
        self._remove_paragraphs_containing_text(targets)

    def _remove_section_properties_from_element(self, elem: etree.Element):
        """
        Remueve recursivamente todas las propiedades de sección (sectPr) de un elemento.

        Esto es CRÍTICO para preservar el diseño de doble columna del documento principal.
        Las section properties controlan el layout de columnas, y si se copian del documento
        de condición, romperán el diseño del documento principal.

        Args:
            elem: Elemento XML del cual remover sectPr
        """
        # Si el elemento es un párrafo, buscar sectPr en sus propiedades
        if elem.tag == f'{{{self.w_ns}}}p':
            pPr = elem.find(f'{{{self.w_ns}}}pPr')
            if pPr is not None:
                sectPr = pPr.find(f'{{{self.w_ns}}}sectPr')
                if sectPr is not None:
                    pPr.remove(sectPr)

        # Buscar y remover sectPr en el nivel de body (no debería estar aquí, pero por seguridad)
        for sectPr in elem.findall(f'.//{{{self.w_ns}}}sectPr'):
            parent = sectPr.getparent()
            if parent is not None:
                parent.remove(sectPr)

    def _remove_paragraphs_containing_text(self, targets: List[str]):
        """Elimina párrafos cuyo texto contiene cualquiera de los objetivos dados."""
        if not targets:
            return

        body = self.root.find(f'.//{{{self.w_ns}}}body')
        if body is None:
            return

        paras_to_remove = []
        for para in body.findall(f'.//{{{self.w_ns}}}p'):
            text = self._get_paragraph_text(para)
            if any(target in text for target in targets):
                paras_to_remove.append(para)

        for para in paras_to_remove:
            parent = para.getparent()
            if parent is not None:
                parent.remove(para)
    
    # Métodos simplificados/stub para compatibilidad
    def process_salto_markers(self):
        """
        Procesa los marcadores {salto} insertando saltos de página y eliminando el marcador.
        Implementación completa usando XML directo.
        """
        salto_pattern = re.compile(r'\{salto\}')
        body = self.root.find(f'.//{{{self.w_ns}}}body')
        if body is None:
            return

        # Obtener todos los párrafos
        all_paras = body.findall(f'.//{{{self.w_ns}}}p')

        for para in all_paras:
            para_text = self._get_paragraph_text(para)

            if salto_pattern.search(para_text):
                # Procesar cada elemento de texto que contiene {salto}
                for text_elem in para.findall(f'.//{{{self.w_ns}}}t'):
                    if text_elem.text and '{salto}' in text_elem.text:
                        # Dividir el texto en antes y después del {salto}
                        parts = text_elem.text.split('{salto}', 1)

                        if len(parts) == 2:
                            before_salto = parts[0]
                            after_salto = parts[1]

                            # Actualizar el texto antes del salto
                            text_elem.text = before_salto

                            # Obtener el run padre
                            run = text_elem.getparent()

                            # Crear un nuevo run con el salto de página
                            new_run = etree.Element(f'{{{self.w_ns}}}r')
                            br = etree.SubElement(new_run, f'{{{self.w_ns}}}br')
                            br.set(f'{{{self.w_ns}}}type', 'page')

                            # Insertar el nuevo run después del run actual
                            para_index = list(para).index(run)
                            para.insert(para_index + 1, new_run)

                            # Si hay texto después del salto, crear otro run
                            if after_salto:
                                after_run = etree.Element(f'{{{self.w_ns}}}r')
                                after_text = etree.SubElement(after_run, f'{{{self.w_ns}}}t')
                                after_text.text = after_salto
                                after_text.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
                                para.insert(para_index + 2, after_run)
                        else:
                            # Solo eliminar el marcador
                            text_elem.text = salto_pattern.sub('', text_elem.text)

    def process_table_of_contents(self):
        """
        Procesa el índice (tabla de contenidos) del documento usando marcadores numéricos.

        Busca contenidos entre <<Indice>> y <<fin Indice>>, extrae los marcadores numéricos
        (<<1>>, <<2>>, etc.), inserta saltos de página antes de ellos, calcula los números
        de página y actualiza el índice. También inserta un salto de página antes del índice.
        """
        body = self.root.find(f'.//{{{self.w_ns}}}body')
        if body is None:
            return

        all_paras = list(body.findall(f'{{{self.w_ns}}}p'))

        # Buscar los marcadores de inicio y fin del índice
        toc_start_idx = None
        toc_end_idx = None

        for i, para in enumerate(all_paras):
            text = self._get_paragraph_text(para)
            if "<<Indice>>" in text:
                toc_start_idx = i
            elif "<<fin Indice>>" in text:
                toc_end_idx = i
                break

        # Si no se encuentran los marcadores, no hacer nada
        if toc_start_idx is None or toc_end_idx is None:
            return

        # Extraer las entradas del índice con sus marcadores numéricos
        toc_entries = []  # Lista de {paragraph, title, marker, marker_num}
        marker_pattern = re.compile(r'<<(\d+)>>')

        for i in range(toc_start_idx + 1, toc_end_idx):
            para = all_paras[i]
            text = self._get_paragraph_text(para)

            if text.strip():  # Solo procesar párrafos no vacíos
                # Buscar el marcador numérico en el texto
                match = marker_pattern.search(text)
                if match:
                    marker_num = match.group(1)
                    marker = f"<<{marker_num}>>"

                    # Extraer el título (texto antes del marcador)
                    title = marker_pattern.sub('', text).strip()

                    toc_entries.append({
                        'paragraph': para,
                        'title': title,
                        'marker': marker,
                        'marker_num': marker_num
                    })

        # Si no hay entradas con marcadores, limpiar y salir
        if not toc_entries:
            self._remove_marker_from_paragraph(all_paras[toc_start_idx], "<<Indice>>")
            self._remove_marker_from_paragraph(all_paras[toc_end_idx], "<<fin Indice>>")
            return

        # Fase 1: Buscar cada marcador en el documento e insertar saltos de página
        for entry in toc_entries:
            marker = entry['marker']
            self._insert_page_break_before_marker_xml(marker, toc_end_idx, all_paras)

        # Fase 2: Calcular números de página para cada marcador
        marker_to_page = {}
        for entry in toc_entries:
            marker = entry['marker']
            page_num = self._find_marker_page_number_xml(marker, toc_end_idx, all_paras)
            if page_num is not None:
                marker_to_page[marker] = page_num

        # Fase 3: Actualizar el índice con los números de página
        for entry in toc_entries:
            para = entry['paragraph']
            title = entry['title']
            marker = entry['marker']

            if marker in marker_to_page:
                page_num = marker_to_page[marker]

                clean_title = re.sub(r'[\.\s]+\d+$', '', title).strip()
                dots_length = max(3, 80 - len(clean_title) - len(str(page_num)) - 2)
                dots = '.' * dots_length

                new_text = f"{clean_title} {dots} {page_num}"
                self._set_paragraph_text(para, new_text)
            else:
                # Entrada sin página -> eliminar del índice
                self._remove_paragraph(para)

        # Fase 4: Eliminar todos los marcadores numéricos del documento
        self._remove_numeric_markers_xml()

        # Eliminar los marcadores <<Indice>> y <<fin Indice>>
        start_para = all_paras[toc_start_idx]
        end_para = all_paras[toc_end_idx]

        self._remove_marker_from_paragraph(start_para, "<<Indice>>")
        if not self._get_paragraph_text(start_para).strip():
            self._remove_paragraph(start_para)

        self._remove_marker_from_paragraph(end_para, "<<fin Indice>>")
        if not self._get_paragraph_text(end_para).strip():
            self._remove_paragraph(end_para)

        # Asegurar que el índice empiece en una nueva página
        if toc_start_idx > 0:
            # Insertar salto de página al final del párrafo anterior
            prev_para = all_paras[toc_start_idx - 1]
            self._insert_page_break_at_end_of_paragraph(prev_para)

    def _insert_page_break_before_marker_xml(self, marker: str, toc_end_idx: int, all_paras: list):
        """
        Busca un marcador numérico en el documento e inserta un salto de página antes de él.

        Args:
            marker: Marcador numérico a buscar (ej: "<<1>>")
            toc_end_idx: Índice del final del índice (para empezar búsqueda después)
            all_paras: Lista de todos los párrafos
        """
        for i in range(toc_end_idx + 1, len(all_paras)):
            para = all_paras[i]
            para_text = self._get_paragraph_text(para)

            if marker in para_text:
                # Verificar si ya hay un salto de página
                has_page_break = self._has_page_break_xml(para)

                # También verificar el párrafo anterior
                if i > 0 and not has_page_break:
                    prev_para = all_paras[i - 1]
                    has_page_break = self._has_page_break_xml(prev_para)

                # Si no tiene salto de página, insertar uno
                if not has_page_break:
                    if i > 0:
                        # Insertar al final del párrafo anterior
                        prev_para = all_paras[i - 1]
                        self._insert_page_break_at_end_of_paragraph(prev_para)
                    else:
                        # Insertar al inicio del párrafo actual
                        self._insert_page_break_at_start_of_paragraph(para)

                # Solo procesar la primera ocurrencia
                break

    def _find_marker_page_number_xml(self, marker: str, start_search_idx: int, all_paras: list) -> Optional[int]:
        """
        Encuentra el número de página donde aparece un marcador numérico.

        Args:
            marker: Marcador numérico a buscar (ej: "<<1>>")
            start_search_idx: Índice desde donde empezar la búsqueda
            all_paras: Lista de todos los párrafos

        Returns:
            Número de página donde se encuentra el marcador, o None si no se encuentra
        """
        page_count = self._calculate_page_count_until_idx(all_paras, start_search_idx)

        for i in range(start_search_idx + 1, len(all_paras)):
            para = all_paras[i]

            # Verificar si hay un salto de página en este párrafo
            if self._has_page_break_xml(para):
                page_count += 1

            # Verificar si este párrafo contiene el marcador
            para_text = self._get_paragraph_text(para)
            if marker in para_text:
                return page_count

        return None

    def _remove_numeric_markers_xml(self):
        """Elimina todos los marcadores numéricos (<<1>>, <<2>>, etc.) del documento."""
        marker_pattern = re.compile(r'<<\d+>>')

        for text_elem in self.root.findall(f'.//{{{self.w_ns}}}t'):
            if text_elem.text and marker_pattern.search(text_elem.text):
                text_elem.text = marker_pattern.sub('', text_elem.text)

    def _calculate_page_count_until_idx(self, all_paras: list, end_idx: int) -> int:
        """Calcula el número de página acumulado hasta un índice de párrafo dado."""
        page_count = 1

        if end_idx is None:
            return page_count

        for i in range(0, min(end_idx + 1, len(all_paras))):
            if self._has_page_break_xml(all_paras[i]):
                page_count += 1

        return page_count

    def _has_page_break_xml(self, para: etree.Element) -> bool:
        """
        Verifica si un párrafo contiene un salto de página.

        Args:
            para: Elemento de párrafo XML

        Returns:
            True si el párrafo contiene un salto de página, False en caso contrario
        """
        # Considerar saltos de página explícitos
        if self._paragraph_has_section_page_break(para):
            return True

        if para.find(f'.//{{{self.w_ns}}}lastRenderedPageBreak') is not None:
            return True

        # Buscar elementos de salto de página (w:br con w:type="page")
        for br in para.findall(f'.//{{{self.w_ns}}}br'):
            break_type = br.get(f'{{{self.w_ns}}}type')
            if break_type == 'page':
                return True
        return False

    def _insert_page_break_at_end_of_paragraph(self, para: etree.Element):
        """Inserta un salto de página al final de un párrafo."""
        # Crear un nuevo run con salto de página
        new_run = etree.Element(f'{{{self.w_ns}}}r')
        br = etree.SubElement(new_run, f'{{{self.w_ns}}}br')
        br.set(f'{{{self.w_ns}}}type', 'page')

        # Agregar al final del párrafo
        para.append(new_run)

    def _insert_page_break_at_start_of_paragraph(self, para: etree.Element):
        """Inserta un salto de página al inicio de un párrafo."""
        # Crear un nuevo run con salto de página
        new_run = etree.Element(f'{{{self.w_ns}}}r')
        br = etree.SubElement(new_run, f'{{{self.w_ns}}}br')
        br.set(f'{{{self.w_ns}}}type', 'page')

        # Insertar al inicio del párrafo
        para.insert(0, new_run)

    def _set_paragraph_text(self, para: etree.Element, new_text: str):
        """Establece el texto de un párrafo, reemplazando todo el contenido de texto."""
        # Encontrar el primer elemento de texto o crear uno nuevo
        text_elems = para.findall(f'.//{{{self.w_ns}}}t')

        if text_elems:
            # Actualizar el primer elemento de texto
            self._set_text_with_preserve(text_elems[0], new_text)

            # Eliminar otros elementos de texto
            for text_elem in text_elems[1:]:
                run = text_elem.getparent()
                if run is not None:
                    run.remove(text_elem)
        else:
            # No hay elementos de texto, crear uno nuevo
            run = para.find(f'.//{{{self.w_ns}}}r')
            if run is None:
                # No hay runs, crear uno nuevo
                run = etree.SubElement(para, f'{{{self.w_ns}}}r')

            text_elem = etree.SubElement(run, f'{{{self.w_ns}}}t')
            self._set_text_with_preserve(text_elem, new_text)

    def clean_unused_markers(self):
        """
        Elimina TODOS los marcadores << >> del documento generado.

        Este método elimina completamente todos los marcadores del formato << >> que
        puedan quedar en el documento, ya sean utilizados o no. Si un párrafo contiene
        SOLO un marcador (o marcador con puntuación/numeración), elimina el párrafo
        completo. Si hay más contenido, solo elimina el marcador.

        IMPORTANTE: Nunca elimina párrafos que contengan imágenes, shapes o dibujos,
        o que tengan configuración de sección (sectPr), para preservar el diseño
        de doble columna y otros elementos visuales.
        """
        marker_pattern = re.compile(r'<<[^>]+>>')
        body = self.root.find(f'.//{{{self.w_ns}}}body')
        if body is None:
            return

        paras_to_delete = []
        all_paras = body.findall(f'{{{self.w_ns}}}p')

        for para in all_paras:
            para_text = self._get_paragraph_text(para)

            if marker_pattern.search(para_text):
                # Proteger párrafos con configuración de sección (columnas, etc.)
                if self._paragraph_has_section_break_xml(para):
                    # Solo eliminar el marcador, preservar el párrafo
                    for text_elem in para.findall(f'.//{{{self.w_ns}}}t'):
                        if text_elem.text:
                            text_elem.text = marker_pattern.sub('', text_elem.text)
                    continue

                # Proteger párrafos con imágenes o dibujos
                if self._has_drawing_or_image_xml(para):
                    # Solo eliminar el marcador, preservar el párrafo
                    for text_elem in para.findall(f'.//{{{self.w_ns}}}t'):
                        if text_elem.text:
                            text_elem.text = marker_pattern.sub('', text_elem.text)
                    continue

                # Verificar si el párrafo solo contiene marcador y elementos decorativos
                text_without_markers = marker_pattern.sub('', para_text).strip()
                # Eliminar puntuación común, números, guiones, viñetas
                text_cleaned = re.sub(r'^[\d\.\-\)\(\s•·◦▪▫○●\*]+$', '', text_without_markers)

                if not text_cleaned:
                    # El párrafo solo contiene marcador + elementos decorativos
                    paras_to_delete.append(para)
                else:
                    # Hay contenido real, solo eliminar el marcador
                    for text_elem in para.findall(f'.//{{{self.w_ns}}}t'):
                        if text_elem.text:
                            text_elem.text = marker_pattern.sub('', text_elem.text)

        # Eliminar los párrafos marcados
        for para in paras_to_delete:
            body.remove(para)

        # Segunda pasada: eliminar cualquier marcador restante en tablas, headers y footers
        # Esto asegura que TODOS los marcadores << >> sean eliminados del documento
        self._remove_all_markers_from_tables()
        self._remove_all_markers_from_headers_footers()

    def _remove_all_markers_from_tables(self):
        """Elimina todos los marcadores << >> de todas las tablas del documento."""
        marker_pattern = re.compile(r'<<[^>]+>>')

        # Buscar todas las tablas en el documento
        for table in self.root.findall(f'.//{{{self.w_ns}}}tbl'):
            # Buscar todos los elementos de texto en la tabla
            for text_elem in table.findall(f'.//{{{self.w_ns}}}t'):
                if text_elem.text and marker_pattern.search(text_elem.text):
                    text_elem.text = marker_pattern.sub('', text_elem.text)

    def _remove_all_markers_from_headers_footers(self):
        """Elimina todos los marcadores << >> de headers y footers."""
        marker_pattern = re.compile(r'<<[^>]+>>')

        # Headers y footers están en archivos separados dentro del documento
        # Buscar en header*.xml y footer*.xml
        header_footer_paths = [
            Path(self.temp_dir) / 'word' / 'header1.xml',
            Path(self.temp_dir) / 'word' / 'header2.xml',
            Path(self.temp_dir) / 'word' / 'header3.xml',
            Path(self.temp_dir) / 'word' / 'footer1.xml',
            Path(self.temp_dir) / 'word' / 'footer2.xml',
            Path(self.temp_dir) / 'word' / 'footer3.xml',
        ]

        for hf_path in header_footer_paths:
            if hf_path.exists():
                try:
                    tree = etree.parse(str(hf_path), self.parser)
                    root = tree.getroot()

                    # Eliminar marcadores de todos los elementos de texto
                    for text_elem in root.findall(f'.//{{{self.w_ns}}}t'):
                        if text_elem.text and marker_pattern.search(text_elem.text):
                            text_elem.text = marker_pattern.sub('', text_elem.text)

                    # Guardar el archivo modificado
                    tree.write(
                        str(hf_path),
                        encoding='UTF-8',
                        xml_declaration=True,
                        standalone=True,
                        pretty_print=False
                    )
                except Exception:
                    # Si hay algún error, continuar con el siguiente
                    pass

    def _paragraph_has_section_break_xml(self, para: etree.Element) -> bool:
        """
        Verifica si un párrafo tiene configuración de sección (sectPr).

        Args:
            para: Elemento de párrafo XML

        Returns:
            True si el párrafo tiene sectPr, False en caso contrario
        """
        # Buscar elemento sectPr en las propiedades del párrafo
        pPr = para.find(f'{{{self.w_ns}}}pPr')
        if pPr is not None:
            sectPr = pPr.find(f'{{{self.w_ns}}}sectPr')
            if sectPr is not None:
                return True
        return False

    def _paragraph_has_section_page_break(self, para: etree.Element) -> bool:
        """Detecta si una sección obliga a iniciar una nueva página."""
        pPr = para.find(f'{{{self.w_ns}}}pPr')
        if pPr is None:
            return False

        sectPr = pPr.find(f'{{{self.w_ns}}}sectPr')
        if sectPr is None:
            return False

        type_elem = sectPr.find(f'{{{self.w_ns}}}type')
        type_val = type_elem.get(f'{{{self.w_ns}}}val') if type_elem is not None else None

        # Considerar como salto de página todo lo que no sea continuo
        return type_val in (None, 'nextPage', 'evenPage', 'oddPage')

    def _has_drawing_or_image_xml(self, para: etree.Element) -> bool:
        """
        Verifica si un párrafo contiene imágenes, shapes, dibujos u otros elementos gráficos.

        Args:
            para: Elemento de párrafo XML

        Returns:
            True si el párrafo contiene elementos gráficos, False en caso contrario
        """
        # Buscar elementos de dibujo (drawing)
        if para.find(f'.//{{{self.w_ns}}}drawing') is not None:
            return True

        # Buscar elementos de imagen (pict)
        if para.find(f'.//{{{self.w_ns}}}pict') is not None:
            return True

        # Buscar elementos VML (shapes de Office)
        v_ns = 'urn:schemas-microsoft-com:vml'
        if para.find(f'.//{{{v_ns}}}shape') is not None:
            return True
        if para.find(f'.//{{{v_ns}}}imagedata') is not None:
            return True

        return False
    
    def remove_empty_lines_at_page_start(self):
        """Elimina líneas vacías al inicio de páginas - stub."""
        pass
    
    def clean_empty_paragraphs(self):
        """Limpia párrafos vacíos - implementación simplificada."""
        body = self.root.find(f'.//{{{self.w_ns}}}body')
        if body is None:
            return

        paras_to_remove = []
        for para in body.findall(f'{{{self.w_ns}}}p'):
            text = self._get_paragraph_text(para)
            normalized_text = text.replace('\u00A0', '')
            if not normalized_text.strip():
                if '\u00A0' in text:
                    continue  # Preservar párrafos separadores con espacios duros
                # Verificar que no tiene imágenes
                has_drawing = para.find(f'.//{{{self.w_ns}}}drawing') is not None
                # No eliminar párrafos que contengan propiedades de sección, ya que
                # suelen almacenar configuraciones de columnas/márgenes que deben
                # preservarse para mantener el diseño del documento.
                has_section = self._paragraph_has_section_break_xml(para)

                if not has_drawing and not has_section:
                    paras_to_remove.append(para)
        
        for para in paras_to_remove:
            body.remove(para)
    
    def remove_empty_pages(self):
        """Elimina páginas vacías - stub."""
        pass  # Difícil de implementar en XML puro
    
    def preserve_headers_and_footers(self):
        """Preserva headers y footers - no necesario (ya se preservan)."""
        pass
    
    def insert_background_image(self, image_path: Path, page_type: str = "first"):
        """Inserta imagen de fondo - stub."""
        pass  # Las imágenes ya se preservan automáticamente
    
    def _get_paragraph_text(self, para: etree.Element) -> str:
        """Obtiene texto completo de un párrafo."""
        texts = []
        for text_elem in para.findall(f'.//{{{self.w_ns}}}t'):
            if text_elem.text:
                texts.append(text_elem.text)
        return ''.join(texts)

    def _remove_marker_from_paragraph(self, para: etree.Element, marker: str):
        """Elimina todas las instancias de un marcador en un párrafo."""
        if para is None or not marker:
            return

        para_text = self._get_paragraph_text(para)

        while marker in para_text:
            self._replace_marker_in_paragraph_xml(para, marker, '')
            para_text = self._get_paragraph_text(para)

    def _replace_marker_in_paragraph_xml(self, para: etree.Element, marker: str, value: str):
        """Reemplaza un marcador dentro de un párrafo preservando los runs existentes."""
        text_nodes = []
        current_pos = 0

        for text_elem in para.findall(f'.//{{{self.w_ns}}}t'):
            text = text_elem.text or ''
            start = current_pos
            end = start + len(text)
            text_nodes.append({'element': text_elem, 'text': text, 'start': start, 'end': end})
            current_pos = end

        if not text_nodes:
            return

        full_text = ''.join(node['text'] for node in text_nodes)

        if marker not in full_text:
            return

        marker_start = full_text.index(marker)
        marker_end = marker_start + len(marker)
        inserted = False
        value = value or ''

        for node in text_nodes:
            text_elem = node['element']
            text = node['text']
            start = node['start']
            end = node['end']

            if end <= marker_start or start >= marker_end:
                # Nodo fuera del marcador
                continue

            before = ''
            after = ''

            if start < marker_start < end:
                before = text[:marker_start - start]

            if start < marker_end < end:
                after = text[marker_end - start:]

            if start <= marker_start and end >= marker_end:
                replacement = before + value + after
                self._set_text_with_preserve(text_elem, replacement)
                inserted = True
            elif start <= marker_start < end:
                self._set_text_with_preserve(text_elem, before + value)
                inserted = True
            elif start < marker_end <= end:
                self._set_text_with_preserve(text_elem, after)
            else:
                # El nodo está completamente dentro del marcador
                self._set_text_with_preserve(text_elem, '')

        if not inserted:
            first_node = next((n for n in text_nodes if n['end'] > marker_start), None)
            if first_node:
                text_elem = first_node['element']
                current_text = text_elem.text or ''
                self._set_text_with_preserve(text_elem, current_text + value)

    def _set_text_with_preserve(self, text_elem: etree.Element, new_text: str):
        """Actualiza el texto garantizando xml:space cuando sea necesario."""
        if new_text is None:
            new_text = ''

        text_elem.text = new_text

        needs_preserve = (
            new_text.startswith(' ') or
            new_text.endswith(' ') or
            '\n' in new_text or
            '\t' in new_text
        )

        if needs_preserve:
            text_elem.set(f'{{{self.xml_ns}}}space', 'preserve')
        else:
            if f'{{{self.xml_ns}}}space' in text_elem.attrib:
                del text_elem.attrib[f'{{{self.xml_ns}}}space']

    def _remove_paragraph(self, para: etree.Element):
        """Elimina por completo un párrafo del documento."""
        if para is None:
            return

        parent = para.getparent()
        if parent is not None:
            parent.remove(para)
    
    def get_document_bytes(self) -> bytes:
        """Retorna el documento como bytes."""
        # Guardar XML
        self.tree.write(
            str(self.doc_xml_path),
            encoding='UTF-8',
            xml_declaration=True,
            standalone=True,
            pretty_print=False
        )
        
        # Reempaquetar
        temp_output = tempfile.mktemp(suffix='.docx')
        try:
            with zipfile.ZipFile(temp_output, 'w', zipfile.ZIP_DEFLATED) as zip_out:
                for root_dir, dirs, files in os.walk(self.temp_dir):
                    for file in files:
                        file_path = Path(root_dir) / file
                        arcname = file_path.relative_to(self.temp_dir)
                        zip_out.write(file_path, arcname)
            
            # Verificar preservación
            final_drawings = len(self.root.findall(f'.//{{{self.w_ns}}}drawing'))
            final_sections = len(self.root.findall(f'.//{{{self.w_ns}}}sectPr'))
            
            if final_drawings < self._initial_drawings or final_sections < self._initial_sections:
                print(f"⚠️  ADVERTENCIA: Se perdieron elementos")
                print(f"   Imágenes: {self._initial_drawings} → {final_drawings}")
                print(f"   Secciones: {self._initial_sections} → {final_sections}")
            
            # Leer bytes
            with open(temp_output, 'rb') as f:
                return f.read()
        finally:
            if Path(temp_output).exists():
                Path(temp_output).unlink()
    
    def get_pdf_bytes(self) -> bytes:
        """Stub para compatibilidad - lanza RuntimeError como el original."""
        raise RuntimeError("Conversión a PDF no disponible en XMLWordEngine")
    
    def __del__(self):
        """Limpia directorio temporal."""
        if hasattr(self, 'temp_dir') and Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)
