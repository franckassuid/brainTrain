#!/usr/bin/env python3
"""
Tests unitaires pour l'API REST de BrainTrain (5 jeux) et la logique métier.
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


class TestMastermindLogic(unittest.TestCase):
    """Tests du calcul des correspondances Mastermind."""

    def test_evaluate_guess_all_correct(self):
        secret = [1, 2, 3, 4]
        guess = [1, 2, 3, 4]
        exact, misplaced = evaluate_mastermind_guess(secret, guess)
        self.assertEqual(exact, 4)
        self.assertEqual(misplaced, 0)

    def test_evaluate_guess_mixed(self):
        secret = [1, 2, 3, 4]
        guess = [1, 3, 2, 5]
        exact, misplaced = evaluate_mastermind_guess(secret, guess)
        self.assertEqual(exact, 1)
        self.assertEqual(misplaced, 2)


class TestCompteEstBonLogic(unittest.TestCase):
    """Tests de la vérification de solution du Compte est bon."""

    def test_valid_solution(self):
        numbers = [25, 50, 4, 3]
        target = 103
        steps = [
            {"a": 25, "op": "*", "b": 4, "result": 100},
            {"a": 100, "op": "+", "b": 3, "result": 103},
        ]
        errors = verify_compte_est_bon_solution(numbers, target, steps)
        self.assertEqual(errors, [])

    def test_invalid_number_reuse(self):
        numbers = [25, 4]
        target = 104
        steps = [
            {"a": 25, "op": "*", "b": 4, "result": 100},
            {"a": 100, "op": "+", "b": 4, "result": 104},  # 4 déjà consommé
        ]
        errors = verify_compte_est_bon_solution(numbers, target, steps)
        self.assertGreater(len(errors), 0)


class TestDataSanitization(unittest.TestCase):
    """Vérifie que les solutions secrètes ne sont pas exposées par défaut."""

    def test_sanitize_compte_est_bon(self):
        raw = {
            "type": "compte_est_bon",
            "id": 1,
            "available_numbers": "[25, 8, 3, 7]",
            "target": 100,
            "solution_steps": '[{"a":25,"op":"+","b":8,"result":33}]',
            "solution_readable": "25 + 8 = 33",
        }
        sanitized = sanitize_game_data(raw, hide_solution=True)
        self.assertNotIn("solution_steps", sanitized)
        self.assertNotIn("solution_readable", sanitized)
        self.assertIsInstance(sanitized["available_numbers"], list)


class TestDatabaseQueries(unittest.TestCase):
    """Tests des requêtes via la base SQLite réelle."""

    def setUp(self):
        self.conn = db.get_connection()

    def tearDown(self):
        self.conn.close()

    def test_get_random_all_five_types(self):
        for g_type in ("sudoku", "mastermind", "nonogram", "hashi", "compte_est_bon"):
            game = query.get_random_game(game_type=g_type, difficulty="facile", conn=self.conn)
            self.assertIsNotNone(game, f"Aucun jeu pour {g_type}")
            self.assertEqual(game["type"], g_type)

    def test_get_games_total_counts(self):
        all_games = query.get_games(conn=self.conn)
        self.assertEqual(len(all_games), 450)


if __name__ == "__main__":
    unittest.main()
