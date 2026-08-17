import json
import threading

from fastapi.testclient import TestClient

import istoric
import main
from main import app

client = TestClient(app)


def _istoric_izolat(monkeypatch, tmp_path):
    monkeypatch.setattr(istoric, "ISTORIC_PATH", tmp_path / "conversatie.json")
    istoric.init_stocare()


def _zaruri(monkeypatch, *valori: float):
    """Fixeaza aruncarile pentru tacuti: 1.0 nu intra nimeni, 0.0 intra primul de pe lista.

    Dupa valorile date, restul aruncarilor pica pe 1.0 - deci fara alte intrari nedorite.
    """
    ramase = list(valori)
    monkeypatch.setattr(main, "zaruri", lambda: ramase.pop(0) if ramase else 1.0)


def _model_fals(monkeypatch):
    """Inlocuieste modelul, ca testele de rutare sa nu astepte cinci generari reale."""
    cereri = []

    def raspunde(mesaj, nume_personaj, sistem=None, temperatura=None, context=None):
        cereri.append({"mesaj": mesaj, "nume": nume_personaj, "context": context})
        yield f"replica {nume_personaj}"

    monkeypatch.setattr(main, "trimite_mesaj_stream", raspunde)
    return cereri


def _evenimente(text: str) -> list[dict]:
    with client.stream("POST", "/api/mesaje", json={"text": text}) as raspuns:
        assert raspuns.status_code == 200
        return [json.loads(linie) for linie in raspuns.iter_lines() if linie.strip()]


def _vorbitori(evenimente: list[dict]) -> list[str]:
    return [e["id"] for e in evenimente if e["tip"] == "personaj"]


def test_pornirea_preincarca_modelul_in_fundal(monkeypatch):
    apelat = threading.Event()
    monkeypatch.setattr(main, "preincarca", apelat.set)

    with TestClient(app):
        assert apelat.wait(timeout=5)


def test_pornirea_nu_cade_daca_modelul_nu_raspunde(monkeypatch):
    def crapa():
        raise RuntimeError("Ollama oprit")

    monkeypatch.setattr(main, "preincarca", crapa)

    main.incalzeste_modelul()  # inghite eroarea, nu opreste serverul


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


def test_profilurile_ajung_in_pagina_fara_system_prompt():
    corp = client.get("/api/personaje").json()

    assert len(corp["personaje"]) == 5
    for profil in corp["personaje"]:
        assert set(profil) == {"id", "nume", "rol", "avatar", "culoare", "culoareFundal"}


def test_profilurile_includ_utilizatoarea():
    utilizator = client.get("/api/personaje").json()["utilizator"]

    assert utilizator["nume"] == "Simona"
    assert utilizator["avatar"] and utilizator["culoare"]


def test_fara_mentiune_raspunde_tot_consiliul(monkeypatch, tmp_path):
    _istoric_izolat(monkeypatch, tmp_path)
    _model_fals(monkeypatch)

    evenimente = _evenimente("Cum arătăm prețurile?")

    assert _vorbitori(evenimente) == list(main.PERSONAJE)
    assert sum(1 for e in evenimente if e["tip"] == "gata") == 5


def test_mentiunea_alege_cine_raspunde(monkeypatch, tmp_path):
    _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)
    _model_fals(monkeypatch)

    evenimente = _evenimente("@Operatoarea câte grame ies dintr-un tub?")

    assert _vorbitori(evenimente) == ["operatoarea"]


def test_mai_multe_mentiuni_raspund_in_ordinea_scrierii(monkeypatch, tmp_path):
    _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)
    _model_fals(monkeypatch)

    evenimente = _evenimente("@Clienta și @Maestra, ce ziceți?")

    assert _vorbitori(evenimente) == ["clienta", "maestra"]


def test_tacutul_caruia_i_iese_aruncarea_se_baga_dupa_cei_chemati(monkeypatch, tmp_path):
    _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch, 0.0, 1.0, 1.0, 1.0)  # castiga primul tacut din personaje.json
    _model_fals(monkeypatch)

    evenimente = _evenimente("@Operatoarea câte grame ies dintr-un tub?")

    assert _vorbitori(evenimente) == ["operatoarea", "antreprenoarea"]


def _model_care_cheama(monkeypatch, chemari: dict[str, str]):
    """Model fals in care unele personaje cheama pe altcineva cu @ in replica lor."""
    cereri = []

    def raspunde(mesaj, nume_personaj, sistem=None, temperatura=None, context=None):
        cereri.append({"mesaj": mesaj, "nume": nume_personaj})
        yield chemari.get(nume_personaj, f"replica {nume_personaj}")

    monkeypatch.setattr(main, "trimite_mesaj_stream", raspunde)
    return cereri


def test_personajul_chemat_de_altul_raspunde_in_aceeasi_runda(monkeypatch, tmp_path):
    _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)
    _model_care_cheama(monkeypatch, {"Maestra": "aici întreab-o pe @Clienta"})

    evenimente = _evenimente("@Maestra ce zici de AB?")

    assert _vorbitori(evenimente) == ["maestra", "clienta"]


def test_cel_chemat_raspunde_replicii_care_l_a_chemat(monkeypatch, tmp_path):
    _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)
    cereri = _model_care_cheama(monkeypatch, {"Maestra": "aici întreab-o pe @Clienta"})

    _evenimente("@Maestra ce zici de AB?")

    assert cereri[-1]["nume"] == "Clienta"
    assert cereri[-1]["mesaj"] == "Maestra: aici întreab-o pe @Clienta"


