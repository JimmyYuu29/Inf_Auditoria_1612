from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from reports.informe_auditoria.logic import apply_plural_markers, build_context


def test_apply_plural_markers_singular_plural():
    text = "la(s) cuestión(es) descrita(s) y una/varias incorrección(es) material(es)"
    assert apply_plural_markers(text, 1) == "la cuestión descrita y una incorrección material"
    assert apply_plural_markers(text, 3) == "las cuestiones descritas y varias incorrecciones materiales"


def test_build_context_multi_paragraph_fundamento():
    config_dir = Path("reports/informe_auditoria/config")
    data_in = {
        "tipo_opinion": "salvedades",
        "motivo_calificacion": "incorreccion",
        "num_salvedades": 2,
        "numero_nota_incorreccion": 11,
        "descripcion_incorreccion": "omitió registrar provisiones",
        "explicacion_correccion_incorreccion": "De haberse registrado",
        "cuantificacion_efectos_incorreccion": "las pérdidas habrían sido mayores",
        "efecto_resultados_impuestos": "el resultado se vería afectado",
    }

    for i in range(1, 3):
        prefix = f"salvedad_{i}"
        data_in[f"{prefix}__numero_nota_incorreccion"] = 10 + i
        data_in[f"{prefix}__descripcion_incorreccion"] = f"incorrección {i}"
        data_in[f"{prefix}__explicacion_correccion_incorreccion"] = f"explicación {i}"
        data_in[f"{prefix}__cuantificacion_efectos_incorreccion"] = f"cuantificación {i}"
        data_in[f"{prefix}__efecto_resultados_impuestos"] = f"efecto {i}"

    context = build_context(data_in, config_dir)
    fundamento = context.get("parrafo_fundamento_calificacion")
    assert fundamento is not None
    assert "\n\n" in fundamento
    assert "incorrección 1" in fundamento
    assert "incorrección 2" in fundamento
    assert "(s)" not in fundamento
    assert "una/varias" not in fundamento
