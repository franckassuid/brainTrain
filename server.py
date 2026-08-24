#!/usr/bin/env python3
"""
BrainTrain - Serveur Backend & Fichiers Statiques.
Supporte 5 jeux : Sudoku, Mastermind, Nonogramme, Hashi (Ponts), Le Compte est bon.
Utilise exclusivement la bibliothèque standard Python pour un démarrage rapide sans dépendances.
"""

from __future__ import annotations

import json
import mimetypes
import os
import sqlite3
import sys
import urllib.parse
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

# Inclusion du dossier files/ dans sys.path pour réutiliser les modules existants
ROOT_DIR = Path(__file__).parent
FILES_DIR = ROOT_DIR / "files"
STATIC_DIR = ROOT_DIR / "static"
sys.path.insert(0, str(FILES_DIR))

import db  # noqa: E402
import query  # noqa: E402
from hashi_generator import validate_hashi_solution  # noqa: E402
from compte_est_bon_generator import verify_solution as verify_compte_est_bon_solution  # noqa: E402


def evaluate_mastermind_guess(secret_code: list[int], guess: list[int]) -> tuple[int, int]:
    """
    Calcule le nombre de pions bien placés (exacts) et mal placés.
    """
    if len(secret_code) != len(guess):
        raise ValueError(f"Taille de supposition invalide ({len(guess)} au lieu de {len(secret_code)})")

    exact = 0
    secret_unmatched = []
    guess_unmatched = []

    for s, g in zip(secret_code, guess):
        if s == g:
            exact += 1
        else:
            secret_unmatched.append(s)
            guess_unmatched.append(g)

    misplaced = 0
    for g in guess_unmatched:
        if g in secret_unmatched:
            misplaced += 1
            secret_unmatched.remove(g)

    return exact, misplaced


def sanitize_game_data(game: sqlite3.Row | dict, hide_solution: bool = True) -> dict:
    d = dict(game)
    g_type = d.get("type")

    # Désérialisation JSON si nécessaire
    for field in ("row_clues", "col_clues", "islands", "solution_bridges", "available_numbers", "allowed_operations", "solution_steps"):
        if field in d and isinstance(d[field], str):
            try:
                d[field] = json.loads(d[field])
            except Exception:
                pass

    if hide_solution:
        if g_type == "sudoku" and "solution_grid" in d:
            del d["solution_grid"]
        elif g_type == "mastermind" and "secret_code" in d:
            del d["secret_code"]
        elif g_type == "nonogram" and "solution_grid" in d:
            del d["solution_grid"]
        elif g_type == "hashi" and "solution_bridges" in d:
            del d["solution_bridges"]
        elif g_type == "compte_est_bon":
            if "solution_steps" in d:
                del d["solution_steps"]
            if "solution_readable" in d:
                del d["solution_readable"]

    return d


