from ai_client import trimite_mesaj


def test_trimite_mesaj_returneaza_text_nevid():
    raspuns = trimite_mesaj("Raspunde cu un singur cuvant: OK.")

    assert isinstance(raspuns, str)
    assert raspuns.strip() != ""
