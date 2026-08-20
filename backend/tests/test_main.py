import asyncio
import json
import threading

import pytest
from fastapi.testclient import TestClient

import istoric
import main
import personaje
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


def test_fara_mentiune_vorbesc_doar_cativa_nu_tot_consiliul(monkeypatch, tmp_path):
    """Pana la M15 raspundeau toate cinci si filtra PAS. La o intrebare larga n-avea ce filtra:
    subiectul le pica tuturor in domeniu, deci vorbeau 4-5, cu non-sequitur de la cei fara nimic
    de spus. Acum runda isi alege vorbitorii."""
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)
    _model_fals(monkeypatch)

    evenimente = _evenimente("Cum arătăm prețurile?", conversatie)

    minim, maxim = personaje.VORBITORI_PE_RUNDA
    assert minim <= len(_vorbitori(evenimente)) <= maxim < len(main.PERSONAJE)


def test_mentionatul_ia_cuvantul(monkeypatch, tmp_path):
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)
    _toti_tac(monkeypatch, in_afara_de="Operatoarea")

    evenimente = _evenimente("@Operatoarea câte grame ies dintr-un tub?", conversatie)

    assert _vorbitori(evenimente) == ["operatoarea"]


def test_nu_se_mai_intreaba_tot_consiliul_ca_sa_vorbeasca_unul(monkeypatch, tmp_path):
    """Pana la M15, o mentiune costa cinci apeluri la model: erau intrebati toti si tacea cine
    n-avea nimic. Acum e intrebat cine ia cuvantul, deci runda se si termina mai repede."""
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)  # 1.0: nu intra niciun nementionat peste cea chemata
    cereri = _toti_tac(monkeypatch, in_afara_de="Operatoarea")

    _evenimente("@Operatoarea câte grame ies dintr-un tub?", conversatie)

    assert [c["nume"] for c in cereri] == ["Operatoarea"]


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
    _toti_tac(monkeypatch, in_afara_de="Maestra")

    evenimente = _evenimente("Cum arătăm prețurile?", conversatie)

    intrebati = sum(1 for e in evenimente if e["tip"] == "personaj")
    assert sum(1 for e in evenimente if e["tip"] == "tace") == intrebati - 1
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

    assert [c["nume"] for c in cereri] == ["Operatoarea"]
    assert main.INDEMN_OBLIGAT in cereri[0]["sistem"]


def test_alesul_care_nu_e_chemat_pe_nume_poate_sa_taca(monkeypatch, tmp_path):
    """Fara mentiune, sortii obliga unul singur dintre cei alesi. Ceilalti pastreaza PAS - acolo
    ramane plasa de siguranta pentru intrebarea ingusta, pe care selectia n-are cum s-o judece."""
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)
    cereri = _model_fals(monkeypatch)

    _evenimente("Cum arătăm prețurile?", conversatie)

    obligati = [c for c in cereri if main.INDEMN_OBLIGAT in c["sistem"]]
    assert len(cereri) > 1
    assert len(obligati) == 1


def test_cel_intrat_pe_cei_douazeci_la_suta_e_intrebat_si_obligat(monkeypatch, tmp_path):
    """Pe el l-au adus sortii, nu subiectul, deci nu se mai intreaba daca are ceva de zis."""
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch, 0.0, 0.0)  # intra un nementionat, si e primul de pe lista
    cereri = _model_fals(monkeypatch)

    _evenimente("@Operatoarea câte grame ies dintr-un tub?", conversatie)

    assert [c["nume"] for c in cereri] == ["Operatoarea", "Antreprenoarea"]
    assert all(main.INDEMN_OBLIGAT in c["sistem"] for c in cereri)


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
    _zaruri(monkeypatch, 0.0, 1.0)  # intra si un al treilea, ultimul de pe lista
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

    _evenimente("@Clienta, tu ce zici?", conversatie)
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


# ---------- conversatia continua singura ----------


def _continuare(conversatie: str, runda: int) -> list[dict]:
    with client.stream(
        "POST", f"/api/conversatii/{conversatie}/continuare", json={"runda": runda}
    ) as raspuns:
        assert raspuns.status_code == 200
        return [json.loads(linie) for linie in raspuns.iter_lines() if linie.strip()]


def _ultimul_vorbitor(conversatie: str) -> str:
    return client.get(f"/api/conversatii/{conversatie}/mesaje").json()[-1]["personajId"]


