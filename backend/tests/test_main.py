from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_pagina_chat_se_incarca():
    raspuns = client.get("/")

    assert raspuns.status_code == 200
    assert "text/html" in raspuns.headers["content-type"]


def test_health_confirma_modelul():
    raspuns = client.get("/api/health")

    assert raspuns.status_code == 200
    corp = raspuns.json()
    assert corp["status"] == "ok"
    assert corp["model_raspunde"] is True


def test_trimite_mesaj_primeste_raspuns_de_la_maestra():
    raspuns = client.post("/api/mesaje", json={"text": "Ce parere ai despre AB simulat pe poza?"})

    assert raspuns.status_code == 200
    corp = raspuns.json()
    assert corp["personaj"] == "Maestra"
    assert corp["text"].strip() != ""
