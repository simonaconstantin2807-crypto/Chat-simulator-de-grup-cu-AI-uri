import random

import pytest

from personaje import (
    gaseste_mentiuni,
    incarca_personaje,
    obligati_sa_raspunda,
    ordinea_vorbitorilor,
    probabilitati,
    profil_public,
)

PERSONAJE = incarca_personaje()


def _consiliu(cati: int) -> dict:
    """Un consiliu de marimea ceruta, ca sa verific ca nimic nu e legat de cifra 5."""
    return {f"p{i}": {"id": f"p{i}", "nume": f"P{i}"} for i in range(1, cati + 1)}


def _sorti(*valori: float):
    """Aruncarea cu banul, cu rezultate dictate: 0.0 intra mereu, 1.0 nu intra niciodata."""
    ramase = list(valori)
    return lambda: ramase.pop(0)


def test_sunt_cele_cinci_personaje_din_spec():
    assert set(PERSONAJE) == {
        "maestra",
        "antreprenoarea",
        "clienta",
        "operatoarea",
        "programatorul",
    }


def test_fiecare_personaj_are_identitate_completa():
    for personaj in PERSONAJE.values():
        assert personaj["nume"] and personaj["rol"] and personaj["avatar"]
        assert personaj["culoare"].startswith("#") and personaj["culoareFundal"].startswith("#")
        assert personaj["systemPrompt"].strip()
        assert 0 <= personaj["temperaturaRecomandata"] <= 1


def test_elementele_vizuale_sunt_unice_pentru_fiecare():
    """Se recunosc dintr-o privire doar daca nu impart avatarul sau culoarea."""
    avatare = [p["avatar"] for p in PERSONAJE.values()]
    culori = [p["culoare"] for p in PERSONAJE.values()]

    assert len(set(avatare)) == len(avatare)
    assert len(set(culori)) == len(culori)


def test_fiecare_stie_ca_poate_chema_pe_altcineva_cu_at():
    """Lantul de chemari nu porneste daca personajele nu stiu ca @Nume e o convocare."""
    for personaj in PERSONAJE.values():
        assert "@" in personaj["systemPrompt"], f"{personaj['nume']} nu stie de conventia @"


def test_fiecare_stie_ca_poate_sa_taca(monkeypatch=None):
    """Fara regula asta in prompt, nimeni nu scrie PAS si toti raspund la orice."""
    for personaj in PERSONAJE.values():
        assert "PAS" in personaj["systemPrompt"], f"{personaj['nume']} nu stie sa taca"


def test_vocile_sunt_diferite_prin_temperatura():
    temperaturi = {p["temperaturaRecomandata"] for p in PERSONAJE.values()}

    assert len(temperaturi) > 1


def test_profilul_public_nu_scurge_system_promptul():
    profil = profil_public(PERSONAJE["maestra"])

    assert "systemPrompt" not in profil
    assert profil["nume"] == "Maestra"
    assert set(profil) == {"id", "nume", "rol", "avatar", "culoare", "culoareFundal"}


def test_mentiunea_dupa_nume_ignora_literele_mari():
    assert gaseste_mentiuni("@maestra ce zici?", PERSONAJE) == ["maestra"]
    assert gaseste_mentiuni("@Maestra ce zici?", PERSONAJE) == ["maestra"]


def test_mentiunile_pastreaza_ordinea_si_nu_se_repeta():
    text = "@Clienta și @Operatoarea, ce ziceți? @Clienta mai ales tu."

    assert gaseste_mentiuni(text, PERSONAJE) == ["clienta", "operatoarea"]


def test_mentiunea_necunoscuta_e_ignorata():
    assert gaseste_mentiuni("@Bunicuta ce zici?", PERSONAJE) == []


def test_mentionatii_raspund_sigur():
    sanse = probabilitati("@Maestra și @Programatorul, ce ziceți?", PERSONAJE)

    assert sanse["maestra"] == 1.0
    assert sanse["programatorul"] == 1.0