def test_lantul_de_chemari_se_opreste_dupa_un_val(monkeypatch, tmp_path):
    """Altfel doua personaje care se invoca reciproc tin runda la nesfarsit."""
    _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)
    _model_care_cheama(
        monkeypatch,
        {"Maestra": "hai @Clienta", "Clienta": "și @Operatoarea, și @Programatorul"},
    )

    evenimente = _evenimente("@Maestra ce zici de AB?")

    assert _vorbitori(evenimente) == ["maestra", "clienta"]


def test_nimeni_nu_vorbeste_de_doua_ori_in_aceeasi_runda(monkeypatch, tmp_path):
    _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)
    _model_care_cheama(monkeypatch, {"Maestra": "de acord cu @Clienta și @Maestra"})

    evenimente = _evenimente("@Maestra și @Clienta, ce ziceți?")

    assert _vorbitori(evenimente) == ["maestra", "clienta"]


def test_evenimentul_de_personaj_poarta_identitatea_lui(monkeypatch, tmp_path):
    _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)
    _model_fals(monkeypatch)

    evenimente = _evenimente("@Maestra ce zici de AB?")
    identitate = next(e for e in evenimente if e["tip"] == "personaj")

    assert identitate["nume"] == "Maestra"
    assert identitate["avatar"] and identitate["culoare"] and identitate["culoareFundal"]


def test_runda_se_salveaza_cu_id_de_personaj(monkeypatch, tmp_path):
    _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)
    _model_fals(monkeypatch)

    _evenimente("@Maestra ce zici de AB?")
    istoricul = client.get("/api/mesaje").json()

    assert istoricul[0]["eu"] is True and istoricul[0]["text"] == "@Maestra ce zici de AB?"
    assert istoricul[1] == {
        "eu": False,
        "personajId": "maestra",
        "nume": "Maestra",
        "avatar": main.PERSONAJE["maestra"]["avatar"],
        "culoare": main.PERSONAJE["maestra"]["culoare"],
        "culoareFundal": main.PERSONAJE["maestra"]["culoareFundal"],
        "text": "replica Maestra",
    }


def test_personajul_primeste_istoricul_conversatiei(monkeypatch, tmp_path):
    _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)
    cereri = _model_fals(monkeypatch)

    _evenimente("@Maestra prima întrebare")
    _evenimente("@Maestra a doua întrebare")

    assert cereri[-1]["context"] == [
        {"role": "user", "content": "@Maestra prima întrebare"},
        {"role": "assistant", "content": "replica Maestra"},
    ]


def test_personajele_nu_aud_replicile_celorlalti(monkeypatch, tmp_path):
    """Ramane pe etapa urmatoare, impreuna cu logica de tura."""
    _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)
    cereri = _model_fals(monkeypatch)

    _evenimente("Prima rundă, toată lumea")
    _evenimente("@Maestra și acum?")

    replici_straine = [
        mesaj
        for mesaj in cereri[-1]["context"]
        if mesaj["role"] == "assistant" and mesaj["content"] != "replica Maestra"
    ]
    assert replici_straine == []


def test_eroarea_unui_personaj_nu_opreste_runda(monkeypatch, tmp_path):
    _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)

    def raspunde(mesaj, nume_personaj, sistem=None, temperatura=None, context=None):
        if nume_personaj == "Clienta":
            raise RuntimeError("Ollama oprit")
        yield f"replica {nume_personaj}"

    monkeypatch.setattr(main, "trimite_mesaj_stream", raspunde)

    evenimente = _evenimente("@Clienta și @Maestra, ce ziceți?")

    assert [e["tip"] for e in evenimente if e["tip"] in ("eroare", "gata")] == ["eroare", "gata"]
    assert _vorbitori(evenimente) == ["clienta", "maestra"]


def test_raspunsul_real_al_modelului_ajunge_bucata_cu_bucata(monkeypatch, tmp_path):
    _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)

    evenimente = _evenimente("@Maestra ce părere ai despre AB simulat pe poză?")
    bucati = [e["text"] for e in evenimente if e["tip"] == "text"]

    assert _vorbitori(evenimente) == ["maestra"]
    assert len(bucati) > 1
    assert "".join(bucati).strip() != ""


def test_istoric_gol_la_start(monkeypatch, tmp_path):
    _istoric_izolat(monkeypatch, tmp_path)

    raspuns = client.get("/api/mesaje")

    assert raspuns.status_code == 200
    assert raspuns.json() == []


def test_istoric_intoarce_mesajele_salvate_in_ordine(monkeypatch, tmp_path):
    _istoric_izolat(monkeypatch, tmp_path)
    mesaj1 = {"eu": True, "nume": "Simona", "avatar": "🙋", "culoare": "#3D3A36", "text": "Salut"}
    mesaj2 = {"eu": False, "personajId": "maestra", "nume": "Maestra", "text": "Bună"}
    istoric.salveaza_mesaj(mesaj1)
    istoric.salveaza_mesaj(mesaj2)

    raspuns = client.get("/api/mesaje")

    assert raspuns.status_code == 200
    assert raspuns.json() == [mesaj1, mesaj2]
