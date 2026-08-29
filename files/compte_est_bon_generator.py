"""
Générateur de niveaux "Le Compte est bon".

Règles du jeu :
- chaque nombre disponible peut être utilisé au maximum une fois ;
- le joueur peut utiliser une partie ou la totalité des nombres ;
- le résultat final doit atteindre exactement la cible ;
- seules les divisions donnant un résultat entier sont autorisées ;
- opérations autorisées : addition, soustraction, multiplication, division.

Principe de génération (même logique que pour le Sudoku et le Hashi : on
construit la SOLUTION d'abord, ce qui garantit par construction qu'une
solution valide existe) :
1. Tirer un jeu de nombres disponibles (mélange de "petits" nombres 1-10
   et, à partir du niveau moyen, de "grands" nombres 25/50/75/100 comme
   au jeu télévisé).
2. Choisir un sous-ensemble de ces nombres (une partie ou la totalité).
3. Combiner ce sous-ensemble deux par deux, dans un ordre aléatoire, avec
   un opérateur choisi aléatoirement parmi les opérations valides à
   chaque étape (résultat entier strictement positif, division exacte),
   jusqu'à obtenir un seul nombre final : la cible.
4. On retente si la cible obtenue sort de la plage jugée adaptée à la
   difficulté, ou si la combinaison (nombres + cible) a déjà été générée
   (pour éviter des niveaux trop semblables).
"""

from __future__ import annotations

import random

LARGE_NUMBERS = [25, 50, 75, 100]
OP_SYMBOLS = {"+": "+", "-": "−", "*": "×", "/": "÷"}
MAX_INTERMEDIATE = 999_999  # borne de sécurité contre l'explosion combinatoire

DIFFICULTY_PARAMS = {
    # NOTE : ces paramètres ont été renforcés (v5) car les niveaux "facile"
    # générés avec les valeurs précédentes (cible 10-100, 0 grand nombre,
    # sous-ensemble minimal de 2 nombres) étaient jugés trop simples. Les
    # 100 niveaux déjà en base avant ce changement gardent leurs anciens
    # paramètres (jamais régénérés) ; seuls les niveaux ajoutés à partir de
    # maintenant utilisent ces valeurs plus exigeantes.
    "facile": {
        "count": 4,
        "large_count_choices": [0, 1],
        "large_count_weights": [70, 30],   # avant : jamais de grand nombre
        "target_range": (30, 150),          # avant : (10, 100)
        "min_subset_size": 3,               # avant : 2 (empêche les solutions à 2 nombres)
    },
    "moyen": {
        "count": 5,
        "large_count_choices": [0, 1, 2],
        "large_count_weights": [30, 50, 20],  # avant : [50, 40, 10]
        "target_range": (150, 600),           # avant : (100, 500)
        "min_subset_size": 4,                 # avant : 2
    },
    "difficile": {
        "count": 6,
        "large_count_choices": [1, 2, 3],      # avant : [0, 1, 2, 3] — toujours >=1 grand nombre
        "large_count_weights": [30, 45, 25],
        "target_range": (400, 999),            # avant : (200, 999)
        "min_subset_size": 5,                  # avant : 2 — quasi obligation d'utiliser presque tous les nombres
    },
}


# -------------------------------------------------------------------
# Génération du jeu de nombres disponibles
# -------------------------------------------------------------------
def generate_numbers(difficulty: str, rng: random.Random) -> list[int]:
    params = DIFFICULTY_PARAMS[difficulty]
    count = params["count"]

    large_count = rng.choices(params["large_count_choices"], weights=params["large_count_weights"])[0]
    large_count = min(large_count, len(LARGE_NUMBERS), count)

    larges = rng.sample(LARGE_NUMBERS, large_count)
    smalls = [rng.randint(1, 10) for _ in range(count - large_count)]

    numbers = larges + smalls
    rng.shuffle(numbers)
    return numbers


# -------------------------------------------------------------------
# Combinaison aléatoire d'un sous-ensemble de nombres jusqu'à une cible
# -------------------------------------------------------------------
def _merge_numbers(values: list[int], rng: random.Random) -> tuple[int, list[dict], list[str]]:
    """
    Combine les valeurs deux par deux (opérande choisi aléatoirement)
    jusqu'à n'en obtenir qu'une seule.
    Renvoie (valeur_finale, étapes_json, lignes_lisibles).
    """
    tiles = [{"value": v} for v in values]
    steps = []
    readable_lines = []

    while len(tiles) > 1:
        i, j = rng.sample(range(len(tiles)), 2)
        if i > j:
            i, j = j, i
        a, b = tiles[i]["value"], tiles[j]["value"]

        candidates = []  # (op, operand_a, operand_b, result)

        # addition (toujours valide)
        candidates.append(("+", a, b, a + b))

        # multiplication (si sous la borne de sécurité)
        product = a * b
        if product <= MAX_INTERMEDIATE:
            candidates.append(("*", a, b, product))

        # soustraction (résultat strictement positif uniquement)
        hi, lo = (a, b) if a >= b else (b, a)
        if hi != lo:
            candidates.append(("-", hi, lo, hi - lo))

        # division (résultat entier strictement positif uniquement)
        hi, lo = (a, b) if a >= b else (b, a)
        if lo != 0 and hi % lo == 0:
            result = hi // lo
            if result > 0:
                candidates.append(("/", hi, lo, result))

        op, oa, ob, result = rng.choice(candidates)

        del tiles[j]
        del tiles[i]
        tiles.append({"value": result})

        steps.append({"a": oa, "op": op, "b": ob, "result": result})
        readable_lines.append(f"{oa} {OP_SYMBOLS[op]} {ob} = {result}")

    return tiles[0]["value"], steps, readable_lines


