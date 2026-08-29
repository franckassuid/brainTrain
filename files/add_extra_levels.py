"""
Script d'AJOUT de niveaux supplémentaires, en plus de ceux déjà en base.

Ajoute, pour CHAQUE type de jeu, 100 nouveaux niveaux répartis en
30 faciles / 30 moyens / 40 difficiles (au lieu de la répartition
20/20/10 utilisée par `generate_data.py` pour le peuplement initial).

Comme `generate_data.py`, ce script est PUREMENT ADDITIF : il n'exécute
jamais de DELETE ni de DROP, et amorce ses mécanismes de déduplication
(grilles déjà vues, codes déjà utilisés, etc.) à partir du contenu déjà
présent en base, pour éviter tout doublon avec les niveaux existants —
pas seulement entre les nouveaux niveaux entre eux.

Cas particulier — Compte est bon et Cross Math : les niveaux "faciles"
générés avec les paramètres d'origine ont été jugés trop simples. Les
paramètres de difficulté de `compte_est_bon_generator.py` et
`cross_math_generator.py` ont donc été renforcés (voir le commentaire
DIFFICULTY_PARAMS dans chacun de ces deux fichiers) AVANT l'exécution de
ce script. Concrètement :
- les niveaux déjà en base (250 Compte est bon, 50 Cross Math) gardent
  leurs anciens paramètres, plus faciles, et ne sont PAS régénérés ;
- les 100 nouveaux niveaux ajoutés ici, pour ces deux types, utilisent
  les nouveaux paramètres renforcés.
Pour les 4 autres types (Sudoku, Mastermind, Nonogramme, Hashi), les
paramètres de difficulté n'ont pas changé : les 100 niveaux ajoutés sont
directement comparables aux niveaux déjà en base pour la même difficulté.

Usage :
    python add_extra_levels.py
"""

from __future__ import annotations

import sys

from db import get_connection
from generate_data import (
    generate_sudoku_batch,
    generate_mastermind_batch,
    generate_nonogram_batch,
    generate_hashi_batch,
    generate_compte_est_bon_batch,
    generate_cross_math_batch,
)

EXTRA_DISTRIBUTION = {"facile": 30, "moyen": 30, "difficile": 40}  # 100 au total


def main() -> None:
    print("=== Ajout de 100 niveaux supplémentaires par type de jeu ===")
    print(f"Répartition : {EXTRA_DISTRIBUTION} (100 au total par type)\n")

    conn = get_connection()

    before = {
        table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for table in (
            "sudoku_puzzles", "mastermind_games", "nonogram_puzzles",
            "hashi_puzzles", "compte_est_bon_puzzles", "cross_math_puzzles",
        )
    }

    generate_sudoku_batch(conn, EXTRA_DISTRIBUTION)
    generate_mastermind_batch(conn, EXTRA_DISTRIBUTION)
    generate_nonogram_batch(conn, EXTRA_DISTRIBUTION)
    generate_hashi_batch(conn, EXTRA_DISTRIBUTION)
    generate_compte_est_bon_batch(conn, EXTRA_DISTRIBUTION)
    generate_cross_math_batch(conn, EXTRA_DISTRIBUTION)

    after = {
        table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for table in before
    }

    print("\n" + "=" * 60)
    print("Résumé (avant -> après, delta) :")
    total_added = 0
    for table in before:
        delta = after[table] - before[table]
        total_added += delta
        print(f"  {table:<28} {before[table]:>4} -> {after[table]:>4}  (+{delta})")
    print(f"\nTotal ajouté : {total_added} niveaux.")

    conn.close()


if __name__ == "__main__":
    sys.exit(main())
