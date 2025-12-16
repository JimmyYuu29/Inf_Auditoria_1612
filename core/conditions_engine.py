"""
Conditions Engine - Motor de evaluación de expresiones condicionales

Evalúa expresiones lógicas de forma segura usando AST parsing para determinar
qué bloques de texto o campos deben mostrarse según el contexto.

SEGURIDAD: No usa eval() directo, sino un parser basado en AST de Python que
solo permite operadores seguros (comparación, lógica, paréntesis).
"""

import ast
from typing import Dict, Any, List, Optional, Union
from report_platform.core.utils import setup_logger
from report_platform.core.schema_models import BlockDefinition, BlockRule

logger = setup_logger(__name__)


# ==============================================================================
# EVALUADOR SEGURO BASADO EN AST
# ==============================================================================

class SafeConditionEvaluator(ast.NodeVisitor):
    """
    Evaluador seguro de expresiones condicionales usando AST.

    Soporta:
    - Comparaciones: ==, !=, <, >, <=, >=, in, not in
    - Lógica: and, or, not
    - Paréntesis para agrupación
    - Literales: strings, números, booleanos (True/False), None
    - Variables del contexto

    No permite:
    - Llamadas a funciones
    - Atributos de objetos
    - Operaciones aritméticas (solo comparaciones)
    - Imports o asignaciones
    """

    def __init__(self, context: Dict[str, Any]):
        """
        Inicializa el evaluador con un contexto.

        Args:
            context: Diccionario con variables disponibles
        """
        self.context = context

    def visit_BoolOp(self, node: ast.BoolOp) -> bool:
        """Evalúa operadores booleanos (and, or)."""
        if isinstance(node.op, ast.And):
            return all(self.visit(value) for value in node.values)
        elif isinstance(node.op, ast.Or):
            return any(self.visit(value) for value in node.values)
        else:
            raise ValueError(f"Operador booleano no soportado: {node.op}")

    def visit_UnaryOp(self, node: ast.UnaryOp) -> Union[bool, int, float]:
        """Evalúa operadores unarios (not, -, +)."""
        operand = self.visit(node.operand)

        if isinstance(node.op, ast.Not):
            return not operand
        elif isinstance(node.op, ast.UAdd):
            return +operand
        elif isinstance(node.op, ast.USub):
            return -operand
        else:
            raise ValueError(f"Operador unario no soportado: {node.op}")

    def visit_Compare(self, node: ast.Compare) -> bool:
        """Evalúa comparaciones (==, !=, <, >, <=, >=, in, not in)."""
        left = self.visit(node.left)

        for op, comparator in zip(node.ops, node.comparators):
            right = self.visit(comparator)

            if isinstance(op, ast.Eq):
                result = left == right
            elif isinstance(op, ast.NotEq):
                result = left != right
            elif isinstance(op, ast.Lt):
                result = left < right
            elif isinstance(op, ast.LtE):
                result = left <= right
            elif isinstance(op, ast.Gt):
                result = left > right
            elif isinstance(op, ast.GtE):
                result = left >= right
            elif isinstance(op, ast.In):
                result = left in right
            elif isinstance(op, ast.NotIn):
                result = left not in right
            elif isinstance(op, ast.Is):
                result = left is right
            elif isinstance(op, ast.IsNot):
                result = left is not right
            else:
                raise ValueError(f"Operador de comparación no soportado: {op}")

            if not result:
                return False

            left = right  # Para comparaciones encadenadas: a < b < c

        return True

    def visit_Name(self, node: ast.Name) -> Any:
        """Evalúa nombres de variables."""
        var_name = node.id

        # Constantes permitidas
        if var_name == 'True':
            return True
        elif var_name == 'False':
            return False
        elif var_name == 'None':
            return None

        # Buscar en contexto
        if var_name in self.context:
            return self.context[var_name]

        # Variable no encontrada - retornar None para evitar errores
        logger.warning(f"Variable '{var_name}' no encontrada en contexto")
        return None

    def visit_Constant(self, node: ast.Constant) -> Any:
        """Evalúa constantes (strings, números, booleanos)."""
        return node.value

    def visit_Str(self, node: ast.Str) -> str:
        """Evalúa strings (compatibilidad Python 3.7)."""
        return node.s

    def visit_Num(self, node: ast.Num) -> Union[int, float]:
        """Evalúa números (compatibilidad Python 3.7)."""
        return node.n

    def visit_NameConstant(self, node: ast.NameConstant) -> Any:
        """Evalúa constantes con nombre (compatibilidad Python 3.7)."""
        return node.value

    def visit_List(self, node: ast.List) -> list:
        """Evalúa listas literales."""
        return [self.visit(elem) for elem in node.elts]

    def visit_Tuple(self, node: ast.Tuple) -> tuple:
        """Evalúa tuplas literales."""
        return tuple(self.visit(elem) for elem in node.elts)

    def generic_visit(self, node: ast.AST) -> None:
        """Rechaza nodos no permitidos."""
        raise ValueError(
            f"Operación no permitida en expresión de condición: {node.__class__.__name__}"
        )


