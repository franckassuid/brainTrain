"""
Générateur de grilles de Sudoku.

Principe :
1. Générer une grille pleine valide (backtracking randomisé).
2. Retirer des cases une par une (ordre aléatoire) en vérifiant après
   chaque retrait que la grille possède toujours une SOLUTION UNIQUE
   (via un solveur qui s'arrête dès qu'il trouve 2 solutions).
3. S'arrêter quand on atteint le nombre d'indices cible pour la difficulté,
   ou quand on ne peut plus retirer de case sans casser l'unicité.
"""

from __future__ import annotations

import random

GRID_SIZE = 9
BOX_SIZE = 3


# -------------------------------------------------------------------
# Outils de base sur la grille (liste de 81 entiers, 0 = case vide)
# -------------------------------------------------------------------
def _row_of(pos: int) -> int:
    return pos // 9


def _col_of(pos: int) -> int:
    return pos % 9


def _box_of(pos: int) -> int:
    r, c = _row_of(pos), _col_of(pos)
    return (r // 3) * 3 + (c // 3)


# précalcul des positions par ligne / colonne / bloc pour la rapidité
_ROW_POSITIONS = [[r * 9 + c for c in range(9)] for r in range(9)]
_COL_POSITIONS = [[r * 9 + c for r in range(9)] for c in range(9)]
_BOX_POSITIONS = [
    [
        (br * 3 + dr) * 9 + (bc * 3 + dc)
        for dr in range(3)
        for dc in range(3)
    ]
    for br in range(3)
    for bc in range(3)
]


def get_candidates(grid: list[int], pos: int) -> list[int]:
    """Renvoie les chiffres 1-9 possibles pour une case vide donnée."""
    used = set()
    r, c, b = _row_of(pos), _col_of(pos), _box_of(pos)
    for p in _ROW_POSITIONS[r]:
        if grid[p]:
            used.add(grid[p])
    for p in _COL_POSITIONS[c]:
        if grid[p]:
            used.add(grid[p])
    for p in _BOX_POSITIONS[b]:
        if grid[p]:
            used.add(grid[p])
    return [v for v in range(1, 10) if v not in used]


def is_valid_full_grid(grid: list[int]) -> bool:
    """Vérifie qu'une grille complète respecte les règles du Sudoku."""
    if len(grid) != 81 or any(v == 0 for v in grid):
        return False
    for positions in list(_ROW_POSITIONS) + list(_COL_POSITIONS) + list(_BOX_POSITIONS):
        values = [grid[p] for p in positions]
        if sorted(values) != list(range(1, 10)):
            return False
    return True


# -------------------------------------------------------------------
# Génération d'une grille pleine valide
# -------------------------------------------------------------------
def generate_full_grid() -> list[int]:
    grid = [0] * 81

    def fill(pos: int) -> bool:
        if pos == 81:
            return True
        if grid[pos] != 0:
            return fill(pos + 1)
        candidates = get_candidates(grid, pos)
        random.shuffle(candidates)
        for v in candidates:
            grid[pos] = v
            if fill(pos + 1):
                return True
            grid[pos] = 0
        return False

    fill(0)
    return grid


# -------------------------------------------------------------------
# Solveur : compte le nombre de solutions (plafonné) via backtracking
# avec heuristique "cellule la plus contrainte" (MRV)
# -------------------------------------------------------------------
def count_solutions(grid: list[int], limit: int = 2) -> int:
    grid = grid[:]  # copie de travail
    count = 0

    def backtrack() -> None:
        nonlocal count
        if count >= limit:
            return

        best_pos = None
        best_candidates = None
        for pos in range(81):
            if grid[pos] == 0:
                candidates = get_candidates(grid, pos)
                if best_candidates is None or len(candidates) < len(best_candidates):
                    best_pos, best_candidates = pos, candidates
                    if len(candidates) <= 1:
                        break

        if best_pos is None:
            # plus aucune case vide -> une solution complète trouvée
            count += 1
            return

        if not best_candidates:
            return  # impasse, aucune valeur possible

        for v in best_candidates:
            grid[best_pos] = v
            backtrack()
            grid[best_pos] = 0
            if count >= limit:
                return

    backtrack()
    return count


def has_unique_solution(grid: list[int]) -> bool:
    return count_solutions(grid, limit=2) == 1


# -------------------------------------------------------------------
# Création d'une grille jouable (puzzle) à partir d'une grille pleine
# -------------------------------------------------------------------
def make_puzzle(solution: list[int], clue_target: int) -> tuple[list[int], int]:
    """
    Retire des cases de `solution` tant que la solution reste unique,
    jusqu'à atteindre `clue_target` indices restants (ou jusqu'à ne
    plus pouvoir retirer sans casser l'unicité).
    Renvoie (grille_puzzle, nombre_d_indices_final).
    """
    grid = solution[:]
    positions = list(range(81))
    random.shuffle(positions)

    remaining_clues = 81
    for pos in positions:
        if remaining_clues <= clue_target:
            break
        backup = grid[pos]
        grid[pos] = 0
        if has_unique_solution(grid):
            remaining_clues -= 1
        else:
            grid[pos] = backup  # on annule le retrait

    return grid, remaining_clues


def grid_to_string(grid: list[int]) -> str:
    return "".join(str(v) for v in grid)


def string_to_grid(s: str) -> list[int]:
    return [int(ch) for ch in s]


# -------------------------------------------------------------------
# Génération d'un puzzle complet pour une difficulté donnée
# -------------------------------------------------------------------
DIFFICULTY_CLUE_TARGETS = {
    "facile": 40,     # beaucoup d'indices -> résolution rapide
    "moyen": 30,
    "difficile": 24,  # peu d'indices -> plus long à résoudre
}


def generate_sudoku_puzzle(difficulty: str) -> dict:
    solution = generate_full_grid()
    assert is_valid_full_grid(solution)

    clue_target = DIFFICULTY_CLUE_TARGETS[difficulty]
    puzzle, clue_count = make_puzzle(solution, clue_target)

    return {
        "starting_grid": grid_to_string(puzzle),
        "solution_grid": grid_to_string(solution),
        "difficulty": difficulty,
        "clue_count": clue_count,
    }
