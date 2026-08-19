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


def _istoric_izolat(monkeypatch, tmp_path) -> str:
    """Un folder de date numai al testului si o conversatie proaspata in el."""
    monkeypatch.setattr(istoric, "DATE_DIR", tmp_path / "date")
    istoric.init_stocare()
    return client.post("/api/conversatii").json()["id"]


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


def _mesaj_nou_peste_runda(monkeypatch, conversatie):
    """Modelul e intrerupt de un mesaj de-al meu, picat exact intre doua bucati de replica."""
    cereri = []

    def raspunde(mesaj, nume_personaj, sistem=None, temperatura=None, context=None):
        cereri.append(nume_personaj)
        yield "început de replică"
        main.incepe_runda(conversatie, {**main.UTILIZATOR, "eu": True, "text": "de fapt, altceva"})
        yield " și restul replicii"

    monkeypatch.setattr(main, "trimite_mesaj_stream", raspunde)
    return cereri


def _evenimente(text: str, conversatie: str) -> list[dict]:
    with client.stream(
        "POST", f"/api/conversatii/{conversatie}/mesaje", json={"text": text}
    ) as raspuns:
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
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    _model_fals(monkeypatch)

    evenimente = _evenimente("Cum arătăm prețurile?", conversatie)

    assert _vorbitori(evenimente) == list(main.PERSONAJE)
    assert sum(1 for e in evenimente if e["tip"] == "gata") == 5


def test_mentionatul_raspunde_iar_cine_n_are_ce_zice_tace(monkeypatch, tmp_path):
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)
    _toti_tac(monkeypatch, in_afara_de="Operatoarea")

    evenimente = _evenimente("@Operatoarea câte grame ies dintr-un tub?", conversatie)

    assert _vorbitori(evenimente) == ["operatoarea"]


def test_toti_sunt_intrebati_chiar_daca_doar_unul_vorbeste(monkeypatch, tmp_path):
    """Tacerea costa un apel la model - nu se poate sti ca cineva n-are nimic fara sa-l intrebi."""
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)
    cereri = _toti_tac(monkeypatch, in_afara_de="Operatoarea")

    _evenimente("@Operatoarea câte grame ies dintr-un tub?", conversatie)

    assert len(cereri) == len(main.PERSONAJE)
    assert cereri[0]["nume"] == "Operatoarea"  # cel chemat e primul intrebat


def test_cine_tace_nu_lasa_urma_in_istoric(monkeypatch, tmp_path):
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)
    _toti_tac(monkeypatch, in_afara_de="Operatoarea")

    _evenimente("@Operatoarea câte grame ies dintr-un tub?", conversatie)
    istoricul = client.get(f"/api/conversatii/{conversatie}/mesaje").json()

    assert [m.get("personajId") for m in istoricul] == [None, "operatoarea"]


def test_pagina_afla_ca_personajul_a_tacut(monkeypatch, tmp_path):
    """Bula de "scrie..." e deja pe ecran cand se afla; trebuie stearsa cumva."""
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)
    _toti_tac(monkeypatch, in_afara_de="Operatoarea")

    evenimente = _evenimente("@Operatoarea câte grame ies dintr-un tub?", conversatie)

    assert sum(1 for e in evenimente if e["tip"] == "tace") == len(main.PERSONAJE) - 1
    assert sum(1 for e in evenimente if e["tip"] == "gata") == 1


def test_pagina_afla_cand_nu_vorbeste_nimeni(monkeypatch, tmp_path):
    """Un mesaj la care n-are nimeni ce raspunde („Mulțumesc, notat.") nu are voie sa lase
    ecranul neschimbat: asa nu se distinge de un server picat."""
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)
    _toti_tac(monkeypatch)

    evenimente = _evenimente("Mulțumesc, notat.", conversatie)

    assert evenimente[-1] == {"tip": "consiliul_tace"}


def test_daca_a_vorbit_macar_unul_nu_se_anunta_tacere(monkeypatch, tmp_path):
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)
    _toti_tac(monkeypatch, in_afara_de="Operatoarea")

    evenimente = _evenimente("@Operatoarea câte grame ies dintr-un tub?", conversatie)

    assert not [e for e in evenimente if e["tip"] == "consiliul_tace"]


def test_mentionatul_nu_are_voie_sa_taca(monkeypatch, tmp_path):
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)
    cereri = _model_fals(monkeypatch)

    _evenimente("@Operatoarea câte grame ies dintr-un tub?", conversatie)

    chemata = next(c for c in cereri if c["nume"] == "Operatoarea")
    libera = next(c for c in cereri if c["nume"] == "Maestra")
    assert main.INDEMN_OBLIGAT in chemata["sistem"]
    assert main.INDEMN_OBLIGAT not in libera["sistem"]


