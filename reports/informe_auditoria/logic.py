"""
================================================================================
LOGIC.PY - Motor de Contexto para Informes de Auditoría
================================================================================

Este módulo implementa la lógica central del Esquema A:
- Carga los archivos YAML de configuración
- Evalúa las condiciones de cada bloque de texto
- Renderiza las plantillas con Jinja2
- Construye el contexto final para la plantilla Word

Versión: 3.0 - Esquema A (lógica externa)

Uso:
    from logic import build_context
    
    data_in = {
        'tipo_opinion': 'favorable',
        'tipo_cuentas': 'normales',
        'nombre_entidad': 'ABC S.A.',
        ...
    }
    
    context = build_context(data_in)
    # context contiene todas las variables listas para la plantilla Word
================================================================================
"""

import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from jinja2 import Environment, BaseLoader
import logging

# Importar el evaluador de condiciones del core
from core.conditions_engine import evaluate_condition

# Configuración del logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BloquesTextoProcessor:
    """
    Procesador de bloques de texto condicionales.

    Lee la configuración YAML, evalúa condiciones y renderiza plantillas
    según las reglas definidas en bloques_texto.yaml.
    """
    
    def __init__(self, config_dir: Optional[Path] = None):
        """
        Inicializa el procesador.
        
        Args:
            config_dir: Directorio donde se encuentran los archivos YAML.
                       Si es None, usa el directorio actual.
        """
        self.config_dir = config_dir or Path(__file__).parent
        self.jinja_env = Environment(loader=BaseLoader())
        self.bloques_texto: List[Dict] = []
        self._load_config()
    
    def _load_config(self) -> None:
        """
        Carga la configuración de bloques de texto desde archivos YAML.

        Busca y carga todos los archivos bloques_texto*.yaml en el
        directorio de configuración del plugin.
        """
        # Buscar archivos de bloques (pueden estar divididos en partes)
        yaml_files = list(self.config_dir.glob("bloques_texto*.yaml"))
        
        if not yaml_files:
            logger.warning("No se encontraron archivos bloques_texto*.yaml")
            return
        
        for yaml_file in sorted(yaml_files):
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    content = yaml.safe_load(f)
                    if content and 'bloques_texto' in content:
                        self.bloques_texto.extend(content['bloques_texto'])
                    elif content and isinstance(content, list):
                        # Si el archivo es solo una lista de bloques
                        self.bloques_texto.extend(content)
            except Exception as e:
                logger.error(f"Error cargando {yaml_file}: {e}")
    
    def _evaluar_condicion(self, condicion: str, contexto: Dict[str, Any]) -> bool:
        """
        Evalúa una condición en el contexto dado usando el motor del core.

        Args:
            condicion: Expresión de condición como string (ej: "tipo_opinion == 'favorable'")
            contexto: Diccionario con las variables del contexto

        Returns:
            True si la condición se cumple, False en caso contrario
        """
        # Usar el evaluador seguro del core (basado en AST)
        return evaluate_condition(condicion, contexto)
    
    def _renderizar_plantilla(self, plantilla: str, contexto: Dict[str, Any]) -> str:
        """
        Renderiza una plantilla Jinja2 con el contexto dado.
        
        Args:
            plantilla: Texto de la plantilla con variables {{ var }}
            contexto: Diccionario con las variables
        
        Returns:
            Texto renderizado
        """
        try:
            template = self.jinja_env.from_string(plantilla)
            return template.render(**contexto).strip()
        except Exception as e:
            logger.error(f"Error renderizando plantilla: {e}")
            return ""
    
    def procesar_bloque(self, bloque: Dict, contexto: Dict[str, Any]) -> str:
        """
        Procesa un bloque de texto evaluando sus reglas.
        
        Args:
            bloque: Definición del bloque con id, reglas, etc.
            contexto: Diccionario con las variables del contexto
        
        Returns:
            Texto resultante del bloque (vacío si ninguna regla coincide)
        """
        bloque_id = bloque.get('id', 'unknown')
        reglas = bloque.get('reglas', [])
        
        for regla in reglas:
            condicion = regla.get('cuando', 'True')
            plantilla = regla.get('plantilla', '')
            
            if self._evaluar_condicion(condicion, contexto):
                resultado = self._renderizar_plantilla(plantilla, contexto)
                logger.debug(f"Bloque '{bloque_id}': condición '{condicion}' = True")
                return resultado
        
        logger.debug(f"Bloque '{bloque_id}': ninguna condición coincidió")
        return ""
    
    def procesar_todos(self, contexto: Dict[str, Any]) -> Dict[str, str]:
        """
        Procesa todos los bloques de texto.
        
        Args:
            contexto: Diccionario con las variables del contexto
        
        Returns:
            Diccionario con id_bloque -> texto_renderizado
        """
        resultados = {}
        for bloque in self.bloques_texto:
            bloque_id = bloque.get('id')
            if bloque_id:
                resultados[bloque_id] = self.procesar_bloque(bloque, contexto)
        return resultados


