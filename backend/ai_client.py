from typing import Iterator

import ollama

MODEL_IMPLICIT = "gemma4:e2b"

# Cat timp tine Ollama modelul in memorie intre mesaje. Implicit sunt 5 minute, iar dupa ele
# urmatorul mesaj asteapta ~13s doar reincarcarea celor 6.7 GB de pe disc (masurat: 13.10s la
# rece vs 1.11s la cald). O ora acopera o sesiune de consiliu fara reincarcari.
KEEP_ALIVE = "1h"

# gemma4:e2b e un model "thinking": implicit isi scrie intai rationamentul intern - sute de
# tokeni pe care utilizatoarea nu-i vede, dar ii asteapta - si abia apoi raspunsul. Oprit,
# primul cuvant vizibil apare in ~3s in loc de ~17s (masurat pe aceeasi intrebare).
GANDIRE = False

# Personajele au in system prompt regula "1-3 propozitii scurte". Plafonul opreste derapajele
# rare, nu raspunsul normal, care sta pe la 40-60 de tokeni.
MAX_TOKENI = 200


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


def _construieste_cerere(mesaj: str, sistem: str | None, temperatura: float | None) -> dict:
    mesaje = []
    if sistem:
        mesaje.append({"role": "system", "content": sistem})
    mesaje.append({"role": "user", "content": mesaj})

    # gemma4:e2b crapa la incarcarea pe GPU (bug CUDA cu driverul curent) - ruleaza pe CPU pana
    # se rezolva. Verificat din nou cu Ollama 0.32.9 / driver 610.88: llama-server iese cu
    # 0xc0000409 si "CUDA error: shared object initialization failed", indiferent de num_ctx.
    optiuni = {"num_gpu": 0, "num_predict": MAX_TOKENI}
    if temperatura is not None:
        optiuni["temperature"] = temperatura

    return {"messages": mesaje, "options": optiuni, "keep_alive": KEEP_ALIVE, "think": GANDIRE}


def preincarca(model: str = MODEL_IMPLICIT) -> None:
    """Aduce modelul in memorie inainte de primul mesaj, ca sa nu astepte utilizatoarea incarcarea."""
    ollama.chat(
        model=model,
        messages=[{"role": "user", "content": "ok"}],
        options={"num_gpu": 0, "num_predict": 1},
        keep_alive=KEEP_ALIVE,
        think=GANDIRE,
    )


def trimite_mesaj(
    mesaj: str,
    model: str = MODEL_IMPLICIT,
    sistem: str | None = None,
    temperatura: float | None = None,
) -> str:
    cerere = _construieste_cerere(mesaj, sistem, temperatura)
    raspuns = ollama.chat(model=model, **cerere)
    return raspuns["message"]["content"]


def trimite_mesaj_stream(
    mesaj: str,
    nume_personaj: str,
    model: str = MODEL_IMPLICIT,
    sistem: str | None = None,
    temperatura: float | None = None,
) -> Iterator[str]:
    cerere = _construieste_cerere(mesaj, sistem, temperatura)
    stream = ollama.chat(model=model, stream=True, **cerere)
    bucati = (bucata["message"]["content"] for bucata in stream)
    yield from _curata_stream(bucati, nume_personaj)