def test_tacutul_care_castiga_aruncarea_e_obligat_si_el(monkeypatch, tmp_path):
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch, 0.0, 1.0, 1.0, 1.0)  # castiga primul tacut din personaje.json
    cereri = _model_fals(monkeypatch)

    _evenimente("@Operatoarea câte grame ies dintr-un tub?", conversatie)

    norocoasa = next(c for c in cereri if c["nume"] == "Antreprenoarea")
    assert main.INDEMN_OBLIGAT in norocoasa["sistem"]


def test_mai_multe_mentiuni_raspund_in_ordinea_scrierii(monkeypatch, tmp_path):
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)
    _model_fals(monkeypatch, {"Antreprenoarea": "PAS", "Operatoarea": "PAS", "Programatorul": "PAS"})

    evenimente = _evenimente("@Clienta și @Maestra, ce ziceți?", conversatie)

    assert _vorbitori(evenimente) == ["clienta", "maestra"]


def test_fiecare_raspunde_ultimei_replici_din_chat(monkeypatch, tmp_path):
    """Al doilea vorbitor reactioneaza la primul, nu la mesajul meu - asa curge o discutie."""
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)
    cereri = _model_fals(monkeypatch)

    _evenimente("@Clienta și @Maestra, ce ziceți?", conversatie)

    assert cereri[0]["mesaj"] == "@Clienta și @Maestra, ce ziceți?"
    assert cereri[1]["mesaj"] == "Clienta: replica Clienta"


def test_personajele_aud_ce_s_a_zis_inainte_in_aceeasi_runda(monkeypatch, tmp_path):
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)
    cereri = _model_fals(monkeypatch)

    _evenimente("@Clienta și @Maestra, ce ziceți?", conversatie)

    # Maestra e a doua intrebata: replica Clientei ii vine ca intrebare curenta...
    assert cereri[1]["mesaj"] == "Clienta: replica Clienta"
    # ...iar pentru a treia, replica Clientei a coborat deja in context.
    assert cereri[2]["context"][-1] == {"role": "user", "content": "Clienta: replica Clienta"}
    assert cereri[2]["mesaj"] == "Maestra: replica Maestra"


def test_evenimentul_de_personaj_poarta_identitatea_lui(monkeypatch, tmp_path):
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)
    _model_fals(monkeypatch)

    evenimente = _evenimente("@Maestra ce zici de AB?", conversatie)
    identitate = next(e for e in evenimente if e["tip"] == "personaj")

    assert identitate["nume"] == "Maestra"
    assert identitate["avatar"] and identitate["culoare"] and identitate["culoareFundal"]


def test_runda_se_salveaza_cu_id_de_personaj(monkeypatch, tmp_path):
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)
    _model_fals(monkeypatch)

    _evenimente("@Maestra ce zici de AB?", conversatie)
    istoricul = client.get(f"/api/conversatii/{conversatie}/mesaje").json()

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
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)
    cereri = _toti_tac(monkeypatch, in_afara_de="Maestra")

    _evenimente("@Maestra prima întrebare", conversatie)
    _evenimente("@Maestra a doua întrebare", conversatie)

    ultima = [c for c in cereri if c["nume"] == "Maestra"][-1]
    assert ultima["context"] == [
        {"role": "user", "content": "@Maestra prima întrebare"},
        {"role": "assistant", "content": "replica Maestra"},
    ]


def test_personajele_aud_replicile_celorlalti_intre_runde(monkeypatch, tmp_path):
    """Punctul 4 din definitia de "gata": un personaj comenteaza ce a zis alt personaj."""
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)
    cereri = _model_fals(monkeypatch)

    _evenimente("Prima rundă, toată lumea", conversatie)
    _evenimente("@Maestra și acum?", conversatie)

    ultima = [c for c in cereri if c["nume"] == "Maestra"][-1]
    straini = [m["content"] for m in ultima["context"] if m["content"].startswith("Clienta:")]
    assert straini == ["Clienta: replica Clienta"]


def test_personajul_chemat_de_altul_raspunde_imediat_si_obligatoriu(monkeypatch, tmp_path):
    """@ scris de un personaj cheama la fel ca @ scris de mine."""
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)
    cereri = _model_fals(
        monkeypatch,
        {"Maestra": "aici o întreb pe @Operatoarea", "Antreprenoarea": "PAS", "Clienta": "PAS"},
    )

    evenimente = _evenimente("@Maestra ce zici de AB?", conversatie)

    assert _vorbitori(evenimente)[:2] == ["maestra", "operatoarea"]
    chemata = next(c for c in cereri if c["nume"] == "Operatoarea")
    assert main.INDEMN_OBLIGAT in chemata["sistem"]
    assert chemata["mesaj"] == "Maestra: aici o întreb pe @Operatoarea"