def evaluate_condition(condition: str, context: Dict[str, Any]) -> bool:
    """
    Evalúa una condición en un contexto dado de forma segura usando AST.

    Args:
        condition: Expresión de condición como string
                  (ej: "tipo_opinion == 'favorable' and pais == 'ES'")
        context: Diccionario con las variables disponibles

    Returns:
        True si la condición se cumple, False en caso contrario

    Ejemplos:
        >>> ctx = {'tipo_opinion': 'favorable', 'tipo_cuentas': 'normales'}
        >>> evaluate_condition("tipo_opinion == 'favorable'", ctx)
        True

        >>> evaluate_condition("tipo_opinion == 'favorable' and tipo_cuentas == 'consolidadas'", ctx)
        False

        >>> evaluate_condition("(tipo_opinion == 'favorable' or tipo_opinion == 'salvedades') and tipo_cuentas == 'normales'", ctx)
        True
    """
    if not condition or condition.strip() == '':
        return True

    try:
        # Parsear la expresión a AST
        tree = ast.parse(condition, mode='eval')

        # Evaluar usando el visitante seguro
        evaluator = SafeConditionEvaluator(context)
        result = evaluator.visit(tree.body)

        return bool(result)

    except SyntaxError as e:
        logger.error(f"Error de sintaxis en condición '{condition}': {e}")
        return False

    except ValueError as e:
        logger.error(f"Error evaluando condición '{condition}': {e}")
        return False

    except Exception as e:
        logger.warning(f"Error inesperado evaluando condición '{condition}': {e}")
        return False


# ==============================================================================
# EVALUACIÓN DE MÚLTIPLES CONDICIONES
# ==============================================================================

def evaluate_any(conditions: List[str], context: Dict[str, Any]) -> bool:
    """
    Evalúa múltiples condiciones con lógica OR.

    Args:
        conditions: Lista de expresiones de condición
        context: Diccionario con las variables

    Returns:
        True si al menos una condición se cumple
    """
    return any(evaluate_condition(cond, context) for cond in conditions)


def evaluate_all(conditions: List[str], context: Dict[str, Any]) -> bool:
    """
    Evalúa múltiples condiciones con lógica AND.

    Args:
        conditions: Lista de expresiones de condición
        context: Diccionario con las variables

    Returns:
        True si todas las condiciones se cumplen
    """
    return all(evaluate_condition(cond, context) for cond in conditions)


# ==============================================================================
# EVALUACIÓN DE DEPENDENCIAS DE CAMPOS
# ==============================================================================

def should_show_field(field_id: str, dependency_condition: Optional[str],
                     context: Dict[str, Any]) -> bool:
    """
    Determina si un campo debe mostrarse según su condición de dependencia.

    Args:
        field_id: ID del campo
        dependency_condition: Expresión de condición de dependencia
        context: Contexto actual

    Returns:
        True si el campo debe mostrarse
    """
    # Si no hay condición de dependencia, siempre se muestra
    if not dependency_condition:
        return True

    # Evaluar la condición
    return evaluate_condition(dependency_condition, context)


