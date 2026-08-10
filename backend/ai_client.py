import ollama

MODEL_IMPLICIT = "gemma4:e2b"


def trimite_mesaj(
    mesaj: str,
    model: str = MODEL_IMPLICIT,
    sistem: str | None = None,
    temperatura: float | None = None,
) -> str:
    mesaje = []
    if sistem:
        mesaje.append({"role": "system", "content": sistem})
    mesaje.append({"role": "user", "content": mesaj})

    # gemma4:e2b crapa la incarcarea pe GPU (bug CUDA cu driverul curent) - ruleaza pe CPU pana se rezolva.
    optiuni = {"num_gpu": 0}
    if temperatura is not None:
        optiuni["temperature"] = temperatura

    raspuns = ollama.chat(model=model, messages=mesaje, options=optiuni)
    return raspuns["message"]["content"]