def test_nementionatii_impart_intre_ei_douazeci_la_suta():
    sanse = probabilitati("@Maestra și @Programatorul, ce ziceți?", PERSONAJE)
    taciti = ["antreprenoarea", "clienta", "operatoarea"]

    assert sum(sanse[id_personaj] for id_personaj in taciti) == pytest.approx(0.2)
    assert sanse["clienta"] == pytest.approx(0.2 / 3)


def test_un_singur_mentionat_lasa_douazeci_la_suta_celorlalti_patru():
    """Exemplul din cerinta: 80% pentru cel chemat, 5% pentru fiecare dintre ceilalti patru."""
    sanse = probabilitati("@Programatorul e fezabil?", PERSONAJE)

    assert sanse["programatorul"] == 1.0
    assert sanse["maestra"] == pytest.approx(0.05)


def test_procentele_se_recalculeaza_cand_adaug_personaje():
    """Nimic nu e hardcodat pe consiliul de azi: la 9 personaje, cei 8 taciti impart tot 20%."""
    consiliu = _consiliu(9)

    sanse = probabilitati("@P4 ce zici?", consiliu)
    taciti = [id_personaj for id_personaj in consiliu if id_personaj != "p4"]

    assert sanse["p4"] == 1.0
    assert sum(sanse[id_personaj] for id_personaj in taciti) == pytest.approx(0.2)
    assert sanse["p1"] == pytest.approx(0.2 / 8)


def test_fara_mentiune_intra_tot_consiliul_cu_certitudine():
    """Sedinta convocata integral (SPEC §3): nu exista grup de 80%, deci nu se trage la sorti."""
    sanse = probabilitati("Cum arătăm prețurile?", PERSONAJE)

    assert set(sanse) == set(PERSONAJE)
    assert all(sansa == 1.0 for sansa in sanse.values())


def test_toti_mentionati_nu_lasa_pe_nimeni_de_tras_la_sorti():
    text = "@Maestra @Antreprenoarea @Clienta @Operatoarea @Programatorul, toți!"

    sanse = probabilitati(text, PERSONAJE)

    assert all(sansa == 1.0 for sansa in sanse.values())


def test_toti_sunt_intrebati_mentionatii_primii():
    """Chat natural: fiecare cantareste daca are ceva de zis, deci fiecare e intrebat."""
    ordine = ordinea_vorbitorilor("@Clienta și @Maestra, ce ziceți?", PERSONAJE)

    assert ordine[:2] == ["clienta", "maestra"]
    assert set(ordine) == set(PERSONAJE)


def test_fara_mentiune_ordinea_e_cea_din_fisier():
    assert ordinea_vorbitorilor("Cum arătăm prețurile?", PERSONAJE) == list(PERSONAJE)


def test_mentionatul_e_obligat_chiar_daca_sortii_cad_prost():
    """Mentiunea nu e o sansa, e o convocare - restul pierd toate cele patru aruncari."""
    obligati = obligati_sa_raspunda(
        "@Programatorul e fezabil?", PERSONAJE, sansa=_sorti(1.0, 1.0, 1.0, 1.0)
    )

    assert obligati == ["programatorul"]


def test_tacutul_care_castiga_aruncarea_e_obligat_sa_contribuie():
    """Asa nimeni nu e pus sa vorbeasca dupa ce tocmai a zis ca n-are nimic de adaugat."""
    obligati = obligati_sa_raspunda(
        "@Programatorul e fezabil?", PERSONAJE, sansa=_sorti(0.0, 1.0, 1.0, 1.0)
    )

    assert obligati == ["programatorul", "antreprenoarea"]


def test_fara_mentiune_nimeni_nu_e_obligat():
    """Nu exista grup chemat, deci fiecare decide singur daca are ceva de spus."""
    assert obligati_sa_raspunda("Cum arătăm prețurile?", PERSONAJE, sansa=_sorti(0.0)) == []


def test_pe_termen_lung_intrusii_aduc_o_cincime_de_replica():
    """Cei 20% se vad la mia de runde: in medie 0.2 obligati peste cei chemati."""
    zaruri = random.Random(2026).random
    intrusi = 0

    for _ in range(1000):
        obligati = obligati_sa_raspunda("@Maestra ce zici?", PERSONAJE, sansa=zaruri)
        intrusi += len(obligati) - 1

    assert 0.17 < intrusi / 1000 < 0.23
