"""
Fonctions permettant de demander un jeu à la base selon :
- son type ('sudoku', 'mastermind', 'nonogram', 'hashi', 'compte_est_bon'
  ou 'cross_math')
- sa difficulté ('facile', 'moyen', 'difficile')
- le temps disponible (en minutes)

Tous les paramètres sont optionnels et combinables.

Tirage aléatoire "sans type précisé" (voir get_random_game) :
Comme les types de jeux n'ont pas le même nombre de niveaux en base
(250 pour le Compte est bon contre 50 pour les autres), un tirage
uniforme sur l'ensemble des lignes favoriserait mécaniquement le Compte
est bon (5x plus de chances d'être choisi). Pour éviter ce biais, le
tirage se fait en DEUX ÉTAPES :
  1. on choisit un TYPE de jeu au hasard, de façon équiprobable, parmi
     les seuls types qui ont au moins un résultat pour les filtres
     demandés (difficulté / durée) ;
  2. on choisit ensuite un jeu au hasard DANS ce type.
Chaque type de jeu compatible garde ainsi la même probabilité d'être
proposé, quel que soit son nombre de niveaux en base.
"""

from __future__ import annotations

import json
import random
import sqlite3

from db import get_connection

VALID_TYPES = {"sudoku", "mastermind", "nonogram", "hashi", "compte_est_bon", "cross_math"}
VALID_DIFFICULTIES = {"facile", "moyen", "difficile"}


def _apply_filters(query, params, difficulty, max_duration):
    if difficulty:
        query += " AND difficulty = ?"
        params.append(difficulty)
    if max_duration is not None:
        query += " AND estimated_duration_minutes <= ?"
        params.append(max_duration)
    return query, params


def _fetch_sudoku(conn, difficulty=None, max_duration=None):
    query, params = _apply_filters("SELECT * FROM sudoku_puzzles WHERE 1=1", [], difficulty, max_duration)
    rows = conn.execute(query, params).fetchall()
    return [dict(row, type="sudoku") for row in rows]


def _fetch_mastermind(conn, difficulty=None, max_duration=None):
    query, params = _apply_filters("SELECT * FROM mastermind_games WHERE 1=1", [], difficulty, max_duration)
    rows = conn.execute(query, params).fetchall()
    return [dict(row, type="mastermind") for row in rows]


def _fetch_nonogram(conn, difficulty=None, max_duration=None):
    query, params = _apply_filters("SELECT * FROM nonogram_puzzles WHERE 1=1", [], difficulty, max_duration)
    rows = conn.execute(query, params).fetchall()
    games = []
    for row in rows:
        game = dict(row, type="nonogram")
        game["row_clues"] = json.loads(game["row_clues"])
        game["col_clues"] = json.loads(game["col_clues"])
        game["solution_unique"] = bool(game["solution_unique"])
        games.append(game)
    return games


def _fetch_hashi(conn, difficulty=None, max_duration=None):
    query, params = _apply_filters("SELECT * FROM hashi_puzzles WHERE 1=1", [], difficulty, max_duration)
    rows = conn.execute(query, params).fetchall()
    games = []
    for row in rows:
        game = dict(row, type="hashi")
        game["islands"] = json.loads(game["islands"])
        game["solution_bridges"] = json.loads(game["solution_bridges"])
        game["solution_unique"] = bool(game["solution_unique"])
        games.append(game)
    return games


def _fetch_compte_est_bon(conn, difficulty=None, max_duration=None):
    query, params = _apply_filters("SELECT * FROM compte_est_bon_puzzles WHERE 1=1", [], difficulty, max_duration)
    rows = conn.execute(query, params).fetchall()
    games = []
    for row in rows:
        game = dict(row, type="compte_est_bon")
        game["available_numbers"] = json.loads(game["available_numbers"])
        game["allowed_operations"] = json.loads(game["allowed_operations"])
        game["solution_steps"] = json.loads(game["solution_steps"])
        games.append(game)
    return games


def _fetch_cross_math(conn, difficulty=None, max_duration=None):
    query, params = _apply_filters("SELECT * FROM cross_math_puzzles WHERE 1=1", [], difficulty, max_duration)
    rows = conn.execute(query, params).fetchall()
    games = []
    for row in rows:
        game = dict(row, type="cross_math")
        game["given_grid"] = json.loads(game["given_grid"])
        game["solution_grid"] = json.loads(game["solution_grid"])
        game["row_operators"] = json.loads(game["row_operators"])
        game["col_operators"] = json.loads(game["col_operators"])
        game["row_results"] = json.loads(game["row_results"])
        game["col_results"] = json.loads(game["col_results"])
        game["available_numbers"] = json.loads(game["available_numbers"])
        game["solution_unique"] = bool(game["solution_unique"])
        games.append(game)
    return games