def test_cine_a_vorbit_deja_nu_e_chemat_inapoi_in_aceeasi_runda(monkeypatch, tmp_path):
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)
    _model_fals(monkeypatch, {"Maestra": "de acord cu @Clienta și @Maestra"})

    evenimente = _evenimente("@Clienta și @Maestra, ce ziceți?", conversatie)

    vorbitori = _vorbitori(evenimente)
    assert len(vorbitori) == len(set(vorbitori))


def test_eroarea_unui_personaj_nu_opreste_runda(monkeypatch, tmp_path):
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)

    tac = {"Antreprenoarea": "PAS", "Operatoarea": "PAS", "Programatorul": "PAS"}

    def raspunde(mesaj, nume_personaj, sistem=None, temperatura=None, context=None):
        if nume_personaj == "Clienta":
            raise RuntimeError("Ollama oprit")
        yield tac.get(nume_personaj, f"replica {nume_personaj}")

    monkeypatch.setattr(main, "trimite_mesaj_stream", raspunde)

    evenimente = _evenimente("@Clienta și @Maestra, ce ziceți?", conversatie)

    assert [e["tip"] for e in evenimente if e["tip"] in ("eroare", "gata")] == ["eroare", "gata"]
    assert _intrebati(evenimente)[:2] == ["clienta", "maestra"]  # amandoua au fost intrebate
    assert _vorbitori(evenimente) == ["maestra"]  # runda a mers mai departe peste eroare


@pytest.mark.ollama
def test_raspunsul_real_al_modelului_ajunge_bucata_cu_bucata(monkeypatch, tmp_path):
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)

    evenimente = _evenimente("@Maestra ce părere ai despre AB simulat pe poză?", conversatie)
    bucati = [e["text"] for e in evenimente if e["tip"] == "text"]

    assert _vorbitori(evenimente)[0] == "maestra"
    assert len(bucati) > 1
    assert "".join(bucati).strip() != ""


def test_istoric_gol_la_start(monkeypatch, tmp_path):
    conversatie = _istoric_izolat(monkeypatch, tmp_path)

    raspuns = client.get(f"/api/conversatii/{conversatie}/mesaje")

    assert raspuns.status_code == 200
    assert raspuns.json() == []


def test_istoric_intoarce_mesajele_salvate_in_ordine(monkeypatch, tmp_path):
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    mesaj1 = {"eu": True, "nume": "Simona", "avatar": "🙋", "culoare": "#3D3A36", "text": "Salut"}
    mesaj2 = {"eu": False, "personajId": "maestra", "nume": "Maestra", "text": "Bună"}
    istoric.salveaza_mesaj(conversatie, mesaj1)
    istoric.salveaza_mesaj(conversatie, mesaj2)

    raspuns = client.get(f"/api/conversatii/{conversatie}/mesaje")

    assert raspuns.status_code == 200
    assert raspuns.json() == [mesaj1, mesaj2]


def test_mesajul_meu_nou_opreste_runda_in_curs(monkeypatch, tmp_path):
    """M9: nu astept sa termine consiliul ca sa fiu ascultata - runda veche se taie pe loc."""
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)
    _mesaj_nou_peste_runda(monkeypatch, conversatie)

    evenimente = _evenimente("@Maestra ce zici de AB?", conversatie)

    assert [e["tip"] for e in evenimente] == ["personaj", "text"]


def test_runda_anulata_nu_mai_intreaba_personajele_urmatoare(monkeypatch, tmp_path):
    """Altfel s-ar arde tokeni pentru o runda pe care n-o mai vede nimeni."""
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)
    cereri = _mesaj_nou_peste_runda(monkeypatch, conversatie)

    _evenimente("@Maestra ce zici de AB?", conversatie)

    assert cereri == ["Maestra"]


def test_replica_ramasa_pe_jumatate_nu_ajunge_in_istoric(monkeypatch, tmp_path):
    """Ce s-a sters de pe ecran nu are voie sa reapara la refresh."""
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)
    _mesaj_nou_peste_runda(monkeypatch, conversatie)

    _evenimente("@Maestra ce zici de AB?", conversatie)
    istoricul = client.get(f"/api/conversatii/{conversatie}/mesaje").json()

    assert [m["text"] for m in istoricul] == ["@Maestra ce zici de AB?", "de fapt, altceva"]


def test_runda_se_opreste_cand_pagina_nu_mai_asculta(monkeypatch, tmp_path):
    """Un tab inchis n-are voie sa lase modelul sa scrie mai departe."""
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    numar = main.incepe_runda(conversatie, {**main.UTILIZATOR, "eu": True, "text": "o întrebare"})

    assert asyncio.run(main.trebuie_oprita(numar, _Pagina(inchisa=True))) is True


