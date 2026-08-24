#!/usr/bin/env python3
"""
Tests unitaires pour l'API REST de BrainTrain (6 jeux) et la logique métier.
"""

from __future__ import annotations

import json
import sqlite3
import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
FILES_DIR = ROOT_DIR / "files"
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(FILES_DIR))

import db
import query
from server import evaluate_mastermind_guess, sanitize_game_data
from compte_est_bon_generator import verify_solution as verify_compte_est_bon_solution
from cross_math_generator import evaluate_chain, validate_player_grid


class TestMastermindLogic(unittest.TestCase):
    """Tests du calcul des correspondances Mastermind."""

    def test_evaluate_guess_all_correct(self):
        secret = [1, 2, 3, 4]
        guess = [1, 2, 3, 4]
        exact, misplaced = evaluate_mastermind_guess(secret, guess)
        self.assertEqual(exact, 4)
        self.assertEqual(misplaced, 0)


class TestCrossMathLogic(unittest.TestCase):
    """Tests de la règle de calcul et de la validation Cross Math."""

    def test_evaluate_chain_strict_left_to_right(self):
        # 2 + 3 * 4 doit donner (2 + 3) * 4 = 20 (et non 2 + 12 = 14)
        res = evaluate_chain([2, 3, 4], ["+", "*"])
        self.assertEqual(res, 20)

    def test_evaluate_chain_division_exact(self):
        res = evaluate_chain([20, 4, 2], ["/", "+"])
        self.assertEqual(res, 7)  # 20 / 4 = 5, 5 + 2 = 7

    def test_evaluate_chain_division_non_integer(self):
        res = evaluate_chain([20, 3], ["/"])
        self.assertIsNone(res)


class TestDataSanitization(unittest.TestCase):
    """Vérifie que les solutions secrètes ne sont pas exposées par défaut."""

    def test_sanitize_cross_math(self):
        raw = {
            "type": "cross_math",
            "id": 1,
            "grid_size": 3,
            "given_grid": "[[1, null, 3], [null, 5, null], [7, null, 9]]",
            "solution_grid": "[[1, 2, 3], [4, 5, 6], [7, 8, 9]]",
            "row_operators": '[["+", "+"], ["-", "+"], ["+", "-"]]',
            "col_operators": '[["+", "+"], ["+", "+"], ["+", "+"]]',
            "row_results": "[6, 7, 8]",
            "col_results": "[12, 15, 18]",
            "available_numbers": "[2, 4, 6, 8]",
        }
        sanitized = sanitize_game_data(raw, hide_solution=True)
        self.assertNotIn("solution_grid", sanitized)
        self.assertIn("given_grid", sanitized)
        self.assertIsInstance(sanitized["given_grid"], list)


class TestDatabaseQueries(unittest.TestCase):
    """Tests des requêtes via la base SQLite réelle."""

    def setUp(self):
        self.conn = db.get_connection()

    def tearDown(self):
        self.conn.close()

    def test_get_random_all_six_types(self):
        for g_type in ("sudoku", "mastermind", "nonogram", "hashi", "compte_est_bon", "cross_math"):
            game = query.get_random_game(game_type=g_type, difficulty="facile", conn=self.conn)
            self.assertIsNotNone(game, f"Aucun jeu pour {g_type}")
            self.assertEqual(game["type"], g_type)

    def test_get_games_total_counts(self):
        all_games = query.get_games(conn=self.conn)
        self.assertEqual(len(all_games), 500)


if __name__ == "__main__":
    unittest.main()
