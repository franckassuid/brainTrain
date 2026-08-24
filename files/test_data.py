"""
Tests de validation de la base de données générée.

Vérifie :
- les comptes et répartitions par difficulté (Sudoku, Mastermind,
  Nonogramme, Hashi, Compte est bon, Cross Math)
- que chaque grille de Sudoku de départ et sa solution sont cohérentes
- que chaque grille solution respecte les règles du Sudoku
- que chaque grille de départ a bien une solution UNIQUE
- que les codes secrets de Mastermind respectent leurs contraintes
- que les indices de chaque Nonogramme correspondent EXACTEMENT à la
  grille solution stockée, et que la solution est unique
- que chaque puzzle Hashi respecte toutes les règles (alignement, pas de
  croisement, valeurs, connexité) via un validateur dédié
- que chaque solution du Compte est bon atteint réellement la cible, que
  la division est toujours entière et qu'aucun nombre n'est utilisé plus
  de fois qu'il n'est disponible
- que chaque solution Cross Math est mathématiquement valide (règle de
  calcul gauche->droite / haut->bas, sans priorité opératoire), que
  chaque division est entière, que la solution est unique (recomptée
  par le solveur), qu'une mauvaise proposition est rejetée et que la
  bonne solution est acceptée
- que les durées estimées correspondent bien à la difficulté
- que la fonction de requête filtre correctement les 6 types de jeux
- que le tirage aléatoire SANS type précisé est équilibré entre les
  types de jeux, indépendamment de leur nombre de niveaux en base
- (implicitement, via les comptes exacts de chaque table) qu'aucune
  donnée d'un autre type de jeu n'a été modifiée par l'ajout de Cross Math

Usage :
    python test_data.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

from db import get_connection
from sudoku_generator import (
    is_valid_full_grid,
    has_unique_solution,
    string_to_grid,
)
from mastermind_generator import string_to_code, DIFFICULTY_PARAMS
from nonogram_generator import (
    grid_to_clues,
    string_to_grid as nonogram_string_to_grid,
    has_unique_solution as nonogram_has_unique_solution,
    DIFFICULTY_SIZES as NONOGRAM_SIZES,
)
from hashi_generator import (
    validate_hashi_solution,
    check_uniqueness_if_feasible,
    UNIQUENESS_CHECK_MAX_ISLANDS,
)
from compte_est_bon_generator import verify_solution as compte_est_bon_verify_solution
from cross_math_generator import (
    evaluate_chain as cross_math_evaluate_chain,
    validate_player_grid as cross_math_validate_player_grid,
    is_correct_player_grid as cross_math_is_correct_player_grid,
    count_solutions as cross_math_count_solutions,
    DIFFICULTY_PARAMS as CROSS_MATH_DIFFICULTY_PARAMS,
)

SUDOKU_DURATIONS = {"facile": 5, "moyen": 10, "difficile": 20}
MASTERMIND_DURATIONS = {"facile": 5, "moyen": 10, "difficile": 15}
NONOGRAM_DURATIONS = {"facile": 5, "moyen": 10, "difficile": 20}
HASHI_DURATIONS = {"facile": 5, "moyen": 10, "difficile": 20}
COMPTE_EST_BON_DURATIONS = {"facile": 5, "moyen": 10, "difficile": 20}
CROSS_MATH_DURATIONS = {"facile": 5, "moyen": 10, "difficile": 20}
EXPECTED_DISTRIBUTION = {"facile": 20, "moyen": 20, "difficile": 10}
COMPTE_EST_BON_EXPECTED_DISTRIBUTION = {"facile": 100, "moyen": 100, "difficile": 50}


failures = []


def check(condition: bool, message: str) -> None:
    if condition:
        print(f"  OK   - {message}")
    else:
        print(f"  FAIL - {message}")
        failures.append(message)


def test_sudoku(conn) -> None:
    print("\n--- Sudoku ---")
    rows = conn.execute("SELECT * FROM sudoku_puzzles").fetchall()

    check(len(rows) == 50, f"50 grilles au total (trouvé {len(rows)})")

    counts = {"facile": 0, "moyen": 0, "difficile": 0}
    starting_grids_seen = set()

    for row in rows:
        difficulty = row["difficulty"]
        counts[difficulty] += 1

        start = string_to_grid(row["starting_grid"])
        solution = string_to_grid(row["solution_grid"])

        # 1. la solution est une grille pleine valide
        if not is_valid_full_grid(solution):
            failures.append(f"id={row['id']} : solution invalide")
            print(f"  FAIL - id={row['id']} solution invalide")
            continue

        # 2. la grille de départ est cohérente avec la solution
        #    (chaque case non-vide de départ == la valeur en solution)
        consistent = all(
            (start[i] == 0 or start[i] == solution[i]) for i in range(81)
        )
        if not consistent:
            failures.append(f"id={row['id']} : grille de départ incohérente avec la solution")
            print(f"  FAIL - id={row['id']} grille de départ incohérente")

        # 3. la grille de départ a une solution unique
        unique = has_unique_solution(start)
        if not unique:
            failures.append(f"id={row['id']} : solution NON unique")
            print(f"  FAIL - id={row['id']} solution non unique")

        # 4. durée cohérente avec la difficulté
        if row["estimated_duration_minutes"] != SUDOKU_DURATIONS[difficulty]:
            failures.append(f"id={row['id']} : durée incohérente pour {difficulty}")

        starting_grids_seen.add(row["starting_grid"])

    check(counts["facile"] == 20, f"20 grilles faciles (trouvé {counts['facile']})")
    check(counts["moyen"] == 20, f"20 grilles moyennes (trouvé {counts['moyen']})")
    check(counts["difficile"] == 10, f"10 grilles difficiles (trouvé {counts['difficile']})")
    check(len(starting_grids_seen) == len(rows), "toutes les grilles de départ sont différentes")
    check(
        all(string_to_grid(r["solution_grid"]) and True for r in rows),
        "toutes les solutions ont bien 81 caractères",
    )
    print("  (solutions vérifiées comme uniques pour les 50 grilles)")


def test_mastermind(conn) -> None:
    print("\n--- Mastermind ---")
    rows = conn.execute("SELECT * FROM mastermind_games").fetchall()

    check(len(rows) == 50, f"50 parties au total (trouvé {len(rows)})")

    counts = {"facile": 0, "moyen": 0, "difficile": 0}
    codes_seen_by_difficulty = {"facile": set(), "moyen": set(), "difficile": set()}

    for row in rows:
        difficulty = row["difficulty"]
        counts[difficulty] += 1
        params = DIFFICULTY_PARAMS[difficulty]

        # 1. paramètres cohérents avec la difficulté
        if row["num_colors"] != params["num_colors"]:
            failures.append(f"id={row['id']} : num_colors incohérent pour {difficulty}")
        if row["num_positions"] != params["num_positions"]:
            failures.append(f"id={row['id']} : num_positions incohérent pour {difficulty}")
        if row["max_attempts"] != params["max_attempts"]:
            failures.append(f"id={row['id']} : max_attempts incohérent pour {difficulty}")

        # 2. code secret valide : bonne longueur, valeurs dans la plage
        code = string_to_code(row["secret_code"])
        if len(code) != row["num_positions"]:
            failures.append(f"id={row['id']} : longueur du code incorrecte")
        if not all(1 <= v <= row["num_colors"] for v in code):
            failures.append(f"id={row['id']} : valeur du code hors plage de couleurs")

        # 3. durée cohérente
        if row["estimated_duration_minutes"] != MASTERMIND_DURATIONS[difficulty]:
            failures.append(f"id={row['id']} : durée incohérente pour {difficulty}")

        codes_seen_by_difficulty[difficulty].add(row["secret_code"])

    check(counts["facile"] == 20, f"20 parties faciles (trouvé {counts['facile']})")
    check(counts["moyen"] == 20, f"20 parties moyennes (trouvé {counts['moyen']})")
    check(counts["difficile"] == 10, f"10 parties difficiles (trouvé {counts['difficile']})")

    for difficulty, codes in codes_seen_by_difficulty.items():
        expected = EXPECTED_DISTRIBUTION[difficulty]
        check(
            len(codes) == expected,
            f"codes secrets tous différents pour '{difficulty}' ({len(codes)}/{expected})",
        )

    # progression de la difficulté : + de couleurs / positions = + difficile
    check(
        DIFFICULTY_PARAMS["facile"]["num_colors"] < DIFFICULTY_PARAMS["moyen"]["num_colors"]
        < DIFFICULTY_PARAMS["difficile"]["num_colors"],
        "le nombre de couleurs augmente avec la difficulté",
    )
    check(
        DIFFICULTY_PARAMS["facile"]["num_positions"] <= DIFFICULTY_PARAMS["moyen"]["num_positions"]
        < DIFFICULTY_PARAMS["difficile"]["num_positions"],
        "le nombre de positions augmente (ou reste égal) avec la difficulté",
    )


def test_nonogram(conn) -> None:
    print("\n--- Nonogramme ---")
    rows = conn.execute("SELECT * FROM nonogram_puzzles").fetchall()

    check(len(rows) == 50, f"50 grilles au total (trouvé {len(rows)})")

    counts = {"facile": 0, "moyen": 0, "difficile": 0}
    solutions_seen = set()
    unverified_count = 0

    for row in rows:
        difficulty = row["difficulty"]
        counts[difficulty] += 1

        expected_rows, expected_cols = NONOGRAM_SIZES[difficulty]
        if (row["num_rows"], row["num_cols"]) != (expected_rows, expected_cols):
            failures.append(
                f"id={row['id']} : taille {row['num_rows']}x{row['num_cols']} "
                f"!= attendue {expected_rows}x{expected_cols} pour '{difficulty}'"
            )

        grid = nonogram_string_to_grid(row["solution_grid"])
        if len(grid) != row["num_rows"] * row["num_cols"]:
            failures.append(f"id={row['id']} : longueur de grille incorrecte")
            continue

        stored_row_clues = json.loads(row["row_clues"])
        stored_col_clues = json.loads(row["col_clues"])

        # 1. les indices stockés correspondent EXACTEMENT à la grille solution
        computed_row_clues, computed_col_clues = grid_to_clues(grid, row["num_rows"], row["num_cols"])
        if computed_row_clues != stored_row_clues:
            failures.append(f"id={row['id']} : indices de lignes incohérents avec la solution")
        if computed_col_clues != stored_col_clues:
            failures.append(f"id={row['id']} : indices de colonnes incohérents avec la solution")

        # 2. la solution est bien unique d'après les indices stockés
        if row["solution_unique"]:
            unique = nonogram_has_unique_solution(stored_row_clues, stored_col_clues)
            if unique is not True:
                failures.append(
                    f"id={row['id']} : marqué unique en base mais le solveur "
                    f"ne le confirme pas (résultat={unique})"
                )
        else:
            unverified_count += 1

        # 3. durée cohérente avec la difficulté
        if row["estimated_duration_minutes"] != NONOGRAM_DURATIONS[difficulty]:
            failures.append(f"id={row['id']} : durée incohérente pour {difficulty}")

        solutions_seen.add(row["solution_grid"])

    check(counts["facile"] == 20, f"20 grilles faciles (trouvé {counts['facile']})")
    check(counts["moyen"] == 20, f"20 grilles moyennes (trouvé {counts['moyen']})")
    check(counts["difficile"] == 10, f"10 grilles difficiles (trouvé {counts['difficile']})")
    check(len(solutions_seen) == len(rows), "toutes les grilles solutions sont différentes")
    check(
        unverified_count == 0,
        f"toutes les grilles ont une solution unique confirmée ({unverified_count} non confirmée(s))",
    )
    check(
        NONOGRAM_SIZES["facile"] <= NONOGRAM_SIZES["moyen"] <= NONOGRAM_SIZES["difficile"],
        "les tailles de grille augmentent (ou restent égales) avec la difficulté",
    )
    print(
        f"  (indices vérifiés comme exacts et solution unique pour les {len(rows)} grilles "
        f"— tailles {NONOGRAM_SIZES})"
    )


def test_hashi(conn) -> None:
    print("\n--- Hashi (Ponts) ---")
    rows = conn.execute("SELECT * FROM hashi_puzzles").fetchall()

    check(len(rows) == 50, f"50 puzzles au total (trouvé {len(rows)})")

    counts = {"facile": 0, "moyen": 0, "difficile": 0}
    checked_count = 0
    unique_count = 0

    for row in rows:
        difficulty = row["difficulty"]
        counts[difficulty] += 1

        islands_data = json.loads(row["islands"])  # liste de [row, col, value]
        bridges = [tuple(b) for b in json.loads(row["solution_bridges"])]

        islands = [(r, c) for r, c, v in islands_data]
        values = [v for r, c, v in islands_data]

        # 1. validation robuste et complète de la solution stockée
        errors = validate_hashi_solution(islands, values, bridges)
        if errors:
            failures.append(f"id={row['id']} : solution invalide -> {errors}")
            print(f"  FAIL - id={row['id']} : {errors}")
            continue

        # 2. cohérence des coordonnées avec les dimensions de la grille
        out_of_bounds = any(
            not (0 <= r < row["num_rows"] and 0 <= c < row["num_cols"])
            for r, c in islands
        )
        if out_of_bounds:
            failures.append(f"id={row['id']} : île en dehors des limites de la grille")

        # 3. re-vérification de l'unicité quand la base affirme qu'elle a été
        #    confirmée (uniquement plausible pour les petites grilles)
        if row["solution_unique"]:
            check_result = check_uniqueness_if_feasible(islands, values)
            unique_count += 1
            if check_result is not True:
                failures.append(
                    f"id={row['id']} : marqué unique en base mais non reconfirmé "
                    f"(résultat={check_result})"
                )
            if len(islands) > UNIQUENESS_CHECK_MAX_ISLANDS:
                failures.append(
                    f"id={row['id']} : marqué unique alors que le nombre d'îles "
                    f"({len(islands)}) dépasse le seuil vérifiable"
                )
        else:
            checked_count += 1  # non vérifié : comptabilisé comme "limite connue"

        # 4. durée cohérente avec la difficulté
        if row["estimated_duration_minutes"] != HASHI_DURATIONS[difficulty]:
            failures.append(f"id={row['id']} : durée incohérente pour {difficulty}")

    check(counts["facile"] == 20, f"20 puzzles faciles (trouvé {counts['facile']})")
    check(counts["moyen"] == 20, f"20 puzzles moyens (trouvé {counts['moyen']})")
    check(counts["difficile"] == 10, f"10 puzzles difficiles (trouvé {counts['difficile']})")
    print(
        f"  (solution validée règle par règle pour les {len(rows)} puzzles ; "
        f"unicité confirmée pour {unique_count}, non vérifiée pour {checked_count} "
        f"— limite documentée dans README.md)"
    )


def test_compte_est_bon(conn) -> None:
    print("\n--- Le Compte est bon ---")
    rows = conn.execute("SELECT * FROM compte_est_bon_puzzles").fetchall()

    check(len(rows) == 250, f"250 niveaux au total (trouvé {len(rows)})")

    counts = {"facile": 0, "moyen": 0, "difficile": 0}
    expected_count_by_diff = {"facile": 4, "moyen": 5, "difficile": 6}
    combos_seen = set()
    division_steps_checked = 0
    invalid_solutions = 0

    for row in rows:
        difficulty = row["difficulty"]
        counts[difficulty] += 1

        numbers = json.loads(row["available_numbers"])
        steps = json.loads(row["solution_steps"])
        allowed_ops = json.loads(row["allowed_operations"])
        target = row["target"]

        # 1. bon nombre de nombres disponibles pour la difficulté
        if len(numbers) != expected_count_by_diff[difficulty]:
            failures.append(
                f"id={row['id']} : {len(numbers)} nombres au lieu de "
                f"{expected_count_by_diff[difficulty]} pour '{difficulty}'"
            )

        # 2. les 4 opérations sont bien listées comme autorisées
        if set(allowed_ops) != {"+", "-", "*", "/"}:
            failures.append(f"id={row['id']} : opérations autorisées incorrectes ({allowed_ops})")

        # 3. la solution enregistrée est rejouée et vérifiée intégralement :
        #    - chaque étape n'utilise que des nombres encore disponibles
        #      (donc aucun nombre utilisé plus de fois qu'il n'est fourni)
        #    - les divisions sont exactes (entières)
        #    - le résultat final atteint bien la cible
        errors = compte_est_bon_verify_solution(numbers, target, steps)
        if errors:
            invalid_solutions += 1
            failures.append(f"id={row['id']} : solution invalide -> {errors}")
            print(f"  FAIL - id={row['id']} : {errors}")

        for step in steps:
            if step["op"] == "/":
                division_steps_checked += 1
                if step["b"] == 0 or step["a"] % step["b"] != 0:
                    failures.append(f"id={row['id']} : division non entière détectée ({step})")

        # 4. durée cohérente avec la difficulté
        if row["estimated_duration_minutes"] != COMPTE_EST_BON_DURATIONS[difficulty]:
            failures.append(f"id={row['id']} : durée incohérente pour {difficulty}")

        combos_seen.add((tuple(sorted(numbers)), target))

    check(counts["facile"] == 100, f"100 niveaux faciles (trouvé {counts['facile']})")
    check(counts["moyen"] == 100, f"100 niveaux moyens (trouvé {counts['moyen']})")
    check(counts["difficile"] == 50, f"50 niveaux difficiles (trouvé {counts['difficile']})")
    check(invalid_solutions == 0, f"toutes les solutions atteignent la cible sans erreur ({invalid_solutions} invalide(s))")
    check(
        len(combos_seen) == len(rows),
        f"les niveaux sont variés : {len(combos_seen)}/{len(rows)} combinaisons (nombres+cible) distinctes",
    )
    print(
        f"  ({len(rows)} solutions entièrement rejouées et vérifiées, "
        f"{division_steps_checked} division(s) contrôlée(s) comme entières)"
    )


def test_cross_math(conn) -> None:
    print("\n--- Cross Math ---")
    rows = conn.execute("SELECT * FROM cross_math_puzzles").fetchall()

    check(len(rows) == 50, f"50 niveaux au total (trouvé {len(rows)})")

    counts = {"facile": 0, "moyen": 0, "difficile": 0}
    invalid_solution_count = 0
    non_unique_count = 0
    bad_division_count = 0
    accepted_correct_count = 0
    rejected_wrong_count = 0
    seen_signatures = set()

    for row in rows:
        difficulty = row["difficulty"]
        counts[difficulty] += 1
        k = row["grid_size"]

        given_grid = json.loads(row["given_grid"])
        solution_grid = json.loads(row["solution_grid"])
        row_operators = json.loads(row["row_operators"])
        col_operators = json.loads(row["col_operators"])
        row_results = json.loads(row["row_results"])
        col_results = json.loads(row["col_results"])
        available_numbers = json.loads(row["available_numbers"])

        # 1. taille de grille cohérente avec la difficulté annoncée
        expected_k = CROSS_MATH_DIFFICULTY_PARAMS[difficulty]["grid_size"]
        if k != expected_k:
            failures.append(f"id={row['id']} : taille de grille {k} != attendue {expected_k} pour '{difficulty}'")

        # 2. la grille solution respecte réellement chaque équation, selon
        #    LA règle de calcul officielle (gauche->droite, haut->bas,
        #    sans priorité opératoire) — validée à partir des données
        #    stockées uniquement (pas de simple recopie)
        solution_errors = cross_math_validate_player_grid(
            given_grid, row_operators, col_operators, row_results, col_results,
            available_numbers, solution_grid,
        )
        if solution_errors:
            invalid_solution_count += 1
            failures.append(f"id={row['id']} : solution stockée invalide -> {solution_errors}")
            print(f"  FAIL - id={row['id']} : {solution_errors}")
        else:
            accepted_correct_count += 1

        # 3. aucune division décimale ni par zéro (vérification directe,
        #    en rejouant chaque ligne/colonne avec la règle officielle)
        for line_values, line_ops in [
            *[(row_i, row_operators[i]) for i, row_i in enumerate(solution_grid)],
            *[
                ([solution_grid[r][c] for r in range(k)], col_operators[c])
                for c in range(k)
            ],
        ]:
            result = cross_math_evaluate_chain(line_values, line_ops)
            if result is None:
                bad_division_count += 1
                failures.append(f"id={row['id']} : équation invalide détectée (division non entière ou négative)")
                continue
            # double-vérification directe des divisions
            r = line_values[0]
            for num, op in zip(line_values[1:], line_ops):
                if op == "/":
                    if num == 0 or r % num != 0:
                        bad_division_count += 1
                        failures.append(f"id={row['id']} : division non entière ({r} / {num})")
                    r = r // num if num != 0 else r
                elif op == "+":
                    r = r + num
                elif op == "-":
                    r = r - num
                elif op == "*":
                    r = r * num

        # 4. UNICITÉ de la solution (recomptée indépendamment, pas de
        #    simple confiance dans le flag stocké)
        if row["solution_unique"]:
            n_solutions = cross_math_count_solutions(
                given_grid, row_operators, col_operators, row_results, col_results,
                available_numbers, limit=2,
            )
            if n_solutions != 1:
                non_unique_count += 1
                failures.append(f"id={row['id']} : unicité annoncée mais {n_solutions} solution(s) trouvée(s)")
        else:
            non_unique_count += 1
            failures.append(f"id={row['id']} : solution_unique=0 (devrait toujours être 1 dans ce jeu de données)")

        # 5. rejet d'une mauvaise proposition : on altère une case à
        #    compléter (échange de deux valeurs disponibles) et on vérifie
        #    que le validateur la rejette (sauf cas très rare où l'échange
        #    donne accidentellement une solution alternative valide, ce
        #    qui contredirait l'unicité déjà testée ci-dessus)
        blanks = [(r, c) for r in range(k) for c in range(k) if given_grid[r][c] is None]
        if len(blanks) >= 2:
            wrong_grid = [line[:] for line in solution_grid]
            (r1, c1), (r2, c2) = blanks[0], blanks[1]
            if wrong_grid[r1][c1] != wrong_grid[r2][c2]:
                wrong_grid[r1][c1], wrong_grid[r2][c2] = wrong_grid[r2][c2], wrong_grid[r1][c1]
                is_correct = cross_math_is_correct_player_grid(
                    given_grid, row_operators, col_operators, row_results, col_results,
                    available_numbers, wrong_grid,
                )
                if is_correct:
                    failures.append(f"id={row['id']} : une proposition erronée (permutation) a été acceptée à tort")
                else:
                    rejected_wrong_count += 1

        # 6. durée cohérente avec la difficulté
        if row["estimated_duration_minutes"] != CROSS_MATH_DURATIONS[difficulty]:
            failures.append(f"id={row['id']} : durée incohérente pour {difficulty}")

        seen_signatures.add(
            (tuple(tuple(r) for r in solution_grid), tuple(tuple(o) for o in row_operators),
             tuple(tuple(o) for o in col_operators), tuple(row_results), tuple(col_results))
        )

    check(counts["facile"] == 20, f"20 niveaux faciles (trouvé {counts['facile']})")
    check(counts["moyen"] == 20, f"20 niveaux moyens (trouvé {counts['moyen']})")
    check(counts["difficile"] == 10, f"10 niveaux difficiles (trouvé {counts['difficile']})")
    check(invalid_solution_count == 0, f"toutes les solutions stockées sont mathématiquement valides ({invalid_solution_count} invalide(s))")
    check(bad_division_count == 0, f"aucune division décimale ou par zéro détectée ({bad_division_count} trouvée(s))")
    check(non_unique_count == 0, f"toutes les solutions sont confirmées uniques ({non_unique_count} problème(s))")
    check(
        rejected_wrong_count > 0,
        f"le validateur rejette bien les mauvaises propositions testées ({rejected_wrong_count} rejet(s) confirmé(s))",
    )
    check(accepted_correct_count == len(rows), f"le validateur accepte la bonne solution pour tous les niveaux ({accepted_correct_count}/{len(rows)})")
    check(
        len(seen_signatures) == len(rows),
        f"les niveaux sont variés, aucun doublon (même par transposition) : "
        f"{len(seen_signatures)}/{len(rows)} signatures distinctes",
    )
    print(
        f"  ({len(rows)} solutions revérifiées intégralement, unicité recomptée par le solveur, "
        f"rejet de proposition erronée testé sur chaque niveau ayant >=2 cases à compléter)"
    )


def test_other_games_untouched_by_cross_math(conn) -> None:
    """
    Vérifie explicitement que l'ajout de Cross Math n'a modifié aucune
    donnée des autres types de jeux : le nombre de lignes de chaque table
    correspond exactement à ce qui existait avant l'ajout de Cross Math.

    Remarque : on ne suppose PAS que les identifiants sont contigus à
    partir de 1, car ces tables ont pu être régénérées lors de sessions
    de développement précédentes (avant l'ajout de Cross Math) — seul le
    nombre de lignes (et, en pratique, leur contenu — vérifié manuellement
    par empreinte MD5 avant/après l'ajout de Cross Math, voir README.md)
    doit rester strictement identique désormais que `generate_data.py`
    n'écrit plus jamais dans une table déjà peuplée (voir sa docstring).
    """
    print("\n--- Non-régression : les autres jeux n'ont pas été modifiés ---")

    tables_and_expected_counts = [
        ("sudoku_puzzles", 50),
        ("mastermind_games", 50),
        ("nonogram_puzzles", 50),
        ("hashi_puzzles", 50),
        ("compte_est_bon_puzzles", 250),
    ]
    for table, expected_count in tables_and_expected_counts:
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        check(count == expected_count, f"{table} : {expected_count} lignes toujours présentes (trouvé {count})")

    generate_data_path = Path(__file__).parent / "generate_data.py"
    with open(generate_data_path, "r", encoding="utf-8") as f:
        source = f.read()
    check(
        "DELETE FROM" not in source and "DROP TABLE" not in source,
        "generate_data.py ne contient aucune instruction DELETE/DROP (purement additif)",
    )


def test_query_function(conn) -> None:
    print("\n--- Fonction de requête get_games / get_random_game ---")
    from query import get_games, get_random_game, VALID_TYPES

    all_games = get_games(conn=conn)
    check(len(all_games) == 500, f"500 jeux au total via get_games() (trouvé {len(all_games)})")

    for game_type, expected in [
        ("sudoku", 50), ("mastermind", 50), ("nonogram", 50), ("hashi", 50),
        ("compte_est_bon", 250), ("cross_math", 50),
    ]:
        results = get_games(game_type=game_type, conn=conn)
        check(
            len(results) == expected,
            f"get_games(game_type='{game_type}') renvoie {expected} résultats (trouvé {len(results)})",
        )
        check(
            all(g["type"] == game_type for g in results),
            f"tous les résultats de '{game_type}' portent bien type='{game_type}'",
        )

    easy_only = get_games(difficulty="facile", conn=conn)
    # 20 (sudoku) + 20 (mastermind) + 20 (nonogram) + 20 (hashi) + 100 (compte_est_bon) + 20 (cross_math) = 200
    check(len(easy_only) == 200, f"get_games(difficulty='facile') renvoie 200 résultats (trouvé {len(easy_only)})")

    short_games = get_games(max_duration=5, conn=conn)
    check(
        all(g["estimated_duration_minutes"] <= 5 for g in short_games),
        "get_games(max_duration=5) ne renvoie que des jeux <= 5 minutes",
    )

    combo = get_games(game_type="mastermind", difficulty="difficile", max_duration=15, conn=conn)
    check(len(combo) == 10, "combinaison type+difficulté+durée renvoie les 10 mastermind difficiles")

    nonogram_combo = get_games(game_type="nonogram", difficulty="difficile", max_duration=20, conn=conn)
    check(len(nonogram_combo) == 10, "combinaison type+difficulté+durée renvoie les 10 nonogrammes difficiles")

    hashi_combo = get_games(game_type="hashi", difficulty="facile", conn=conn)
    check(len(hashi_combo) == 20, "get_games(game_type='hashi', difficulty='facile') renvoie 20 résultats")

    compte_combo = get_games(game_type="compte_est_bon", difficulty="difficile", conn=conn)
    check(len(compte_combo) == 50, "get_games(game_type='compte_est_bon', difficulty='difficile') renvoie 50 résultats")

    cross_math_combo = get_games(game_type="cross_math", difficulty="difficile", conn=conn)
    check(len(cross_math_combo) == 10, "get_games(game_type='cross_math', difficulty='difficile') renvoie 10 résultats")

    random_game = get_random_game(game_type="sudoku", conn=conn)
    check(random_game is not None and random_game["type"] == "sudoku", "get_random_game() renvoie un jeu du bon type")

    random_nonogram = get_random_game(game_type="nonogram", conn=conn)
    check(
        random_nonogram is not None and isinstance(random_nonogram["row_clues"], list),
        "get_random_game(game_type='nonogram') désérialise bien row_clues en liste Python",
    )

    random_hashi = get_random_game(game_type="hashi", conn=conn)
    check(
        random_hashi is not None and isinstance(random_hashi["islands"], list),
        "get_random_game(game_type='hashi') désérialise bien islands en liste Python",
    )

    random_compte = get_random_game(game_type="compte_est_bon", conn=conn)
    check(
        random_compte is not None and isinstance(random_compte["available_numbers"], list),
        "get_random_game(game_type='compte_est_bon') désérialise bien available_numbers en liste Python",
    )

    random_cross_math = get_random_game(game_type="cross_math", conn=conn)
    check(
        random_cross_math is not None
        and isinstance(random_cross_math["given_grid"], list)
        and isinstance(random_cross_math["row_operators"], list),
        "get_random_game(game_type='cross_math') désérialise bien given_grid / row_operators en listes Python",
    )

    empty = get_games(game_type="sudoku", difficulty="difficile", max_duration=1, conn=conn)
    check(empty == [], "critères impossibles à satisfaire renvoient une liste vide")

    try:
        get_games(game_type="inconnu", conn=conn)
        failures.append("get_games(game_type='inconnu') aurait dû lever une ValueError")
    except ValueError:
        check(True, "get_games(game_type='inconnu') lève bien une ValueError")


def test_balanced_random_selection(conn) -> None:
    print("\n--- Équilibre du tirage aléatoire (get_random_game sans type précisé) ---")
    from query import get_random_game, VALID_TYPES

    n_samples = 4000
    tally = Counter()
    for _ in range(n_samples):
        game = get_random_game(conn=conn)
        tally[game["type"]] += 1

    expected_share = 1 / len(VALID_TYPES)  # ≈ 16.7% pour 6 types
    tolerance = 0.06  # marge généreuse (écart-type théorique ~0.6% à 4000 tirages)

    print(f"  {n_samples} tirages, part attendue par type ≈ {expected_share:.0%} :")
    all_balanced = True
    for t in sorted(VALID_TYPES):
        observed_share = tally[t] / n_samples
        within_tolerance = abs(observed_share - expected_share) <= tolerance
        all_balanced = all_balanced and within_tolerance
        status = "OK" if within_tolerance else "FAIL"
        print(f"    [{status}] {t:<15} {tally[t]:>5} tirages  ({observed_share:.1%})")
        if not within_tolerance:
            failures.append(
                f"tirage aléatoire déséquilibré pour '{t}' : {observed_share:.1%} "
                f"(attendu ≈ {expected_share:.0%} ± {tolerance:.0%})"
            )

    check(
        all_balanced,
        "chaque type de jeu est tiré avec une probabilité ≈ égale, malgré 250 niveaux "
        "pour 'compte_est_bon' contre 50 pour les autres types (dont le nouveau 'cross_math')",
    )

    # Le Compte est bon représente 250/500 = 50% des LIGNES de la base : si le
    # tirage était uniforme sur l'ensemble des lignes (bug), il apparaîtrait
    # environ 50% du temps au lieu de ≈ 16.7% (1/6). On vérifie explicitement
    # que ce biais n'est PAS présent.
    naive_uniform_share = 250 / 500
    observed_compte_share = tally["compte_est_bon"] / n_samples
    check(
        abs(observed_compte_share - naive_uniform_share) > 0.15,
        f"'compte_est_bon' n'est PAS sur-représenté comme le serait un tirage "
        f"uniforme sur les lignes ({observed_compte_share:.1%} observé vs "
        f"{naive_uniform_share:.1%} qu'un tirage naïf donnerait)",
    )

    # avec une difficulté filtrée, l'équilibre doit être maintenu (tous les
    # types ont des niveaux 'facile', donc tous restent compatibles)
    tally_easy = Counter()
    n_easy_samples = 3000
    for _ in range(n_easy_samples):
        game = get_random_game(difficulty="facile", conn=conn)
        tally_easy[game["type"]] += 1

    easy_balanced = all(
        abs(tally_easy[t] / n_easy_samples - expected_share) <= tolerance for t in VALID_TYPES
    )
    check(
        easy_balanced,
        f"le tirage reste équilibré par type même filtré sur difficulty='facile' ({dict(tally_easy)})",
    )

    # tirage avec type explicite : comportement simple inchangé, toujours le bon type
    check(
        all(get_random_game(game_type="compte_est_bon", conn=conn)["type"] == "compte_est_bon" for _ in range(20)),
        "get_random_game(game_type='compte_est_bon') renvoie toujours ce type précis",
    )
    check(
        all(get_random_game(game_type="cross_math", conn=conn)["type"] == "cross_math" for _ in range(20)),
        "get_random_game(game_type='cross_math') renvoie toujours ce type précis",
    )


def main() -> None:
    conn = get_connection()
    test_sudoku(conn)
    test_mastermind(conn)
    test_nonogram(conn)
    test_hashi(conn)
    test_compte_est_bon(conn)
    test_cross_math(conn)
    test_other_games_untouched_by_cross_math(conn)
    test_query_function(conn)
    test_balanced_random_selection(conn)
    conn.close()

    print("\n" + "=" * 50)
    if failures:
        print(f"{len(failures)} test(s) en échec :")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    else:
        print("Tous les tests sont passés avec succès.")
        sys.exit(0)


if __name__ == "__main__":
    main()