def test_runda_curenta_merge_mai_departe_cat_timp_pagina_asculta(monkeypatch, tmp_path):
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    numar = main.incepe_runda(conversatie, {**main.UTILIZATOR, "eu": True, "text": "o întrebare"})

    assert asyncio.run(main.trebuie_oprita(numar, _Pagina(inchisa=False))) is False


# ---------- conversatii multiple ----------


def test_lista_de_conversatii_are_mereu_macar_una(monkeypatch, tmp_path):
    """Deschid aplicatia si am unde scrie, chiar daca n-am facut inca nicio conversatie."""
    _istoric_izolat(monkeypatch, tmp_path)

    conversatii = client.get("/api/conversatii").json()

    assert len(conversatii) >= 1
    assert all("titlu" in c and "numarMesaje" in c for c in conversatii)


def test_conversatia_noua_apare_in_lista_si_e_goala(monkeypatch, tmp_path):
    _istoric_izolat(monkeypatch, tmp_path)

    noua = client.post("/api/conversatii").json()

    assert noua["id"] in [c["id"] for c in client.get("/api/conversatii").json()]
    assert client.get(f"/api/conversatii/{noua['id']}/mesaje").json() == []


def test_titlul_se_scrie_singur_din_primul_meu_mesaj(monkeypatch, tmp_path):
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)
    _toti_tac(monkeypatch, in_afara_de="Maestra")

    _evenimente("@Maestra ce zici de AB?", conversatie)

    listata = next(c for c in client.get("/api/conversatii").json() if c["id"] == conversatie)
    assert listata["titlu"] == "@Maestra ce zici de AB?"


def test_pot_redenumi_o_conversatie(monkeypatch, tmp_path):
    conversatie = _istoric_izolat(monkeypatch, tmp_path)

    raspuns = client.patch(f"/api/conversatii/{conversatie}", json={"titlu": "AB pe poză"})

    assert raspuns.status_code == 200
    assert "mesaje" not in raspuns.json()  # raspunsul e un rand de lista, nu toata arhiva
    listata = next(c for c in client.get("/api/conversatii").json() if c["id"] == conversatie)
    assert listata["titlu"] == "AB pe poză"


def test_conversatia_stearsa_dispare_cu_tot_cu_istoricul_ei(monkeypatch, tmp_path):
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)
    _toti_tac(monkeypatch, in_afara_de="Maestra")
    _evenimente("@Maestra ce zici de AB?", conversatie)

    client.delete(f"/api/conversatii/{conversatie}")

    assert conversatie not in [c["id"] for c in client.get("/api/conversatii").json()]
    assert client.get(f"/api/conversatii/{conversatie}/mesaje").status_code == 404


def test_dupa_ce_sterg_tot_ramane_o_conversatie_goala(monkeypatch, tmp_path):
    """Nu raman cu ecranul fara niciun loc in care sa scriu."""
    _istoric_izolat(monkeypatch, tmp_path)

    for conversatie in client.get("/api/conversatii").json():
        raspuns = client.delete(f"/api/conversatii/{conversatie['id']}")

    assert len(raspuns.json()) == 1
    assert raspuns.json()[0]["numarMesaje"] == 0


def test_personajele_dintr_o_conversatie_nu_vad_nimic_din_alta(monkeypatch, tmp_path):
    """Fiecare conversatie e o sedinta separata: ce s-a zis in prima nu ajunge in a doua."""
    prima = _istoric_izolat(monkeypatch, tmp_path)
    a_doua = client.post("/api/conversatii").json()["id"]
    _zaruri(monkeypatch)
    cereri = _model_fals(monkeypatch)

    _evenimente("Secretul din prima conversație", prima)
    _evenimente("@Maestra ce zici de AB?", a_doua)

    ultima = [c for c in cereri if c["nume"] == "Maestra"][-1]
    assert ultima["context"] == []
    assert ultima["mesaj"] == "@Maestra ce zici de AB?"


def test_mesajul_meu_intra_doar_in_conversatia_in_care_l_am_scris(monkeypatch, tmp_path):
    prima = _istoric_izolat(monkeypatch, tmp_path)
    a_doua = client.post("/api/conversatii").json()["id"]
    _zaruri(monkeypatch)
    _toti_tac(monkeypatch)

    _evenimente("Doar aici", prima)

    assert client.get(f"/api/conversatii/{a_doua}/mesaje").json() == []


def test_o_conversatie_care_nu_exista_da_404(monkeypatch, tmp_path):
    _istoric_izolat(monkeypatch, tmp_path)

    assert client.get("/api/conversatii/nascocita/mesaje").status_code == 404
    assert client.patch("/api/conversatii/nascocita", json={"titlu": "x"}).status_code == 404
    with client.stream(
        "POST", "/api/conversatii/nascocita/mesaje", json={"text": "salut"}
    ) as raspuns:
        assert raspuns.status_code == 404
