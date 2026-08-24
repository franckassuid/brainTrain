"""
Générateur de niveaux "Cross Math".

Règles du jeu :
- une grille k x k de nombres est traversée par k équations horizontales
  (une par ligne) et k équations verticales (une par colonne) ;
- chaque ligne/colonne de k nombres est reliée par (k-1) opérateurs fixes
  et affichés (les "opérateurs visibles"), et doit atteindre un résultat
  donné (row_results / col_results) ;
- le joueur reçoit un ensemble de nombres disponibles ("available_numbers")
  à placer dans les cases vides de la grille (les autres cases sont déjà
  remplies : "given_grid") ;
- chaque nombre disponible doit être utilisé exactement une fois (aucune
  case vide ne reste vide, aucun nombre disponible n'est utilisé deux fois).

RÈGLE DE CALCUL (appliquée PARTOUT dans ce module — génération, solveur,
validateur — une seule fonction fait foi : `evaluate_chain`) :
  Chaque ligne/colonne se calcule STRICTEMENT DE GAUCHE À DROITE (pour les
  lignes) ou DE HAUT EN BAS (pour les colonnes), SANS PRIORITÉ OPÉRATOIRE
  IMPLICITE. Pour 3 nombres a, b, c et 2 opérateurs op1, op2 :
      résultat = (a op1 b) op2 c
  et non "a op1 (b op2 c)" ni une quelconque priorité entre + - × ÷.
  Contraintes à chaque étape intermédiaire :
    - le résultat doit être un entier positif ou nul ;
    - une division doit être exacte (dividende multiple du diviseur) ET
      produire un résultat strictement positif (jamais de division par
      zéro, jamais de résultat nul ou négatif après division).

Principe de génération (même logique que pour le Sudoku, le Hashi et le
Compte est bon : on construit la SOLUTION d'abord) :
1. Tirer une grille k x k de nombres aléatoires (plage selon la difficulté).
2. Pour chaque ligne puis chaque colonne, chercher — par énumération
   exhaustive de toutes les combinaisons d'opérateurs autorisés — une
   séquence d'opérateurs qui rend l'équation valide selon la règle de
   calcul ci-dessus. L'addition et la multiplication sont toujours
   valides quels que soient les nombres (jamais négatives, toujours
   entières) ; c'est donc essentiellement la division qui contraint le
   choix. On retente avec une nouvelle grille si une ligne/colonne ne
   trouve aucune combinaison valide, ou si le mélange d'opérateurs requis
   par la difficulté (présence de × et ÷) n'est pas atteint.
3. On choisit quelles cases restent "données" (given_grid) et lesquelles
   deviennent des cases à remplir, selon la difficulté.
4. Un solveur (recherche exhaustive des façons de placer le MULTI-ENSEMBLE
   des nombres disponibles dans les cases vides, avec élagage dès qu'une
   ligne ou une colonne est complète) vérifie que la solution est UNIQUE.
   Si ce n'est pas le cas, on retente avec une nouvelle grille/répartition.
5. On vérifie enfin que le niveau n'est pas un simple doublon (par
   transposition) d'un niveau déjà généré dans ce lot.
"""
from __future__ import annotations

import random

OPERATORS = ["+", "-", "*", "/"]
OP_SYMBOLS = {"+": "+", "-": "−", "*": "×", "/": "÷"}  # symboles d'affichage

MAX_VALUE = 20_000  # borne de sécurité contre l'explosion combinatoire

DIFFICULTY_PARAMS = {
    "facile": {
        "grid_size": 3,
        "number_range": (1, 9),
        "allowed_operators": ["+", "-"],
        "given_fraction": 0.6,   # part de cases pré-remplies
        "min_mult_or_div": 0,    # pas de x/÷ exigé
        "min_div": 0,
    },
    "moyen": {
        "grid_size": 4,
        "number_range": (1, 9),
        "allowed_operators": ["+", "-", "*", "/"],
        "given_fraction": 0.4,
        "min_mult_or_div": 2,    # au moins 2 occurrences de × ou ÷
        "min_div": 1,            # au moins 1 division
    },
    "difficile": {
        "grid_size": 4,
        "number_range": (1, 12),
        "allowed_operators": ["+", "-", "*", "/"],
        "given_fraction": 0.15,
        "min_mult_or_div": 4,
        "min_div": 2,
    },
}

# Budget de sécurité pour le solveur de vérification d'unicité (nombre
# de noeuds explorés).
SOLVER_NODE_BUDGET = 500_000


