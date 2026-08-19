import ollama
import pytest

from ai_client import (
    KEEP_ALIVE,
    MAX_TOKENI,
    MODEL_IMPLICIT,
    _construieste_cerere,
    _curata_stream,
    elimina_prefix_nume,
    fara_pas,
    preincarca,
    trimite_mesaj,
    trimite_mesaj_stream,
)


@pytest.mark.ollama
def test_trimite_mesaj_returneaza_text_nevid():
    raspuns = trimite_mesaj("Raspunde cu un singur cuvant: OK.")

    assert isinstance(raspuns, str)
    assert raspuns.strip() != ""


@pytest.mark.ollama
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


def test_cererea_pune_istoricul_intre_system_prompt_si_mesajul_curent():
    context = [
        {"role": "user", "content": "prima întrebare"},
        {"role": "assistant", "content": "primul răspuns"},
    ]

    cerere = _construieste_cerere(
        "a doua întrebare", sistem="Ești Maestra.", temperatura=None, context=context
    )

    assert [m["role"] for m in cerere["messages"]] == ["system", "user", "assistant", "user"]
    assert cerere["messages"][-1]["content"] == "a doua întrebare"


def test_cererea_opreste_gandirea_modelului():
    cerere = _construieste_cerere("Salut", sistem=None, temperatura=None)

    assert cerere["think"] is False


@pytest.mark.ollama
def test_modelul_scrie_text_vizibil_nu_doar_rationament():
    """Cu gandirea pornita, modelul consuma sute de tokeni interni si nu ajunge la raspuns."""
    bucati = list(trimite_mesaj_stream("Ce parere ai despre AB simulat pe poza?", "Maestra"))

    assert "".join(bucati).strip() != ""


@pytest.mark.ollama
def test_preincarca_aduce_modelul_in_memorie():
    preincarca()

    incarcate = ollama.ps().models

    assert any(m.model == MODEL_IMPLICIT for m in incarcate)


@pytest.mark.ollama
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


def test_pasul_singur_nu_lasa_nimic_sa_treaca():
    """Cine n-are ce adauga scrie doar PAS, iar PAS-ul nu trebuie sa ajunga pe ecran."""
    assert list(fara_pas(iter(["PAS"]))) == []


def test_pasul_e_recunoscut_cu_punctuatie_si_litere_mici():
    assert list(fara_pas(iter(["Pas."]))) == []
    assert list(fara_pas(iter(["  pas  "]))) == []


def test_replica_normala_trece_intreaga():
    bucati = ["Contează ", "codul ", "exact al mărgelei."]

    assert "".join(fara_pas(iter(bucati))) == "Contează codul exact al mărgelei."


def test_replica_care_incepe_cu_pas_nu_e_confundata():
    """„Pas cu pas" e o replica adevarata, nu o abtinere."""
    bucati = ["Pas", " cu pas", ", altfel iese prost."]

    assert "".join(fara_pas(iter(bucati))) == "Pas cu pas, altfel iese prost."


def test_pasul_impartit_pe_mai_multe_bucati_e_tot_pas():
    assert list(fara_pas(iter(["P", "A", "S"]))) == []


def test_raspunsul_gol_nu_produce_nimic():
    assert list(fara_pas(iter([""]))) == []