# ==============================================================================
# PROCESAMIENTO DE BLOQUES DE TEXTO
# ==============================================================================

def evaluate_block(block: BlockDefinition, context: Dict[str, Any]) -> Optional[str]:
    """
    Evalúa un bloque de texto y devuelve la plantilla de la primera regla que coincida.

    Args:
        block: Definición del bloque
        context: Contexto con variables

    Returns:
        Plantilla (string) de la regla que coincidió, o None si ninguna coincide
    """
    for rule in block.reglas:
        if evaluate_condition(rule.cuando, context):
            logger.debug(f"Bloque '{block.id}': condición '{rule.cuando}' = True")
            return rule.plantilla

    logger.debug(f"Bloque '{block.id}': ninguna condición coincidió")
    return None


def evaluate_all_blocks(blocks: List[BlockDefinition],
                       context: Dict[str, Any]) -> Dict[str, str]:
    """
    Evalúa todos los bloques de texto y devuelve un diccionario con las plantillas.

    Args:
        blocks: Lista de definiciones de bloques
        context: Contexto con variables

    Returns:
        Diccionario {block_id: plantilla_seleccionada}
    """
    results = {}

    for block in blocks:
        plantilla = evaluate_block(block, context)
        if plantilla is not None:
            results[block.id] = plantilla
        else:
            # Si ninguna regla coincide, usar cadena vacía
            results[block.id] = ""

    return results


# ==============================================================================
# VALIDACIÓN DE EXPRESIONES
# ==============================================================================

def is_valid_expression(expression: str) -> bool:
    """
    Valida que una expresión sea sintácticamente correcta.

    Args:
        expression: Expresión a validar

    Returns:
        True si la expresión es válida sintácticamente
    """
    try:
        ast.parse(expression, mode='eval')
        return True
    except SyntaxError:
        return False


def get_variables_in_expression(expression: str) -> List[str]:
    """
    Extrae las variables referenciadas en una expresión usando AST.

    Args:
        expression: Expresión a analizar

    Returns:
        Lista de nombres de variables
    """
    try:
        tree = ast.parse(expression, mode='eval')

        variables = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                # Excluir constantes
                if node.id not in ('True', 'False', 'None'):
                    variables.add(node.id)

        return sorted(list(variables))

    except SyntaxError:
        logger.error(f"Error de sintaxis al extraer variables de: {expression}")
        return []


# ==============================================================================
# CONSTRUCCIÓN DE EXPRESIONES CONDICIONALES
# ==============================================================================

