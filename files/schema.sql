-- =========================================================
-- Base de données locale — Application d'entraînement mental
-- Version 1 : Sudoku + Mastermind
-- =========================================================

PRAGMA foreign_keys = ON;

-- -----------------------------------------------------------
-- Table SUDOKU
-- -----------------------------------------------------------
-- starting_grid / solution_grid : chaînes de 81 caractères,
-- lecture ligne par ligne (row-major), '0' = case vide.
-- Exemple : "530070000600195000098000060800060003400803001700020006060000280000419005000080"
CREATE TABLE IF NOT EXISTS sudoku_puzzles (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    starting_grid               TEXT    NOT NULL,
    solution_grid                TEXT    NOT NULL,
    difficulty                  TEXT    NOT NULL CHECK (difficulty IN ('facile', 'moyen', 'difficile')),
    estimated_duration_minutes  INTEGER NOT NULL,
    clue_count                  INTEGER NOT NULL,           -- nombre de cases pré-remplies (indicatif)
    created_at                  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CHECK (length(starting_grid) = 81),
    CHECK (length(solution_grid) = 81)
);

-- -----------------------------------------------------------
-- Table MASTERMIND
-- -----------------------------------------------------------
-- secret_code : suite de chiffres séparés par des virgules,
-- chaque chiffre représente une couleur (1 à num_colors).
-- Exemple pour 4 positions : "2,4,1,4"
CREATE TABLE IF NOT EXISTS mastermind_games (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    secret_code                 TEXT    NOT NULL,
    num_colors                  INTEGER NOT NULL,
    num_positions                INTEGER NOT NULL,
    max_attempts                INTEGER NOT NULL,
    difficulty                  TEXT    NOT NULL CHECK (difficulty IN ('facile', 'moyen', 'difficile')),
    estimated_duration_minutes  INTEGER NOT NULL,
    created_at                  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- -----------------------------------------------------------
-- Table NONOGRAMME
-- -----------------------------------------------------------
-- solution_grid : chaîne de num_rows*num_cols caractères ('0'/'1'),
-- lecture ligne par ligne (row-major).
-- row_clues / col_clues : listes de listes d'entiers encodées en JSON,
-- ex. row_clues = "[[2],[1,1],[],[3]]" (une case vide -> liste vide []).
-- solution_unique : 1 si l'unicité de la solution a été vérifiée par le
-- solveur (voir nonogram_generator.py), 0 sinon (cf. limites documentées
-- dans README.md — ne devrait normalement jamais arriver pour ce jeu de
-- 50 grilles vu leur taille modeste, mais le champ existe pour la
-- transparence si un puzzle devait être accepté sans vérification).
CREATE TABLE IF NOT EXISTS nonogram_puzzles (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    num_rows                    INTEGER NOT NULL,
    num_cols                    INTEGER NOT NULL,
    solution_grid               TEXT    NOT NULL,
    row_clues                   TEXT    NOT NULL,   -- JSON
    col_clues                   TEXT    NOT NULL,   -- JSON
    difficulty                  TEXT    NOT NULL CHECK (difficulty IN ('facile', 'moyen', 'difficile')),
    estimated_duration_minutes  INTEGER NOT NULL,
    solution_unique             INTEGER NOT NULL DEFAULT 1 CHECK (solution_unique IN (0, 1)),
    created_at                  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CHECK (length(solution_grid) = num_rows * num_cols)
);

-- -----------------------------------------------------------
-- Table HASHI (Ponts)
-- -----------------------------------------------------------
-- islands : JSON, liste de [row, col, value] — la donnée du puzzle
--   (les nombres affichés sur chaque île).
-- solution_bridges : JSON, liste de [index_ile_a, index_ile_b, nombre_de_ponts]
--   où les index font référence à la position de l'île dans `islands`
--   (0-indexé, dans l'ordre où elle apparaît dans la liste JSON).
-- solution_unique : 1 si l'unicité a été vérifiée par le solveur (uniquement
-- tenté pour les petites grilles, cf. limite documentée dans README.md),
-- 0 si seule la validité de la solution stockée a été vérifiée (pas
-- l'unicité — trop coûteux en calcul pour les grilles moyennes/difficiles
-- dans cette première version).
CREATE TABLE IF NOT EXISTS hashi_puzzles (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    num_rows                    INTEGER NOT NULL,
    num_cols                    INTEGER NOT NULL,
    islands                     TEXT    NOT NULL,   -- JSON
    solution_bridges            TEXT    NOT NULL,   -- JSON
    difficulty                  TEXT    NOT NULL CHECK (difficulty IN ('facile', 'moyen', 'difficile')),
    estimated_duration_minutes  INTEGER NOT NULL,
    solution_unique             INTEGER NOT NULL DEFAULT 0 CHECK (solution_unique IN (0, 1)),
    created_at                  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- -----------------------------------------------------------
-- Table LE COMPTE EST BON
-- -----------------------------------------------------------
-- available_numbers : JSON, liste des nombres disponibles pour ce niveau,
--   ex. "[25, 8, 3, 7]".
-- allowed_operations : JSON, liste des opérations autorisées (toujours
--   les 4 dans cette version, colonne conservée pour une éventuelle
--   évolution future — ex. un mode restreint sans division).
-- solution_steps : JSON, liste ordonnée d'étapes rejouables,
--   ex. "[{"a":25,"op":"+","b":8,"result":33}, ...]" — chaque étape ne
--   consomme un nombre (nombre de départ ou résultat intermédiaire) que
--   s'il est encore disponible, ce qui permet de vérifier automatiquement
--   qu'aucun nombre n'est utilisé plus d'une fois.
-- solution_readable : la même solution sous une forme lisible par un
--   humain (une ligne par étape, ex. "25 + 8 = 33").
CREATE TABLE IF NOT EXISTS compte_est_bon_puzzles (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    available_numbers           TEXT    NOT NULL,   -- JSON
    target                       INTEGER NOT NULL,
    allowed_operations           TEXT    NOT NULL DEFAULT '["+", "-", "*", "/"]',  -- JSON
    solution_steps               TEXT    NOT NULL,   -- JSON
    solution_readable            TEXT    NOT NULL,
    difficulty                  TEXT    NOT NULL CHECK (difficulty IN ('facile', 'moyen', 'difficile')),
    estimated_duration_minutes  INTEGER NOT NULL,
    created_at                  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- -----------------------------------------------------------
-- Index utiles pour les requêtes par type / difficulté / durée
-- -----------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_sudoku_difficulty   ON sudoku_puzzles (difficulty);
CREATE INDEX IF NOT EXISTS idx_sudoku_duration      ON sudoku_puzzles (estimated_duration_minutes);

CREATE INDEX IF NOT EXISTS idx_mastermind_difficulty ON mastermind_games (difficulty);
CREATE INDEX IF NOT EXISTS idx_mastermind_duration    ON mastermind_games (estimated_duration_minutes);

CREATE INDEX IF NOT EXISTS idx_nonogram_difficulty ON nonogram_puzzles (difficulty);
CREATE INDEX IF NOT EXISTS idx_nonogram_duration    ON nonogram_puzzles (estimated_duration_minutes);

CREATE INDEX IF NOT EXISTS idx_hashi_difficulty ON hashi_puzzles (difficulty);
CREATE INDEX IF NOT EXISTS idx_hashi_duration    ON hashi_puzzles (estimated_duration_minutes);

CREATE INDEX IF NOT EXISTS idx_compte_est_bon_difficulty ON compte_est_bon_puzzles (difficulty);
CREATE INDEX IF NOT EXISTS idx_compte_est_bon_duration    ON compte_est_bon_puzzles (estimated_duration_minutes);
