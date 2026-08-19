import asyncio
import json
import threading

import pytest
from fastapi.testclient import TestClient

import istoric
import main
from main import app

client = TestClient(app)


class _Pagina:
    """Conexiunea cu pagina, vazuta de server: deschisa sau inchisa de utilizatoare."""

    def __init__(self, inchisa: bool):
        self.inchisa = inchisa

    async def is_disconnected(self) -> bool:
        return self.inchisa


def _istoric_izolat(monkeypatch, tmp_path):
    monkeypatch.setattr(istoric, "ISTORIC_PATH", tmp_path / "conversatie.json")
    istoric.init_stocare()


def _zaruri(monkeypatch, *valori: float):
    """Fixeaza aruncarile pentru tacuti: 1.0 nu intra nimeni, 0.0 intra primul de pe lista.

    Dupa valorile date, restul aruncarilor pica pe 1.0 - deci fara alte intrari nedorite.
    """
    ramase = list(valori)
    monkeypatch.setattr(main, "zaruri", lambda: ramase.pop(0) if ramase else 1.0)


def _model_fals(monkeypatch, replici: dict | None = None):
    """Inlocuieste modelul. `replici` da textul pentru anumite personaje (ex. PAS)."""
    cereri = []

    def raspunde(mesaj, nume_personaj, sistem=None, temperatura=None, context=None):
        cereri.append(
            {"mesaj": mesaj, "nume": nume_personaj, "sistem": sistem, "context": context}
        )
        yield (replici or {}).get(nume_personaj, f"replica {nume_personaj}")

    monkeypatch.setattr(main, "trimite_mesaj_stream", raspunde)
    return cereri


def _toti_tac(monkeypatch, in_afara_de: str = ""):
    """Toti scriu PAS, mai putin cine e numit - cazul obisnuit intr-un chat linistit."""
    nume = [p["nume"] for p in main.PERSONAJE.values()]
    return _model_fals(monkeypatch, {n: "PAS" for n in nume if n != in_afara_de})


def _mesaj_nou_peste_runda(monkeypatch):
    """Modelul e intrerupt de un mesaj de-al meu, picat exact intre doua bucati de replica."""
    cereri = []

    def raspunde(mesaj, nume_personaj, sistem=None, temperatura=None, context=None):
        cereri.append(nume_personaj)
        yield "început de replică"
        main.incepe_runda({**main.UTILIZATOR, "eu": True, "text": "de fapt, altceva"})
        yield " și restul replicii"

    monkeypatch.setattr(main, "trimite_mesaj_stream", raspunde)
    return cereri


def _evenimente(text: str) -> list[dict]:
    with client.stream("POST", "/api/mesaje", json={"text": text}) as raspuns:
        assert raspuns.status_code == 200
        return [json.loads(linie) for linie in raspuns.iter_lines() if linie.strip()]


def _vorbitori(evenimente: list[dict]) -> list[str]:
    """Doar cine a si spus ceva: bula apare pentru toti, dar cine tace o pierde imediat."""
    vorbitori, curent = [], None
    for eveniment in evenimente:
        if eveniment["tip"] == "personaj":
            curent = eveniment["id"]
        elif eveniment["tip"] == "gata" and curent:
            vorbitori.append(curent)
    return vorbitori


def _intrebati(evenimente: list[dict]) -> list[str]:
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


@pytest.mark.ollama
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


def test_mentionatul_raspunde_iar_cine_n_are_ce_zice_tace(monkeypatch, tmp_path):
    _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)
    _toti_tac(monkeypatch, in_afara_de="Operatoarea")

    evenimente = _evenimente("@Operatoarea câte grame ies dintr-un tub?")

    assert _vorbitori(evenimente) == ["operatoarea"]


def test_toti_sunt_intrebati_chiar_daca_doar_unul_vorbeste(monkeypatch, tmp_path):
    """Tacerea costa un apel la model - nu se poate sti ca cineva n-are nimic fara sa-l intrebi."""
    _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)
    cereri = _toti_tac(monkeypatch, in_afara_de="Operatoarea")

    _evenimente("@Operatoarea câte grame ies dintr-un tub?")

    assert len(cereri) == len(main.PERSONAJE)
    assert cereri[0]["nume"] == "Operatoarea"  # cel chemat e primul intrebat


def test_cine_tace_nu_lasa_urma_in_istoric(monkeypatch, tmp_path):
    _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)
    _toti_tac(monkeypatch, in_afara_de="Operatoarea")

    _evenimente("@Operatoarea câte grame ies dintr-un tub?")
    istoricul = client.get("/api/mesaje").json()

    assert [m.get("personajId") for m in istoricul] == [None, "operatoarea"]


