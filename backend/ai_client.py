import re
from typing import Iterator

import ollama

MODEL_IMPLICIT = "gemma4:e2b"

# Cat timp tine Ollama modelul in memorie intre mesaje. Implicit sunt 5 minute, iar dupa ele
# urmatorul mesaj asteapta ~13s doar reincarcarea de pe disc. O ora acopera o sesiune de
# consiliu fara reincarcari. Recontrolat pe 19 august 2026, dupa trecerea inapoi pe GPU:
# 12.22s la rece vs 0.87s la cald, deci intarzierea evitata e aceeasi. Cat sta incarcat, ocupa
# 1.59 GB din cei 6 GB de VRAM (nu 5.57 GB din RAM-ul de sistem, ca pe vremea rularii pe CPU),
# asa ca ora asta nu mai apasa pe memorie.
KEEP_ALIVE = "1h"

# gemma4:e2b e un model "thinking": implicit isi scrie intai rationamentul intern - sute de
# tokeni pe care utilizatoarea nu-i vede, dar ii asteapta - si abia apoi raspunsul. Oprit,
# primul cuvant vizibil apare in ~3s in loc de ~17s (masurat pe aceeasi intrebare).
GANDIRE = False

# Plafonul opreste derapajele rare, nu raspunsul normal. De la M14, fiecare personaj are alta
# regula de lungime in system prompt, deci si alta mediana - masurat pe gemma4:e2b, pe replici
# de pe domeniul propriu, 20 august 2026: Operatoarea si Clienta 9 tokeni, Programatorul 52,
# Antreprenoarea 56, Maestra 93. Cel mai lung raspuns vazut: 114. Nimic nu s-a terminat brusc,
# deci 200 are inca loc si pentru cea mai vorbareata.
MAX_TOKENI = 200


# Cuvantul prin care un personaj spune ca n-are nimic de adaugat. Nu ajunge niciodata pe ecran:
# tacerea lui e raspunsul. Regula e in system prompt-uri, in personaje.json.
SEMNAL_PAS = "PAS"


# Semnalul lipit in fata unei replici adevarate: „PAS. Trebuie sa lansam cu un singur plan."
# gemma4:e2b scrie uneori si semnalul, si raspunsul - masurat la M14, 4 din 12 replici pe
# domeniul propriu. Se cere punctuatie dupa el, ca „Pas cu pas" sa ramana intreg, si majuscule,
# pentru ca doar asa il scrie cand asculta de regula.
TIPAR_PAS_IN_FATA = re.compile(rf"^{SEMNAL_PAS}[.!…:]+\s*")


# Sub atatea litere, un raspuns nu mai e o contributie la discutie, ci un ecou.
#
# Fiecare raspunde ultimei replici din chat (M8), iar cand aceea e o intrebare, modelul mic o ia
# ca pe o intrebare adresata lui si raspunde literal, intr-un cuvant: Operatoarea a intrebat
# „Cat de multe coduri Miyuki sunt necesare pentru o forma data?", iar Clienta a raspuns „Multe."
# Regula ramane cum e - tot ea produce si replicile bune, cele care decurg din ce s-a zis inainte
# - deci se taie rezultatul, nu regula.
#
# Doua exceptii, pentru ca ar taia tocmai vocile care vorbesc scurt din fire: o cifra („~30g" de
# la Operatoarea) si o chemare („@Maestra?", care porneste replica altcuiva) sunt contributii
# oricat de scurte ar fi.
LITERE_MINIME_REPLICA = 15


def este_pas(text: str) -> bool:
    return text.strip().strip(".!…").upper() == SEMNAL_PAS


def e_contributie(text: str) -> bool:
    """Daca replica duce ceva mai departe sau e doar un ecou al intrebarii dinainte."""
    curat = text.strip()
    if len(curat) >= LITERE_MINIME_REPLICA:
        return True
    return "@" in curat or any(litera.isdigit() for litera in curat)