def _cine_urmeaza(conversatie: str) -> dict:
    """Cine iese la aruncarea 0.0: primul din consiliu care nu tocmai a vorbit."""
    ultimul = _ultimul_vorbitor(conversatie)
    return next(p for p in main.PERSONAJE.values() if p["id"] != ultimul)


def _continua(evenimente: list[dict]) -> dict | None:
    return next((e for e in evenimente if e["tip"] == "continua"), None)


def _o_runda_si_o_continuare(monkeypatch, tmp_path, replici=None):
    """Runda mea, apoi numarul ei - de aici incolo conversatia poate merge singura."""
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)
    cereri = _model_fals(monkeypatch, replici)

    evenimente = _evenimente("Cum arătăm prețurile?", conversatie)

    return conversatie, _continua(evenimente)["runda"], cereri


def test_dupa_runda_mea_conversatia_mai_are_de_zis_intre_doua_si_patru_replici(
    monkeypatch, tmp_path
):
    """Nu la infinit: pe gemma4:e2b, dupa vreo 8-10 replici autonome discutia intra in bucla."""
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)
    _model_fals(monkeypatch)

    continua = _continua(_evenimente("Cum arătăm prețurile?", conversatie))

    minim, maxim = main.REPLICI_AUTONOME
    assert minim <= continua["replici"] <= maxim


def test_numarul_de_replici_autonome_e_tras_la_sorti_intre_plafoane():
    minim, maxim = main.REPLICI_AUTONOME

    assert main.cate_replici_autonome(sansa=lambda: 0.0) == minim
    assert main.cate_replici_autonome(sansa=lambda: 0.999) == maxim
    assert main.cate_replici_autonome(sansa=lambda: 1.0) == maxim  # un fals de test poate da 1.0


def test_pauza_dintre_replicile_autonome_o_da_serverul(monkeypatch, tmp_path):
    """Un singur loc unde se schimba intervalul: pagina nu-si alege singura secundele."""
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)
    _model_fals(monkeypatch)

    continua = _continua(_evenimente("Cum arătăm prețurile?", conversatie))

    assert continua["pauzaSecunde"] == list(main.PAUZA_SECUNDE)


def test_consiliul_care_a_tacut_nu_continua_singur(monkeypatch, tmp_path):
    """N-avea nimeni ce spune la mesajul meu; n-are rost sa se caute vorbitori mai departe."""
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)
    _toti_tac(monkeypatch)

    evenimente = _evenimente("Mulțumesc, notat.", conversatie)

    assert _continua(evenimente) is None


def test_runda_taiata_de_mesajul_meu_nu_promite_replici_autonome(monkeypatch, tmp_path):
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)
    _mesaj_nou_peste_runda(monkeypatch, conversatie)

    evenimente = _evenimente("@Maestra ce zici de AB?", conversatie)

    assert _continua(evenimente) is None


def test_la_o_replica_autonoma_vorbeste_un_singur_personaj(monkeypatch, tmp_path):
    conversatie, runda, _ = _o_runda_si_o_continuare(monkeypatch, tmp_path)
    _zaruri(monkeypatch, 0.0)

    evenimente = _continuare(conversatie, runda)

    assert len(_vorbitori(evenimente)) == 1


def test_cine_tocmai_a_vorbit_nu_incepe_si_replica_urmatoare(monkeypatch, tmp_path):
    conversatie, runda, _ = _o_runda_si_o_continuare(monkeypatch, tmp_path)
    ultimul = _ultimul_vorbitor(conversatie)
    _zaruri(monkeypatch, 0.0)

    evenimente = _continuare(conversatie, runda)

    assert ultimul not in _intrebati(evenimente)


def test_cel_chemat_si_neajuns_la_cuvant_are_intaietate_la_replica_autonoma(monkeypatch, tmp_path):
    """Regula 80/20 din sesiunea 11: aruncarea sub prag scoate cuvantul celui asteptat.

    Chemarea ramane in aer pentru ca Maestra o cheama pe Operatoarea dupa ce aceasta vorbise
    deja - nimeni nu vorbeste de doua ori in aceeasi runda.
    """
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)
    _model_fals(
        monkeypatch,
        {
            "Maestra": "nu știu, @Operatoarea ce zici?",
            "Antreprenoarea": "PAS",
            "Clienta": "PAS",
            "Programatorul": "PAS",
        },
    )
    runda = _continua(_evenimente("@Operatoarea și @Maestra, ce ziceți?", conversatie))["runda"]
    _zaruri(monkeypatch, 0.79, 0.0)

    evenimente = _continuare(conversatie, runda)

    assert _intrebati(evenimente)[0] == "operatoarea"


