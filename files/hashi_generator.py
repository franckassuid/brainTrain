"""
Générateur de puzzles Hashi (Ponts / Hashiwokakero).

Règles du jeu :
- Les ponts relient deux îles alignées horizontalement ou verticalement,
  sans qu'aucune autre île ne se trouve entre elles.
- Il peut y avoir 0, 1 ou 2 ponts entre deux îles.
- Les ponts ne peuvent pas se croiser.
- Le nombre inscrit sur chaque île doit être exactement égal au nombre
  total de ponts qui y sont connectés.
- Toutes les îles doivent former un seul groupe connecté.

Stratégie de génération (comme pour le Sudoku : on construit d'abord une
SOLUTION valide, puis on en déduit l'énoncé) :
1. On place les îles une par une par une "croissance" aléatoire à partir
   d'une île de départ : chaque nouvelle île est reliée en ligne droite à
   une île existante (ce qui garantit par construction l'alignement, la
   connexité, et l'absence d'île intermédiaire sur ce segment).
2. Chaque segment ainsi créé devient une arête du graphe final ; on
   retient l'ensemble des cellules qu'il traverse pour interdire tout
   croisement futur.
3. On ajoute ensuite, si possible, quelques arêtes supplémentaires entre
   îles déjà alignées (toujours en vérifiant l'absence de croisement),
   pour enrichir le puzzle.
4. Chaque arête reçoit aléatoirement 1 ou 2 ponts.
5. Le nombre affiché sur chaque île est la somme des ponts qui lui sont
   connectés — garanti cohérent par construction.

Limite documentée (voir README.md) : l'UNICITÉ de la solution n'est
vérifiée par un solveur que pour les petites grilles (peu d'îles), car la
recherche exhaustive devient coûteuse au-delà. Pour les grilles moyennes
et difficiles, seule la VALIDITÉ de la solution stockée est garantie
(toutes les règles ci-dessus sont vérifiées par `validate_hashi_solution`),
mais l'unicité n'est pas prouvée. Le champ `solution_unique` en base
reflète honnêtement ce qui a été vérifié.
"""

from __future__ import annotations

import random

Island = tuple[int, int]  # (row, col)

DIFFICULTY_PARAMS = {
    "facile": {
        "width": 6, "height": 6,
        "island_count_range": (6, 8),
        "extra_edges_range": (0, 2),
        "double_bridge_prob": 0.25,
        "max_growth_step": 3,
    },
    "moyen": {
        "width": 8, "height": 8,
        "island_count_range": (10, 14),
        "extra_edges_range": (2, 5),
        "double_bridge_prob": 0.35,
        "max_growth_step": 4,
    },
    "difficile": {
        "width": 10, "height": 10,
        "island_count_range": (16, 20),
        "extra_edges_range": (4, 8),
        "double_bridge_prob": 0.45,
        "max_growth_step": 4,
    },
}

# Uniquement pour les petites grilles : au-delà, on ne tente pas la preuve
# d'unicité (voir docstring du module et README.md).
UNIQUENESS_CHECK_MAX_ISLANDS = 9
UNIQUENESS_CHECK_NODE_BUDGET = 150_000


# -------------------------------------------------------------------
# Géométrie : cellules traversées par un segment horizontal/vertical
# -------------------------------------------------------------------
def path_cells(a: Island, b: Island) -> set[Island]:
    """Cellules strictement comprises entre deux îles alignées (exclut les îles)."""
    r0, c0 = a
    r1, c1 = b
    cells = set()
    if r0 == r1:
        step = 1 if c1 > c0 else -1
        for cc in range(c0 + step, c1, step):
            cells.add((r0, cc))
    elif c0 == c1:
        step = 1 if r1 > r0 else -1
        for rr in range(r0 + step, r1, step):
            cells.add((rr, c0))
    else:
        raise ValueError("Les îles doivent être alignées (même ligne ou même colonne).")
    return cells


def is_aligned(a: Island, b: Island) -> bool:
    return a[0] == b[0] or a[1] == b[1]