def calcular_variables_auxiliares(data_in: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calcula las variables auxiliares derivadas de los datos de entrada.
    
    Estas variables simplifican las plantillas evitando lógica repetitiva.
    
    Args:
        data_in: Datos de entrada del usuario
    
    Returns:
        Diccionario con variables auxiliares calculadas
    """
    aux = {}
    
    tipo_cuentas = data_in.get('tipo_cuentas', 'normales')
    tipo_entidad = data_in.get('tipo_entidad', 'No EIP')
    tipo_opinion = data_in.get('tipo_opinion', 'favorable')
    entidad_cotizada = data_in.get('entidad_cotizada', 'no')
    auditor_continuidad = data_in.get('auditor_continuidad', 'no')
    descripcion_servicios = data_in.get('descripcion_servicios_adicionales', '')
    einf_facilitado = data_in.get('einf_facilitado', 'si')
    limitacion_alcance = data_in.get('limitacion_alcance', 'no')
    motivo_calificacion = data_in.get('motivo_calificacion', '')
    
    # Nombre del tipo de cuentas
    if tipo_cuentas == 'consolidadas':
        aux['nombre_tipo_cuentas'] = 'cuentas anuales consolidadas'
    elif tipo_cuentas == 'abreviadas':
        aux['nombre_tipo_cuentas'] = 'cuentas anuales abreviadas'
    else:
        aux['nombre_tipo_cuentas'] = 'cuentas anuales'
    
    # Nombre del fundamento según opinión
    if tipo_opinion == 'desfavorable':
        aux['nombre_fundamento'] = 'opinión desfavorable'
    elif tipo_opinion == 'denegada':
        aux['nombre_fundamento'] = 'denegación de opinión'
    elif tipo_opinion == 'salvedades':
        aux['nombre_fundamento'] = 'opinión con salvedades'
    else:
        aux['nombre_fundamento'] = 'opinión'
    
    # Sufijos para tipo de cuentas
    aux['sufijo_consolidada'] = ' consolidada' if tipo_cuentas == 'consolidadas' else ''
    aux['sufijo_abreviadas'] = ' abreviadas' if tipo_cuentas == 'abreviadas' else ''
    
    if tipo_cuentas == 'consolidadas':
        aux['sufijo_tipo_cuentas'] = ' consolidadas'
        aux['sufijo_tipo_cuentas_simple'] = ' consolidadas'
    elif tipo_cuentas == 'abreviadas':
        aux['sufijo_tipo_cuentas'] = ' abreviadas'
        aux['sufijo_tipo_cuentas_simple'] = ' abreviadas'
    else:
        aux['sufijo_tipo_cuentas'] = ''
        aux['sufijo_tipo_cuentas_simple'] = ''
    
    # Sufijos para EIP y consolidado
    aux['sufijo_consolidado_eip'] = ' consolidado' if (tipo_cuentas == 'consolidadas' and tipo_entidad == 'EIP') else ''
    aux['sufijo_consolidado_simple'] = 'consolidado' if tipo_cuentas == 'consolidadas' else ''
    aux['sufijo_sociedad_dominante'] = 'de la Sociedad dominante' if tipo_cuentas == 'consolidadas' else 'de la Entidad'
    aux['sufijo_parte_consolidado'] = 'de esta parte' if tipo_cuentas == 'consolidadas' else ''
    aux['sufijo_einf_consolidado'] = '(EINF) consolidado' if tipo_cuentas == 'consolidadas' else ''
    
    # Texto de conocimiento de entidad
    aux['texto_conocimiento_entidad'] = 'del Grupo' if tipo_cuentas == 'consolidadas' else 'de la Entidad'
    
    # Texto para cotizadas (IAGC)
    if entidad_cotizada == 'si':
        aux['texto_cotizada_iagc'] = (
            ', determinada información incluida en el Informe Anual de Gobierno Corporativo '
            'y el Informe Anual de Remuneraciones de los Consejeros, a los que se refiere '
            'la Ley de Auditoría de Cuentas,'
        )
    else:
        aux['texto_cotizada_iagc'] = ''
    
    # Texto EINF facilitado
    aux['texto_einf_facilitado'] = 'se facilita' if einf_facilitado == 'si' else 'no se facilita'
    
    # Texto auditor continuidad
    aux['texto_auditor_continuidad'] = 'fuimos designados' if auditor_continuidad == 'si' else 'no fuimos designados'
    
    # Texto de servicios adicionales
    if descripcion_servicios:
        aux['texto_servicios_adicionales'] = (
            f'Los servicios distintos a los de auditoría de cuentas, adicionales a los indicados '
            f'en la memoria de las cuentas anuales (y/o en el informe de gestión), que han sido '
            f'prestados a la Entidad auditada han sido los siguientes:\n\n'
            f'* {descripcion_servicios}'
        )
    else:
        aux['texto_servicios_adicionales'] = 'No se han prestado servicios adicionales distintos a la auditoría.'
    
    # Nombre tipo opinión para fundamento
    if tipo_opinion == 'desfavorable':
        aux['nombre_tipo_opinion_fundamento'] = 'desfavorable'
    else:
        aux['nombre_tipo_opinion_fundamento'] = 'con salvedades'
    
    # Texto intro KAM/AMRA (cuando hay incertidumbre u otros)
    incertidumbre = data_in.get('incertidumbre_funcionamiento', 'no')
    if incertidumbre == 'si':
        aux['texto_intro_kam'] = (
            'Además de la cuestión descrita en la sección Incertidumbre material relacionada '
            'con la empresa en funcionamiento, hemos determinado que las cuestiones que se '
            'describen a continuación son las cuestiones clave consideradas en la auditoría '
            'que se deben comunicar en nuestro informe.'
        )
        aux['texto_intro_amra'] = (
            'Además de la cuestión descrita en la sección Incertidumbre material relacionada '
            'con la empresa en funcionamiento, hemos determinado que los riesgos que se '
            'describen a continuación son los riesgos más significativos considerados en '
            'la auditoría que se deben comunicar en nuestro informe.'
        )
    else:
        aux['texto_intro_kam'] = (
            'Hemos determinado que las cuestiones que se describen a continuación son las '
            'cuestiones clave consideradas en la auditoría que se deben comunicar en nuestro informe.'
        )
        aux['texto_intro_amra'] = (
            'Hemos determinado que los riesgos que se describen a continuación son los '
            'riesgos más significativos considerados en la auditoría que se deben comunicar '
            'en nuestro informe.'
        )
    
    # Textos para informe de gestión con EINF
    if tipo_opinion == 'favorable':
        aux['texto_opinion_gestion_einf'] = (
            ' y que el resto de la información que contiene el informe de gestión concuerda '
            'con la de las cuentas anuales del ejercicio y su contenido y presentación son '
            'conformes a la normativa que resulta de aplicación'
        )
        aux['texto_fundamento_einf'] = ''
    elif tipo_opinion == 'salvedades' and limitacion_alcance != 'si':
        aux['texto_opinion_gestion_einf'] = (
            ' y que, salvo por las incorrección(es) material(es) indicadas, el resto de la '
            'información que contiene el informe de gestión concuerda con la de las cuentas '
            'anuales del ejercicio y su contenido y presentación son conformes a la normativa '
            'que resulta de aplicación'
        )
        aux['texto_fundamento_einf'] = (
            f'Como se describe en la sección Fundamento de la opinión {aux["nombre_tipo_opinion_fundamento"]}, '
            f'existen {"una/varias incorrección(es) material(es)" if motivo_calificacion == "incorreccion" else "una/varias limitación(es) al alcance"} '
            f'en las cuentas anuales adjuntas. Hemos concluido que dichas circunstancias afectan '
            f'de igual manera y en la misma medida al informe de gestión.'
        )
    elif tipo_opinion == 'salvedades' and limitacion_alcance == 'si':
        aux['texto_opinion_gestion_einf'] = ''
        aux['texto_fundamento_einf'] = (
            'Como se describe en la sección Fundamento de la opinión con salvedades, no hemos '
            'podido obtener evidencia de auditoría suficiente y adecuada sobre la(s) cuestión(es) '
            'indicada(s) en dicha sección, lo que supone una/varias limitación(es) al alcance de '
            'nuestro trabajo. En consecuencia, no hemos podido alcanzar una conclusión sobre si '
            'la información que contiene el informe de gestión concuerda con la de las cuentas '
            'anuales ni sobre si su contenido y presentación son conformes a la normativa aplicable.'
        )
    else:
        aux['texto_opinion_gestion_einf'] = ''
        aux['texto_fundamento_einf'] = ''

    return aux


def apply_plural_markers(text: str, n: int) -> str:
    """
    Automatically convert plural marker patterns based on the count.

    Converts patterns like:
    - "la(s)" -> "la" (n=1) or "las" (n>1)
    - "cuestión(es)" -> "cuestión" (n=1) or "cuestiones" (n>1)
    - "descrita(s)" -> "descrita" (n=1) or "descritas" (n>1)
    - "indicada(s)" -> "indicada" (n=1) or "indicadas" (n>1)
    - "incorrección(es)" -> "incorrección" (n=1) or "incorrecciones" (n>1)
    - "material(es)" -> "material" (n=1) or "materiales" (n>1)
    - "limitación(es)" -> "limitación" (n=1) or "limitaciones" (n>1)
    - "una/varias incorrección(es) material(es)" -> singular/plural phrase
    - "una/varias limitación(es) al alcance" -> singular/plural phrase

    Args:
        text: Text containing plural markers
        n: Count of items (1 = singular, >1 = plural)

    Returns:
        Text with resolved plural forms
    """
    import re

    if not text or not isinstance(text, str):
        return text

    # Define singular/plural replacements
    if n == 1:
        # Singular forms
        replacements = [
            # Common patterns with (s) suffix
            (r'\bla\(s\)', 'la'),
            (r'\bLa\(s\)', 'La'),
            (r'\bdescrita\(s\)', 'descrita'),
            (r'\bDescrita\(s\)', 'Descrita'),
            (r'\bindicada\(s\)', 'indicada'),
            (r'\bIndicada\(s\)', 'Indicada'),
            # Noun patterns with (es) suffix
            (r'\bcuestión\(es\)', 'cuestión'),
            (r'\bCuestión\(es\)', 'Cuestión'),
            (r'\bincorrección\(es\)', 'incorrección'),
            (r'\bIncorrección\(es\)', 'Incorrección'),
            (r'\blimitación\(es\)', 'limitación'),
            (r'\bLimitación\(es\)', 'Limitación'),
            (r'\bmaterial\(es\)', 'material'),
            (r'\bMaterial\(es\)', 'Material'),
            # Complex phrases with una/varias
            (r'una/varias incorrección\(es\) material\(es\)', 'una incorrección material'),
            (r'Una/varias incorrección\(es\) material\(es\)', 'Una incorrección material'),
            (r'una/varias limitación\(es\) al alcance', 'una limitación al alcance'),
            (r'Una/varias limitación\(es\) al alcance', 'Una limitación al alcance'),
            (r'una/varias limitación\(es\)', 'una limitación'),
            (r'Una/varias limitación\(es\)', 'Una limitación'),
            (r'una/varias incorrección\(es\)', 'una incorrección'),
            (r'Una/varias incorrección\(es\)', 'Una incorrección'),
            # Generic una/varias handling
            (r'\buna/varias\b', 'una'),
            (r'\bUna/varias\b', 'Una'),
        ]
    else:
        # Plural forms
        replacements = [
            # Common patterns with (s) suffix
            (r'\bla\(s\)', 'las'),
            (r'\bLa\(s\)', 'Las'),
            (r'\bdescrita\(s\)', 'descritas'),
            (r'\bDescrita\(s\)', 'Descritas'),
            (r'\bindicada\(s\)', 'indicadas'),
            (r'\bIndicada\(s\)', 'Indicadas'),
            # Noun patterns with (es) suffix
            (r'\bcuestión\(es\)', 'cuestiones'),
            (r'\bCuestión\(es\)', 'Cuestiones'),
            (r'\bincorrección\(es\)', 'incorrecciones'),
            (r'\bIncorrección\(es\)', 'Incorrecciones'),
            (r'\blimitación\(es\)', 'limitaciones'),
            (r'\bLimitación\(es\)', 'Limitaciones'),
            (r'\bmaterial\(es\)', 'materiales'),
            (r'\bMaterial\(es\)', 'Materiales'),
            # Complex phrases with una/varias
            (r'una/varias incorrección\(es\) material\(es\)', 'varias incorrecciones materiales'),
            (r'Una/varias incorrección\(es\) material\(es\)', 'Varias incorrecciones materiales'),
            (r'una/varias limitación\(es\) al alcance', 'varias limitaciones al alcance'),
            (r'Una/varias limitación\(es\) al alcance', 'Varias limitaciones al alcance'),
            (r'una/varias limitación\(es\)', 'varias limitaciones'),
            (r'Una/varias limitación\(es\)', 'Varias limitaciones'),
            (r'una/varias incorrección\(es\)', 'varias incorrecciones'),
            (r'Una/varias incorrección\(es\)', 'Varias incorrecciones'),
            # Generic una/varias handling
            (r'\buna/varias\b', 'varias'),
            (r'\bUna/varias\b', 'Varias'),
        ]

    result = text
    for pattern, replacement in replacements:
        result = re.sub(pattern, replacement, result)

    return result


def build_context(data_in: Dict[str, Any], config_dir: Optional[Path] = None) -> Dict[str, Any]:
    """
    Construye el contexto completo para la plantilla Word.
    
    Esta es la función principal que:
    1. Toma los datos de entrada del usuario
    2. Calcula las variables auxiliares
    3. Procesa todos los bloques de texto condicionales
    4. Devuelve un contexto unificado para Jinja2
    
    Args:
        data_in: Diccionario con los valores introducidos por el usuario
        config_dir: Directorio donde están los archivos YAML (opcional)
    
    Returns:
        Diccionario con todas las variables listas para la plantilla
    
    Ejemplo:
        >>> data_in = {
        ...     'tipo_opinion': 'favorable',
        ...     'tipo_cuentas': 'normales',
        ...     'nombre_entidad': 'Empresa ABC S.A.',
        ...     'dia_cierre_ejercicio': 31,
        ...     'mes_cierre_ejercicio': 'diciembre',
        ...     'ano_cierre_ejercicio': 2024,
        ...     # ... resto de campos
        ... }
        >>> context = build_context(data_in)
        >>> # context['parrafo_opinion'] contiene el párrafo de opinión renderizado
    """
    # 1. Iniciar con los datos de entrada
    context = dict(data_in)

    # 2. Calcular variables auxiliares
    auxiliares = calcular_variables_auxiliares(data_in)
    context.update(auxiliares)

    # 3. Calcular año anterior si no está presente
    if 'ano_cierre_ejercicio' in context and 'ano_cierre_anterior' not in context:
        context['ano_cierre_anterior'] = context['ano_cierre_ejercicio'] - 1

    # 4. Determine multi-issue count for plural handling
    tipo_opinion = data_in.get('tipo_opinion', 'favorable')
    motivo_calificacion = data_in.get('motivo_calificacion', '')

    # Calculate n for plural markers
    n_issues = 1
    if tipo_opinion == 'salvedades':
        try:
            n_issues = int(data_in.get('num_salvedades') or 1)
            n_issues = max(1, min(10, n_issues))
        except (ValueError, TypeError):
            n_issues = 1
    elif tipo_opinion == 'desfavorable':
        try:
            n_issues = int(data_in.get('num_desfavorables') or 1)
            n_issues = max(1, min(10, n_issues))
        except (ValueError, TypeError):
            n_issues = 1

    # Store n for reference
    context['_n_issues'] = n_issues

    # 5. Procesar todos los bloques de texto
    processor = BloquesTextoProcessor(config_dir)
    bloques_renderizados = processor.procesar_todos(context)
    context.update(bloques_renderizados)

    # 6. Generate multi-paragraph fundamento if N > 1
    if tipo_opinion in ('salvedades', 'desfavorable') and n_issues > 1:
        # Get the single-instance template from bloques_texto.yaml
        fundamento_template = None
        for bloque in processor.bloques_texto:
            if bloque.get('id') == 'parrafo_fundamento_calificacion':
                for regla in bloque.get('reglas', []):
                    condicion = regla.get('cuando', 'True')
                    if processor._evaluar_condicion(condicion, context):
                        fundamento_template = regla.get('plantilla', '')
                        break
                break

        if fundamento_template:
            paragraphs = []
            for i in range(1, n_issues + 1):
                # Build a temporary context for this instance
                tmp_context = context.copy()

                # Determine the key prefix based on opinion type
                if tipo_opinion == 'salvedades':
                    key_prefix = f"salvedad_{i}"
                else:
                    key_prefix = f"desfavorable_{i}"

                # Map composite keys back to original field names
                # Find all fields with this prefix in data_in
                for key, value in data_in.items():
                    if key.startswith(f"{key_prefix}__"):
                        original_field = key[len(f"{key_prefix}__"):]
                        tmp_context[original_field] = value

                # For first instance, use original field values if composite not found
                if i == 1:
                    # Original fields are already in context
                    pass

                # Render the template for this instance
                try:
                    rendered = processor._renderizar_plantilla(fundamento_template, tmp_context)
                    if rendered.strip():
                        paragraphs.append(rendered.strip())
                except Exception as e:
                    logger.warning(f"Error rendering fundamento for instance {i}: {e}")

            # Join paragraphs with double newlines
            if paragraphs:
                context['parrafo_fundamento_calificacion'] = '\n\n'.join(paragraphs)

    # 7. Apply plural markers to all string values in context
    for key, value in list(context.items()):
        if isinstance(value, str) and ('(s)' in value or '(es)' in value or 'una/varias' in value):
            context[key] = apply_plural_markers(value, n_issues)

    logger.info(f"Contexto construido con {len(context)} variables (n_issues={n_issues})")
    return context


# ==============================================================================
# EJEMPLO DE USO Y PRUEBAS
# ==============================================================================

if __name__ == "__main__":
    # Datos de ejemplo para prueba
    datos_ejemplo = {
        # Información general
        'tipo_administradores': 'los administradores',
        'Organo': 'los Accionistas',
        'nombre_entidad': 'Empresa Ejemplo S.A.',
        'ciudad_auditoria': 'Madrid',
        'nombre_auditor': 'Juan García López',
        'numero_roac_auditor': 'S0702',
        
        # Tipo de cuentas y entidad
        'tipo_cuentas': 'normales',
        'tipo_entidad': 'No EIP',
        'tipo_auditoria': 'Obligatoria',
        
        # Opinión
        'tipo_opinion': 'favorable',
        'marco_normativo': 'PGC',
        'numero_nota_marco': 2,
        
        # Fechas
        'dia_cierre_ejercicio': 31,
        'mes_cierre_ejercicio': 'diciembre',
        'ano_cierre_ejercicio': 2024,
        'dia_informe_auditoria': 15,
        'mes_informe_auditoria': 'marzo',
        'ano_informe_auditoria': 2025,
        
        # Otras condiciones
        'incertidumbre_funcionamiento': 'no',
        'enfasis_adicional': 'no',
        'amra_voluntario': 'no',
        'otros_kam': 'no',
        'otros_amra': 'no',
        'otras_cuestiones': 'no',
        'obligacion_presentar_informe_gestion': 'si',
        'obligacion_EINF': 'no',
        'firma_digital': 'no',
    }
    
    # Construir contexto
    print("=" * 70)
    print("PRUEBA DE BUILD_CONTEXT")
    print("=" * 70)
    
    context = build_context(datos_ejemplo, Path(__file__).parent)
    
    # Mostrar algunos resultados
    print(f"\n📄 titulo_tipo_opinion: {context.get('titulo_tipo_opinion', 'NO DEFINIDO')}")
    print(f"\n📄 nombre_tipo_cuentas: {context.get('nombre_tipo_cuentas', 'NO DEFINIDO')}")
    print(f"\n📄 Fragmento de parrafo_opinion:")
    parrafo = context.get('parrafo_opinion', 'NO DEFINIDO')
    print(f"   {parrafo[:200]}..." if len(parrafo) > 200 else f"   {parrafo}")
    
    print("\n" + "=" * 70)
    print(f"Total de variables en contexto: {len(context)}")
    print("=" * 70)