def test_daca_alesul_tace_replica_nu_se_pierde_ci_se_incearca_altcineva(monkeypatch, tmp_path):
    conversatie, runda, _ = _o_runda_si_o_continuare(monkeypatch, tmp_path)
    primul_ales = _cine_urmeaza(conversatie)
    _model_fals(monkeypatch, {primul_ales["nume"]: "PAS"})
    _zaruri(monkeypatch, 0.0, 0.0)

    evenimente = _continuare(conversatie, runda)

    assert _intrebati(evenimente)[0] == primul_ales["id"]
    assert [e["tip"] for e in evenimente if e["tip"] in ("tace", "gata")] == ["tace", "gata"]
    assert len(_vorbitori(evenimente)) == 1


def test_o_replica_autonoma_nu_intreaba_tot_consiliul_daca_toti_tac(monkeypatch, tmp_path):
    """Plafonul de incercari: altfel o discutie stinsa ar cere cinci apeluri la model pe replica."""
    conversatie, runda, _ = _o_runda_si_o_continuare(monkeypatch, tmp_path)
    _toti_tac(monkeypatch)
    _zaruri(monkeypatch, *([0.0] * 6))

    evenimente = _continuare(conversatie, runda)

    assert len(_intrebati(evenimente)) == main.INCERCARI_PE_REPLICA
    assert not _vorbitori(evenimente)


def test_personajul_care_vorbeste_de_la_sine_nu_e_obligat_sa_vorbeasca(monkeypatch, tmp_path):
    """Nimeni nu l-a chemat pe nume: are voie sa scrie PAS, ca in orice alta runda."""
    conversatie, runda, cereri = _o_runda_si_o_continuare(monkeypatch, tmp_path)
    _zaruri(monkeypatch, 0.0)

    _continuare(conversatie, runda)

    assert main.INDEMN_OBLIGAT not in cereri[-1]["sistem"]


def test_replica_autonoma_raspunde_ultimei_replici_din_chat(monkeypatch, tmp_path):
    conversatie, runda, cereri = _o_runda_si_o_continuare(monkeypatch, tmp_path)
    vorbitorul_dinainte = main.PERSONAJE[_ultimul_vorbitor(conversatie)]["nume"]
    _zaruri(monkeypatch, 0.0)

    _continuare(conversatie, runda)

    assert cereri[-1]["mesaj"] == f"{vorbitorul_dinainte}: replica {vorbitorul_dinainte}"


def test_replica_autonoma_ramane_in_istoricul_conversatiei(monkeypatch, tmp_path):
    conversatie, runda, _ = _o_runda_si_o_continuare(monkeypatch, tmp_path)
    _zaruri(monkeypatch, 0.0)

    evenimente = _continuare(conversatie, runda)
    istoricul = client.get(f"/api/conversatii/{conversatie}/mesaje").json()

    assert istoricul[-1]["personajId"] == _vorbitori(evenimente)[0]


def test_mesajul_meu_anuleaza_replicile_autonome_ramase(monkeypatch, tmp_path):
    """Am prioritate (M9): ce mai avea consiliul de zis singur nu se aduna peste runda mea noua."""
    conversatie, runda, _ = _o_runda_si_o_continuare(monkeypatch, tmp_path)
    _zaruri(monkeypatch)
    _evenimente("De fapt, altceva.", conversatie)
    inainte = client.get(f"/api/conversatii/{conversatie}/mesaje").json()
    _zaruri(monkeypatch, 0.0)

    evenimente = _continuare(conversatie, runda)

    assert evenimente == []
    assert client.get(f"/api/conversatii/{conversatie}/mesaje").json() == inainte


def test_o_conversatie_goala_n_are_ce_continua(monkeypatch, tmp_path):
    """Fara nicio replica in urma, n-ar avea nimeni la ce raspunde."""
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch, 0.0)

    assert _continuare(conversatie, main.numarul_rundei()) == []