# Registre centralisé : un seul endroit à mettre à jour pour ajouter un type.
TYPE_FETCHERS = {
    "sudoku": _fetch_sudoku,
    "mastermind": _fetch_mastermind,
    "nonogram": _fetch_nonogram,
    "hashi": _fetch_hashi,
    "compte_est_bon": _fetch_compte_est_bon,
    "cross_math": _fetch_cross_math,
}


def get_games(
    game_type: str | None = None,
    difficulty: str | None = None,
    max_duration: int | None = None,
    conn: sqlite3.Connection | None = None,
) -> list[dict]:
    """
    Renvoie la liste des jeux correspondant aux critères donnés.

    game_type    : 'sudoku', 'mastermind', 'nonogram', 'hashi',
                   'compte_est_bon', 'cross_math', ou None pour tous les types.
    difficulty   : 'facile', 'moyen', 'difficile', ou None pour toutes.
    max_duration : durée max en minutes disponible pour jouer, ou None.
    conn         : connexion SQLite existante (sinon une nouvelle est ouverte).
    """
    if game_type is not None and game_type not in VALID_TYPES:
        raise ValueError(f"game_type invalide : {game_type!r} (attendu : {VALID_TYPES})")
    if difficulty is not None and difficulty not in VALID_DIFFICULTIES:
        raise ValueError(f"difficulty invalide : {difficulty!r} (attendu : {VALID_DIFFICULTIES})")

    own_conn = conn is None
    conn = conn or get_connection()

    try:
        results = []
        for t, fetch in TYPE_FETCHERS.items():
            if game_type in (None, t):
                results += fetch(conn, difficulty, max_duration)
        return results
    finally:
        if own_conn:
            conn.close()


def get_random_game(
    game_type: str | None = None,
    difficulty: str | None = None,
    max_duration: int | None = None,
    conn: sqlite3.Connection | None = None,
) -> dict | None:
    """
    Tire un jeu au hasard parmi ceux qui correspondent aux critères.

    - Si `game_type` est précisé : tirage uniforme parmi les jeux de ce
      type correspondant aux filtres (comportement simple, inchangé).
    - Si `game_type` est None : tirage en DEUX ÉTAPES pour garantir que
      chaque type de jeu compatible avec les filtres a la même
      probabilité d'être proposé, indépendamment de son nombre de
      niveaux en base (voir docstring du module). Concrètement :
        1. on détermine les types ayant au moins un jeu correspondant
           aux filtres (difficulté / durée) ;
        2. on choisit un type au hasard, de façon équiprobable, parmi
           ces types compatibles ;
        3. on choisit un jeu au hasard dans ce type.
    """
    if game_type is not None:
        games = get_games(game_type, difficulty, max_duration, conn)
        return random.choice(games) if games else None

    if difficulty is not None and difficulty not in VALID_DIFFICULTIES:
        raise ValueError(f"difficulty invalide : {difficulty!r} (attendu : {VALID_DIFFICULTIES})")

    own_conn = conn is None
    conn = conn or get_connection()

    try:
        games_by_type: dict[str, list[dict]] = {}
        for t, fetch in TYPE_FETCHERS.items():
            games = fetch(conn, difficulty, max_duration)
            if games:
                games_by_type[t] = games

        if not games_by_type:
            return None

        chosen_type = random.choice(list(games_by_type.keys()))
        return random.choice(games_by_type[chosen_type])
    finally:
        if own_conn:
            conn.close()


if __name__ == "__main__":
    # Petite démo manuelle
    print("Un Sudoku facile jouable en moins de 6 minutes :")
    print(get_random_game(game_type="sudoku", difficulty="facile", max_duration=6))

    print("\nN'importe quel jeu jouable en 5 minutes ou moins (tirage équilibré par type) :")
    print(get_random_game(max_duration=5))

    print("\nUne partie de Mastermind difficile :")
    print(get_random_game(game_type="mastermind", difficulty="difficile"))

    print("\nUn Nonogramme moyen :")
    print(get_random_game(game_type="nonogram", difficulty="moyen"))

    print("\nUn puzzle Hashi facile :")
    print(get_random_game(game_type="hashi", difficulty="facile"))

    print("\nUn niveau du Compte est bon difficile :")
    print(get_random_game(game_type="compte_est_bon", difficulty="difficile"))

    print("\nUn niveau Cross Math moyen :")
    print(get_random_game(game_type="cross_math", difficulty="moyen"))

    print("\nRépartition observée sur 2000 tirages sans type précisé :")
    from collections import Counter
    tally = Counter(get_random_game()["type"] for _ in range(2000))
    for t in sorted(VALID_TYPES):
        print(f"  {t:<15} {tally[t]:>5}  ({100 * tally[t] / 2000:.1f}%)")