# -------------------------------------------------------------------
# Construction de la disposition des îles + arêtes (solution)
# -------------------------------------------------------------------
def _grow_island_layout(width: int, height: int, target_count: int, max_step: int, rng: random.Random):
    """
    Construit une liste d'îles connectées par croissance aléatoire.
    Renvoie (islands, tree_edges, used_cells) où :
    - islands       : liste de positions (row, col)
    - tree_edges    : liste de (i, j) index dans `islands`, arbre couvrant
    - used_cells    : ensemble des cellules occupées par une île ou un pont
    """
    start = (rng.randrange(height), rng.randrange(width))
    islands: list[Island] = [start]
    occupied: set[Island] = {start}
    used_path_cells: set[Island] = set()
    tree_edges: list[tuple[int, int]] = []

    attempts = 0
    max_attempts = target_count * 60

    while len(islands) < target_count and attempts < max_attempts:
        attempts += 1
        src_idx = rng.randrange(len(islands))
        r0, c0 = islands[src_idx]
        direction = rng.choice(["up", "down", "left", "right"])
        dist = rng.randint(1, max_step)

        if direction == "up":
            r1, c1 = r0 - dist, c0
        elif direction == "down":
            r1, c1 = r0 + dist, c0
        elif direction == "left":
            r1, c1 = r0, c0 - dist
        else:
            r1, c1 = r0, c0 + dist

        if not (0 <= r1 < height and 0 <= c1 < width):
            continue
        candidate = (r1, c1)
        if candidate in occupied or candidate in used_path_cells:
            continue

        segment_cells = path_cells((r0, c0), candidate)
        if segment_cells & occupied or segment_cells & used_path_cells:
            continue

        islands.append(candidate)
        occupied.add(candidate)
        used_path_cells |= segment_cells
        tree_edges.append((src_idx, len(islands) - 1))

    return islands, tree_edges, occupied, used_path_cells


def _try_add_extra_edges(
    islands: list[Island],
    existing_pairs: set[frozenset],
    used_path_cells: set[Island],
    occupied: set[Island],
    target_extra: int,
    rng: random.Random,
) -> list[tuple[int, int]]:
    """Tente d'ajouter des arêtes supplémentaires entre îles déjà alignées, sans croisement."""
    n = len(islands)
    candidate_pairs = []
    for i in range(n):
        for j in range(i + 1, n):
            if is_aligned(islands[i], islands[j]) and frozenset((i, j)) not in existing_pairs:
                candidate_pairs.append((i, j))
    rng.shuffle(candidate_pairs)

    added = []
    for i, j in candidate_pairs:
        if len(added) >= target_extra:
            break
        segment = path_cells(islands[i], islands[j])
        if segment & occupied or segment & used_path_cells:
            continue
        used_path_cells |= segment
        existing_pairs.add(frozenset((i, j)))
        added.append((i, j))
    return added


def generate_hashi_solution(difficulty: str, rng: random.Random) -> dict:
    """Construit une disposition d'îles + un jeu de ponts valides pour une difficulté donnée."""
    params = DIFFICULTY_PARAMS[difficulty]
    target_count = rng.randint(*params["island_count_range"])

    islands, tree_edges, occupied, used_path_cells = _grow_island_layout(
        params["width"], params["height"], target_count, params["max_growth_step"], rng
    )

    existing_pairs = {frozenset(e) for e in tree_edges}
    target_extra = rng.randint(*params["extra_edges_range"])
    extra_edges = _try_add_extra_edges(
        islands, existing_pairs, used_path_cells, occupied, target_extra, rng
    )

    all_edges = tree_edges + extra_edges
    bridges = []
    values = [0] * len(islands)
    for i, j in all_edges:
        count = 2 if rng.random() < params["double_bridge_prob"] else 1
        bridges.append((i, j, count))
        values[i] += count
        values[j] += count

    return {
        "width": params["width"],
        "height": params["height"],
        "islands": islands,
        "values": values,
        "bridges": bridges,
    }