def fara_pas(bucati: Iterator[str]) -> Iterator[str]:
    """Retine inceputul raspunsului cat sa distinga o abtinere de o replica adevarata.

    Cat timp textul strans ar putea fi inca doar `PAS`, nu iese nimic. La prima litera in
    plus ("Pas cu pas...") se elibereaza tot si restul curge normal, ca sa nu se piarda
    efectul de scriere in timp real - mai putin semnalul, daca modelul l-a scris si pe el
    inaintea replicii.
    """
    retinut = ""
    for bucata in bucati:
        retinut += bucata
        # Punctuatia nu conteaza la numaratoare: "Pas." e tot o abtinere, "Pas cu" nu mai e.
        if len(retinut.strip().strip(".!…")) > len(SEMNAL_PAS):
            eliberat = TIPAR_PAS_IN_FATA.sub("", retinut.lstrip(), count=1)
            if eliberat:
                yield eliberat
            break
    else:
        if retinut.strip() and not este_pas(retinut):
            yield retinut
        return

    for bucata in bucati:
        yield bucata


def fara_replici_degenerate(bucati: Iterator[str]) -> Iterator[str]:
    """Inghite replica prea scurta ca sa fie o contributie, pe aceeasi cale ca `PAS`: tacere.

    Se retine inceputul cat sa se stie de care e. La prima litera peste `LITERE_MINIME_REPLICA`
    - sau la prima cifra, sau la primul `@` - se elibereaza tot si restul curge normal. Daca
    fluxul se termina inainte, nu iese nimic.

    Filtrarea e in stream, nu dupa ce s-a strans raspunsul intreg, din acelasi motiv ca la
    `fara_pas`: altfel „Multe." ar aparea si ar disparea sub ochii utilizatoarei.
    """
    retinut = ""
    for bucata in bucati:
        retinut += bucata
        if e_contributie(retinut):
            yield retinut
            break
    else:
        return

    for bucata in bucati:
        yield bucata


def elimina_prefix_nume(text: str, nume: str) -> str:
    prefix = f"{nume}:"
    if text.strip().lower().startswith(prefix.lower()):
        return text.split(":", 1)[1].lstrip()
    return text


def _curata_stream(bucati: Iterator[str], nume: str) -> Iterator[str]:
    prag = len(nume) + 2
    buffer = ""
    for bucata in bucati:
        buffer += bucata
        if ":" in buffer or len(buffer) > prag:
            rezultat = elimina_prefix_nume(buffer, nume)
            if rezultat:
                yield rezultat
            break
    else:
        if buffer:
            yield elimina_prefix_nume(buffer, nume)
        return

    for bucata in bucati:
        yield bucata


def _construieste_cerere(
    mesaj: str,
    sistem: str | None,
    temperatura: float | None,
    context: list[dict] | None = None,
    max_tokeni: int = MAX_TOKENI,
) -> dict:
    mesaje = []
    if sistem:
        mesaje.append({"role": "system", "content": sistem})
    # Istoricul intra intre system prompt si mesajul curent, ca modelul sa stie ce s-a discutat.
    mesaje.extend(context or [])
    mesaje.append({"role": "user", "content": mesaj})

    # Aici a stat `num_gpu: 0`, pentru ca pe Ollama 0.32.9 gemma4:e2b crapa la incarcarea pe GPU
    # (llama-server iesea cu 0xc0000409 si "CUDA error: shared object initialization failed",
    # indiferent de num_ctx). In Ollama 0.32.14 parea rezolvat, verificat pe 19 august 2026 cu
    # acelasi driver NVIDIA 610.88 si RTX 4050 Laptop 6 GB: modelul intra intreg in VRAM (1.59 GB,
    # 100% GPU), raspunde corect, 84.5 tokeni/s, incarcare 12-16s.
    #
    # Recontrolat pe 20 august 2026: nu e rezolvat, e doar rar. Din patru incarcari la rece intr-o
    # zi, una a picat cu exact aceeasi eroare (14:15:57 in %LOCALAPPDATA%\Ollama\server.log), iar
    # incercarea urmatoare a mers. De-asta exista `_bucati_cu_reincercare`, nu pentru ca ar fi
    # nevoie de num_gpu inapoi: cand modelul chiar se incarca, merge pe GPU cum scrie mai sus.
    #
    # Sa nu se reintroduca workaround-ul: pe CPU acelasi model cerea 5.57 GB in RAM de sistem
    # (din 15.19 GB totali) si se incarca in ~98s, iar cand RAM-ul era ocupat de alte aplicatii
    # alocarea esua - "unable to allocate CPU buffer" - si llama-server crapa in rafala (4 crash-uri
    # in 47s pe 13 august, 2 pe 17 august), cu cate un dump de ~228 MB de fiecare data.
    optiuni = {"num_predict": max_tokeni}
    if temperatura is not None:
        optiuni["temperature"] = temperatura

    return {"messages": mesaje, "options": optiuni, "keep_alive": KEEP_ALIVE, "think": GANDIRE}


