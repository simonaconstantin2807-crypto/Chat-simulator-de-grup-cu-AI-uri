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

# Personajele au in system prompt regula "1-3 propozitii scurte". Plafonul opreste derapajele
# rare, nu raspunsul normal, care sta pe la 40-60 de tokeni.
MAX_TOKENI = 200


# Cuvantul prin care un personaj spune ca n-are nimic de adaugat. Nu ajunge niciodata pe ecran:
# tacerea lui e raspunsul. Regula e in system prompt-uri, in personaje.json.
SEMNAL_PAS = "PAS"


def este_pas(text: str) -> bool:
    return text.strip().strip(".!…").upper() == SEMNAL_PAS


def fara_pas(bucati: Iterator[str]) -> Iterator[str]:
    """Retine inceputul raspunsului cat sa distinga o abtinere de o replica adevarata.

    Cat timp textul strans ar putea fi inca doar `PAS`, nu iese nimic. La prima litera in
    plus ("Pas cu pas...") se elibereaza tot si restul curge normal, ca sa nu se piarda
    efectul de scriere in timp real.
    """
    retinut = ""
    for bucata in bucati:
        retinut += bucata
        # Punctuatia nu conteaza la numaratoare: "Pas." e tot o abtinere, "Pas cu" nu mai e.
        if len(retinut.strip().strip(".!…")) > len(SEMNAL_PAS):
            yield retinut
            break
    else:
        if retinut.strip() and not este_pas(retinut):
            yield retinut
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
) -> dict:
    mesaje = []
    if sistem:
        mesaje.append({"role": "system", "content": sistem})
    # Istoricul intra intre system prompt si mesajul curent, ca modelul sa stie ce s-a discutat.
    mesaje.extend(context or [])
    mesaje.append({"role": "user", "content": mesaj})

    # Aici a stat `num_gpu: 0`, pentru ca pe Ollama 0.32.9 gemma4:e2b crapa la incarcarea pe GPU
    # (llama-server iesea cu 0xc0000409 si "CUDA error: shared object initialization failed",
    # indiferent de num_ctx). Bug-ul e rezolvat in Ollama 0.32.14, verificat pe 19 august 2026 cu
    # acelasi driver NVIDIA 610.88 si RTX 4050 Laptop 6 GB: modelul intra intreg in VRAM (1.59 GB,
    # 100% GPU), raspunde corect, 84.5 tokeni/s, incarcare 12-16s.
    #
    # Sa nu se reintroduca workaround-ul: pe CPU acelasi model cerea 5.57 GB in RAM de sistem
    # (din 15.19 GB totali) si se incarca in ~98s, iar cand RAM-ul era ocupat de alte aplicatii
    # alocarea esua - "unable to allocate CPU buffer" - si llama-server crapa in rafala (4 crash-uri
    # in 47s pe 13 august, 2 pe 17 august), cu cate un dump de ~228 MB de fiecare data.
    optiuni = {"num_predict": MAX_TOKENI}
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
) -> str:
    cerere = _construieste_cerere(mesaj, sistem, temperatura, context)
    raspuns = ollama.chat(model=model, **cerere)
    return raspuns["message"]["content"]


def trimite_mesaj_stream(
    mesaj: str,
    nume_personaj: str,
    model: str = MODEL_IMPLICIT,
    sistem: str | None = None,
    temperatura: float | None = None,
    context: list[dict] | None = None,
) -> Iterator[str]:
    cerere = _construieste_cerere(mesaj, sistem, temperatura, context)
    stream = ollama.chat(model=model, stream=True, **cerere)
    bucati = (bucata["message"]["content"] for bucata in stream)
    yield from _curata_stream(bucati, nume_personaj)
