#!/usr/bin/env python3
"""
Tests d'intégration de bout en bout pour le serveur BrainTrain (5 jeux).
"""

from __future__ import annotations

import json
import urllib.request
import urllib.parse
import unittest


SERVER_URL = "http://localhost:8000"


class TestBrainTrainIntegration(unittest.TestCase):
    """Tests d'intégration via requêtes HTTP réelles sur le serveur en écoute."""

    def get(self, path: str):
        url = f"{SERVER_URL}{path}"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.status, response.headers, response.read()

    def post(self, path: str, payload: dict):
        url = f"{SERVER_URL}{path}"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST", headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.status, response.headers, response.read()

    def test_static_index_html(self):
        status, _, content = self.get("/")
        self.assertEqual(status, 200)
        self.assertIn(b"BrainTrain", content)
        self.assertIn(b"view-sudoku", content)
        self.assertIn(b"view-mastermind", content)
        self.assertIn(b"view-nonogram", content)
        self.assertIn(b"view-hashi", content)
        self.assertIn(b"view-compte-est-bon", content)

    def test_api_health(self):
        status, _, body = self.get("/api/health")
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data.get("status"), "ok")

    def test_api_games_total_count(self):
        status, _, body = self.get("/api/games")
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["total"], 450)

    def test_compte_est_bon_gameplay_flow(self):
        status, _, body = self.get("/api/games/random?type=compte_est_bon&difficulty=facile")
        self.assertEqual(status, 200)
        game = json.loads(body.decode("utf-8"))
        game_id = game["id"]
        self.assertIn("target", game)
        self.assertIn("available_numbers", game)

        # Récupère la solution
        status, _, body = self.get(f"/api/games/compte_est_bon/{game_id}/solution")
        self.assertEqual(status, 200)
        sol_data = json.loads(body.decode("utf-8"))
        solution_steps = sol_data["solution_steps"]

        # Vérifie avec les étapes de la solution
        status, _, body = self.post("/api/games/compte_est_bon/verify", {"id": game_id, "steps": solution_steps})
        self.assertEqual(status, 200)
        res = json.loads(body.decode("utf-8"))
        self.assertTrue(res["is_complete"])
        self.assertTrue(res["is_valid"])


if __name__ == "__main__":
    unittest.main()
