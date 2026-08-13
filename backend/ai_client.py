from typing import Iterator

import ollama

MODEL_IMPLICIT = "gemma4:e2b"


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

    # gemma4:e2b crapa la incarcarea pe GPU (bug CUDA cu driverul curent) - ruleaza pe CPU pana se rezolva.
    optiuni = {"num_gpu": 0}
    if temperatura is not None:
        optiuni["temperature"] = temperatura

    return {"messages": mesaje, "options": optiuni}


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
