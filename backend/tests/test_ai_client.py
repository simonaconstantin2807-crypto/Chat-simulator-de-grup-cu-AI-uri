import ollama
import pytest

import ai_client

from ai_client import (
    KEEP_ALIVE,
    LITERE_MINIME_REPLICA,
    MAX_TOKENI,
    MODEL_IMPLICIT,
    _construieste_cerere,
    _curata_stream,
    e_contributie,
    elimina_prefix_nume,
    fara_pas,
    fara_replici_degenerate,
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


def test_pasul_urmat_de_o_replica_nu_ajunge_pe_ecran():
    """gemma4:e2b scrie uneori „PAS." si continua cu replica adevarata. PAS-ul nu are voie
    sa se vada oricum ar veni - masurat la M14, 4 din 12 replici pe domeniul propriu."""
    bucati = ["PAS. ", "Trebuie ", "să lansăm cu un singur plan."]

    assert "".join(fara_pas(iter(bucati))) == "Trebuie să lansăm cu un singur plan."


def test_pasul_lipit_de_replica_e_taiat_si_el():
    assert "".join(fara_pas(iter(["PAS.Contează codul exact."]))) == "Contează codul exact."


def test_replica_care_incepe_cu_pas_ca_si_cuvant_ramane_intreaga():
    """„Pas cu pas" incepe la fel, dar nu e o abtinere: dupa PAS nu vine punctuatie."""
    assert "".join(fara_pas(iter(["Pas cu pas, altfel iese prost."]))) == "Pas cu pas, altfel iese prost."


# ---------- replicile degenerate ----------


def test_raspunsul_de_un_cuvant_la_o_intrebare_e_tacere():
    """„Cât de multe coduri sunt necesare?" -> „Multe." Fiecare raspunde ultimei replici, iar
    cand aceea e o intrebare, modelul mic o ia literal si raspunde intr-un cuvant."""
    assert not e_contributie("Multe.")


def test_raspunsul_care_duce_o_idee_trece():
    assert e_contributie("Da, exact asta ziceam.")


def test_raspunsul_scurt_cu_cifra_trece():
    """Operatoarea vorbeste in cifre: „~30g" e scurt, dar e chiar contributia ei."""
    assert e_contributie("~30g")


def test_raspunsul_scurt_care_cheama_pe_cineva_trece():
    """O chemare e o contributie: porneste replica altcuiva."""
    assert e_contributie("@Maestra?")


def test_pragul_e_inclusiv_la_granita():
    la_prag = "a" * LITERE_MINIME_REPLICA
    sub_prag = "a" * (LITERE_MINIME_REPLICA - 1)

    assert e_contributie(la_prag)
    assert not e_contributie(sub_prag)


def test_spatiile_din_jur_nu_umplu_pragul():
    assert not e_contributie("   Multe.   ")


def test_replica_degenerata_nu_apuca_sa_apara_pe_ecran():
    """Se filtreaza in stream, ca la PAS: altfel „Multe." ar aparea si ar disparea sub ochii mei."""
    assert list(fara_replici_degenerate(iter(["Mul", "te."]))) == []


def test_replica_adevarata_curge_mai_departe_bucata_cu_bucata():
    """Se retine doar inceputul, cat sa se stie: dupa prag, restul curge cum vine, ca sa nu se
    piarda efectul de scriere in timp real."""
    bucati = ["Nu sunt de acord", ", codul ", "exact conteaza."]

    iesite = list(fara_replici_degenerate(iter(bucati)))

    assert "".join(iesite) == "".join(bucati)
    assert len(iesite) > 1


def test_cifra_elibereaza_replica_imediat():
    assert "".join(fara_replici_degenerate(iter(["~30", "g"]))) == "~30g"


def test_raspunsul_gol_ramane_gol():
    assert list(fara_replici_degenerate(iter([""]))) == []


# ---------- modelul care crapa la incarcare ----------


def _stream_fals(*bucati: str):
    return iter([{"message": {"content": b}} for b in bucati])


def _ollama_care_crapa(monkeypatch, *rezultate):
    """`ollama.chat` da, pe rand, rezultatele cerute: o exceptie sau un stream."""
    ramase = list(rezultate)
    apeluri = []

    def chat(**cuvinte):
        apeluri.append(cuvinte)
        rezultat = ramase.pop(0)
        if isinstance(rezultat, Exception):
            raise rezultat
        return rezultat

    monkeypatch.setattr(ai_client.ollama, "chat", chat)
    return apeluri


def test_modelul_care_crapa_la_incarcare_e_reincercat_o_data(monkeypatch):
    """Pe masina asta, incarcarea la rece pe GPU esueaza din cand in cand cu 0xc0000409, iar
    incercarea urmatoare merge. Fara reincercare, prima intrebare de dupa o pauza da bula rosie."""
    apeluri = _ollama_care_crapa(
        monkeypatch,
        RuntimeError("CUDA error: shared object initialization failed"),
        _stream_fals("Contează codul ", "exact al mărgelei."),
    )

    text = "".join(trimite_mesaj_stream("Ce zici?", "Maestra"))

    assert text == "Contează codul exact al mărgelei."
    assert len(apeluri) == 2


def test_reincercarea_nu_repeta_ce_a_ajuns_deja_pe_ecran(monkeypatch):
    """Daca modelul cade dupa ce a scris ceva, a doua incercare ar dubla textul in bula."""

    def stream_care_cade():
        yield {"message": {"content": "Contează codul "}}
        raise RuntimeError("conexiunea a picat la mijloc")

    _ollama_care_crapa(monkeypatch, stream_care_cade(), _stream_fals("altceva"))

    bucati = []
    with pytest.raises(RuntimeError):
        for bucata in trimite_mesaj_stream("Ce zici?", "Maestra"):
            bucati.append(bucata)

    assert "".join(bucati) == "Contează codul "


def test_daca_si_a_doua_incercare_crapa_eroarea_iese_afara(monkeypatch):
    """Runda trebuie sa afle: o bula rosie e mai bine decat o asteptare fara capat."""
    _ollama_care_crapa(
        monkeypatch,
        RuntimeError("Ollama oprit"),
        RuntimeError("Ollama tot oprit"),
    )

    with pytest.raises(RuntimeError):
        list(trimite_mesaj_stream("Ce zici?", "Maestra"))