# -------------------------------------------------------------------
# LA règle de calcul, utilisée partout (génération, solveur, validateur)
# -------------------------------------------------------------------
def evaluate_chain(numbers: list[int], operators: list[str]) -> int | None:
    """
    Évalue une chaîne de nombres reliés par des opérateurs, STRICTEMENT
    de gauche à droite, sans priorité opératoire implicite :
        résultat = (((numbers[0] op[0] numbers[1]) op[1] numbers[2]) ...)

    Renvoie None si une contrainte est violée à une étape quelconque :
    résultat négatif, division non entière, division par zéro, ou
    résultat de division non strictement positif.
    """
    if len(operators) != len(numbers) - 1:
        raise ValueError("il faut exactement len(numbers) - 1 opérateurs")

    result = numbers[0]
    if result < 0:
        return None

    for num, op in zip(numbers[1:], operators):
        if op == "+":
            result = result + num
        elif op == "-":
            result = result - num
        elif op == "*":
            result = result * num
        elif op == "/":
            if num == 0 or result % num != 0:
                return None
            result = result // num
            if result <= 0:
                return None
        else:
            raise ValueError(f"opérateur inconnu : {op!r}")

        if result < 0:
            return None
        if abs(result) > MAX_VALUE:
            return None

    return result


# -------------------------------------------------------------------
# Recherche d'une séquence d'opérateurs valide pour une ligne/colonne
# -------------------------------------------------------------------
def _all_operator_sequences(length: int, allowed_ops: list[str]):
    if length == 0:
        yield []
        return
    for op in allowed_ops:
        for rest in _all_operator_sequences(length - 1, allowed_ops):
            yield [op] + rest


def find_valid_operators(
    numbers: list[int], allowed_ops: list[str], rng: random.Random
) -> tuple[list[str], int] | None:
    """
    Cherche, parmi TOUTES les combinaisons d'opérateurs autorisés, celles
    qui rendent l'équation valide (selon `evaluate_chain`). Renvoie une
    combinaison choisie au hasard parmi les valides (avec une préférence
    pour les combinaisons contenant × ou ÷, pour varier les niveaux), ou
    None si aucune combinaison n'est valide.
    """
    n_ops = len(numbers) - 1
    valid = []
    for ops in _all_operator_sequences(n_ops, allowed_ops):
        result = evaluate_chain(numbers, ops)
        if result is not None:
            valid.append((ops, result))

    if not valid:
        return None

    with_mult_or_div = [v for v in valid if any(o in ("*", "/") for o in v[0])]
    if with_mult_or_div and rng.random() < 0.7:
        return rng.choice(with_mult_or_div)
    return rng.choice(valid)


# -------------------------------------------------------------------
# Construction de la grille solution complète (nombres + opérateurs)
# -------------------------------------------------------------------
def _build_full_grid(difficulty: str, rng: random.Random) -> dict | None:
    params = DIFFICULTY_PARAMS[difficulty]
    k = params["grid_size"]
    lo, hi = params["number_range"]

    numbers_grid = [[rng.randint(lo, hi) for _ in range(k)] for _ in range(k)]

    row_operators = []
    row_results = []
    for r in range(k):
        found = find_valid_operators(numbers_grid[r], params["allowed_operators"], rng)
        if found is None:
            return None
        ops, result = found
        row_operators.append(ops)
        row_results.append(result)

    col_operators = []
    col_results = []
    for c in range(k):
        column_values = [numbers_grid[r][c] for r in range(k)]
        found = find_valid_operators(column_values, params["allowed_operators"], rng)
        if found is None:
            return None
        ops, result = found
        col_operators.append(ops)
        col_results.append(result)

    # exigence de mélange d'opérateurs selon la difficulté
    all_ops = [op for line in row_operators + col_operators for op in line]
    mult_or_div_count = sum(1 for op in all_ops if op in ("*", "/"))
    div_count = sum(1 for op in all_ops if op == "/")
    if mult_or_div_count < params["min_mult_or_div"] or div_count < params["min_div"]:
        return None

    return {
        "grid_size": k,
        "numbers_grid": numbers_grid,
        "row_operators": row_operators,
        "col_operators": col_operators,
        "row_results": row_results,
        "col_results": col_results,
    }


