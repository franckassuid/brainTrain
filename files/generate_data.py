"""
Script de remplissage automatique de la base de données.

Génère :
- 50 grilles de Sudoku (20 faciles / 20 moyennes / 10 difficiles)
- 50 parties de Mastermind (20 faciles / 20 moyennes / 10 difficiles)
- 50 Nonogrammes (20 faciles / 20 moyens / 10 difficiles)
- 50 puzzles Hashi / Ponts (20 faciles / 20 moyens / 10 difficiles)
- 250 niveaux du Compte est bon (100 faciles / 100 moyens / 50 difficiles)

IMPORTANT : les 50 Sudoku et 50 Mastermind déjà présents en base ne sont
JAMAIS supprimés ni régénérés par ce script (ils ne sont générés que si
les tables correspondantes sont vides). Les tables Nonogramme, Hashi et
Compte est bon, elles, sont vidées puis régénérées à chaque exécution.

Usage :
    python generate_data.py
"""

import sys
import time

from db import init_db
from sudoku_generator import generate_sudoku_puzzle
from mastermind_generator import generate_mastermind_game
from nonogram_generator import generate_nonogram_puzzle
from hashi_generator import generate_hashi_puzzle
from compte_est_bon_generator import generate_compte_est_bon_puzzle
import json

SUDOKU_DURATIONS = {"facile": 5, "moyen": 10, "difficile": 20}
MASTERMIND_DURATIONS = {"facile": 5, "moyen": 10, "difficile": 15}
NONOGRAM_DURATIONS = {"facile": 5, "moyen": 10, "difficile": 20}
HASHI_DURATIONS = {"facile": 5, "moyen": 10, "difficile": 20}
COMPTE_EST_BON_DURATIONS = {"facile": 5, "moyen": 10, "difficile": 20}

DISTRIBUTION = {"facile": 20, "moyen": 20, "difficile": 10}  # 50 au total
COMPTE_EST_BON_DISTRIBUTION = {"facile": 100, "moyen": 100, "difficile": 50}  # 250 au total


def generate_sudoku_batch(conn) -> None:
    print("Génération des grilles de Sudoku...")
    seen_grids = set()
    total = 0

    for difficulty, count in DISTRIBUTION.items():
        for i in range(count):
            t0 = time.time()
            while True:
                puzzle = generate_sudoku_puzzle(difficulty)
                if puzzle["starting_grid"] not in seen_grids:
                    seen_grids.add(puzzle["starting_grid"])
                    break
            elapsed = time.time() - t0

            conn.execute(
                """
                INSERT INTO sudoku_puzzles
                    (starting_grid, solution_grid, difficulty,
                     estimated_duration_minutes, clue_count)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    puzzle["starting_grid"],
                    puzzle["solution_grid"],
                    difficulty,
                    SUDOKU_DURATIONS[difficulty],
                    puzzle["clue_count"],
                ),
            )
            total += 1
            print(
                f"  [{total}/50] {difficulty:<10} "
                f"{puzzle['clue_count']} indices  ({elapsed:.2f}s)"
            )
    conn.commit()


def generate_mastermind_batch(conn) -> None:
    print("\nGénération des parties de Mastermind...")
    codes_by_difficulty: dict[str, set] = {"facile": set(), "moyen": set(), "difficile": set()}
    total = 0

    for difficulty, count in DISTRIBUTION.items():
        for i in range(count):
            game = generate_mastermind_game(difficulty, codes_by_difficulty[difficulty])
            conn.execute(
                """
                INSERT INTO mastermind_games
                    (secret_code, num_colors, num_positions, max_attempts,
                     difficulty, estimated_duration_minutes)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    game["secret_code"],
                    game["num_colors"],
                    game["num_positions"],
                    game["max_attempts"],
                    difficulty,
                    MASTERMIND_DURATIONS[difficulty],
                ),
            )
            total += 1
            print(f"  [{total}/50] {difficulty:<10} code={game['secret_code']}")
    conn.commit()


