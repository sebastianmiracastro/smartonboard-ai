"""Tests del sintetizador extractivo propio (respuestas sin LLM, 100% local).

Verifican que ante una pregunta se seleccionen las oraciones pertinentes de varios
fragmentos, se reorganicen de forma coherente y se descarte el solape duplicado."""
from app.services.rag import RetrievedChunk
from app.services.extractive import synthesize_answer


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