def test_pagina_afla_ca_personajul_a_tacut(monkeypatch, tmp_path):
    """Bula de "scrie..." e deja pe ecran cand se afla; trebuie stearsa cumva."""
    _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)
    _toti_tac(monkeypatch, in_afara_de="Operatoarea")

    evenimente = _evenimente("@Operatoarea câte grame ies dintr-un tub?")

    assert sum(1 for e in evenimente if e["tip"] == "tace") == len(main.PERSONAJE) - 1
    assert sum(1 for e in evenimente if e["tip"] == "gata") == 1


def test_pagina_afla_cand_nu_vorbeste_nimeni(monkeypatch, tmp_path):
    """Un mesaj la care n-are nimeni ce raspunde („Mulțumesc, notat.") nu are voie sa lase
    ecranul neschimbat: asa nu se distinge de un server picat."""
    _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)
    _toti_tac(monkeypatch)

    evenimente = _evenimente("Mulțumesc, notat.")

    assert evenimente[-1] == {"tip": "consiliul_tace"}


def test_daca_a_vorbit_macar_unul_nu_se_anunta_tacere(monkeypatch, tmp_path):
    _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)
    _toti_tac(monkeypatch, in_afara_de="Operatoarea")

    evenimente = _evenimente("@Operatoarea câte grame ies dintr-un tub?")

    assert not [e for e in evenimente if e["tip"] == "consiliul_tace"]


def test_mentionatul_nu_are_voie_sa_taca(monkeypatch, tmp_path):
    _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)
    cereri = _model_fals(monkeypatch)

    _evenimente("@Operatoarea câte grame ies dintr-un tub?")

    chemata = next(c for c in cereri if c["nume"] == "Operatoarea")
    libera = next(c for c in cereri if c["nume"] == "Maestra")
    assert main.INDEMN_OBLIGAT in chemata["sistem"]
    assert main.INDEMN_OBLIGAT not in libera["sistem"]


def test_tacutul_care_castiga_aruncarea_e_obligat_si_el(monkeypatch, tmp_path):
    _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch, 0.0, 1.0, 1.0, 1.0)  # castiga primul tacut din personaje.json
    cereri = _model_fals(monkeypatch)

    _evenimente("@Operatoarea câte grame ies dintr-un tub?")

    norocoasa = next(c for c in cereri if c["nume"] == "Antreprenoarea")
    assert main.INDEMN_OBLIGAT in norocoasa["sistem"]


def test_mai_multe_mentiuni_raspund_in_ordinea_scrierii(monkeypatch, tmp_path):
    _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)
    _model_fals(monkeypatch, {"Antreprenoarea": "PAS", "Operatoarea": "PAS", "Programatorul": "PAS"})

    evenimente = _evenimente("@Clienta și @Maestra, ce ziceți?")

    assert _vorbitori(evenimente) == ["clienta", "maestra"]


def test_fiecare_raspunde_ultimei_replici_din_chat(monkeypatch, tmp_path):
    """Al doilea vorbitor reactioneaza la primul, nu la mesajul meu - asa curge o discutie."""
    _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)
    cereri = _model_fals(monkeypatch)

    _evenimente("@Clienta și @Maestra, ce ziceți?")

    assert cereri[0]["mesaj"] == "@Clienta și @Maestra, ce ziceți?"
    assert cereri[1]["mesaj"] == "Clienta: replica Clienta"


def test_personajele_aud_ce_s_a_zis_inainte_in_aceeasi_runda(monkeypatch, tmp_path):
    _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)
    cereri = _model_fals(monkeypatch)

    _evenimente("@Clienta și @Maestra, ce ziceți?")

    # Maestra e a doua intrebata: replica Clientei ii vine ca intrebare curenta...
    assert cereri[1]["mesaj"] == "Clienta: replica Clienta"
    # ...iar pentru a treia, replica Clientei a coborat deja in context.
    assert cereri[2]["context"][-1] == {"role": "user", "content": "Clienta: replica Clienta"}
    assert cereri[2]["mesaj"] == "Maestra: replica Maestra"


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
    cereri = _toti_tac(monkeypatch, in_afara_de="Maestra")

    _evenimente("@Maestra prima întrebare")
    _evenimente("@Maestra a doua întrebare")

    ultima = [c for c in cereri if c["nume"] == "Maestra"][-1]
    assert ultima["context"] == [
        {"role": "user", "content": "@Maestra prima întrebare"},
        {"role": "assistant", "content": "replica Maestra"},
    ]


def test_personajele_aud_replicile_celorlalti_intre_runde(monkeypatch, tmp_path):
    """Punctul 4 din definitia de "gata": un personaj comenteaza ce a zis alt personaj."""
    _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)
    cereri = _model_fals(monkeypatch)

    _evenimente("Prima rundă, toată lumea")
    _evenimente("@Maestra și acum?")

    ultima = [c for c in cereri if c["nume"] == "Maestra"][-1]
    straini = [m["content"] for m in ultima["context"] if m["content"].startswith("Clienta:")]
    assert straini == ["Clienta: replica Clienta"]