def generate_nonogram_batch(conn) -> None:
    print("\nGénération des Nonogrammes...")
    seen_grids = set()
    total = 0
    unverified = 0

    for difficulty, count in DISTRIBUTION.items():
        for i in range(count):
            t0 = time.time()
            while True:
                puzzle = generate_nonogram_puzzle(difficulty)
                if puzzle["solution_grid"] not in seen_grids:
                    seen_grids.add(puzzle["solution_grid"])
                    break
            elapsed = time.time() - t0

            if not puzzle["solution_unique"]:
                unverified += 1

            conn.execute(
                """
                INSERT INTO nonogram_puzzles
                    (num_rows, num_cols, solution_grid, row_clues, col_clues,
                     difficulty, estimated_duration_minutes, solution_unique)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    puzzle["num_rows"],
                    puzzle["num_cols"],
                    puzzle["solution_grid"],
                    json.dumps(puzzle["row_clues"]),
                    json.dumps(puzzle["col_clues"]),
                    difficulty,
                    NONOGRAM_DURATIONS[difficulty],
                    1 if puzzle["solution_unique"] else 0,
                ),
            )
            total += 1
            print(
                f"  [{total}/50] {difficulty:<10} "
                f"{puzzle['num_rows']}x{puzzle['num_cols']}  "
                f"unique={puzzle['solution_unique']}  ({elapsed:.3f}s)"
            )
    conn.commit()
    if unverified:
        print(f"  ATTENTION : {unverified} grille(s) acceptée(s) sans unicité confirmée (cf. README.md).")


def generate_hashi_batch(conn) -> None:
    print("\nGénération des puzzles Hashi (Ponts)...")
    total = 0
    checked = 0
    unique = 0

    for difficulty, count in DISTRIBUTION.items():
        for i in range(count):
            t0 = time.time()
            puzzle = generate_hashi_puzzle(difficulty)
            elapsed = time.time() - t0

            if puzzle["uniqueness_checked"]:
                checked += 1
                if puzzle["solution_unique"]:
                    unique += 1

            conn.execute(
                """
                INSERT INTO hashi_puzzles
                    (num_rows, num_cols, islands, solution_bridges,
                     difficulty, estimated_duration_minutes, solution_unique)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    puzzle["num_rows"],
                    puzzle["num_cols"],
                    json.dumps(puzzle["islands"]),
                    json.dumps(puzzle["bridges"]),
                    difficulty,
                    HASHI_DURATIONS[difficulty],
                    1 if puzzle["solution_unique"] else 0,
                ),
            )
            total += 1
            unique_str = (
                "oui" if puzzle["solution_unique"] else
                ("non vérifiée" if not puzzle["uniqueness_checked"] else "NON unique (!)")
            )
            print(
                f"  [{total}/50] {difficulty:<10} "
                f"{len(puzzle['islands'])} îles  unicité={unique_str}  ({elapsed:.3f}s)"
            )
    conn.commit()
    print(
        f"  Unicité vérifiée pour {checked}/{total} puzzles "
        f"(petites grilles seulement, {unique} unique(s) confirmée(s) — cf. README.md)."
    )


def generate_compte_est_bon_batch(conn) -> None:
    print("\nGénération des niveaux du Compte est bon...")
    seen_combinations = set()
    total = 0
    target_total = sum(COMPTE_EST_BON_DISTRIBUTION.values())

    for difficulty, count in COMPTE_EST_BON_DISTRIBUTION.items():
        for i in range(count):
            t0 = time.time()
            while True:
                puzzle = generate_compte_est_bon_puzzle(difficulty)
                key = (tuple(sorted(puzzle["available_numbers"])), puzzle["target"])
                if key not in seen_combinations:
                    seen_combinations.add(key)
                    break
            elapsed = time.time() - t0

            conn.execute(
                """
                INSERT INTO compte_est_bon_puzzles
                    (available_numbers, target, allowed_operations,
                     solution_steps, solution_readable,
                     difficulty, estimated_duration_minutes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    json.dumps(puzzle["available_numbers"]),
                    puzzle["target"],
                    json.dumps(["+", "-", "*", "/"]),
                    json.dumps(puzzle["solution_steps"]),
                    puzzle["solution_readable"],
                    difficulty,
                    COMPTE_EST_BON_DURATIONS[difficulty],
                ),
            )
            total += 1
            if total % 25 == 0 or total == target_total:
                print(
                    f"  [{total}/{target_total}] {difficulty:<10} "
                    f"{puzzle['available_numbers']} -> {puzzle['target']}  ({elapsed:.3f}s)"
                )
    conn.commit()


def main() -> None:
    print("=== Remplissage de la base d'entraînement mental ===\n")
    conn = init_db(reset=False)  # ne supprime jamais la base existante

    sudoku_count = conn.execute("SELECT COUNT(*) FROM sudoku_puzzles").fetchone()[0]
    if sudoku_count == 0:
        generate_sudoku_batch(conn)
    else:
        print(f"Sudoku : {sudoku_count} grilles déjà présentes en base, conservées telles quelles.")

    mastermind_count = conn.execute("SELECT COUNT(*) FROM mastermind_games").fetchone()[0]
    if mastermind_count == 0:
        generate_mastermind_batch(conn)
    else:
        print(f"Mastermind : {mastermind_count} parties déjà présentes en base, conservées telles quelles.")

    # Nonogramme, Hashi et Compte est bon : tables régénérées à chaque
    # exécution du script (elles ne contiennent pas de données à préserver
    # comme Sudoku/Mastermind)
    conn.execute("DELETE FROM nonogram_puzzles")
    conn.execute("DELETE FROM hashi_puzzles")
    conn.execute("DELETE FROM compte_est_bon_puzzles")
    conn.commit()
    generate_nonogram_batch(conn)
    generate_hashi_batch(conn)
    generate_compte_est_bon_batch(conn)

    sudoku_count = conn.execute("SELECT COUNT(*) FROM sudoku_puzzles").fetchone()[0]
    mastermind_count = conn.execute("SELECT COUNT(*) FROM mastermind_games").fetchone()[0]
    nonogram_count = conn.execute("SELECT COUNT(*) FROM nonogram_puzzles").fetchone()[0]
    hashi_count = conn.execute("SELECT COUNT(*) FROM hashi_puzzles").fetchone()[0]
    compte_count = conn.execute("SELECT COUNT(*) FROM compte_est_bon_puzzles").fetchone()[0]

    print(
        f"\nTerminé : {sudoku_count} Sudoku, {mastermind_count} Mastermind, "
        f"{nonogram_count} Nonogrammes, {hashi_count} Hashi, "
        f"{compte_count} Compte est bon."
    )
    conn.close()


if __name__ == "__main__":
    sys.exit(main())
