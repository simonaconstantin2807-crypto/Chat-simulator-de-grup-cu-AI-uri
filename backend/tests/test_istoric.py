import istoric


def test_incarca_istoric_gol_la_start(monkeypatch, tmp_path):
    monkeypatch.setattr(istoric, "DB_PATH", tmp_path / "sub" / "test.db")
    istoric.init_db()

    assert istoric.incarca_istoric() == []


def test_salveaza_si_incarca_pastreaza_ordinea_si_continutul(monkeypatch, tmp_path):
    monkeypatch.setattr(istoric, "DB_PATH", tmp_path / "sub" / "test.db")
    istoric.init_db()

    mesaj1 = {"eu": True, "nume": "Simona", "avatar": "🙋", "culoare": "#6c5ce7", "text": "Salut"}
    mesaj2 = {"eu": False, "nume": "Maestra", "avatar": "🪡", "culoare": "#C9A227", "text": "Bună"}

    istoric.salveaza_mesaj(mesaj1)
    istoric.salveaza_mesaj(mesaj2)

    assert istoric.incarca_istoric() == [mesaj1, mesaj2]
