"""
Générateur de parties de Mastermind.

Paramètres par difficulté :
- facile     : 4 couleurs, 4 positions, 10 tentatives
- moyen      : 6 couleurs, 4 positions, 10 tentatives
- difficile  : 8 couleurs, 5 positions, 12 tentatives

Le code secret est une suite de `num_positions` chiffres,
chacun entre 1 et `num_colors` (les couleurs peuvent se répéter,
comme dans le vrai jeu).
"""
from __future__ import annotations

import random

DIFFICULTY_PARAMS = {
    "facile": {"num_colors": 4, "num_positions": 4, "max_attempts": 10},
    "moyen": {"num_colors": 6, "num_positions": 4, "max_attempts": 10},
    "difficile": {"num_colors": 8, "num_positions": 5, "max_attempts": 12},
}


def generate_secret_code(num_colors: int, num_positions: int) -> list[int]:
    return [random.randint(1, num_colors) for _ in range(num_positions)]


def code_to_string(code: list[int]) -> str:
    return ",".join(str(v) for v in code)


def string_to_code(s: str) -> list[int]:
    return [int(v) for v in s.split(",")]


def generate_mastermind_game(difficulty: str, existing_codes: set[str] | None = None) -> dict:
    """
    Génère une partie de Mastermind.
    `existing_codes` (optionnel) permet d'éviter de régénérer deux fois
    exactement le même code secret pour une même difficulté.
    """
    params = DIFFICULTY_PARAMS[difficulty]
    existing_codes = existing_codes if existing_codes is not None else set()

    for _ in range(1000):  # garde-fou anti-boucle infinie
        code = generate_secret_code(params["num_colors"], params["num_positions"])
        code_str = code_to_string(code)
        if code_str not in existing_codes:
            existing_codes.add(code_str)
            break
    else:
        raise RuntimeError("Impossible de générer un code secret unique supplémentaire.")

    return {
        "secret_code": code_str,
        "num_colors": params["num_colors"],
        "num_positions": params["num_positions"],
        "max_attempts": params["max_attempts"],
        "difficulty": difficulty,
    }
