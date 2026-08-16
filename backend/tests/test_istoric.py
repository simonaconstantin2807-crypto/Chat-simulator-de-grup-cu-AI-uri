import istoric


def _stocare_izolata(monkeypatch, tmp_path):
    monkeypatch.setattr(istoric, "ISTORIC_PATH", tmp_path / "sub" / "conversatie.json")
    istoric.init_stocare()


def test_incarca_istoric_gol_la_start(monkeypatch, tmp_path):
    _stocare_izolata(monkeypatch, tmp_path)

    assert istoric.incarca_istoric() == []


def test_salveaza_si_incarca_pastreaza_ordinea_si_continutul(monkeypatch, tmp_path):
    _stocare_izolata(monkeypatch, tmp_path)

    mesaj1 = {"eu": True, "nume": "Simona", "avatar": "🙋", "culoare": "#3D3A36", "text": "Salut"}
    mesaj2 = {"eu": False, "personajId": "maestra", "nume": "Maestra", "text": "Bună"}

    istoric.salveaza_mesaj(mesaj1)
    istoric.salveaza_mesaj(mesaj2)

    assert istoric.incarca_istoric() == [mesaj1, mesaj2]


def test_conversatia_supravietuieste_repornirii(monkeypatch, tmp_path):
    """Fisierul JSON e citit de la zero, ca dupa un restart al serverului."""
    _stocare_izolata(monkeypatch, tmp_path)
    istoric.salveaza_mesaj({"eu": True, "nume": "Simona", "text": "Rămâne aici?"})

    istoric.init_stocare()  # nu suprascrie ce exista deja

    assert [m["text"] for m in istoric.incarca_istoric()] == ["Rămâne aici?"]


def test_contextul_pastreaza_mesajele_mele_si_replicile_personajului(monkeypatch, tmp_path):
    _stocare_izolata(monkeypatch, tmp_path)
    istoric.salveaza_mesaj({"eu": True, "nume": "Simona", "text": "Ce zici de AB?"})
    istoric.salveaza_mesaj({"eu": False, "personajId": "maestra", "text": "Nu se simulează."})

    assert istoric.context_pentru("maestra") == [
        {"role": "user", "content": "Ce zici de AB?"},
        {"role": "assistant", "content": "Nu se simulează."},
    ]


def test_contextul_nu_contine_replicile_celorlalte_personaje(monkeypatch, tmp_path):
    """Personajele nu se aud inca intre ele - asta ramane pe etapa cu logica de tura."""
    _stocare_izolata(monkeypatch, tmp_path)
    istoric.salveaza_mesaj({"eu": True, "nume": "Simona", "text": "Ce zici de AB?"})
    istoric.salveaza_mesaj({"eu": False, "personajId": "clienta", "text": "Vreau repede."})
    istoric.salveaza_mesaj({"eu": False, "personajId": "maestra", "text": "Nu se simulează."})

    context = istoric.context_pentru("maestra")

    assert {"role": "assistant", "content": "Vreau repede."} not in context
    assert {"role": "assistant", "content": "Nu se simulează."} in context


def test_contextul_taie_la_ultimele_n_mesaje(monkeypatch, tmp_path):
    _stocare_izolata(monkeypatch, tmp_path)
    for i in range(10):
        istoric.salveaza_mesaj({"eu": True, "nume": "Simona", "text": f"mesaj {i}"})

    context = istoric.context_pentru("maestra", limita=3)

    assert [m["content"] for m in context] == ["mesaj 7", "mesaj 8", "mesaj 9"]