def build_condition_from_dict(cond_dict: Dict[str, Any]) -> str:
    """
    Construye una expresión de condición desde un diccionario estructurado.

    Args:
        cond_dict: Diccionario con estructura de condición

    Returns:
        Expresión como string

    Ejemplos:
        >>> cond = {'campo': 'tipo_opinion', 'igual': 'favorable'}
        >>> build_condition_from_dict(cond)
        "tipo_opinion == 'favorable'"

        >>> cond = {'and': [
        ...     {'campo': 'tipo_opinion', 'igual': 'favorable'},
        ...     {'campo': 'tipo_cuentas', 'igual': 'consolidadas'}
        ... ]}
        >>> build_condition_from_dict(cond)
        "(tipo_opinion == 'favorable' and tipo_cuentas == 'consolidadas')"
    """
    # Caso simple: campo == valor
    if 'campo' in cond_dict and 'igual' in cond_dict:
        campo = cond_dict['campo']
        valor = cond_dict['igual']
        # Escapar comillas en el valor
        if isinstance(valor, str):
            valor_escaped = valor.replace("'", "\\'")
            return f"{campo} == '{valor_escaped}'"
        else:
            return f"{campo} == {valor}"

    # Caso: campo != valor
    if 'campo' in cond_dict and 'no_igual' in cond_dict:
        campo = cond_dict['campo']
        valor = cond_dict['no_igual']
        if isinstance(valor, str):
            valor_escaped = valor.replace("'", "\\'")
            return f"{campo} != '{valor_escaped}'"
        else:
            return f"{campo} != {valor}"

    # Caso: campo > valor
    if 'campo' in cond_dict and 'mayor' in cond_dict:
        campo = cond_dict['campo']
        valor = cond_dict['mayor']
        return f"{campo} > {valor}"

    # Caso: campo < valor
    if 'campo' in cond_dict and 'menor' in cond_dict:
        campo = cond_dict['campo']
        valor = cond_dict['menor']
        return f"{campo} < {valor}"

    # Caso: AND de múltiples condiciones
    if 'and' in cond_dict:
        subcondiciones = [build_condition_from_dict(c) for c in cond_dict['and']]
        return f"({' and '.join(subcondiciones)})"

    # Caso: OR de múltiples condiciones
    if 'or' in cond_dict:
        subcondiciones = [build_condition_from_dict(c) for c in cond_dict['or']]
        return f"({' or '.join(subcondiciones)})"

    # Caso: NOT de una condición
    if 'not' in cond_dict:
        subcondicion = build_condition_from_dict(cond_dict['not'])
        return f"(not {subcondicion})"

    logger.warning(f"No se pudo construir condición desde: {cond_dict}")
    return "True"


# ==============================================================================
# UTILIDADES DE DEBUG
# ==============================================================================

def debug_condition_evaluation(condition: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evalúa una condición y devuelve información de debug.

    Args:
        condition: Expresión a evaluar
        context: Contexto de variables

    Returns:
        Diccionario con resultado y detalles
    """
    result = {
        'condition': condition,
        'is_valid': is_valid_expression(condition),
        'variables_used': get_variables_in_expression(condition),
        'result': None,
        'error': None
    }

    try:
        result['result'] = evaluate_condition(condition, context)
    except Exception as e:
        result['error'] = str(e)

    return result


# ==============================================================================
# TESTS
# ==============================================================================

if __name__ == "__main__":
    # Tests básicos
    print("=" * 70)
    print("TESTS DE CONDITIONS_ENGINE")
    print("=" * 70)

    test_context = {
        'tipo_opinion': 'favorable',
        'tipo_cuentas': 'consolidadas',
        'tipo_entidad': 'EIP',
        'importe': 1000000,
        'pais': 'ES',
    }

    test_cases = [
        ("tipo_opinion == 'favorable'", True),
        ("tipo_opinion == 'desfavorable'", False),
        ("tipo_opinion == 'favorable' and tipo_cuentas == 'consolidadas'", True),
        ("tipo_opinion == 'favorable' or tipo_opinion == 'salvedades'", True),
        ("(tipo_opinion == 'favorable' or tipo_opinion == 'salvedades') and pais == 'ES'", True),
        ("tipo_entidad == 'EIP' and tipo_cuentas == 'consolidadas'", True),
        ("importe > 500000", True),
        ("importe < 500000", False),
        ("importe >= 1000000", True),
        ("not (tipo_opinion == 'desfavorable')", True),
        ("tipo_opinion in ['favorable', 'salvedades']", True),
        ("'favorable' in tipo_opinion", True),
    ]

    for expr, expected in test_cases:
        result = evaluate_condition(expr, test_context)
        status = "✅" if result == expected else "❌"
        print(f"{status} {expr}")
        print(f"   Esperado: {expected}, Obtenido: {result}")

    print("\n" + "=" * 70)
    print("EXTRACCIÓN DE VARIABLES")
    print("=" * 70)

    expr = "(tipo_opinion == 'favorable' or tipo_opinion == 'salvedades') and pais == 'ES'"
    variables = get_variables_in_expression(expr)
    print(f"Expresión: {expr}")
    print(f"Variables: {variables}")

    print("\n" + "=" * 70)
