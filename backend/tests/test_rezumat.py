import istoric
import pytest
import rezumat


def _istoric_izolat(monkeypatch, tmp_path) -> str:
    """O conversatie proaspata, intr-un folder de date numai al testului."""
    monkeypatch.setattr(istoric, "DATE_DIR", tmp_path / "date")
    istoric.init_stocare()
    return istoric.creeaza_conversatie()["id"]


def _model_fals(monkeypatch, *raspunsuri: str) -> list[str]:
    """Secretarul, inlocuit: retine ce prompt a primit si da pe rand raspunsurile date."""
    cereri = []
    ramase = list(raspunsuri)

    def raspunde(mesaj, model=None, sistem=None, temperatura=None, max_tokeni=None):
        cereri.append(mesaj)
        return ramase.pop(0) if ramase else "Subiect: mărgele\nDecizii: nimic încă"

    monkeypatch.setattr(rezumat, "trimite_mesaj", raspunde)
    return cereri


def _model_care_crapa(monkeypatch) -> None:
    def crapa(*_, **__):
        raise RuntimeError("Ollama oprit")

    monkeypatch.setattr(rezumat, "trimite_mesaj", crapa)


def _umple(conversatie: str, cate: int, de_la: int = 0) -> None:
    """Mesaje numerotate, ca sa se vada in prompt exact care a ajuns la secretar."""
    for i in range(de_la, de_la + cate):
        istoric.salveaza_mesaj(
            conversatie,
            {"eu": False, "personajId": "maestra", "nume": "Maestra", "text": f"replica {i}"},
        )


def test_cat_incape_in_fereastra_nu_se_rezuma(monkeypatch, tmp_path):
    """Rezumatul e pentru ce s-a pierdut. Cat timp toata sedinta e in context, n-are ce pierde."""
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    cereri = _model_fals(monkeypatch)
    _umple(conversatie, istoric.MESAJE_IN_CONTEXT)

    assert rezumat.actualizeaza_rezumat(conversatie) is None
    assert cereri == []


def test_ce_iese_din_fereastra_intra_in_rezumat(monkeypatch, tmp_path):
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    cereri = _model_fals(monkeypatch, "Subiect: AB-ul\nDecizii: preview pe server")
    _umple(conversatie, istoric.MESAJE_IN_CONTEXT + rezumat.MESAJE_PE_REZUMAT)

    text = rezumat.actualizeaza_rezumat(conversatie)

    assert text == "Subiect: AB-ul\nDecizii: preview pe server"
    assert istoric.rezumatul(conversatie)[0] == text


def test_secretarul_vede_doar_replicile_iesite_din_fereastra(monkeypatch, tmp_path):
    """Ce e inca in contextul fiecaruia n-are de ce sa fie si in rezumat: s-ar auzi de doua ori."""
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    cereri = _model_fals(monkeypatch)
    _umple(conversatie, istoric.MESAJE_IN_CONTEXT + rezumat.MESAJE_PE_REZUMAT)

    rezumat.actualizeaza_rezumat(conversatie)

    assert "replica 0" in cereri[0]
    assert f"replica {rezumat.MESAJE_PE_REZUMAT - 1}" in cereri[0]
    assert f"replica {rezumat.MESAJE_PE_REZUMAT}" not in cereri[0]


def test_rezumatul_se_actualizeaza_incremental_nu_de_la_zero(monkeypatch, tmp_path):
    """Pe gemma4:e2b, rescrierea intregii sedinte la fiecare rundă ar fi un apel din ce in ce
    mai lung. Secretarul primeste rezumatul de pana acum plus doar ce tocmai a iesit."""
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    cereri = _model_fals(monkeypatch, "Subiect: prima parte")
    _umple(conversatie, istoric.MESAJE_IN_CONTEXT + rezumat.MESAJE_PE_REZUMAT)
    rezumat.actualizeaza_rezumat(conversatie)

    _umple(conversatie, rezumat.MESAJE_PE_REZUMAT, de_la=100)
    rezumat.actualizeaza_rezumat(conversatie)

    assert "Subiect: prima parte" in cereri[1]
    assert "replica 0" not in cereri[1]


def test_o_replica_nu_ajunge_de_doua_ori_la_secretar(monkeypatch, tmp_path):
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    cereri = _model_fals(monkeypatch)
    _umple(conversatie, istoric.MESAJE_IN_CONTEXT + 2 * rezumat.MESAJE_PE_REZUMAT)

    rezumat.actualizeaza_rezumat(conversatie)
    _umple(conversatie, rezumat.MESAJE_PE_REZUMAT, de_la=100)
    rezumat.actualizeaza_rezumat(conversatie)

    trimise = [linie for cerere in cereri for linie in cerere.splitlines()]
    assert trimise.count("Maestra: replica 0") == 1