# -------------------------------------------------------------------
# Choix des cases "données" (pré-remplies) vs cases à compléter
# -------------------------------------------------------------------
def _choose_given_grid(numbers_grid, difficulty: str, rng: random.Random):
    k = len(numbers_grid)
    params = DIFFICULTY_PARAMS[difficulty]
    total_cells = k * k
    given_count = max(1, round(total_cells * params["given_fraction"]))
    given_count = min(given_count, total_cells - 1)  # au moins une case à remplir

    positions = [(r, c) for r in range(k) for c in range(k)]
    rng.shuffle(positions)
    given_positions = set(positions[:given_count])

    given_grid = [
        [numbers_grid[r][c] if (r, c) in given_positions else None for c in range(k)]
        for r in range(k)
    ]
    available_numbers = [
        numbers_grid[r][c] for r in range(k) for c in range(k) if (r, c) not in given_positions
    ]
    rng.shuffle(available_numbers)
    return given_grid, available_numbers


# -------------------------------------------------------------------
# Solveur : compte le nombre de façons de placer available_numbers dans
# les cases vides pour satisfaire toutes les équations (plafonné à `limit`)
# -------------------------------------------------------------------
class SolverBudgetExceeded(Exception):
    pass


def count_solutions(
    given_grid: list[list[int | None]],
    row_operators: list[list[str]],
    col_operators: list[list[str]],
    row_results: list[int],
    col_results: list[int],
    available_numbers: list[int],
    limit: int = 2,
    node_budget: int = SOLVER_NODE_BUDGET,
) -> int | None:
    """
    Renvoie le nombre de façons valides de placer le multi-ensemble
    `available_numbers` dans les cases vides de `given_grid` (plafonné à
    `limit`), ou None si le budget de calcul est dépassé.
    """
    k = len(given_grid)
    blanks = [(r, c) for r in range(k) for c in range(k) if given_grid[r][c] is None]

    if len(blanks) != len(available_numbers):
        return 0  # incohérence : ne devrait pas arriver

    # grille de travail
    grid = [row[:] for row in given_grid]

    # multi-ensemble des valeurs restant à placer
    remaining: dict[int, int] = {}
    for v in available_numbers:
        remaining[v] = remaining.get(v, 0) + 1

    count = 0
    nodes_visited = 0

    def row_complete(r: int) -> bool:
        return all(grid[r][c] is not None for c in range(k))

    def col_complete(c: int) -> bool:
        return all(grid[r][c] is not None for r in range(k))

    def check_row(r: int) -> bool:
        values = [grid[r][c] for c in range(k)]
        return evaluate_chain(values, row_operators[r]) == row_results[r]

    def check_col(c: int) -> bool:
        values = [grid[r][c] for r in range(k)]
        return evaluate_chain(values, col_operators[c]) == col_results[c]

    def backtrack(idx: int) -> None:
        nonlocal count, nodes_visited
        if count >= limit:
            return
        if idx == len(blanks):
            count += 1
            return

        r, c = blanks[idx]
        for value in list(remaining.keys()):
            nodes_visited += 1
            if nodes_visited > node_budget:
                raise SolverBudgetExceeded()
            if remaining[value] == 0:
                continue

            grid[r][c] = value
            remaining[value] -= 1

            ok = True
            if row_complete(r) and not check_row(r):
                ok = False
            if ok and col_complete(c) and not check_col(c):
                ok = False

            if ok:
                backtrack(idx + 1)

            remaining[value] += 1
            grid[r][c] = None

            if count >= limit:
                return

    try:
        backtrack(0)
    except SolverBudgetExceeded:
        return None

    return count


def has_unique_solution(
    given_grid, row_operators, col_operators, row_results, col_results, available_numbers
) -> bool | None:
    result = count_solutions(
        given_grid, row_operators, col_operators, row_results, col_results, available_numbers, limit=2
    )
    if result is None:
        return None
    return result == 1


