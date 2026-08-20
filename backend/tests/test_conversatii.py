"""Conversatii separate: fiecare cu istoricul ei, plus migrarea celei vechi, unice."""

import json

import pytest

import istoric


def _stocare_izolata(monkeypatch, tmp_path):
    monkeypatch.setattr(istoric, "DATE_DIR", tmp_path)
    istoric.init_stocare()


def _conversatie_veche(tmp_path, mesaje: list[dict]) -> None:
    """Fisierul unic de dinainte de conversatiile multiple, asa cum il gaseste migrarea."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "conversatie.json").write_text(
        json.dumps(mesaje, ensure_ascii=False), encoding="utf-8"
    )


def test_la_prima_pornire_exista_o_conversatie_goala(monkeypatch, tmp_path):
    """Nu deschid aplicatia intr-un loc fara nicio conversatie in care sa scriu."""
    _stocare_izolata(monkeypatch, tmp_path)

    conversatii = istoric.listeaza_conversatii()

    assert len(conversatii) == 1
    assert istoric.incarca_istoric(conversatii[0]["id"]) == []


def test_conversatia_veche_se_muta_intr_una_noua_la_prima_pornire(monkeypatch, tmp_path):
    """Ce am discutat pana acum nu se pierde cand apar conversatiile multiple."""
    _conversatie_veche(
        tmp_path,
        [
            {"eu": True, "nume": "Simona", "text": "Ce zici de AB?"},
            {"eu": False, "personajId": "maestra", "nume": "Maestra", "text": "Nu se simulează."},
        ],
    )
    _stocare_izolata(monkeypatch, tmp_path)

    conversatii = istoric.listeaza_conversatii()

    assert len(conversatii) == 1
    assert [m["text"] for m in istoric.incarca_istoric(conversatii[0]["id"])] == [
        "Ce zici de AB?",
        "Nu se simulează.",
    ]


def test_conversatia_migrata_isi_ia_titlul_din_primul_meu_mesaj(monkeypatch, tmp_path):
    _conversatie_veche(tmp_path, [{"eu": True, "nume": "Simona", "text": "Ce zici de AB?"}])
    _stocare_izolata(monkeypatch, tmp_path)

    assert istoric.listeaza_conversatii()[0]["titlu"] == "Ce zici de AB?"


def test_migrarea_nu_se_repeta_la_urmatoarea_pornire(monkeypatch, tmp_path):
    """Altfel as gasi aceeasi discutie clonata la fiecare restart al serverului."""
    _conversatie_veche(tmp_path, [{"eu": True, "nume": "Simona", "text": "Ce zici de AB?"}])
    _stocare_izolata(monkeypatch, tmp_path)

    istoric.init_stocare()

    assert len(istoric.listeaza_conversatii()) == 1


def test_o_conversatie_noua_incepe_goala(monkeypatch, tmp_path):
    _stocare_izolata(monkeypatch, tmp_path)

    noua = istoric.creeaza_conversatie()

    assert istoric.incarca_istoric(noua["id"]) == []
    assert noua["titlu"] == ""


def test_fiecare_conversatie_isi_tine_mesajele_ei(monkeypatch, tmp_path):
    _stocare_izolata(monkeypatch, tmp_path)
    una = istoric.creeaza_conversatie()["id"]
    alta = istoric.creeaza_conversatie()["id"]

    istoric.salveaza_mesaj(una, {"eu": True, "nume": "Simona", "text": "Despre AB"})
    istoric.salveaza_mesaj(alta, {"eu": True, "nume": "Simona", "text": "Despre prețuri"})

    assert [m["text"] for m in istoric.incarca_istoric(una)] == ["Despre AB"]
    assert [m["text"] for m in istoric.incarca_istoric(alta)] == ["Despre prețuri"]


def test_personajele_nu_vad_in_context_nimic_din_alta_conversatie(monkeypatch, tmp_path):
    """Doua sedinte de consiliu diferite nu se aud una pe alta."""
    _stocare_izolata(monkeypatch, tmp_path)
    una = istoric.creeaza_conversatie()["id"]
    alta = istoric.creeaza_conversatie()["id"]
    istoric.salveaza_mesaj(una, {"eu": True, "nume": "Simona", "text": "Secretul din prima"})

    assert istoric.context_pentru(alta, "maestra") == []


def test_titlul_se_face_din_primele_cuvinte_ale_primului_meu_mesaj(monkeypatch, tmp_path):
    """Nu sunt obligata sa scriu eu titlul: apare singur cand incep sa vorbesc."""
    _stocare_izolata(monkeypatch, tmp_path)
    conversatie = istoric.creeaza_conversatie()["id"]

    istoric.salveaza_mesaj(
        conversatie,
        {"eu": True, "nume": "Simona", "text": "Merită să simulăm AB-ul pe poză sau nu?"},
    )

    assert istoric.citeste_conversatie(conversatie)["titlu"] == "Merită să simulăm AB-ul pe…"


def test_titlul_nu_se_schimba_la_al_doilea_mesaj(monkeypatch, tmp_path):
    _stocare_izolata(monkeypatch, tmp_path)
    conversatie = istoric.creeaza_conversatie()["id"]

    istoric.salveaza_mesaj(conversatie, {"eu": True, "nume": "Simona", "text": "Prima întrebare"})
    istoric.salveaza_mesaj(conversatie, {"eu": True, "nume": "Simona", "text": "Cu totul altceva"})

    assert istoric.citeste_conversatie(conversatie)["titlu"] == "Prima întrebare"


def test_titlul_pus_de_mine_nu_e_inlocuit_de_primul_mesaj(monkeypatch, tmp_path):
    """Titlul scris de mine e o decizie, nu o valoare provizorie."""
    _stocare_izolata(monkeypatch, tmp_path)
    conversatie = istoric.creeaza_conversatie()["id"]
    istoric.redenumeste_conversatie(conversatie, "Ședința despre culori")

    istoric.salveaza_mesaj(conversatie, {"eu": True, "nume": "Simona", "text": "Ce zici de AB?"})

    assert istoric.citeste_conversatie(conversatie)["titlu"] == "Ședința despre culori"


def test_replica_unui_personaj_nu_da_titlul_conversatiei(monkeypatch, tmp_path):
    """Titlul vine din ce am intrebat eu, nu din ce a raspuns cine s-a nimerit primul."""
    _stocare_izolata(monkeypatch, tmp_path)
    conversatie = istoric.creeaza_conversatie()["id"]

    istoric.salveaza_mesaj(
        conversatie, {"eu": False, "personajId": "maestra", "text": "Nu se simulează."}
    )

    assert istoric.citeste_conversatie(conversatie)["titlu"] == ""


def test_redenumirea_pastreaza_mesajele(monkeypatch, tmp_path):
    _stocare_izolata(monkeypatch, tmp_path)
    conversatie = istoric.creeaza_conversatie()["id"]
    istoric.salveaza_mesaj(conversatie, {"eu": True, "nume": "Simona", "text": "Ce zici de AB?"})

    istoric.redenumeste_conversatie(conversatie, "AB pe poză")

    assert istoric.citeste_conversatie(conversatie)["titlu"] == "AB pe poză"
    assert len(istoric.incarca_istoric(conversatie)) == 1


def test_stergerea_scoate_conversatia_din_lista(monkeypatch, tmp_path):
    _stocare_izolata(monkeypatch, tmp_path)
    ramane = istoric.listeaza_conversatii()[0]["id"]
    de_sters = istoric.creeaza_conversatie()["id"]

    istoric.sterge_conversatie(de_sters)

    assert [c["id"] for c in istoric.listeaza_conversatii()] == [ramane]


def test_dupa_ce_sterg_ultima_conversatie_ramane_una_goala(monkeypatch, tmp_path):
    """Ecranul nu ramane fara niciun loc in care sa scriu."""
    _stocare_izolata(monkeypatch, tmp_path)
    singura = istoric.listeaza_conversatii()[0]["id"]

    istoric.sterge_conversatie(singura)
    istoric.asigura_o_conversatie()

    conversatii = istoric.listeaza_conversatii()
    assert len(conversatii) == 1
    assert conversatii[0]["id"] != singura


def test_conversatia_folosita_ultima_e_prima_in_lista(monkeypatch, tmp_path):
    """Ca intr-o aplicatie de chat: sus e discutia la care lucrez acum."""
    _stocare_izolata(monkeypatch, tmp_path)
    veche = istoric.creeaza_conversatie()["id"]
    noua = istoric.creeaza_conversatie()["id"]

    istoric.salveaza_mesaj(veche, {"eu": True, "nume": "Simona", "text": "Revin aici"})

    assert [c["id"] for c in istoric.listeaza_conversatii()][:2] == [veche, noua]


def test_lista_spune_cate_mesaje_are_fiecare_conversatie(monkeypatch, tmp_path):
    _stocare_izolata(monkeypatch, tmp_path)
    conversatie = istoric.creeaza_conversatie()["id"]
    istoric.salveaza_mesaj(conversatie, {"eu": True, "nume": "Simona", "text": "Unu"})

    listata = next(c for c in istoric.listeaza_conversatii() if c["id"] == conversatie)

    assert listata["numarMesaje"] == 1
    assert "mesaje" not in listata  # lista e un cuprins, nu toata arhiva


def test_conversatiile_supravietuiesc_repornirii(monkeypatch, tmp_path):
    """Fisierele se citesc de la zero, ca dupa un restart al serverului."""
    _stocare_izolata(monkeypatch, tmp_path)
    conversatie = istoric.creeaza_conversatie()["id"]
    istoric.salveaza_mesaj(conversatie, {"eu": True, "nume": "Simona", "text": "Rămâne aici?"})

    istoric.init_stocare()

    assert [m["text"] for m in istoric.incarca_istoric(conversatie)] == ["Rămâne aici?"]


def test_fisierul_unei_conversatii_se_poate_citi_cu_ochiul(monkeypatch, tmp_path):
    """Motivul pentru care ramane JSON: deschid fisierul si vad ce a primit modelul."""
    _stocare_izolata(monkeypatch, tmp_path)
    conversatie = istoric.creeaza_conversatie()["id"]
    istoric.salveaza_mesaj(conversatie, {"eu": True, "nume": "Simona", "text": "Ce zici de AB?"})

    scris = json.loads((tmp_path / "conversatii" / f"{conversatie}.json").read_text("utf-8"))

    assert scris["titlu"] == "Ce zici de AB?"
    assert scris["mesaje"][0]["text"] == "Ce zici de AB?"


@pytest.mark.parametrize("id_inventat", ["../conversatie", "nu-exista", "", "a/b"])
def test_o_conversatie_care_nu_exista_nu_da_niciun_mesaj(monkeypatch, tmp_path, id_inventat):
    """Id-ul vine din URL, deci nu are voie sa scoata citirea din folderul de date."""
    _stocare_izolata(monkeypatch, tmp_path)

    assert istoric.citeste_conversatie(id_inventat) is None
    assert istoric.incarca_istoric(id_inventat) == []


def test_lista_de_conversatii_nu_cara_rezumatul_dupa_ea(monkeypatch, tmp_path):
    """Lista se cere la fiecare mesaj trimis; e un cuprins, nu memoria fiecarei sedinte."""
    _stocare_izolata(monkeypatch, tmp_path)
    conversatie = istoric.creeaza_conversatie()["id"]
    istoric.salveaza_rezumat(conversatie, "Subiect: AB-ul", 6)

    listata = next(c for c in istoric.listeaza_conversatii() if c["id"] == conversatie)

    assert "rezumat" not in listata
    assert "rezumatPanaLa" not in listata


def test_rezumatul_nu_schimba_ordinea_conversatiilor(monkeypatch, tmp_path):
    """Ordinea o dau mesajele mele. Memoria se reface in fundal, nu e o atingere de-a mea."""
    _stocare_izolata(monkeypatch, tmp_path)
    conversatie = istoric.creeaza_conversatie()["id"]
    istoric.creeaza_conversatie()
    inainte = [c["id"] for c in istoric.listeaza_conversatii()]

    istoric.salveaza_rezumat(conversatie, "Subiect: AB-ul", 6)

    assert [c["id"] for c in istoric.listeaza_conversatii()] == inainte


def test_conversatiile_facute_una_dupa_alta_raman_in_ordinea_facerii(monkeypatch, tmp_path):
    """Ceasul Windows sta pe loc ~15ms: sase apeluri la rand la `datetime.now()` dau aceeasi
    microsecunda. Cand momentele ies egale, lista se asaza dupa sufixul aleator din id si
    conversatia tocmai facuta poate ajunge sub una veche."""
    _stocare_izolata(monkeypatch, tmp_path)

    facute = [istoric.creeaza_conversatie()["id"] for _ in range(6)]

    listate = [c["id"] for c in istoric.listeaza_conversatii()]

    assert listate[: len(facute)] == list(reversed(facute))
