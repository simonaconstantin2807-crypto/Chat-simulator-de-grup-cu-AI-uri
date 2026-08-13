import ollama

from ai_client import (
    KEEP_ALIVE,
    MAX_TOKENI,
    MODEL_IMPLICIT,
    _construieste_cerere,
    _curata_stream,
    elimina_prefix_nume,
    preincarca,
    trimite_mesaj,
    trimite_mesaj_stream,
)


def test_trimite_mesaj_returneaza_text_nevid():
    raspuns = trimite_mesaj("Raspunde cu un singur cuvant: OK.")

    assert isinstance(raspuns, str)
    assert raspuns.strip() != ""


def test_trimite_mesaj_stream_returneaza_text_nevid():
    bucati = list(trimite_mesaj_stream("Raspunde cu un singur cuvant: OK.", "Maestra"))
    raspuns = "".join(bucati)

    assert raspuns.strip() != ""


def test_cererea_tine_modelul_incarcat_intre_mesaje():
    cerere = _construieste_cerere("Salut", sistem=None, temperatura=None)

    assert cerere["keep_alive"] == KEEP_ALIVE


def test_cererea_plafoneaza_lungimea_raspunsului():
    cerere = _construieste_cerere("Salut", sistem=None, temperatura=None)

    assert cerere["options"]["num_predict"] == MAX_TOKENI


def test_cererea_opreste_gandirea_modelului():
    cerere = _construieste_cerere("Salut", sistem=None, temperatura=None)

    assert cerere["think"] is False


def test_modelul_scrie_text_vizibil_nu_doar_rationament():
    """Cu gandirea pornita, modelul consuma sute de tokeni interni si nu ajunge la raspuns."""
    bucati = list(trimite_mesaj_stream("Ce parere ai despre AB simulat pe poza?", "Maestra"))

    assert "".join(bucati).strip() != ""


def test_preincarca_aduce_modelul_in_memorie():
    preincarca()

    incarcate = ollama.ps().models

    assert any(m.model == MODEL_IMPLICIT for m in incarcate)


def test_raspunsul_nu_depaseste_plafonul_de_tokeni():
    bucati = list(trimite_mesaj_stream("Descrie in detaliu istoria margelelor Miyuki.", "Maestra"))

    assert 0 < len(bucati) <= MAX_TOKENI


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
