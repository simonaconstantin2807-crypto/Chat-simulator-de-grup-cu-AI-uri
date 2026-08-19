import istoric
from personaje import incarca_personaje


def _istoric_izolat(monkeypatch, tmp_path) -> str:
    """O conversatie proaspata, intr-un folder de date numai al testului."""
    monkeypatch.setattr(istoric, "DATE_DIR", tmp_path / "date")
    istoric.init_stocare()
    return istoric.creeaza_conversatie()["id"]


def test_incarca_istoric_gol_la_start(monkeypatch, tmp_path):
    conversatie = _istoric_izolat(monkeypatch, tmp_path)

    assert istoric.incarca_istoric(conversatie) == []


def test_salveaza_si_incarca_pastreaza_ordinea_si_continutul(monkeypatch, tmp_path):
    conversatie = _istoric_izolat(monkeypatch, tmp_path)

    mesaj1 = {"eu": True, "nume": "Simona", "avatar": "🙋", "culoare": "#3D3A36", "text": "Salut"}
    mesaj2 = {"eu": False, "personajId": "maestra", "nume": "Maestra", "text": "Bună"}

    istoric.salveaza_mesaj(conversatie, mesaj1)
    istoric.salveaza_mesaj(conversatie, mesaj2)

    assert istoric.incarca_istoric(conversatie) == [mesaj1, mesaj2]


def test_conversatia_supravietuieste_repornirii(monkeypatch, tmp_path):
    """Fisierul JSON e citit de la zero, ca dupa un restart al serverului."""
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    istoric.salveaza_mesaj(conversatie, {"eu": True, "nume": "Simona", "text": "Rămâne aici?"})

    istoric.init_stocare()  # nu suprascrie ce exista deja

    assert [m["text"] for m in istoric.incarca_istoric(conversatie)] == ["Rămâne aici?"]


def test_contextul_pastreaza_mesajele_mele_si_replicile_personajului(monkeypatch, tmp_path):
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    istoric.salveaza_mesaj(conversatie, {"eu": True, "nume": "Simona", "text": "Ce zici de AB?"})
    istoric.salveaza_mesaj(
        conversatie, {"eu": False, "personajId": "maestra", "text": "Nu se simulează."}
    )

    assert istoric.context_pentru(conversatie, "maestra") == [
        {"role": "user", "content": "Ce zici de AB?"},
        {"role": "assistant", "content": "Nu se simulează."},
    ]


def test_contextul_contine_si_replicile_celorlalte_personaje(monkeypatch, tmp_path):
    """Fara ele, "contrazici pe altcineva" din system prompt e imposibil de dus la capat."""
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    istoric.salveaza_mesaj(conversatie, {"eu": True, "nume": "Simona", "text": "Ce zici de AB?"})
    istoric.salveaza_mesaj(
        conversatie,
        {"eu": False, "personajId": "clienta", "nume": "Clienta", "text": "Vreau repede."},
    )
    istoric.salveaza_mesaj(
        conversatie,
        {"eu": False, "personajId": "maestra", "nume": "Maestra", "text": "Nu se simulează."},
    )

    assert istoric.context_pentru(conversatie, "maestra") == [
        {"role": "user", "content": "Ce zici de AB?"},
        {"role": "user", "content": "Clienta: Vreau repede."},
        {"role": "assistant", "content": "Nu se simulează."},
    ]


def test_replicile_altora_poarta_numele_ca_sa_nu_se_amestece_vocile(monkeypatch, tmp_path):
    """Fara nume, modelul aude o singura voce si nu stie cui raspunde."""
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    istoric.salveaza_mesaj(conversatie, {"eu": True, "nume": "Simona", "text": "Cine plătește?"})
    istoric.salveaza_mesaj(
        conversatie, {"eu": False, "personajId": "clienta", "nume": "Clienta", "text": "Nu pe Etsy."}
    )

    context = istoric.context_pentru(conversatie, "maestra")

    assert context[0]["content"] == "Cine plătește?"  # mesajele mele raman curate
    assert context[1]["content"] == "Clienta: Nu pe Etsy."


def test_replica_proprie_ramane_fara_nume_in_fata(monkeypatch, tmp_path):
    """Prefixul pe propriile replici l-ar invata pe model sa-si semneze mesajele."""
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    istoric.salveaza_mesaj(
        conversatie,
        {"eu": False, "personajId": "maestra", "nume": "Maestra", "text": "Nu se simulează."},
    )

    assert istoric.context_pentru(conversatie, "maestra") == [
        {"role": "assistant", "content": "Nu se simulează."}
    ]


def test_replica_veche_fara_nume_salvat_cade_pe_id(monkeypatch, tmp_path):
    """Conversatiile salvate inainte de campul `nume` nu trebuie sa crape la citire."""
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    istoric.salveaza_mesaj(
        conversatie, {"eu": False, "personajId": "clienta", "text": "Vreau repede."}
    )

    assert istoric.context_pentru(conversatie, "maestra") == [
        {"role": "user", "content": "clienta: Vreau repede."}
    ]


def test_contextul_taie_la_ultimele_n_mesaje(monkeypatch, tmp_path):
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    for i in range(10):
        istoric.salveaza_mesaj(conversatie, {"eu": True, "nume": "Simona", "text": f"mesaj {i}"})

    context = istoric.context_pentru(conversatie, "maestra", limita=3)

    assert [m["content"] for m in context] == ["mesaj 7", "mesaj 8", "mesaj 9"]


def test_fereastra_acopera_mai_multe_runde_de_consiliu():
    """O runda completa = mesajul meu + cate o replica. Sub trei runde, personajele uita
    ce s-a discutat mai devreme decat apuca sa comenteze. Creste odata cu consiliul."""
    o_runda = 1 + len(incarca_personaje())

    assert istoric.MESAJE_IN_CONTEXT >= 3 * o_runda
