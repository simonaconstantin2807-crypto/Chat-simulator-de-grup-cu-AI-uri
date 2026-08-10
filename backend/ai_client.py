import ollama

MODEL_IMPLICIT = "gemma4:e2b"


def trimite_mesaj(mesaj: str, model: str = MODEL_IMPLICIT) -> str:
    raspuns = ollama.chat(
        model=model,
        messages=[{"role": "user", "content": mesaj}],
        # gemma4:e2b crapa la incarcarea pe GPU (bug CUDA cu driverul curent) - ruleaza pe CPU pana se rezolva.
        options={"num_gpu": 0},
    )
    return raspuns["message"]["content"]
