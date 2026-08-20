"""Regula de tacere, verificata pe model, nu pe mecanica.

Mecanica lui PAS (`fara_pas`, evenimentul `tace`, cine e obligat) e testata determinist in
celelalte fisiere. Aici se verifica singurul lucru pe care mecanica nu-l poate garanta: ca
modelul chiar scrie PAS cand subiectul nu e al lui. Pe gemma4:e2b, cu regula scrisa permisiv
si pusa la mijlocul prompt-ului, rata masurata era 0 din 25 - reguli corecte in cod, invizibile
in practica.

Modelul e stochastic, deci fiecare caz se ruleaza de mai multe ori si se cere o majoritate,
nu unanimitate.
"""

import pytest

from ai_client import fara_pas, trimite_mesaj_stream
from main import INDEMN_OBLIGAT
from personaje import incarca_personaje
from rezumat import ANTET_REZUMAT

PERSONAJE = incarca_personaje()

RULARI = 3

SUBIECT_STRAIN = "Ce părere ai despre structura modulară a bibliotecii de coduri Miyuki?"
SUBIECT_PROPRIU = "Ce trebuie să văd prima dată pe pagina produsului ca să comand de pe Etsy?"


MEMORIE = f"""

{ANTET_REZUMAT}
Subiect: preview-ul de culoare și dimensiunile de la MVP
Decizii: Preview-ul se generează pe server; MVP-ul rămâne pe Delica 11/0.
Maestra: cere referință fizică lângă preview
Clienta: vrea repede, fără coduri
Programatorul: server, ca să nu se rescrie mai târziu"""


def _de_cate_ori_tace(
    id_personaj: str, intrebare: str, obligat: bool = False, memorie: str = ""
) -> int:
    """Cate din `RULARI` incercari se termina in tacere, pe acelasi drum ca serverul."""
    personaj = PERSONAJE[id_personaj]
    sistem = personaj["systemPrompt"] + memorie + (INDEMN_OBLIGAT if obligat else "")

    taceri = 0
    for _ in range(RULARI):
        bucati = trimite_mesaj_stream(
            intrebare,
            personaj["nume"],
            sistem=sistem,
            temperatura=personaj["temperaturaRecomandata"],
        )
        taceri += not "".join(fara_pas(bucati)).strip()
    return taceri


@pytest.mark.ollama
def test_personajul_tace_cand_subiectul_nu_e_al_lui():
    """Clienta n-are ce spune despre structura codului; fara asta, 80/20 nu se vede niciodata."""
    assert _de_cate_ori_tace("clienta", SUBIECT_STRAIN) > RULARI // 2


@pytest.mark.ollama
def test_personajul_vorbeste_cand_subiectul_e_al_lui():
    """Tacerea n-are voie sa se generalizeze: pe domeniul lui raspunde de fiecare data."""
    assert _de_cate_ori_tace("clienta", SUBIECT_PROPRIU) == 0


@pytest.mark.ollama
def test_chemarea_pe_nume_bate_regula_de_tacere():
    """Mentiunea e o convocare: `INDEMN_OBLIGAT` vine dupa regula de tacere si o invinge."""
    assert _de_cate_ori_tace("clienta", SUBIECT_STRAIN, obligat=True) == 0


@pytest.mark.ollama
def test_memoria_lunga_nu_amuteste_consiliul():
    """Rezumatul se lipeste la system prompt, unde e si regula de tacere: daca ajunge dupa ea,
    o intareste, iar personajele tac si cand n-ar trebui. Masurat, cu blocul pus gresit: 14/15."""
    assert _de_cate_ori_tace("clienta", SUBIECT_PROPRIU, memorie=MEMORIE) == 0


@pytest.mark.ollama
def test_chemarea_pe_nume_bate_si_memoria_lunga():
    """A doua jumatate a aceleiasi capcane: `INDEMN_OBLIGAT` ramane ultimul lucru din prompt."""
    assert _de_cate_ori_tace("clienta", SUBIECT_STRAIN, obligat=True, memorie=MEMORIE) <= RULARI // 2
