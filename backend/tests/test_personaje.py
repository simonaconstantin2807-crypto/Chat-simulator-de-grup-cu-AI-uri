import random

from personaje import (
    gaseste_mentiuni,
    incarca_personaje,
    obligati_sa_raspunda,
    ordinea_vorbitorilor,
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


def test_regula_de_tacere_vine_dupa_toate_celelalte_reguli():
    """Pozitia conteaza pe un model de 2B: pusa intre reguli, se pierde (masurat 0 taceri din 25)."""
    for personaj in PERSONAJE.values():
        prompt = personaj["systemPrompt"]
        ultima_regula = prompt.rindex("\n- ")

        assert prompt.index("PAS") > ultima_regula, f"{personaj['nume']} o are prea devreme"


def test_fiecare_isi_stie_domeniul_din_rol():
    """Criteriul de tacere e domeniul concret din `rol`, nu o judecata abstracta.

    Un model de 2B nu poate cantari daca are o opinie fundamentata; poate compara un subiect
    cu o eticheta scurta.
    """
    for personaj in PERSONAJE.values():
        assert f"Domeniul tău: {personaj['rol']}." in personaj["systemPrompt"]


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
    """Mentiunea e o convocare: cei chemati intra fara sa se arunce nimic pentru ei."""
    obligati = obligati_sa_raspunda(
        "@Maestra și @Programatorul, ce ziceți?", PERSONAJE, sansa=_sorti(1.0, 1.0, 1.0)
    )

    assert obligati == ["maestra", "programatorul"]


def test_nementionatii_impart_intre_ei_douazeci_la_suta():
    """Doi chemati, trei tacuti: pragul fiecarui tacut e 0.2/3, nu 0.2."""
    text = "@Maestra și @Programatorul, ce ziceți?"
    prag = 0.2 / 3

    sub_prag = obligati_sa_raspunda(text, PERSONAJE, sansa=_sorti(prag - 0.001, 1.0, 1.0))
    peste_prag = obligati_sa_raspunda(text, PERSONAJE, sansa=_sorti(prag + 0.001, 1.0, 1.0))

    assert sub_prag == ["maestra", "programatorul", "antreprenoarea"]
    assert peste_prag == ["maestra", "programatorul"]


def test_un_singur_mentionat_lasa_douazeci_la_suta_celorlalti_patru():
    """Exemplul din cerinta: cel chemat raspunde sigur, fiecare dintre ceilalti patru are 5%."""
    text = "@Programatorul e fezabil?"

    sub_prag = obligati_sa_raspunda(text, PERSONAJE, sansa=_sorti(0.049, 1.0, 1.0, 1.0))
    peste_prag = obligati_sa_raspunda(text, PERSONAJE, sansa=_sorti(0.051, 1.0, 1.0, 1.0))

    assert sub_prag == ["programatorul", "antreprenoarea"]
    assert peste_prag == ["programatorul"]


def test_procentele_se_recalculeaza_cand_adaug_personaje():
    """Nimic nu e hardcodat pe consiliul de azi: la 9 personaje, cei 8 taciti impart tot 20%."""
    consiliu = _consiliu(9)
    prag = 0.2 / 8

    ceilalti = [1.0] * 7
    sub_prag = obligati_sa_raspunda("@P4 ce zici?", consiliu, sansa=_sorti(prag - 0.001, *ceilalti))
    peste_prag = obligati_sa_raspunda("@P4 ce zici?", consiliu, sansa=_sorti(prag + 0.001, *ceilalti))

    assert sub_prag == ["p4", "p1"]
    assert peste_prag == ["p4"]


def test_toti_mentionati_nu_lasa_pe_nimeni_de_tras_la_sorti():
    text = "@Maestra @Antreprenoarea @Clienta @Operatoarea @Programatorul, toți!"

    # `_sorti()` fara valori crapa daca se arunca vreun zar - deci nici nu se arunca.
    obligati = obligati_sa_raspunda(text, PERSONAJE, sansa=_sorti())

    assert set(obligati) == set(PERSONAJE)


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


def test_fara_mentiune_e_obligat_unul_singur_tras_la_sorti():
    """Nimeni chemat inseamna ca toti pot scrie PAS si raman fara raspuns pe ecran (M9).

    Sortii scot exact un vorbitor obligat; ceilalti isi pastreaza dreptul de a tacea.
    """
    text = "Cum arătăm prețurile?"
    consiliu = list(PERSONAJE)

    assert obligati_sa_raspunda(text, PERSONAJE, sansa=_sorti(0.0)) == [consiliu[0]]
    assert obligati_sa_raspunda(text, PERSONAJE, sansa=_sorti(0.999)) == [consiliu[-1]]


def test_aruncarea_maxima_nu_iese_din_consiliu():
    """`random.random()` nu da niciodata 1.0, dar un fals de test da - runda nu are voie sa crape."""
    assert obligati_sa_raspunda("Cum arătăm prețurile?", PERSONAJE, sansa=_sorti(1.0)) == [
        list(PERSONAJE)[-1]
    ]


def test_pe_termen_lung_intrusii_aduc_o_cincime_de_replica():
    """Cei 20% se vad la mia de runde: in medie 0.2 obligati peste cei chemati."""
    zaruri = random.Random(2026).random
    intrusi = 0

    for _ in range(1000):
        obligati = obligati_sa_raspunda("@Maestra ce zici?", PERSONAJE, sansa=zaruri)
        intrusi += len(obligati) - 1

    assert 0.17 < intrusi / 1000 < 0.23
