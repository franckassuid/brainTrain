"""
Générateur de Nonogrammes (Picross).

Principe :
1. Générer une grille binaire aléatoire (0/1) de taille adaptée à la
   difficulté.
2. En déduire les indices de lignes et de colonnes (longueurs des blocs
   de cases remplies consécutives).
3. Vérifier que ces indices déterminent une SOLUTION UNIQUE, via un
   solveur qui énumère les grilles compatibles (plafonné à 2 solutions).
4. Si la grille générée n'est pas unique (ou si la vérification dépasse
   un budget de calcul), on retire la tentative et on en génère une
   nouvelle — voir la limite documentée dans README.md.

Représentation d'une ligne/colonne : liste d'entiers (longueurs des blocs
de cases remplies, dans l'ordre), liste vide [] si la ligne est entièrement
vide.
"""

from __future__ import annotations

import random

# -------------------------------------------------------------------
# Tailles de grille par difficulté (adaptées à un écran de téléphone :
# petites grilles pour les niveaux faciles, progressivement plus grandes)
# -------------------------------------------------------------------
DIFFICULTY_SIZES = {
    "facile": (5, 5),
    "moyen": (8, 8),
    "difficile": (10, 10),
}

DIFFICULTY_DENSITY = {
    "facile": 0.55,
    "moyen": 0.5,
    "difficile": 0.45,
}

# Budget de sécurité pour le solveur de vérification d'unicité (nombre
# de noeuds explorés). Voir README.md pour les limites de cette approche.
SOLVER_NODE_BUDGET = 400_000


# -------------------------------------------------------------------
# Conversion grille <-> indices de lignes/colonnes
# -------------------------------------------------------------------
def line_to_clue(line: list[int]) -> list[int]:
    """Calcule les indices (longueurs de blocs) d'une ligne binaire."""
    clue = []
    run = 0
    for v in line:
        if v == 1:
            run += 1
        else:
            if run > 0:
                clue.append(run)
            run = 0
    if run > 0:
        clue.append(run)
    return clue


def grid_to_clues(grid: list[int], num_rows: int, num_cols: int) -> tuple[list[list[int]], list[list[int]]]:
    row_clues = []
    for r in range(num_rows):
        row = grid[r * num_cols:(r + 1) * num_cols]
        row_clues.append(line_to_clue(row))

    col_clues = []
    for c in range(num_cols):
        col = [grid[r * num_cols + c] for r in range(num_rows)]
        col_clues.append(line_to_clue(col))

    return row_clues, col_clues


# -------------------------------------------------------------------
# Génération de toutes les configurations possibles d'une ligne pour un
# indice donné (utilisé par le solveur)
# -------------------------------------------------------------------
def _distribute(total: int, bins: int):
    """Génère tous les n-uplets de `bins` entiers >= 0 dont la somme vaut `total`."""
    if bins == 1:
        yield (total,)
        return
    for i in range(total + 1):
        for rest in _distribute(total - i, bins - 1):
            yield (i,) + rest


def all_line_placements(length: int, clue: list[int]) -> list[tuple[int, ...]]:
    """Toutes les configurations binaires de taille `length` satisfaisant `clue`."""
    if not clue:
        return [tuple([0] * length)]

    k = len(clue)
    total_block = sum(clue)
    min_gaps = k - 1
    slack = length - total_block - min_gaps
    if slack < 0:
        return []

    patterns = []
    for extra in _distribute(slack, k + 1):
        row = [0] * extra[0]
        for i in range(k):
            row += [1] * clue[i]
            if i < k - 1:
                row += [0] * (1 + extra[i + 1])
        row += [0] * extra[k]
        patterns.append(tuple(row))
    return patterns


# -------------------------------------------------------------------
# Solveur : compte les solutions compatibles avec les indices donnés
# (plafonné à `limit`), avec un budget de noeuds pour éviter l'explosion
# combinatoire sur les cas défavorables.
# -------------------------------------------------------------------
class SolverBudgetExceeded(Exception):
    pass