def test_rezumatul_nu_costa_un_apel_la_fiecare_mesaj(monkeypatch, tmp_path):
    """Un apel in plus la fiecare mesaj s-ar simti pe un model local: se asteapta un lot."""
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    cereri = _model_fals(monkeypatch)

    mesaje = 3 * rezumat.MESAJE_PE_REZUMAT
    for i in range(istoric.MESAJE_IN_CONTEXT + mesaje):
        _umple(conversatie, 1, de_la=i)
        rezumat.actualizeaza_rezumat(conversatie)

    assert len(cereri) == mesaje // rezumat.MESAJE_PE_REZUMAT


def test_rezumatul_supravietuieste_repornirii(monkeypatch, tmp_path):
    """Decizia consiliului n-are voie sa se piarda la restart, ca si mesajele."""
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    _model_fals(monkeypatch, "Subiect: AB-ul\nDecizii: preview pe server")
    _umple(conversatie, istoric.MESAJE_IN_CONTEXT + rezumat.MESAJE_PE_REZUMAT)
    rezumat.actualizeaza_rezumat(conversatie)

    istoric.init_stocare()  # nu suprascrie ce exista deja

    assert istoric.rezumatul(conversatie)[0] == "Subiect: AB-ul\nDecizii: preview pe server"


def test_rezumatul_ramane_scurt_oricat_ar_scrie_modelul(monkeypatch, tmp_path):
    """Un rezumat cat o sedinta ar muta problema, nu ar rezolva-o: intra in contextul fiecaruia."""
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    lung = "\n".join(f"Maestra: poziția {i}" for i in range(30))
    _model_fals(monkeypatch, lung)
    _umple(conversatie, istoric.MESAJE_IN_CONTEXT + rezumat.MESAJE_PE_REZUMAT)

    text = rezumat.actualizeaza_rezumat(conversatie)

    assert len(text.splitlines()) <= rezumat.RANDURI_REZUMAT


def test_un_personaj_ramane_pe_o_singura_pozitie(monkeypatch, tmp_path):
    """Modelul repeta acelasi nume cu pozitii diferite; ramane ultima, cea de acum."""
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    _model_fals(monkeypatch, "Maestra: vrea AB fidel\nClienta: vrea repede\nMaestra: acceptă compromisul")
    _umple(conversatie, istoric.MESAJE_IN_CONTEXT + rezumat.MESAJE_PE_REZUMAT)

    text = rezumat.actualizeaza_rezumat(conversatie)

    assert text.splitlines() == ["Maestra: acceptă compromisul", "Clienta: vrea repede"]


def test_subiectul_si_deciziile_stau_in_fata_pozitiilor(monkeypatch, tmp_path):
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    _model_fals(monkeypatch, "Maestra: vrea AB fidel\nDecizii: preview pe server\nSubiect: AB-ul")
    _umple(conversatie, istoric.MESAJE_IN_CONTEXT + rezumat.MESAJE_PE_REZUMAT)

    text = rezumat.actualizeaza_rezumat(conversatie)

    assert text.splitlines() == ["Subiect: AB-ul", "Decizii: preview pe server", "Maestra: vrea AB fidel"]


def test_din_rezumat_cade_tot_ce_nu_e_subiect_decizie_sau_pozitie(monkeypatch, tmp_path):
    """Modelul isi anunta rezumatul si il incheie cu o concluzie; nici una nu e memorie."""
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    _model_fals(
        monkeypatch,
        "Iată rezumatul actualizat:\n\n* Subiect: AB-ul\n- Maestra: vrea AB fidel\n"
        "Sper că este de ajutor!\nCineva: nu e din consiliu",
    )
    _umple(conversatie, istoric.MESAJE_IN_CONTEXT + rezumat.MESAJE_PE_REZUMAT)

    text = rezumat.actualizeaza_rezumat(conversatie)

    assert text.splitlines() == ["Subiect: AB-ul", "Maestra: vrea AB fidel"]


