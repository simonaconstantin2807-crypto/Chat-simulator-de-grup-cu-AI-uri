from personaje import alege_destinatarii, gaseste_mentiuni, incarca_personaje, profil_public

PERSONAJE = incarca_personaje()


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


def test_fara_mentiune_raspunde_tot_consiliul():
    assert alege_destinatarii("Cum arătăm prețurile?", PERSONAJE) == list(PERSONAJE)


def test_cu_mentiune_raspunde_doar_cine_e_chemat():
    assert alege_destinatarii("@Programatorul e fezabil?", PERSONAJE) == ["programatorul"]