def test_personajul_chemat_de_altul_raspunde_imediat_si_obligatoriu(monkeypatch, tmp_path):
    """@ scris de un personaj cheama la fel ca @ scris de mine."""
    _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)
    cereri = _model_fals(
        monkeypatch,
        {"Maestra": "aici o întreb pe @Operatoarea", "Antreprenoarea": "PAS", "Clienta": "PAS"},
    )

    evenimente = _evenimente("@Maestra ce zici de AB?")

    assert _vorbitori(evenimente)[:2] == ["maestra", "operatoarea"]
    chemata = next(c for c in cereri if c["nume"] == "Operatoarea")
    assert main.INDEMN_OBLIGAT in chemata["sistem"]
    assert chemata["mesaj"] == "Maestra: aici o întreb pe @Operatoarea"


def test_cine_a_vorbit_deja_nu_e_chemat_inapoi_in_aceeasi_runda(monkeypatch, tmp_path):
    _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)
    _model_fals(monkeypatch, {"Maestra": "de acord cu @Clienta și @Maestra"})

    evenimente = _evenimente("@Clienta și @Maestra, ce ziceți?")

    vorbitori = _vorbitori(evenimente)
    assert len(vorbitori) == len(set(vorbitori))


def test_eroarea_unui_personaj_nu_opreste_runda(monkeypatch, tmp_path):
    _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)

    tac = {"Antreprenoarea": "PAS", "Operatoarea": "PAS", "Programatorul": "PAS"}

    def raspunde(mesaj, nume_personaj, sistem=None, temperatura=None, context=None):
        if nume_personaj == "Clienta":
            raise RuntimeError("Ollama oprit")
        yield tac.get(nume_personaj, f"replica {nume_personaj}")

    monkeypatch.setattr(main, "trimite_mesaj_stream", raspunde)

    evenimente = _evenimente("@Clienta și @Maestra, ce ziceți?")

    assert [e["tip"] for e in evenimente if e["tip"] in ("eroare", "gata")] == ["eroare", "gata"]
    assert _intrebati(evenimente)[:2] == ["clienta", "maestra"]  # amandoua au fost intrebate
    assert _vorbitori(evenimente) == ["maestra"]  # runda a mers mai departe peste eroare


@pytest.mark.ollama
def test_raspunsul_real_al_modelului_ajunge_bucata_cu_bucata(monkeypatch, tmp_path):
    _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)

    evenimente = _evenimente("@Maestra ce părere ai despre AB simulat pe poză?")
    bucati = [e["text"] for e in evenimente if e["tip"] == "text"]

    assert _vorbitori(evenimente)[0] == "maestra"
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


def test_mesajul_meu_nou_opreste_runda_in_curs(monkeypatch, tmp_path):
    """M9: nu astept sa termine consiliul ca sa fiu ascultata - runda veche se taie pe loc."""
    _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)
    _mesaj_nou_peste_runda(monkeypatch)

    evenimente = _evenimente("@Maestra ce zici de AB?")

    assert [e["tip"] for e in evenimente] == ["personaj", "text"]


def test_runda_anulata_nu_mai_intreaba_personajele_urmatoare(monkeypatch, tmp_path):
    """Altfel s-ar arde tokeni pentru o runda pe care n-o mai vede nimeni."""
    _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)
    cereri = _mesaj_nou_peste_runda(monkeypatch)

    _evenimente("@Maestra ce zici de AB?")

    assert cereri == ["Maestra"]


def test_replica_ramasa_pe_jumatate_nu_ajunge_in_istoric(monkeypatch, tmp_path):
    """Ce s-a sters de pe ecran nu are voie sa reapara la refresh."""
    _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)
    _mesaj_nou_peste_runda(monkeypatch)

    _evenimente("@Maestra ce zici de AB?")
    istoricul = client.get("/api/mesaje").json()

    assert [m["text"] for m in istoricul] == ["@Maestra ce zici de AB?", "de fapt, altceva"]


def test_runda_se_opreste_cand_pagina_nu_mai_asculta(monkeypatch, tmp_path):
    """Un tab inchis n-are voie sa lase modelul sa scrie mai departe."""
    _istoric_izolat(monkeypatch, tmp_path)
    numar = main.incepe_runda({**main.UTILIZATOR, "eu": True, "text": "o întrebare"})

    assert asyncio.run(main.trebuie_oprita(numar, _Pagina(inchisa=True))) is True


def test_runda_curenta_merge_mai_departe_cat_timp_pagina_asculta(monkeypatch, tmp_path):
    _istoric_izolat(monkeypatch, tmp_path)
    numar = main.incepe_runda({**main.UTILIZATOR, "eu": True, "text": "o întrebare"})

    assert asyncio.run(main.trebuie_oprita(numar, _Pagina(inchisa=False))) is False
