"""Tests del sintetizador extractivo propio (respuestas sin LLM, 100% local).

Verifican que ante una pregunta se seleccionen las oraciones pertinentes de varios
fragmentos, se reorganicen de forma coherente y se descarte el solape duplicado."""
from app.services.rag import RetrievedChunk
from app.services.extractive import synthesize_answer, _mmr_select


def _chunk(doc_id, idx, content, sim=0.6):
    return RetrievedChunk(content=content, document_id=doc_id, similarity=sim,
                          category="cultura", chunk_index=idx)


def test_sin_fragmentos_devuelve_vacio():
    assert synthesize_answer("¿algo?", []) == ""


def test_selecciona_y_organiza_informacion_relevante():
    chunks = [
        _chunk("doc-1", 0,
               "Para solicitar vacaciones, el empleado envía la solicitud por el portal "
               "de RRHH con al menos 15 días de anticipación. El jefe directo la aprueba "
               "en un plazo de 3 días hábiles."),
        _chunk("doc-1", 1,
               "Cada empleado acumula 15 días hábiles de vacaciones por año. "
               "El menú de la cafetería cambia cada semana en la sede norte."),
    ]
    ans = synthesize_answer("¿Cómo solicito vacaciones y cuántos días tengo?", chunks)

    assert ans, "debe producir una respuesta"
    low = ans.lower()
    # Trae los datos pertinentes (proceso + cantidad de días) de distintos fragmentos
    assert "portal de rrhh" in low
    assert "15 días" in low
    assert "3 días hábiles" in low


def test_descarta_solape_duplicado_entre_fragmentos():
    # El segundo fragmento empieza con el final del primero (solape típico del chunking)
    chunks = [
        _chunk("doc-1", 0,
               "El proceso de onboarding dura dos semanas y termina con una evaluación "
               "final con tu líder de equipo asignado."),
        _chunk("doc-1", 1,
               "con una evaluación final con tu líder de equipo asignado. Después recibes "
               "tu plan de desarrollo profesional."),
    ]
    ans = synthesize_answer("¿Cómo es el proceso de onboarding?", chunks)
    # La frase solapada no debe aparecer dos veces
    assert ans.lower().count("evaluación final con tu líder de equipo asignado") == 1


def test_preserva_pasos_como_vinetas():
    content = (
        "Para solicitar tus vacaciones sigue estos pasos:\n"
        "1. Escribe a tu jefe directo con dos semanas de anticipación.\n"
        "2. Espera la aprobación en el sistema de Recursos Humanos.\n"
        "3. Registra las fechas aprobadas en el portal interno de la empresa."
    )
    ans = synthesize_answer(
        "cómo solicito mis vacaciones paso a paso",
        [_chunk("d1", 0, content)],
        ["pasos para pedir vacaciones", "proceso de solicitud de vacaciones"],
    )
    assert ans.count("•") >= 3                          # los 3 pasos como viñetas
    assert "Escribe a tu jefe" in ans
    assert "Espera la aprobación" in ans                # el paso intermedio NO se pierde
    assert "Registra las fechas aprobadas" in ans       # enumeración completa


def test_mmr_descarta_oraciones_casi_identicas():
    # 0 y 1 casi idénticas (coseno ~0.99); 2 distinta.
    embeddings = [[1.0, 0.0, 0.0], [0.99, 0.14, 0.0], [0.0, 1.0, 0.0]]
    sim_by_i = {0: 0.90, 1: 0.88, 2: 0.55}
    selected = _mmr_select([0, 1, 2], sim_by_i, embeddings, k=3)
    assert 0 in selected and 2 in selected
    assert 1 not in selected                            # redundante con 0 → descartada


def test_mmr_prioriza_la_mas_relevante():
    embeddings = [[1.0, 0.0], [0.0, 1.0], [0.7, 0.7]]
    sim_by_i = {0: 0.9, 1: 0.4, 2: 0.6}
    selected = _mmr_select([0, 1, 2], sim_by_i, embeddings, k=2)
    assert selected[0] == 0                             # la más relevante va primero