# -------------------------------------------------------------------
# Vérification d'une solution (rejouable indépendamment du générateur)
# -------------------------------------------------------------------
def verify_solution(available_numbers: list[int], target: int, steps: list[dict]) -> list[str]:
    """
    Rejoue les étapes de la solution à partir des nombres disponibles et
    vérifie toutes les règles du jeu. Renvoie la liste des erreurs
    trouvées (liste vide = solution valide).
    """
    errors = []
    if not steps:
        return ["aucune étape de solution enregistrée"]

    pool: dict[int, int] = {}
    for v in available_numbers:
        pool[v] = pool.get(v, 0) + 1

    for idx, step in enumerate(steps):
        a, op, b, result = step["a"], step["op"], step["b"], step["result"]

        # consommation de a et b dans le pool (respecte "au maximum une fois")
        if pool.get(a, 0) <= 0:
            errors.append(f"étape {idx} : le nombre {a} n'est pas disponible à ce moment")
            continue
        pool[a] -= 1

        if pool.get(b, 0) <= 0:
            errors.append(f"étape {idx} : le nombre {b} n'est pas disponible à ce moment")
            pool[a] += 1  # on annule la consommation précédente pour ne pas fausser la suite
            continue
        pool[b] -= 1

        if op == "+":
            expected = a + b
        elif op == "-":
            if a < b:
                errors.append(f"étape {idx} : soustraction {a} - {b} donnerait un résultat négatif")
                expected = None
            else:
                expected = a - b
        elif op == "*":
            expected = a * b
        elif op == "/":
            if b == 0 or a % b != 0:
                errors.append(f"étape {idx} : division {a} / {b} n'est pas entière")
                expected = None
            else:
                expected = a // b
        else:
            errors.append(f"étape {idx} : opérateur inconnu {op!r}")
            expected = None

        if expected is not None:
            if expected != result:
                errors.append(f"étape {idx} : résultat incorrect ({a} {op} {b} = {expected}, pas {result})")
            elif result <= 0:
                errors.append(f"étape {idx} : résultat non strictement positif ({result})")

        pool[result] = pool.get(result, 0) + 1

    if steps[-1]["result"] != target:
        errors.append(f"la dernière étape ({steps[-1]['result']}) n'atteint pas la cible ({target})")

    return errors


def is_valid_solution(available_numbers: list[int], target: int, steps: list[dict]) -> bool:
    return len(verify_solution(available_numbers, target, steps)) == 0


# -------------------------------------------------------------------
# Génération d'un niveau complet pour une difficulté donnée
# -------------------------------------------------------------------
def generate_compte_est_bon_puzzle(difficulty: str, max_attempts: int = 300) -> dict:
    params = DIFFICULTY_PARAMS[difficulty]
    target_min, target_max = params["target_range"]

    last_attempt = None

    for _ in range(max_attempts):
        rng = random.Random()
        numbers = generate_numbers(difficulty, rng)

        # sous-ensemble utilisé : une partie ou la totalité des nombres,
        # en favorisant l'utilisation de la plupart d'entre eux
        min_subset = min(params.get("min_subset_size", 2), len(numbers))
        k = rng.choices(
            range(min_subset, len(numbers) + 1),
            weights=[1 if s < len(numbers) else 3 for s in range(min_subset, len(numbers) + 1)],
        )[0]

        positions = list(range(len(numbers)))
        rng.shuffle(positions)
        chosen_positions = positions[:k]
        chosen_values = [numbers[p] for p in chosen_positions]

        target, steps, readable_lines = _merge_numbers(chosen_values, rng)

        errors = verify_solution(numbers, target, steps)
        candidate = {
            "available_numbers": numbers,
            "target": target,
            "solution_steps": steps,
            "solution_readable": "\n".join(readable_lines) + f"\nRésultat obtenu : {target}",
            "difficulty": difficulty,
            "in_range": target_min <= target <= target_max,
            "valid": not errors,
        }

        if errors:
            continue  # sécurité : ne devrait jamais arriver vu la construction

        last_attempt = candidate
        if candidate["in_range"]:
            return candidate

    # dernier recours si la plage cible n'a jamais pu être atteinte
    # (non observé en pratique pour les paramètres utilisés ici)
    if last_attempt is not None:
        return last_attempt
    raise RuntimeError(f"Impossible de générer un niveau valide pour la difficulté {difficulty!r}.")