def test_modelul_care_nu_raspunde_lasa_ce_tinea_minte_neatins(monkeypatch, tmp_path):
    """O eroare de model nu poate sterge memoria: lotul ramane nerezumat si se reia data viitoare."""
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    _model_fals(monkeypatch, "Subiect: AB-ul")
    _umple(conversatie, istoric.MESAJE_IN_CONTEXT + rezumat.MESAJE_PE_REZUMAT)
    rezumat.actualizeaza_rezumat(conversatie)
    _umple(conversatie, rezumat.MESAJE_PE_REZUMAT, de_la=100)

    _model_care_crapa(monkeypatch)

    assert rezumat.actualizeaza_rezumat(conversatie) is None
    assert istoric.rezumatul(conversatie) == ("Subiect: AB-ul", rezumat.MESAJE_PE_REZUMAT)


def test_un_raspuns_din_care_nu_ramane_nimic_nu_sterge_memoria(monkeypatch, tmp_path):
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    _model_fals(monkeypatch, "Subiect: AB-ul", "Îmi pare rău, nu pot ajuta.")
    _umple(conversatie, istoric.MESAJE_IN_CONTEXT + rezumat.MESAJE_PE_REZUMAT)
    rezumat.actualizeaza_rezumat(conversatie)
    _umple(conversatie, rezumat.MESAJE_PE_REZUMAT, de_la=100)

    assert rezumat.actualizeaza_rezumat(conversatie) is None
    assert istoric.rezumatul(conversatie)[0] == "Subiect: AB-ul"


def test_rezumatul_unei_conversatii_nu_se_amesteca_in_alta(monkeypatch, tmp_path):
    """Ca si mesajele: doua sedinte de consiliu diferite nu se aud una pe alta."""
    _istoric_izolat(monkeypatch, tmp_path)
    prima = istoric.creeaza_conversatie()["id"]
    a_doua = istoric.creeaza_conversatie()["id"]
    _model_fals(monkeypatch, "Subiect: AB-ul")
    _umple(prima, istoric.MESAJE_IN_CONTEXT + rezumat.MESAJE_PE_REZUMAT)
    rezumat.actualizeaza_rezumat(prima)

    assert istoric.rezumatul(a_doua) == ("", 0)
    assert rezumat.bloc_pentru_prompt(a_doua) == ""


@pytest.mark.ollama
def test_secretarul_scoate_un_rezumat_folosibil():
    """Singurul lucru pe care testele deterministe nu-l pot garanta: ca un model de 2B chiar
    scoate subiectul, decizia si pozitiile, nu un eseu."""
    sedinta = [
        {"eu": True, "nume": "Simona", "text": "Merită să simulăm AB-ul pe poză?"},
        {"nume": "Maestra", "text": "AB-ul nu se poate simula fidel pe o mărgea fotografiată."},
        {"nume": "Clienta", "text": "Vreau doar să văd cum arată în altă culoare, să comand."},
        {"eu": True, "nume": "Simona", "text": "Facem preview-ul pe server sau în browser?"},
        {"nume": "Antreprenoarea", "text": "Pe server, ca să nu poată fi manipulat din client."},
        {"nume": "Programatorul", "text": "De acord, rămâne pe server. Închidem subiectul."},
    ]
    nume = {mesaj["nume"] for mesaj in sedinta}

    text = rezumat.cere_rezumat("", sedinta, nume)
    randuri = text.splitlines()

    assert 2 <= len(randuri) <= rezumat.RANDURI_REZUMAT
    assert randuri[0].startswith("Subiect:")
    assert any(rand.startswith("Decizii:") for rand in randuri)
    assert all(rand.split(":")[0] in {"Subiect", "Decizii"} | nume for rand in randuri)


def test_memoria_e_marcata_ca_sa_nu_fie_confundata_cu_o_replica(monkeypatch, tmp_path):
    """Fara antet, un model de 2B raspunde rezumatului ca si cum tocmai l-ar fi spus cineva."""
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    istoric.salveaza_rezumat(conversatie, "Subiect: AB-ul", 6)

    bloc = rezumat.bloc_pentru_prompt(conversatie)

    assert rezumat.ANTET_REZUMAT in bloc
    assert bloc.index(rezumat.ANTET_REZUMAT) < bloc.index("Subiect: AB-ul")


def test_o_sedinta_scurta_nu_plateste_nimic_pentru_memoria_lunga(monkeypatch, tmp_path):
    """Cat timp toata discutia incape in fereastra, prompt-ul ramane exact cel dinainte de M12."""
    conversatie = _istoric_izolat(monkeypatch, tmp_path)
    _umple(conversatie, 3)

    assert rezumat.bloc_pentru_prompt(conversatie) == ""