def test_replicile_autonome_stau_in_conversatia_lor(monkeypatch, tmp_path):
    conversatie, runda, _ = _o_runda_si_o_continuare(monkeypatch, tmp_path)
    alta = client.post("/api/conversatii").json()["id"]
    _zaruri(monkeypatch, 0.0)

    _continuare(conversatie, runda)

    assert client.get(f"/api/conversatii/{alta}/mesaje").json() == []


def test_o_conversatie_care_nu_exista_nu_poate_fi_continuata(monkeypatch, tmp_path):
    _istoric_izolat(monkeypatch, tmp_path)

    with client.stream(
        "POST", "/api/conversatii/nascocita/continuare", json={"runda": 1}
    ) as raspuns:
        assert raspuns.status_code == 404


# ---------- memoria lunga: rezumatul sedintei ----------


def _secretar_fals(monkeypatch, text: str | None = "Subiect: prețurile"):
    """Rezumatul, fara model: `None` inseamna „n-a fost nimic de rezumat"."""
    apeluri = []

    def rezuma(id_conversatie):
        apeluri.append(id_conversatie)
        return text

    monkeypatch.setattr(main.rezumat, "actualizeaza_rezumat", rezuma)
    return apeluri


def test_pot_sa_vad_ce_tine_minte_consiliul(monkeypatch, tmp_path):
    """Scopul rezumatului e sa stiu ce s-a decis; daca nu-l pot citi, n-am de unde sti."""
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    istoric.salveaza_rezumat(conversatie, "Subiect: AB-ul\nDecizii: preview pe server", 6)

    raspuns = client.get(f"/api/conversatii/{conversatie}/rezumat").json()

    assert raspuns["rezumat"] == "Subiect: AB-ul\nDecizii: preview pe server"


def test_o_sedinta_scurta_n_are_inca_ce_tine_minte(monkeypatch, tmp_path):
    conversatie = _istoric_izolat(monkeypatch, tmp_path)

    assert client.get(f"/api/conversatii/{conversatie}/rezumat").json()["rezumat"] == ""


def test_rezumatul_unei_conversatii_care_nu_exista_da_404(monkeypatch, tmp_path):
    _istoric_izolat(monkeypatch, tmp_path)

    assert client.get("/api/conversatii/nascocita/rezumat").status_code == 404


def test_pagina_afla_la_capatul_rundei_ce_a_retinut_consiliul(monkeypatch, tmp_path):
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)
    _model_fals(monkeypatch)
    _secretar_fals(monkeypatch)

    evenimente = _evenimente("Cum arătăm prețurile?", conversatie)

    assert {"tip": "rezumat", "text": "Subiect: prețurile"} in evenimente


def test_runda_din_care_n_a_iesit_nimic_nou_nu_anunta_niciun_rezumat(monkeypatch, tmp_path):
    """Rezumatul se schimba la cateva runde, nu la fiecare: pagina afla doar cand chiar s-a schimbat."""
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)
    _model_fals(monkeypatch)
    _secretar_fals(monkeypatch, text=None)

    evenimente = _evenimente("Cum arătăm prețurile?", conversatie)

    assert not [e for e in evenimente if e["tip"] == "rezumat"]


def test_consiliul_care_a_tacut_nu_pune_nimic_in_memorie(monkeypatch, tmp_path):
    """N-a vorbit nimeni, deci n-are ce se rezuma - si nici de ce sa se astepte dupa model."""
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)
    _toti_tac(monkeypatch)
    apeluri = _secretar_fals(monkeypatch)

    _evenimente("Mulțumesc, notat.", conversatie)

    assert apeluri == []


def test_runda_taiata_de_mesajul_meu_nu_mai_reface_memoria(monkeypatch, tmp_path):
    """Rezumatul cere un apel la model; o runda peste care am scris nu-l mai merita."""
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)
    _mesaj_nou_peste_runda(monkeypatch, conversatie)
    apeluri = _secretar_fals(monkeypatch)

    _evenimente("Cum arătăm prețurile?", conversatie)

    assert apeluri == []


def test_personajul_isi_aduce_aminte_ce_a_iesit_din_fereastra(monkeypatch, tmp_path):
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    istoric.salveaza_rezumat(conversatie, "Decizii: preview pe server", 6)
    _zaruri(monkeypatch)
    cereri = _model_fals(monkeypatch)

    _evenimente("Și prețurile?", conversatie)

    assert all("Decizii: preview pe server" in cerere["sistem"] for cerere in cereri)


