from app.models.models import Document, DocumentChunk
from tests.conftest import get_token


def _add_docs(db_session, company_id: str):
    doc_publico = Document(
        id="doc-pub", company_id=company_id,
        name="Manual público", status="indexado",
        uploaded_by="user-rrhh", require_rrhh=False, require_gerencia=False,
    )
    doc_rrhh = Document(
        id="doc-rrhh", company_id=company_id,
        name="Nómina interna", status="indexado",
        uploaded_by="user-rrhh", require_rrhh=True, require_gerencia=False,
    )
    doc_gerencia = Document(
        id="doc-ger", company_id=company_id,
        name="Presupuesto gerencial", status="indexado",
        uploaded_by="user-rrhh", require_rrhh=False, require_gerencia=True,
    )
    doc_seniority = Document(
        id="doc-senior", company_id=company_id,
        name="Guía Senior", status="indexado",
        uploaded_by="user-rrhh", require_rrhh=False, require_gerencia=False,
        min_seniority=3,
    )
    doc_dept = Document(
        id="doc-dept", company_id=company_id,
        name="Doc solo RR.HH.", status="indexado",
        uploaded_by="user-rrhh", require_rrhh=False, require_gerencia=False,
        dept_permission="dept-rrhh",
    )
    db_session.add_all([doc_publico, doc_rrhh, doc_gerencia, doc_seniority, doc_dept])
    db_session.commit()


def test_empleado_solo_ve_documentos_publicos(client, seed_data, db_session):
    _add_docs(db_session, "comp-test")
    token = get_token(client, "carlos@test.co", "test123")
    resp = client.get("/api/documents/", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    ids = {d["id"] for d in resp.json()}
    assert "doc-pub" in ids
    assert "doc-rrhh" not in ids
    assert "doc-ger" not in ids


def test_empleado_junior_no_ve_doc_de_seniority_alta(client, seed_data, db_session):
    _add_docs(db_session, "comp-test")
    token = get_token(client, "carlos@test.co", "test123")  # seniority_level=1
    resp = client.get("/api/documents/", headers={"Authorization": f"Bearer {token}"})
    ids = {d["id"] for d in resp.json()}
    assert "doc-senior" not in ids  # requiere seniority >= 3


def test_empleado_no_ve_doc_de_otro_departamento(client, seed_data, db_session):
    _add_docs(db_session, "comp-test")
    token = get_token(client, "carlos@test.co", "test123")  # dept-eng, no dept-rrhh
    resp = client.get("/api/documents/", headers={"Authorization": f"Bearer {token}"})
    ids = {d["id"] for d in resp.json()}
    assert "doc-dept" not in ids  # dept_permission=dept-rrhh


def test_rrhh_ve_todos_los_documentos(client, seed_data, db_session):
    _add_docs(db_session, "comp-test")
    token = get_token(client, "andrea@test.co", "test123")
    resp = client.get("/api/documents/", headers={"Authorization": f"Bearer {token}"})
    ids = {d["id"] for d in resp.json()}
    assert "doc-pub" in ids
    assert "doc-rrhh" in ids
    # RR.HH. no ve doc de gerencia (require_gerencia=True)
    assert "doc-ger" not in ids


def test_delete_documento_borra_sus_chunks(client, seed_data, db_session):
    db_session.add(Document(id="doc-del", company_id="comp-test", name="Borrable",
                            status="indexado", uploaded_by="user-rrhh"))
    db_session.add(DocumentChunk(document_id="doc-del", company_id="comp-test",
                                 content="fragmento", chunk_index=0))
    db_session.commit()

    token = get_token(client, "andrea@test.co", "test123")
    resp = client.delete("/api/documents/doc-del", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, resp.text
    assert db_session.query(DocumentChunk).filter_by(document_id="doc-del").count() == 0
    assert db_session.query(Document).filter_by(id="doc-del").count() == 0


def test_retry_reinicia_estado_y_acepta(client, seed_data, db_session):
    db_session.add(Document(
        id="doc-retry", company_id="comp-test", name="guia.txt", format="txt",
        status="error", error_message="fallo transitorio", uploaded_by="user-rrhh",
        file_data=b"Contenido de prueba con texto suficiente para poder indexarlo.",
    ))
    db_session.commit()

    token = get_token(client, "andrea@test.co", "test123")
    resp = client.post("/api/documents/doc-retry/retry",
                       headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, resp.text
    doc = db_session.query(Document).filter_by(id="doc-retry").first()
    assert doc.status == "en_cola"
    assert doc.error_message is None


def test_retry_sin_archivo_guardado_da_400(client, seed_data, db_session):
    db_session.add(Document(id="doc-nofile", company_id="comp-test", name="x", status="error",
                            uploaded_by="user-rrhh"))
    db_session.commit()
    token = get_token(client, "andrea@test.co", "test123")
    resp = client.post("/api/documents/doc-nofile/retry",
                       headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 400


def test_retry_solo_rrhh(client, seed_data):
    token = get_token(client, "carlos@test.co", "test123")
    resp = client.post("/api/documents/x/retry", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


def test_download_respeta_el_rbac(client, seed_data, db_session):
    db_session.add(Document(id="dl-pub", company_id="comp-test", name="publico.txt", format="txt",
                            status="indexado", uploaded_by="user-rrhh", file_data=b"contenido publico"))
    db_session.add(Document(id="dl-rrhh", company_id="comp-test", name="rrhh.txt", format="txt",
                            status="indexado", uploaded_by="user-rrhh", require_rrhh=True,
                            file_data=b"solo rrhh"))
    db_session.commit()

    emp = get_token(client, "carlos@test.co", "test123")
    # El empleado descarga el documento público
    ok = client.get("/api/documents/dl-pub/download", headers={"Authorization": f"Bearer {emp}"})
    assert ok.status_code == 200 and ok.content == b"contenido publico"
    # Pero NO el confidencial de RR.HH.
    denied = client.get("/api/documents/dl-rrhh/download", headers={"Authorization": f"Bearer {emp}"})
    assert denied.status_code == 403
    # RR.HH. sí puede el suyo
    rrhh = get_token(client, "andrea@test.co", "test123")
    ok2 = client.get("/api/documents/dl-rrhh/download", headers={"Authorization": f"Bearer {rrhh}"})
    assert ok2.status_code == 200 and ok2.content == b"solo rrhh"


def test_upload_documento_solo_rrhh(client, seed_data):
    token_emp = get_token(client, "carlos@test.co", "test123")
    resp = client.post(
        "/api/documents/upload",
        files={"file": ("test.txt", b"Contenido de prueba", "text/plain")},
        headers={"Authorization": f"Bearer {token_emp}"},
    )
    assert resp.status_code == 403
