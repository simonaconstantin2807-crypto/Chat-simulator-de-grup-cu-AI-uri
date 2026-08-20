import random

from personaje import (
    VORBITORI_PE_RUNDA,
    alege_vorbitorul,
    chemati_fara_raspuns,
    gaseste_mentiuni,
    incarca_personaje,
    obligati_sa_raspunda,
    profil_public,
    vorbitorii_rundei,
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


def test_fiecare_isi_stie_subiectele_lui():
    """Criteriul de tacere e o lista de subiecte concrete, nu o judecata abstracta.

    Un model de 2B nu poate cantari daca are o opinie fundamentata; poate compara mesajul cu
    niște subiecte numite. Eticheta scurta de la M10 („Domeniul tău: <rol>") era prea vaga:
    Clienta tacea 2 din 10 la intrebari strict tehnice, iar cu subiectele numite 6 din 10.
    """
    for personaj in PERSONAJE.values():
        subiecte = personaj["systemPrompt"].split("Vorbești despre:")[-1].splitlines()[0]

        assert len(subiecte.split(",")) >= 3, f"{personaj['nume']} n-are subiecte destule"


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
    vorbitori = vorbitorii_rundei(
        "@Maestra și @Programatorul, ce ziceți?", PERSONAJE, sansa=_sorti(1.0)
    )

    assert vorbitori == ["maestra", "programatorul"]


def test_nementionatii_impart_intre_ei_douazeci_la_suta():
    """Sansa ca cineva nechemat sa intre in runda e 20%, o singura aruncare pentru toti."""
    text = "@Maestra și @Programatorul, ce ziceți?"

    sub_prag = vorbitorii_rundei(text, PERSONAJE, sansa=_sorti(0.199, 0.0))
    peste_prag = vorbitorii_rundei(text, PERSONAJE, sansa=_sorti(0.201))

    assert sub_prag == ["maestra", "programatorul", "antreprenoarea"]
    assert peste_prag == ["maestra", "programatorul"]


def test_intra_un_singur_nementionat_nu_toti_cei_carora_le_iese():
    """Runda nu creste la loc la patru-cinci guri: peste cei chemati intra cel mult unul."""
    vorbitori = vorbitorii_rundei("@Programatorul e fezabil?", PERSONAJE, sansa=_sorti(0.0, 0.0))

    assert len(vorbitori) == 2


def test_procentele_se_recalculeaza_cand_adaug_personaje():
    """Nimic nu e hardcodat pe consiliul de azi: si la 9 personaje, tot 20% intra neinvitat.

    Aruncarea fiind una singura pentru toti, procentul nu mai depinde de cati sunt - inainte
    se imparteau `PARTEA_NEMENTIONATILOR` intre ei, tocmai ca sa iasa acelasi lucru.
    """
    consiliu = _consiliu(9)

    sub_prag = vorbitorii_rundei("@P4 ce zici?", consiliu, sansa=_sorti(0.199, 0.0))
    peste_prag = vorbitorii_rundei("@P4 ce zici?", consiliu, sansa=_sorti(0.201))

    assert sub_prag == ["p4", "p1"]
    assert peste_prag == ["p4"]


def test_toti_mentionati_nu_lasa_pe_nimeni_de_tras_la_sorti():
    text = "@Maestra @Antreprenoarea @Clienta @Operatoarea @Programatorul, toți!"

    vorbitori = vorbitorii_rundei(text, PERSONAJE, sansa=_sorti(0.0))

    assert set(vorbitori) == set(PERSONAJE)


def test_fara_mentiune_vorbesc_doi_sau_trei_nu_tot_consiliul():
    """Miezul lui M15: la o intrebare larga, criteriul de domeniu se potriveste pentru aproape
    toti, deci PAS n-are ce filtra. Selectia tine runda scurta in locul lui."""
    minim, maxim = VORBITORI_PE_RUNDA
    zaruri = random.Random(2026).random

    marimi = {len(vorbitorii_rundei("Cum arătăm prețurile?", PERSONAJE, sansa=zaruri)) for _ in range(200)}

    assert marimi == set(range(minim, maxim + 1))


def test_fara_mentiune_nimeni_nu_e_ales_de_doua_ori():
    vorbitori = vorbitorii_rundei("Cum arătăm prețurile?", PERSONAJE, sansa=random.Random(7).random)

    assert len(set(vorbitori)) == len(vorbitori)


def test_un_consiliu_mai_mic_decat_plafonul_nu_blocheaza_runda():
    """Cu doua personaje nu se pot alege trei - runda se multumeste cu cati sunt."""
    consiliu = _consiliu(2)

    vorbitori = vorbitorii_rundei("Cum arătăm prețurile?", consiliu, sansa=_sorti(1.0, 0.0, 0.0))

    assert set(vorbitori) == set(consiliu)


def test_mentionatul_e_obligat_chiar_daca_sortii_cad_prost():
    """Mentiunea nu e o sansa, e o convocare."""
    text = "@Programatorul e fezabil?"
    vorbitori = vorbitorii_rundei(text, PERSONAJE, sansa=_sorti(1.0))

    assert obligati_sa_raspunda(text, vorbitori, PERSONAJE, sansa=_sorti()) == ["programatorul"]


def test_cel_intrat_pe_cei_douazeci_la_suta_e_obligat_si_el():
    """Pe el l-au adus sortii, nu subiectul: daca l-am lasa sa se filtreze singur, n-ar mai fi
    nicio diferenta fata de a-l intreba degeaba."""
    text = "@Programatorul e fezabil?"
    vorbitori = vorbitorii_rundei(text, PERSONAJE, sansa=_sorti(0.0, 0.0))

    obligati = obligati_sa_raspunda(text, vorbitori, PERSONAJE, sansa=_sorti())

    assert obligati == vorbitori and len(obligati) == 2


def test_fara_mentiune_e_obligat_unul_singur_dintre_cei_alesi():
    """Nimeni chemat inseamna ca toti pot scrie PAS si raman fara raspuns pe ecran (M9).

    Sortii scot exact un vorbitor obligat, si numai dintre cei alesi - unul neales n-ar fi
    intrebat niciodata, deci obligatia lui n-ar ajunge nicaieri.
    """
    text = "Cum arătăm prețurile?"
    vorbitori = ["maestra", "clienta", "operatoarea"]

    assert obligati_sa_raspunda(text, vorbitori, PERSONAJE, sansa=_sorti(0.0)) == ["maestra"]
    assert obligati_sa_raspunda(text, vorbitori, PERSONAJE, sansa=_sorti(0.999)) == ["operatoarea"]


def test_ceilalti_alesi_isi_pastreaza_dreptul_de_a_tacea():
    """PAS ramane plasa de siguranta pentru intrebarea ingusta, pe care selectia n-o poate judeca."""
    vorbitori = ["maestra", "clienta", "operatoarea"]

    obligati = obligati_sa_raspunda("Cum arătăm prețurile?", vorbitori, PERSONAJE, sansa=_sorti(0.0))

    assert len(obligati) == 1


def test_aruncarea_maxima_nu_iese_din_consiliu():
    """`random.random()` nu da niciodata 1.0, dar un fals de test da - runda nu are voie sa crape."""
    vorbitori = ["maestra", "clienta"]

    assert obligati_sa_raspunda("Cum arătăm?", vorbitori, PERSONAJE, sansa=_sorti(1.0)) == ["clienta"]


def test_pe_termen_lung_intrusii_aduc_o_cincime_de_replica():
    """Cei 20% se vad la mia de runde: in medie 0.2 vorbitori peste cei chemati."""
    zaruri = random.Random(2026).random
    intrusi = 0

    for _ in range(1000):
        intrusi += len(vorbitorii_rundei("@Maestra ce zici?", PERSONAJE, sansa=zaruri)) - 1

    assert 0.17 < intrusi / 1000 < 0.23


def test_runda_pornita_de_mine_costa_mai_putine_apeluri_decat_consiliul_intreg():
    """Castigul practic al selectiei: 2-3 apeluri la model in loc de 5, deci runda se termina
    vizibil mai repede."""
    zaruri = random.Random(11).random

    cei_mai_multi = max(
        len(vorbitorii_rundei("Cum arătăm prețurile?", PERSONAJE, sansa=zaruri)) for _ in range(200)
    )

    assert cei_mai_multi < len(PERSONAJE)


# ---------- conversatia care continua singura ----------


def _replica_de_la(id_personaj: str, text: str) -> dict:
    return {"eu": False, "personajId": id_personaj, "nume": id_personaj.capitalize(), "text": text}


def _mesajul_meu(text: str) -> dict:
    return {"eu": True, "nume": "Simona", "text": text}


def test_cel_chemat_care_n_a_ajuns_la_cuvant_ramane_asteptat():
    mesaje = [_mesajul_meu("@Maestra ce zici de AB?"), _replica_de_la("clienta", "eu zic că da")]

    assert chemati_fara_raspuns(mesaje, PERSONAJE) == ["maestra"]


def test_chemarea_se_stinge_cand_cel_chemat_vorbeste():
    mesaje = [
        _mesajul_meu("@Maestra ce zici de AB?"),
        _replica_de_la("maestra", "AB-ul nu se poate simula"),
    ]

    assert chemati_fara_raspuns(mesaje, PERSONAJE) == []


def test_chemarea_facuta_de_un_personaj_conteaza_la_fel_ca_a_mea():
    mesaje = [_replica_de_la("maestra", "aici o întreb pe @Operatoarea")]

    assert chemati_fara_raspuns(mesaje, PERSONAJE) == ["operatoarea"]


def test_cine_se_cheama_pe_sine_nu_se_asteapta_pe_sine():
    """Altfel un personaj care isi scrie numele si-ar da singur prioritate la replica urmatoare."""
    mesaje = [_replica_de_la("maestra", "cum spuneam eu, @Maestra, mai devreme")]

    assert chemati_fara_raspuns(mesaje, PERSONAJE) == []


def test_optzeci_la_suta_din_replicile_libere_merg_la_cei_chemati():
    """Regula 80/20 din sesiunea 11: vorbeste unul singur, cel mai probabil unul dintre chemati."""
    sub_prag = alege_vorbitorul(PERSONAJE, ["maestra"], sansa=_sorti(0.79, 0.0))
    peste_prag = alege_vorbitorul(PERSONAJE, ["maestra"], sansa=_sorti(0.81, 0.0))

    assert sub_prag == "maestra"
    assert peste_prag == "antreprenoarea"  # primul dintre ceilalti


def test_cine_tocmai_a_vorbit_nu_ia_din_nou_cuvantul():
    """Doua replici la rand de la acelasi personaj n-ar mai fi o conversatie de grup."""
    consiliu = list(PERSONAJE)

    ales = alege_vorbitorul(PERSONAJE, [], exclusi=[consiliu[0]], sansa=_sorti(0.0))

    assert ales == consiliu[1]


def test_fara_niciun_chemat_alegerea_e_dintre_toti_ceilalti():
    """Nimeni nefiind asteptat, nu se mai imparte nimic: o singura aruncare, pentru vorbitor."""
    consiliu = list(PERSONAJE)

    assert alege_vorbitorul(PERSONAJE, [], sansa=_sorti(0.0)) == consiliu[0]
    assert alege_vorbitorul(PERSONAJE, [], sansa=_sorti(0.999)) == consiliu[-1]


def test_cand_toti_ceilalti_au_fost_incercati_vorbeste_cel_chemat():
    """Ultimul ramas nu mai are cu cine imparti procentele - nu se arunca niciun zar pentru grup."""
    ceilalti = [p for p in PERSONAJE if p != "maestra"]

    ales = alege_vorbitorul(PERSONAJE, ["maestra"], exclusi=ceilalti, sansa=_sorti(0.0))

    assert ales == "maestra"


def test_nu_mai_e_nimeni_de_ales_cand_toti_au_incercat():
    assert alege_vorbitorul(PERSONAJE, [], exclusi=list(PERSONAJE), sansa=_sorti()) is None


def test_procentul_de_optzeci_ramane_valid_cand_adaug_personaje():
    consiliu = _consiliu(9)

    sub_prag = alege_vorbitorul(consiliu, ["p7"], sansa=_sorti(0.79, 0.0))
    peste_prag = alege_vorbitorul(consiliu, ["p7"], sansa=_sorti(0.81, 0.0))

    assert sub_prag == "p7"
    assert peste_prag == "p1"


def test_pe_termen_lung_chematii_iau_patru_replici_din_cinci():
    zaruri = random.Random(2026).random
    ai_chematului = 0

    for _ in range(1000):
        if alege_vorbitorul(PERSONAJE, ["maestra"], sansa=zaruri) == "maestra":
            ai_chematului += 1

    assert 0.77 < ai_chematului / 1000 < 0.83


def test_fiecare_scrie_cu_alta_energie():
    """intr-un grup real unul scrie trei cuvinte și altul un paragraf. Regula de lungime e
    parte din voce, deci difera de la personaj la personaj."""
    reguli = {p["systemPrompt"].split("Reguli:")[1].splitlines()[1] for p in PERSONAJE.values()}

    assert len(reguli) == len(PERSONAJE)