def test_memoria_lunga_nu_ia_fata_chemarii_pe_nume(monkeypatch, tmp_path):
    """Ordinea din prompt e tot ce sustine regula de la M10: ce e ultimul castiga.

    Masurat pe gemma4:e2b, cu rezumatul mutat inaintea `INDEMN_OBLIGAT`: cel chemat pe nume pe
    un subiect strain tace 1 data din 15, ca si fara memorie. Cu rezumatul pus in fata
    contextului, adica dupa indemn in prompt-ul pe care il vede modelul, tace 14 din 15.
    """
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    istoric.salveaza_rezumat(conversatie, "Decizii: preview pe server", 6)
    _zaruri(monkeypatch)
    cereri = _model_fals(monkeypatch)

    _evenimente("@Maestra, ce zici?", conversatie)

    chemata = next(c for c in cereri if c["nume"] == main.PERSONAJE["maestra"]["nume"])
    assert chemata["sistem"].endswith(main.INDEMN_OBLIGAT)
    assert "Decizii: preview pe server" in chemata["sistem"]


def test_si_replica_de_la_sine_vine_cu_memoria_lunga(monkeypatch, tmp_path):
    """Conversatia merge singura mai departe; n-are voie sa uite intre timp ce s-a decis."""
    conversatie, runda, cereri = _o_runda_si_o_continuare(monkeypatch, tmp_path)
    istoric.salveaza_rezumat(conversatie, "Decizii: preview pe server", 6)
    cereri.clear()
    _zaruri(monkeypatch, 0.0)

    _continuare(conversatie, runda)

    assert "Decizii: preview pe server" in cereri[0]["sistem"]


# ---------- ce se intampla cand ceva merge prost ----------


def test_pagina_afla_ca_modelul_nu_raspunde_in_loc_sa_primeasca_o_eroare_de_server(monkeypatch):
    """Cu Ollama oprit, „e viu serverul?" trebuie sa raspunda, nu sa cada si el."""

    def crapa(*argumente, **cuvinte):
        raise RuntimeError("Ollama oprit")

    monkeypatch.setattr(main, "trimite_mesaj", crapa)

    raspuns = client.get("/api/health")

    assert raspuns.status_code == 200
    assert raspuns.json()["model_raspunde"] is False


def test_mesajul_prea_lung_e_refuzat_si_nu_intra_in_istoric(monkeypatch, tmp_path):
    """Peste plafon, Ollama scoate system prompt-ul din context si raspunde un asistent
    generic, fara personaj si fara regula de tacere. Masurat la M14, pe 20.000 de litere."""
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    cereri = _model_fals(monkeypatch)

    raspuns = client.post(
        f"/api/conversatii/{conversatie}/mesaje", json={"text": "a" * (main.LITERE_IN_MESAJ + 1)}
    )

    assert raspuns.status_code == 422
    assert cereri == []
    assert istoric.incarca_istoric(conversatie) == []


def test_un_mesaj_lung_cat_plafonul_trece(monkeypatch, tmp_path):
    """Plafonul opreste derapajele, nu intrebarile lungi: exact cat e permis merge intreg."""
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)
    cereri = _model_fals(monkeypatch)
    text = "Ce zici de " + "mărgele " * 200

    evenimente = _evenimente(text[: main.LITERE_IN_MESAJ], conversatie)

    assert _vorbitori(evenimente)
    assert cereri[0]["mesaj"] == text[: main.LITERE_IN_MESAJ]


def test_conversatia_stearsa_in_timpul_rundei_nu_e_reinviata_de_replici(monkeypatch, tmp_path):
    """Sterg conversatia cat vorbeste consiliul: replicile ramase n-au unde se duce si nu
    trebuie sa refaca fisierul pe care tocmai l-am aruncat."""
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)

    def raspunde_si_sterg(mesaj, nume_personaj, sistem=None, temperatura=None, context=None):
        istoric.sterge_conversatie(conversatie)
        yield f"replica {nume_personaj}"

    monkeypatch.setattr(main, "trimite_mesaj_stream", raspunde_si_sterg)

    evenimente = _evenimente("Cum arătăm prețurile?", conversatie)

    assert "gata" not in [e["tip"] for e in evenimente]
    assert istoric.citeste_conversatie(conversatie) is None