# -------------------------------------------------------------------
# Validation robuste d'une solution stockée (règle par règle)
# -------------------------------------------------------------------
def validate_hashi_solution(
    islands: list[Island],
    values: list[int],
    bridges: list[tuple[int, int, int]],
) -> list[str]:
    """
    Vérifie toutes les règles du Hashi sur une solution complète.
    Renvoie la liste des violations trouvées (liste vide = solution valide).
    """
    errors = []
    n = len(islands)

    if len(set(islands)) != n:
        errors.append("des îles occupent la même cellule")

    seen_pairs = set()
    used_cells: dict[Island, tuple[int, int]] = {}  # cellule -> (i, j) de l'arête propriétaire

    for (i, j, count) in bridges:
        if not (0 <= i < n and 0 <= j < n) or i == j:
            errors.append(f"arête invalide ({i}, {j})")
            continue
        pair = frozenset((i, j))
        if pair in seen_pairs:
            errors.append(f"plusieurs arêtes entre les mêmes îles {i} et {j}")
        seen_pairs.add(pair)

        if count not in (1, 2):
            errors.append(f"nombre de ponts invalide ({count}) entre {i} et {j}")

        a, b = islands[i], islands[j]
        if not is_aligned(a, b):
            errors.append(f"pont non aligné entre les îles {i} et {j}")
            continue

        segment = path_cells(a, b)
        island_positions = set(islands)
        if segment & island_positions:
            errors.append(f"une île se trouve entre les îles {i} et {j} (pont invalide)")

        for cell in segment:
            owner = used_cells.get(cell)
            if owner is not None and owner != (i, j):
                errors.append(f"croisement ou chevauchement de ponts détecté en {cell}")
            used_cells[cell] = (i, j)

    # somme des ponts par île == valeur affichée
    computed_values = [0] * n
    for (i, j, count) in bridges:
        if 0 <= i < n and 0 <= j < n:
            computed_values[i] += count
            computed_values[j] += count
    for idx in range(n):
        if computed_values[idx] != values[idx]:
            errors.append(
                f"île {idx} : somme des ponts ({computed_values[idx]}) "
                f"!= valeur attendue ({values[idx]})"
            )
        if not (1 <= values[idx] <= 8):
            errors.append(f"île {idx} : valeur hors bornes ({values[idx]})")

    # connexité : toutes les îles reliées entre elles via des ponts (count > 0)
    if n > 0:
        adjacency: dict[int, list[int]] = {k: [] for k in range(n)}
        for (i, j, count) in bridges:
            if count > 0 and 0 <= i < n and 0 <= j < n:
                adjacency[i].append(j)
                adjacency[j].append(i)
        visited = set()
        stack = [0]
        while stack:
            node = stack.pop()
            if node in visited:
                continue
            visited.add(node)
            stack.extend(adjacency[node])
        if len(visited) != n:
            errors.append(f"toutes les îles ne sont pas connectées ({len(visited)}/{n})")

    return errors


def is_valid_hashi_solution(islands, values, bridges) -> bool:
    return len(validate_hashi_solution(islands, values, bridges)) == 0


# -------------------------------------------------------------------
# Vérification (best-effort) de l'unicité pour les petites grilles
# -------------------------------------------------------------------
class SolverBudgetExceeded(Exception):
    pass


def _compute_potential_edges(islands: list[Island]) -> list[tuple[int, int]]:
    """Pour chaque île, l'île la plus proche dans chacune des 4 directions (visibilité directe)."""
    n = len(islands)
    edges = set()
    for i, (r, c) in enumerate(islands):
        best = {"up": None, "down": None, "left": None, "right": None}
        best_dist = {"up": None, "down": None, "left": None, "right": None}
        for j, (r2, c2) in enumerate(islands):
            if i == j:
                continue
            if c2 == c and r2 < r:
                d = r - r2
                if best_dist["up"] is None or d < best_dist["up"]:
                    best_dist["up"], best["up"] = d, j
            elif c2 == c and r2 > r:
                d = r2 - r
                if best_dist["down"] is None or d < best_dist["down"]:
                    best_dist["down"], best["down"] = d, j
            elif r2 == r and c2 < c:
                d = c - c2
                if best_dist["left"] is None or d < best_dist["left"]:
                    best_dist["left"], best["left"] = d, j
            elif r2 == r and c2 > c:
                d = c2 - c
                if best_dist["right"] is None or d < best_dist["right"]:
                    best_dist["right"], best["right"] = d, j
        for direction, j in best.items():
            if j is not None:
                edges.add((min(i, j), max(i, j)))
    return sorted(edges)