def preincarca(model: str = MODEL_IMPLICIT) -> None:
    """Aduce modelul in memorie inainte de primul mesaj, ca sa nu astepte utilizatoarea incarcarea."""
    ollama.chat(
        model=model,
        messages=[{"role": "user", "content": "ok"}],
        options={"num_predict": 1},
        keep_alive=KEEP_ALIVE,
        think=GANDIRE,
    )


def trimite_mesaj(
    mesaj: str,
    model: str = MODEL_IMPLICIT,
    sistem: str | None = None,
    temperatura: float | None = None,
    context: list[dict] | None = None,
    max_tokeni: int = MAX_TOKENI,
) -> str:
    """Un raspuns intreg, nu in bucati: pentru ce nu ajunge pe ecran cat se scrie.

    `max_tokeni` e aici pentru rezumatul din `rezumat.py`, care are nevoie de mai mult decat
    cele 1-3 propozitii ale unei replici.
    """
    cerere = _construieste_cerere(mesaj, sistem, temperatura, context, max_tokeni)
    raspuns = ollama.chat(model=model, **cerere)
    return raspuns["message"]["content"]


def _bucati_cu_reincercare(model: str, cerere: dict) -> Iterator[str]:
    """Bucatile raspunsului, cu inca o incercare daca modelul crapa inainte de primul cuvant.

    Incarcarea la rece a lui gemma4:e2b pe GPU esueaza din cand in cand, iar urmatoarea
    incercare merge. Masurat pe 20 august 2026, in `%LOCALAPPDATA%\\Ollama\\server.log`: patru
    incarcari la rece, una picata cu `llama-server terminated, exit status 0xc0000409` si
    „CUDA error: shared object initialization failed" - aceeasi eroare pentru care exista
    workaround-ul `num_gpu: 0`, despre care se credea (si scrie mai jos) ca e rezolvata in
    Ollama 0.32.14. E doar mult mai rara, nu disparuta. Fara reincercare, prima intrebare de
    dupa o pauza mai lunga se alege din cand in cand cu o bula rosie.

    Se reincearca numai cat timp n-a iesit nimic: daca modelul cade dupa ce a scris ceva, a
    doua incercare ar dubla textul in bula, iar utilizatoarea a si citit prima jumatate.
    """
    for ultima_incercare in (False, True):
        a_pornit = False
        try:
            for bucata in ollama.chat(model=model, stream=True, **cerere):
                a_pornit = True
                yield bucata["message"]["content"]
            return
        except Exception as eroare:
            if ultima_incercare or a_pornit:
                raise
            print(f"[avertisment] modelul n-a pornit, se mai incearca o data: {eroare}")


def trimite_mesaj_stream(
    mesaj: str,
    nume_personaj: str,
    model: str = MODEL_IMPLICIT,
    sistem: str | None = None,
    temperatura: float | None = None,
    context: list[dict] | None = None,
) -> Iterator[str]:
    cerere = _construieste_cerere(mesaj, sistem, temperatura, context)
    yield from _curata_stream(_bucati_cu_reincercare(model, cerere), nume_personaj)