# -------------------------------------------------------------------
# Validation d'une proposition du joueur (règle par règle, à partir
# UNIQUEMENT des données stockées en base — sans jamais comparer
# directement à la grille solution)
# -------------------------------------------------------------------
def validate_player_grid(
    given_grid: list[list[int | None]],
    row_operators: list[list[str]],
    col_operators: list[list[str]],
    row_results: list[int],
    col_results: list[int],
    available_numbers: list[int],
    proposed_grid: list[list[int]],
) -> list[str]:
    """
    Vérifie une grille proposée par le joueur à partir des seules données
    stockées du niveau (given_grid, opérateurs, résultats, nombres
    disponibles) — jamais en la comparant à une grille solution.
    Renvoie la liste des erreurs (liste vide = proposition correcte).
    """
    errors = []
    k = len(given_grid)

    if len(proposed_grid) != k or any(len(row) != k for row in proposed_grid):
        return [f"dimensions de la grille proposée incorrectes (attendu {k}x{k})"]

    # 1. les cases déjà données ne doivent pas avoir été modifiées
    for r in range(k):
        for c in range(k):
            if given_grid[r][c] is not None and proposed_grid[r][c] != given_grid[r][c]:
                errors.append(
                    f"case ({r},{c}) : valeur donnée modifiée "
                    f"({given_grid[r][c]} -> {proposed_grid[r][c]})"
                )

    # 2. le multi-ensemble des valeurs placées dans les cases vides doit
    #    correspondre EXACTEMENT à available_numbers (pas de réutilisation,
    #    pas de nombre inventé, tous les nombres disponibles utilisés)
    placed_values = [
        proposed_grid[r][c] for r in range(k) for c in range(k) if given_grid[r][c] is None
    ]
    if sorted(placed_values) != sorted(available_numbers):
        errors.append(
            "les nombres placés dans les cases vides ne correspondent pas "
            "exactement aux nombres disponibles (doublon, oubli, ou nombre invalide)"
        )

    # 3. chaque équation de ligne et de colonne doit être satisfaite selon
    #    la règle de calcul officielle (evaluate_chain)
    for r in range(k):
        values = proposed_grid[r]
        result = evaluate_chain(values, row_operators[r])
        if result != row_results[r]:
            errors.append(f"ligne {r} : résultat {result} != attendu {row_results[r]}")

    for c in range(k):
        values = [proposed_grid[r][c] for r in range(k)]
        result = evaluate_chain(values, col_operators[c])
        if result != col_results[c]:
            errors.append(f"colonne {c} : résultat {result} != attendu {col_results[c]}")

    return errors


def is_correct_player_grid(*args, **kwargs) -> bool:
    return len(validate_player_grid(*args, **kwargs)) == 0


# -------------------------------------------------------------------
# Signature canonique (pour éviter les doublons triviaux par transposition)
# -------------------------------------------------------------------
def canonical_signature(puzzle: dict) -> tuple:
    """
    Renvoie une signature invariante par transposition de la grille
    (échange lignes/colonnes), afin de détecter les niveaux qui ne
    seraient qu'un même puzzle "tourné" (doublon trivial).
    """
    def signature_of(numbers_grid, row_ops, col_ops, row_res, col_res):
        return (
            tuple(tuple(row) for row in numbers_grid),
            tuple(tuple(ops) for ops in row_ops),
            tuple(tuple(ops) for ops in col_ops),
            tuple(row_res),
            tuple(col_res),
        )

    k = puzzle["grid_size"]
    numbers_grid = puzzle["numbers_grid"]
    transposed = [[numbers_grid[r][c] for r in range(k)] for c in range(k)]

    sig_original = signature_of(
        numbers_grid, puzzle["row_operators"], puzzle["col_operators"],
        puzzle["row_results"], puzzle["col_results"],
    )
    sig_transposed = signature_of(
        transposed, puzzle["col_operators"], puzzle["row_operators"],
        puzzle["col_results"], puzzle["row_results"],
    )
    return min(sig_original, sig_transposed)


# -------------------------------------------------------------------
# Génération d'un niveau complet pour une difficulté donnée
# -------------------------------------------------------------------
def generate_cross_math_puzzle(difficulty: str, max_attempts: int = 200) -> dict:
    for _ in range(max_attempts):
        rng = random.Random()
        full = _build_full_grid(difficulty, rng)
        if full is None:
            continue

        given_grid, available_numbers = _choose_given_grid(full["numbers_grid"], difficulty, rng)

        unique = has_unique_solution(
            given_grid, full["row_operators"], full["col_operators"],
            full["row_results"], full["col_results"], available_numbers,
        )
        if unique is not True:
            continue  # non unique (ou budget de calcul dépassé) : on retente

        return {
            "grid_size": full["grid_size"],
            "given_grid": given_grid,
            "solution_grid": full["numbers_grid"],
            "row_operators": full["row_operators"],
            "col_operators": full["col_operators"],
            "row_results": full["row_results"],
            "col_results": full["col_results"],
            "available_numbers": available_numbers,
            "difficulty": difficulty,
            "solution_unique": True,
            "canonical_key": canonical_signature(full),
        }

    raise RuntimeError(f"Impossible de générer un niveau Cross Math valide pour {difficulty!r}.")