def count_hashi_solutions(
    islands: list[Island],
    values: list[int],
    limit: int = 2,
    node_budget: int = UNIQUENESS_CHECK_NODE_BUDGET,
) -> int | None:
    """
    Compte le nombre de solutions (plafonné) satisfaisant les nombres
    inscrits sur les îles, par recherche exhaustive sur les arêtes
    potentielles. Renvoie None si le budget de calcul est dépassé.
    """
    n = len(islands)
    potential_edges = _compute_potential_edges(islands)
    edge_segments = [path_cells(islands[i], islands[j]) for (i, j) in potential_edges]

    assignment = [0] * len(potential_edges)
    remaining_capacity = list(values)  # ce qu'il reste à atteindre par île
    used_cells: dict[Island, int] = {}  # cellule -> index d'arête occupante
    count = 0
    nodes_visited = 0

    # arêtes potentielles concernant chaque île, pour la propagation
    island_edges: dict[int, list[int]] = {k: [] for k in range(n)}
    for idx, (i, j) in enumerate(potential_edges):
        island_edges[i].append(idx)
        island_edges[j].append(idx)

    def max_possible(island_idx: int, from_edge: int) -> int:
        total = 0
        for e in island_edges[island_idx]:
            if e >= from_edge:
                total += 2
        return total

    def backtrack(edge_idx: int) -> None:
        nonlocal count, nodes_visited
        if count >= limit:
            return
        if edge_idx == len(potential_edges):
            if all(v == 0 for v in remaining_capacity):
                # connexité
                adjacency: dict[int, list[int]] = {k: [] for k in range(n)}
                for e_idx, val in enumerate(assignment):
                    if val > 0:
                        i, j = potential_edges[e_idx]
                        adjacency[i].append(j)
                        adjacency[j].append(i)
                visited = set()
                stack = [0]
                while stack:
                    node = stack.pop()
                    if node in visited:
                        continue
                    visited.add(node)
                    stack.extend(adjacency[node])
                if len(visited) == n:
                    count += 1
            return

        i, j = potential_edges[edge_idx]
        segment = edge_segments[edge_idx]

        for val in (0, 1, 2):
            nodes_visited += 1
            if nodes_visited > node_budget:
                raise SolverBudgetExceeded()

            if val > remaining_capacity[i] or val > remaining_capacity[j]:
                continue

            if val > 0:
                if segment & used_cells.keys():
                    continue

            # élagage : la capacité restante doit rester atteignable
            remaining_capacity[i] -= val
            remaining_capacity[j] -= val
            assignment[edge_idx] = val
            if val > 0:
                for cell in segment:
                    used_cells[cell] = edge_idx

            feasible = (
                remaining_capacity[i] <= max_possible(i, edge_idx + 1)
                and remaining_capacity[j] <= max_possible(j, edge_idx + 1)
            )
            if feasible:
                backtrack(edge_idx + 1)

            if val > 0:
                for cell in list(segment):
                    if used_cells.get(cell) == edge_idx:
                        del used_cells[cell]
            remaining_capacity[i] += val
            remaining_capacity[j] += val
            assignment[edge_idx] = 0

            if count >= limit:
                return

    try:
        backtrack(0)
    except SolverBudgetExceeded:
        return None

    return count


def check_uniqueness_if_feasible(islands: list[Island], values: list[int]) -> bool | None:
    """
    Tente une vérification d'unicité uniquement si le nombre d'îles reste
    raisonnable (voir UNIQUENESS_CHECK_MAX_ISLANDS). Renvoie True/False si
    vérifié, None si non tenté ou si le budget de calcul a été dépassé.
    """
    if len(islands) > UNIQUENESS_CHECK_MAX_ISLANDS:
        return None
    result = count_hashi_solutions(islands, values, limit=2)
    if result is None:
        return None
    return result == 1


# -------------------------------------------------------------------
# Génération d'un puzzle complet pour une difficulté donnée
# -------------------------------------------------------------------
def generate_hashi_puzzle(difficulty: str, max_attempts: int = 50) -> dict:
    for _ in range(max_attempts):
        rng = random.Random()
        solution = generate_hashi_solution(difficulty, rng)
        islands = solution["islands"]
        values = solution["values"]
        bridges = solution["bridges"]

        errors = validate_hashi_solution(islands, values, bridges)
        if errors:
            # ne devrait normalement pas arriver vu la construction ;
            # on régénère par sécurité plutôt que de stocker un puzzle invalide.
            continue

        if len(islands) < 4:
            continue  # puzzle trop petit pour être intéressant, on retente

        unique = check_uniqueness_if_feasible(islands, values)

        if unique is False:
            # unicité vérifiable mais non satisfaite : on retente une autre disposition
            # plutôt que de garder un puzzle à solutions multiples
            continue

        return {
            "num_rows": solution["height"],
            "num_cols": solution["width"],
            "islands": [(r, c, v) for (r, c), v in zip(islands, values)],
            "bridges": bridges,
            "difficulty": difficulty,
            "solution_unique": bool(unique) if unique is not None else False,
            "uniqueness_checked": unique is not None,
        }

    raise RuntimeError(f"Impossible de générer un puzzle Hashi valide pour la difficulté {difficulty!r}.")