def test_replica_dintr_o_conversatie_stearsa_nu_o_readuce_in_lista(monkeypatch, tmp_path):
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    istoric.sterge_conversatie(conversatie)

    salvat = istoric.salveaza_mesaj(conversatie, {"eu": False, "nume": "Maestra", "text": "Bună"})

    assert salvat is False
    assert conversatie not in [c["id"] for c in istoric.listeaza_conversatii()]


# ---------- replicile degenerate, in runda ----------


def _model_pe_rand(monkeypatch, *replici: str):
    """Modelul da, pe rand, replicile date; ultima se repeta daca se cere mai mult."""
    cereri = []

    def raspunde(mesaj, nume_personaj, sistem=None, temperatura=None, context=None):
        cereri.append({"mesaj": mesaj, "nume": nume_personaj, "sistem": sistem, "context": context})
        yield replici[min(len(cereri) - 1, len(replici) - 1)]

    monkeypatch.setattr(main, "trimite_mesaj_stream", raspunde)
    return cereri


def test_replica_degenerata_nu_ajunge_pe_ecran_si_nici_in_istoric(monkeypatch, tmp_path):
    """Aceeasi cale ca PAS: nu se vede, nu se salveaza."""
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)
    _model_pe_rand(monkeypatch, "Multe.")

    evenimente = _evenimente("Cum arătăm prețurile?", conversatie)

    assert not [e for e in evenimente if e["tip"] == "text"]
    assert _vorbitori(evenimente) == []
    assert [m.get("personajId") for m in istoric.incarca_istoric(conversatie)] == [None]


def test_chematul_care_scoate_o_replica_degenerata_mai_primeste_o_sansa(monkeypatch, tmp_path):
    """Cel convocat pe nume n-are voie sa dispara: runda goala e exact ce a reparat M9."""
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)
    cereri = _model_pe_rand(monkeypatch, "Multe.", "Contează codul exact al mărgelei.")

    evenimente = _evenimente("@Maestra ce zici?", conversatie)

    assert len(cereri) == 2
    assert _vorbitori(evenimente) == ["maestra"]


def test_a_doua_incercare_intreaba_mesajul_meu_nu_replica_dinainte(monkeypatch, tmp_path):
    """Cauza replicii de un cuvant e ca intrebarea dinainte era o intrebare. La a doua
    incercare i se da mesajul meu, care l-a si convocat."""
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)
    istoric.salveaza_mesaj(
        conversatie,
        {"eu": False, "personajId": "operatoarea", "nume": "Operatoarea", "text": "Câte coduri?"},
    )
    cereri = _model_pe_rand(monkeypatch, "Multe.", "Contează codul exact al mărgelei.")

    _evenimente("@Maestra ce zici?", conversatie)

    assert cereri[0]["mesaj"] == "@Maestra ce zici?"  # ultima replica din chat e mesajul meu
    assert cereri[1]["mesaj"] == "@Maestra ce zici?"
    assert "Operatoarea: Câte coduri?" in [m["content"] for m in cereri[1]["context"]]


def test_cel_neobligat_nu_primeste_a_doua_sansa(monkeypatch, tmp_path):
    """Un apel in plus se da doar cui i s-a cerut sa vorbeasca; restul tac si gata."""
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)
    cereri = _model_pe_rand(monkeypatch, "Multe.")

    evenimente = _evenimente("Cum arătăm prețurile?", conversatie)

    intrebati = [e for e in evenimente if e["tip"] == "personaj"]
    # unul singur e obligat, deci un singur apel in plus peste cati au fost intrebati
    assert len(cereri) == len(intrebati) + 1


def test_dupa_a_doua_incercare_degenerata_personajul_tace(monkeypatch, tmp_path):
    """Nu se insista la nesfarsit: doua incercari, apoi tacerea se anunta ca atare."""
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)
    cereri = _model_pe_rand(monkeypatch, "Multe.", "Puține.")

    evenimente = _evenimente("@Maestra ce zici?", conversatie)

    assert len(cereri) == 2
    assert evenimente[-1] == {"tip": "consiliul_tace"}


def test_replica_scurta_cu_cifra_ramane_in_istoric(monkeypatch, tmp_path):
    """Pragul n-are voie sa manance vocea Operatoarei, care chiar vorbeste in cifre."""
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    _zaruri(monkeypatch)
    _model_pe_rand(monkeypatch, "~30g")

    _evenimente("@Operatoarea câte grame?", conversatie)

    assert [m["text"] for m in istoric.incarca_istoric(conversatie)][-1] == "~30g"