class BrainTrainHandler(SimpleHTTPRequestHandler):
    """Gestionnaire HTTP pour l'API REST et les fichiers statiques de l'application."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def send_json_response(self, data: dict | list, status: int = 200) -> None:
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(payload)

    def send_error_response(self, message: str, status: int = 400) -> None:
        self.send_json_response({"error": message}, status=status)

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    # -------------------------------------------------------------------------
    # Routeur GET
    # -------------------------------------------------------------------------
    def do_GET(self) -> None:
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path.rstrip("/")
        query_params = urllib.parse.parse_qs(parsed_url.query)

        # Health Check
        if path == "/api/health":
            self.send_json_response({"status": "ok", "app": "BrainTrain", "version": "3.0"})
            return

        # Tirage d'un jeu aléatoire (tirage équilibré entre les 5 types)
        if path == "/api/games/random":
            self.handle_get_random_game(query_params)
            return

        # Liste des jeux selon filtres
        if path == "/api/games":
            self.handle_get_games(query_params)
            return

        # Routes spécifiques par jeu
        parts = path.split("/")
        if len(parts) >= 5 and parts[1] == "api" and parts[2] == "games":
            game_type = parts[3]
            if parts[4].isdigit():
                game_id = int(parts[4])
                is_solution = len(parts) == 6 and parts[5] in ("solution", "reveal")

                if game_type == "sudoku":
                    if is_solution:
                        self.handle_get_sudoku_solution(game_id)
                    else:
                        self.handle_get_sudoku(game_id)
                    return
                elif game_type == "mastermind":
                    if is_solution:
                        self.handle_get_mastermind_reveal(game_id)
                    else:
                        self.handle_get_mastermind(game_id)
                    return
                elif game_type == "nonogram":
                    if is_solution:
                        self.handle_get_nonogram_solution(game_id)
                    else:
                        self.handle_get_nonogram(game_id)
                    return
                elif game_type == "hashi":
                    if is_solution:
                        self.handle_get_hashi_solution(game_id)
                    else:
                        self.handle_get_hashi(game_id)
                    return
                elif game_type == "compte_est_bon":
                    if is_solution:
                        self.handle_get_compte_est_bon_solution(game_id)
                    else:
                        self.handle_get_compte_est_bon(game_id)
                    return

        # Service de fichiers statiques
        if not path.startswith("/api"):
            target_file = STATIC_DIR / (path[1:] if path else "index.html")
            if target_file.is_file():
                super().do_GET()
                return
            elif path == "" or path == "/":
                self.path = "/index.html"
                super().do_GET()
                return

        super().do_GET()

    # -------------------------------------------------------------------------
    # Routeur POST
    # -------------------------------------------------------------------------
    def do_POST(self) -> None:
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path.rstrip("/")

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"

        try:
            payload = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self.send_error_response("Format JSON invalide", status=400)
            return

        if path == "/api/games/sudoku/verify":
            self.handle_verify_sudoku(payload)
            return

        if path == "/api/games/mastermind/guess":
            self.handle_mastermind_guess(payload)
            return

        if path == "/api/games/nonogram/verify":
            self.handle_verify_nonogram(payload)
            return

        if path == "/api/games/hashi/verify":
            self.handle_verify_hashi(payload)
            return

        if path == "/api/games/compte_est_bon/verify":
            self.handle_verify_compte_est_bon(payload)
            return

        self.send_error_response("Route POST non trouvée", status=404)

    # -------------------------------------------------------------------------
    # Handlers Spécifiques
    # -------------------------------------------------------------------------
    def handle_get_random_game(self, params: dict) -> None:
        game_type = params.get("type", [None])[0]
        difficulty = params.get("difficulty", [None])[0]
        max_duration_str = params.get("max_duration", [None])[0]

        max_duration = int(max_duration_str) if max_duration_str and max_duration_str.isdigit() else None

        try:
            conn = db.get_connection()
            game = query.get_random_game(
                game_type=game_type if game_type in query.VALID_TYPES else None,
                difficulty=difficulty if difficulty in query.VALID_DIFFICULTIES else None,
                max_duration=max_duration,
                conn=conn,
            )
            conn.close()

            if not game:
                self.send_error_response("Aucun jeu trouvé pour ces critères", status=404)
                return

            self.send_json_response(sanitize_game_data(game, hide_solution=True))
        except Exception as e:
            self.send_error_response(f"Erreur interne : {str(e)}", status=500)

    def handle_get_games(self, params: dict) -> None:
        game_type = params.get("type", [None])[0]
        difficulty = params.get("difficulty", [None])[0]
        max_duration_str = params.get("max_duration", [None])[0]

        max_duration = int(max_duration_str) if max_duration_str and max_duration_str.isdigit() else None

        try:
            conn = db.get_connection()
            games = query.get_games(
                game_type=game_type if game_type in query.VALID_TYPES else None,
                difficulty=difficulty if difficulty in query.VALID_DIFFICULTIES else None,
                max_duration=max_duration,
                conn=conn,
            )
            conn.close()

            sanitized = [sanitize_game_data(g, hide_solution=True) for g in games]
            self.send_json_response({"total": len(sanitized), "games": sanitized})
        except Exception as e:
            self.send_error_response(f"Erreur interne : {str(e)}", status=500)

    # --- SUDOKU ---
    def handle_get_sudoku(self, sudoku_id: int) -> None:
        conn = db.get_connection()
        row = conn.execute("SELECT * FROM sudoku_puzzles WHERE id = ?", (sudoku_id,)).fetchone()
        conn.close()
        if not row:
            self.send_error_response("Grille Sudoku non trouvée", status=404)
            return
        self.send_json_response(sanitize_game_data(dict(row, type="sudoku"), hide_solution=True))

    def handle_get_sudoku_solution(self, sudoku_id: int) -> None:
        conn = db.get_connection()
        row = conn.execute("SELECT id, solution_grid FROM sudoku_puzzles WHERE id = ?", (sudoku_id,)).fetchone()
        conn.close()
        if not row:
            self.send_error_response("Grille Sudoku non trouvée", status=404)
            return
        self.send_json_response({"id": row["id"], "solution_grid": row["solution_grid"]})

    def handle_verify_sudoku(self, payload: dict) -> None:
        sudoku_id = payload.get("id")
        user_grid = payload.get("grid")

        if not sudoku_id or not isinstance(user_grid, str) or len(user_grid) != 81:
            self.send_error_response("Paramètres 'id' et 'grid' (81 caractères) requis", status=400)
            return

        conn = db.get_connection()
        row = conn.execute("SELECT id, solution_grid FROM sudoku_puzzles WHERE id = ?", (sudoku_id,)).fetchone()
        conn.close()

        if not row:
            self.send_error_response("Grille Sudoku non trouvée", status=404)
            return

        solution = row["solution_grid"]
        errors = []
        is_complete = True

        for i in range(81):
            char_user = user_grid[i]
            char_sol = solution[i]
            if char_user == "0":
                is_complete = False
            elif char_user != char_sol:
                errors.append(i)

        is_valid = len(errors) == 0
        self.send_json_response({
            "id": sudoku_id,
            "is_valid": is_valid,
            "is_complete": is_complete and is_valid,
            "errors": errors,
        })

    # --- MASTERMIND ---
    def handle_get_mastermind(self, game_id: int) -> None:
        conn = db.get_connection()
        row = conn.execute("SELECT * FROM mastermind_games WHERE id = ?", (game_id,)).fetchone()
        conn.close()
        if not row:
            self.send_error_response("Partie Mastermind non trouvée", status=404)
            return
        self.send_json_response(sanitize_game_data(dict(row, type="mastermind"), hide_solution=True))

    def handle_get_mastermind_reveal(self, game_id: int) -> None:
        conn = db.get_connection()
        row = conn.execute("SELECT id, secret_code FROM mastermind_games WHERE id = ?", (game_id,)).fetchone()
        conn.close()
        if not row:
            self.send_error_response("Partie Mastermind non trouvée", status=404)
            return
        code_list = [int(v) for v in row["secret_code"].split(",")]
        self.send_json_response({"id": row["id"], "secret_code": code_list})

    def handle_mastermind_guess(self, payload: dict) -> None:
        game_id = payload.get("id")
        guess = payload.get("guess")

        if not game_id or not isinstance(guess, list):
            self.send_error_response("Paramètres 'id' et 'guess' requis", status=400)
            return

        conn = db.get_connection()
        row = conn.execute("SELECT * FROM mastermind_games WHERE id = ?", (game_id,)).fetchone()
        conn.close()

        if not row:
            self.send_error_response("Partie Mastermind non trouvée", status=404)
            return

        secret_code = [int(v) for v in row["secret_code"].split(",")]
        if len(guess) != len(secret_code):
            self.send_error_response(f"Longueur invalide ({len(guess)} au lieu de {len(secret_code)})", status=400)
            return

        exact, misplaced = evaluate_mastermind_guess(secret_code, guess)
        won = exact == len(secret_code)

        self.send_json_response({
            "id": game_id,
            "guess": guess,
            "exact": exact,
            "misplaced": misplaced,
            "won": won,
            "secret_code": secret_code if won else None,
        })

    # --- NONOGRAMME ---
    def handle_get_nonogram(self, game_id: int) -> None:
        conn = db.get_connection()
        row = conn.execute("SELECT * FROM nonogram_puzzles WHERE id = ?", (game_id,)).fetchone()
        conn.close()
        if not row:
            self.send_error_response("Puzzle Nonogramme non trouvé", status=404)
            return
        self.send_json_response(sanitize_game_data(dict(row, type="nonogram"), hide_solution=True))

    def handle_get_nonogram_solution(self, game_id: int) -> None:
        conn = db.get_connection()
        row = conn.execute("SELECT id, solution_grid FROM nonogram_puzzles WHERE id = ?", (game_id,)).fetchone()
        conn.close()
        if not row:
            self.send_error_response("Puzzle Nonogramme non trouvé", status=404)
            return
        self.send_json_response({"id": row["id"], "solution_grid": row["solution_grid"]})

    def handle_verify_nonogram(self, payload: dict) -> None:
        game_id = payload.get("id")
        user_grid = payload.get("grid")

        if not game_id or not isinstance(user_grid, str):
            self.send_error_response("Paramètres 'id' et 'grid' requis", status=400)
            return

        conn = db.get_connection()
        row = conn.execute("SELECT id, num_rows, num_cols, solution_grid FROM nonogram_puzzles WHERE id = ?", (game_id,)).fetchone()
        conn.close()

        if not row:
            self.send_error_response("Puzzle Nonogramme non trouvé", status=404)
            return

        total_cells = row["num_rows"] * row["num_cols"]
        if len(user_grid) != total_cells:
            self.send_error_response(f"Longueur invalide ({len(user_grid)} au lieu de {total_cells})", status=400)
            return

        solution = row["solution_grid"]
        errors = [i for i in range(total_cells) if user_grid[i] == "1" and solution[i] != "1"]
        is_complete = user_grid == solution
        is_valid = len(errors) == 0

        self.send_json_response({
            "id": game_id,
            "is_valid": is_valid,
            "is_complete": is_complete,
            "errors": errors,
        })

    # --- HASHI (PONTS) ---
    def handle_get_hashi(self, game_id: int) -> None:
        conn = db.get_connection()
        row = conn.execute("SELECT * FROM hashi_puzzles WHERE id = ?", (game_id,)).fetchone()
        conn.close()
        if not row:
            self.send_error_response("Puzzle Hashi non trouvé", status=404)
            return
        self.send_json_response(sanitize_game_data(dict(row, type="hashi"), hide_solution=True))

    def handle_get_hashi_solution(self, game_id: int) -> None:
        conn = db.get_connection()
        row = conn.execute("SELECT id, solution_bridges FROM hashi_puzzles WHERE id = ?", (game_id,)).fetchone()
        conn.close()
        if not row:
            self.send_error_response("Puzzle Hashi non trouvé", status=404)
            return
        bridges = json.loads(row["solution_bridges"])
        self.send_json_response({"id": row["id"], "solution_bridges": bridges})

    def handle_verify_hashi(self, payload: dict) -> None:
        game_id = payload.get("id")
        user_bridges = payload.get("bridges")

        if not game_id or not isinstance(user_bridges, list):
            self.send_error_response("Paramètres 'id' et 'bridges' requis", status=400)
            return

        conn = db.get_connection()
        row = conn.execute("SELECT * FROM hashi_puzzles WHERE id = ?", (game_id,)).fetchone()
        conn.close()

        if not row:
            self.send_error_response("Puzzle Hashi non trouvé", status=404)
            return

        islands_data = json.loads(row["islands"])
        islands = [(r, c) for r, c, v in islands_data]
        values = [v for r, c, v in islands_data]

        bridges_tuples = [(int(b[0]), int(b[1]), int(b[2])) for b in user_bridges if len(b) >= 3 and b[2] > 0]
        validation_errors = validate_hashi_solution(islands, values, bridges_tuples)
        is_complete = len(validation_errors) == 0

        self.send_json_response({
            "id": game_id,
            "is_valid": len([e for e in validation_errors if "somme des ponts" not in e and "connectées" not in e]) == 0,
            "is_complete": is_complete,
            "errors": validation_errors,
        })

    # --- LE COMPTE EST BON ---
    def handle_get_compte_est_bon(self, game_id: int) -> None:
        conn = db.get_connection()
        row = conn.execute("SELECT * FROM compte_est_bon_puzzles WHERE id = ?", (game_id,)).fetchone()
        conn.close()
        if not row:
            self.send_error_response("Niveau Compte est bon non trouvé", status=404)
            return
        self.send_json_response(sanitize_game_data(dict(row, type="compte_est_bon"), hide_solution=True))

    def handle_get_compte_est_bon_solution(self, game_id: int) -> None:
        conn = db.get_connection()
        row = conn.execute("SELECT id, solution_steps, solution_readable FROM compte_est_bon_puzzles WHERE id = ?", (game_id,)).fetchone()
        conn.close()
        if not row:
            self.send_error_response("Niveau Compte est bon non trouvé", status=404)
            return
        steps = json.loads(row["solution_steps"])
        self.send_json_response({
            "id": row["id"],
            "solution_steps": steps,
            "solution_readable": row["solution_readable"],
        })

    def handle_verify_compte_est_bon(self, payload: dict) -> None:
        game_id = payload.get("id")
        steps = payload.get("steps")  # liste de {"a": x, "op": "+", "b": y, "result": z}

        if not game_id or not isinstance(steps, list):
            self.send_error_response("Paramètres 'id' et 'steps' requis", status=400)
            return

        conn = db.get_connection()
        row = conn.execute("SELECT id, available_numbers, target FROM compte_est_bon_puzzles WHERE id = ?", (game_id,)).fetchone()
        conn.close()

        if not row:
            self.send_error_response("Niveau Compte est bon non trouvé", status=404)
            return

        available_numbers = json.loads(row["available_numbers"])
        target = row["target"]

        errors = verify_compte_est_bon_solution(available_numbers, target, steps)
        is_complete = len(errors) == 0

        self.send_json_response({
            "id": game_id,
            "is_valid": len(errors) == 0,
            "is_complete": is_complete,
            "errors": errors,
        })


def run_server(port: int = 8000) -> None:
    mimetypes.add_type("application/javascript", ".js")
    mimetypes.add_type("text/css", ".css")
    mimetypes.add_type("image/svg+xml", ".svg")

    STATIC_DIR.mkdir(parents=True, exist_ok=True)

    server_address = ("", port)
    httpd = ThreadingHTTPServer(server_address, BrainTrainHandler)
    print(f"🧠 BrainTrain Serveur v3 démarré sur http://localhost:{port}")
    print("5 jeux supportés : Sudoku, Mastermind, Nonogramme, Hashi, Compte est bon")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nArrêt du serveur BrainTrain.")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    run_server(port)
