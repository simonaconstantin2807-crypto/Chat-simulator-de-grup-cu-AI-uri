from ai_client import _curata_stream, elimina_prefix_nume, trimite_mesaj, trimite_mesaj_stream


def test_trimite_mesaj_returneaza_text_nevid():
    raspuns = trimite_mesaj("Raspunde cu un singur cuvant: OK.")

    assert isinstance(raspuns, str)
    assert raspuns.strip() != ""


def test_trimite_mesaj_stream_returneaza_text_nevid():
    bucati = list(trimite_mesaj_stream("Raspunde cu un singur cuvant: OK.", "Maestra"))
    raspuns = "".join(bucati)

    assert raspuns.strip() != ""


def test_elimina_prefix_nume_taie_prefixul_cu_spatiu():
    assert elimina_prefix_nume("Maestra: bună ziua", "Maestra") == "bună ziua"


def test_elimina_prefix_nume_taie_prefixul_fara_spatiu():
    assert elimina_prefix_nume("Maestra:bună ziua", "Maestra") == "bună ziua"


def test_elimina_prefix_nume_ignora_litere_mari_mici():
    assert elimina_prefix_nume("maestra: bună ziua", "Maestra") == "bună ziua"


def test_elimina_prefix_nume_lasa_neschimbat_daca_nu_exista_prefix():
    assert elimina_prefix_nume("bună ziua, Maestra", "Maestra") == "bună ziua, Maestra"


def test_curata_stream_taie_prefixul_impartit_pe_mai_multe_bucati():
    bucati = ["Maestra", ": ", "bună ", "ziua"]

    rezultat = "".join(_curata_stream(iter(bucati), "Maestra"))

    assert rezultat == "bună ziua"


def test_curata_stream_produce_raspuns_scurt_fara_doua_puncte():
    bucati = ["Da", "."]

    rezultat = "".join(_curata_stream(iter(bucati), "Maestra"))

    assert rezultat == "Da."


def test_curata_stream_lasa_neschimbat_textul_fara_prefix():
    bucati = ["Bună ziua, ", "cum sunteți azi?"]

    rezultat = "".join(_curata_stream(iter(bucati), "Maestra"))

    assert rezultat == "Bună ziua, cum sunteți azi?"
