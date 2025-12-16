"""
Módulo para procesar y construir las estructuras de datos de las tablas
según las configuraciones del YAML tablas.yaml.
"""
import re
from typing import Dict, List, Any, Optional


class TableBuilder:
    """Construye las estructuras de datos para las tablas del informe."""

    def __init__(self, cfg_tab: dict, simple_inputs: dict):
        """
        Inicializa el constructor de tablas.

        Args:
            cfg_tab: Configuración de tablas.yaml
            simple_inputs: Entradas de variables simples (para ejercicios, etc.)
        """
        self.cfg_tab = cfg_tab
        self.simple_inputs = simple_inputs
        self.tables_config = cfg_tab.get("tables", {})

    def build_all_tables(self, table_inputs: dict) -> dict:
        """
        Construye todas las tablas según las configuraciones.

        Args:
            table_inputs: Datos de entrada de todas las tablas

        Returns:
            Diccionario con {marker: table_data} para todas las tablas
        """
        all_tables = {}

        # 1. Tabla de análisis indirecto global (TNMM)
        if "analisis_indirecto_global" in self.tables_config:
            table_data = self.build_tnmm_global(table_inputs)
            all_tables.update(table_data)

        # 2. Tablas de análisis indirecto por operación
        if "analisis_indirecto_operacion" in self.tables_config:
            table_data = self.build_tnmm_por_operacion(table_inputs)
            all_tables.update(table_data)

        # 3. Tabla de partidas contables
        if "partidas_contables" in self.tables_config:
            table_data = self.build_partidas_contables(table_inputs)
            all_tables.update(table_data)

        # 4. Tabla de operaciones vinculadas
        if "operaciones_vinculadas" in self.tables_config:
            table_data = self.build_operaciones_vinculadas(table_inputs)
            all_tables.update(table_data)

        # 5. Tablas de cumplimiento
        for key in ["cumplimiento_inicial_LF", "cumplimiento_inicial_MF",
                    "cumplimiento_formal_LF", "cumplimiento_formal_MF"]:
            if key in self.tables_config:
                table_data = self.build_cumplimiento_table(key, table_inputs)
                all_tables.update(table_data)

        # 6. Tabla de riesgos
        if "riesgos_pt" in self.tables_config:
            table_data = self.build_riesgos_table(table_inputs)
            all_tables.update(table_data)

        return all_tables

    def build_tnmm_global(self, table_inputs: dict) -> dict:
        """Construye la tabla de análisis TNMM global."""
        cfg = self.tables_config["analisis_indirecto_global"]
        marker = cfg["marker"]

        data = table_inputs.get("analisis_indirecto_global", {})

        rows = []
        for row_cfg in cfg.get("rows", []):
            row_id = row_cfg["id"]
            row_data = {"label": row_cfg.get("label", "")}

            # Obtener valores de las columnas
            for col in cfg.get("columns", []):
                col_id = col["id"]
                value = data.get(row_id, {}).get(col_id, "")
                row_data[col_id] = value

            rows.append(row_data)

        return {marker: {
            "table_id": "analisis_indirecto_global",
            "columns": cfg.get("columns", []),
            "rows": rows
        }}

    def build_tnmm_por_operacion(self, table_inputs: dict) -> dict:
        """Construye las tablas TNMM por operación."""
        cfg = self.tables_config["analisis_indirecto_operacion"]
        marker_pattern = cfg["marker_pattern"]

        all_tables = {}

        # Obtener el rango máximo de operaciones
        max_ops = cfg.get("parameters", {}).get("n", {}).get("max", 10)

        for n in range(1, max_ops + 1):
            marker = marker_pattern.format(n=n)
            table_id = f"analisis_indirecto_operacion_{n}"

            data = table_inputs.get(table_id, {})

            # Si no hay datos, no crear la tabla
            if not data:
                continue

            rows = []
            for row_cfg in cfg.get("rows", []):
                row_id = row_cfg["id"]
                row_data = {"label": row_id}  # Usar el row_id como label

                # Obtener valores de las columnas (incluye nombre_operacion)
                for col in cfg.get("columns", []):
                    col_id = col["id"]
                    value = data.get(col_id, "")
                    row_data[col_id] = value

                rows.append(row_data)

            all_tables[marker] = {
                "table_id": table_id,
                "columns": cfg.get("columns", []),
                "rows": rows
            }

        return all_tables

    def build_partidas_contables(self, table_inputs: dict) -> dict:
        """Construye la tabla de partidas contables con cabeceras dinámicas."""
        cfg = self.tables_config["partidas_contables"]
        marker = cfg["marker"]

        ejercicio_actual = self._extract_year(
            self.simple_inputs.get("ejercicio_corto")
            or self.simple_inputs.get("ejercicio_completo")
            or "2023"
        )
        ejercicio_anterior = self._extract_year(
            self.simple_inputs.get("ejercicio_anterior") or "2022"
        )

        data = table_inputs.get("partidas_contables", {})

        rows = []
        for row_cfg in cfg.get("rows", []):
            row_id = row_cfg["id"]
            label = row_cfg["label"]
            input_mode = row_cfg.get("input_mode", "manual")

            row_data = {"partida": label}

            if input_mode == "manual":
                vals = data.get(row_id, {})
                ea = vals.get("ejercicio_actual")
                ep = vals.get("ejercicio_anterior")
            else:  # calculated
                # Calcular según fórmulas
                vals = data.get(row_id, {})
                ea = vals.get("ejercicio_actual")
                ep = vals.get("ejercicio_anterior")

                # Nota: las fórmulas se evaluarán después con acceso a otras filas
                # Por simplicidad, aquí asumimos que ya vienen calculadas del UI

            row_data["ejercicio_actual"] = ea
            row_data["ejercicio_anterior"] = ep

            # Calcular variación si está configurado
            if row_cfg.get("calculate_variacion", False):
                if ea is not None and ep is not None and ep != 0:
                    variacion = ((ea - ep) / ep) * 100
                    row_data["variacion"] = variacion
                else:
                    row_data["variacion"] = None
            else:
                row_data["variacion"] = None

            rows.append(row_data)

        return {marker: {
            "table_id": "partidas_contables",
            "headers": {
                "ejercicio_actual": ejercicio_actual,
                "ejercicio_anterior": ejercicio_anterior
            },
            "columns": cfg.get("columns", []),
            "rows": rows
        }}

    @staticmethod
    def _extract_year(value: Optional[str]) -> str:
        """Extrae el año (primer número de 4 dígitos) de un texto."""

        if not value:
            return ""

        match = re.search(r"(\d{4})", str(value))
        return match.group(1) if match else str(value)

    def build_operaciones_vinculadas(self, table_inputs: dict) -> dict:
        """Construye la tabla de operaciones vinculadas con totales."""
        cfg = self.tables_config["operaciones_vinculadas"]
        marker = cfg["marker"]

        rows = table_inputs.get("operaciones_vinculadas", [])

        # Eliminar filas vacías si está configurado
        if cfg.get("remove_empty_rows", False):
            cleaned = []
            for row in rows:
                # Considerar fila vacía si todas las columnas están vacías
                if any(str(row.get(col["id"], "")).strip() for col in cfg["columns"]):
                    cleaned.append(row)
            rows = cleaned

        # Calcular totales
        footer_rows = []
        for footer_cfg in cfg.get("footer_rows", []):
            if footer_cfg["row_type"] == "sum":
                sum_row = {"tipo_operacion": footer_cfg["label"]}

                for col_id in footer_cfg["sum_columns"]:
                    total = sum(row.get(col_id, 0) or 0 for row in rows)
                    sum_row[col_id] = total

                footer_rows.append(sum_row)

            elif footer_cfg["row_type"] == "percent_of_total":
                # Calcular pesos como porcentaje del total
                peso_row = {"tipo_operacion": footer_cfg["label"]}

                # Obtener los totales del footer anterior
                if footer_rows:
                    total_row = footer_rows[0]

                    for col_id in footer_cfg.get("sum_columns", footer_cfg.get("columns", [])):
                        total = total_row.get(col_id, 0)
                        if total != 0:
                            # Aquí podríamos calcular pesos, pero necesitaríamos un total de referencia
                            # Por simplicidad, dejamos vacío o calculamos después
                            peso_row[col_id] = ""
                        else:
                            peso_row[col_id] = ""

                footer_rows.append(peso_row)

        return {marker: {
            "table_id": "operaciones_vinculadas",
            "columns": cfg.get("columns", []),
            "rows": rows,
            "footer_rows": footer_rows
        }}

    def build_cumplimiento_table(self, table_id: str, table_inputs: dict) -> dict:
        """Construye las tablas de cumplimiento."""
        cfg = self.tables_config[table_id]
        marker = cfg["marker"]

        rows = table_inputs.get(table_id, [])

        return {marker: {
            "table_id": table_id,
            "columns": cfg.get("columns", []),
            "rows": rows
        }}

    def build_riesgos_table(self, table_inputs: dict) -> dict:
        """Construye la tabla de riesgos."""
        cfg = self.tables_config["riesgos_pt"]
        marker = cfg["marker"]

        rows = table_inputs.get("riesgos_pt", [])

        return {marker: {
            "table_id": "riesgos_pt",
            "columns": cfg.get("columns", []),
            "rows": rows
        }}


def calculate_formulas(rows_data: List[dict], formulas: dict) -> List[dict]:
    """
    Calcula las fórmulas de las filas calculadas.

    Args:
        rows_data: Lista de filas con datos
        formulas: Diccionario con fórmulas a evaluar

    Returns:
        Lista de filas con valores calculados
    """
    # Crear un diccionario de acceso rápido por id de fila
    rows_by_id = {}
    for row in rows_data:
        if "id" in row:
            rows_by_id[row["id"]] = row

    # Evaluar fórmulas
    for row in rows_data:
        if "formula" in row:
            # Aquí se evaluaría la fórmula
            # Por simplicidad, esto se manejará en el UI
            pass

    return rows_data