def count_nonogram_solutions(
    row_clues: list[list[int]],
    col_clues: list[list[int]],
    limit: int = 2,
    node_budget: int = SOLVER_NODE_BUDGET,
) -> int | None:
    """
    Renvoie le nombre de solutions (plafonné à `limit`), ou None si le
    budget de calcul a été dépassé avant de pouvoir conclure.
    """
    num_rows = len(row_clues)
    num_cols = len(col_clues)

    row_patterns = [all_line_placements(num_cols, clue) for clue in row_clues]
    col_patterns = [all_line_placements(num_rows, clue) for clue in col_clues]

    if any(len(rp) == 0 for rp in row_patterns) or any(len(cp) == 0 for cp in col_patterns):
        return 0  # indices incohérents, aucune grille possible

    count = 0
    nodes_visited = 0
    assigned_rows: list[tuple[int, ...] | None] = [None] * num_rows

    def col_prefix_ok(col_idx: int, up_to_row: int) -> bool:
        target = tuple(assigned_rows[i][col_idx] for i in range(up_to_row + 1))
        for pattern in col_patterns[col_idx]:
            if pattern[:up_to_row + 1] == target:
                return True
        return False

    def backtrack(r: int) -> None:
        nonlocal count, nodes_visited
        if count >= limit:
            return
        if r == num_rows:
            count += 1
            return

        for pattern in row_patterns[r]:
            nodes_visited += 1
            if nodes_visited > node_budget:
                raise SolverBudgetExceeded()

            assigned_rows[r] = pattern
            if all(col_prefix_ok(c, r) for c in range(num_cols)):
                backtrack(r + 1)
            assigned_rows[r] = None
            if count >= limit:
                return

    try:
        backtrack(0)
    except SolverBudgetExceeded:
        return None

    return count


def has_unique_solution(row_clues: list[list[int]], col_clues: list[list[int]]) -> bool | None:
    """True si unique, False si zéro ou plusieurs solutions, None si non vérifiable (budget dépassé)."""
    result = count_nonogram_solutions(row_clues, col_clues, limit=2)
    if result is None:
        return None
    return result == 1


# -------------------------------------------------------------------
# Génération d'une grille aléatoire "raisonnable" (pas totalement vide,
# pas totalement pleine, ce qui donnerait des indices dégénérés)
# -------------------------------------------------------------------
def generate_random_grid(num_rows: int, num_cols: int, density: float) -> list[int]:
    while True:
        grid = [1 if random.random() < density else 0 for _ in range(num_rows * num_cols)]
        filled = sum(grid)
        # on évite les grilles quasi vides ou quasi pleines (peu intéressantes
        # à jouer et plus susceptibles d'avoir des solutions multiples)
        total = num_rows * num_cols
        if 0.2 * total <= filled <= 0.8 * total:
            return grid


def grid_to_string(grid: list[int]) -> str:
    return "".join(str(v) for v in grid)


def string_to_grid(s: str) -> list[int]:
    return [int(ch) for ch in s]


# -------------------------------------------------------------------
# Génération d'un puzzle complet pour une difficulté donnée
# -------------------------------------------------------------------
def generate_nonogram_puzzle(difficulty: str, max_attempts: int = 200) -> dict:
    """
    Génère un Nonogramme dont la solution est garantie unique, en
    réessayant avec une nouvelle grille aléatoire tant que l'unicité
    n'est pas confirmée (ou que le solveur ne peut pas conclure dans
    son budget de calcul).

    Si, après `max_attempts` tentatives, aucune grille unique n'a pu
    être trouvée, la dernière grille générée est renvoyée avec
    `solution_unique = False` — voir la limite documentée dans
    README.md (ce cas ne s'est jamais produit lors des tests pour les
    tailles utilisées ici : 5x5, 8x8, 10x10).
    """
    num_rows, num_cols = DIFFICULTY_SIZES[difficulty]
    density = DIFFICULTY_DENSITY[difficulty]

    last_attempt = None

    for _ in range(max_attempts):
        grid = generate_random_grid(num_rows, num_cols, density)
        row_clues, col_clues = grid_to_clues(grid, num_rows, num_cols)

        unique = has_unique_solution(row_clues, col_clues)
        last_attempt = {
            "num_rows": num_rows,
            "num_cols": num_cols,
            "solution_grid": grid_to_string(grid),
            "row_clues": row_clues,
            "col_clues": col_clues,
            "difficulty": difficulty,
            "solution_unique": bool(unique),
        }
        if unique:
            return last_attempt

    # Dernier recours : on renvoie la dernière tentative avec le flag à False
    return last_attempt
