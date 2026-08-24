# Base de données — Application d'entraînement mental (v1 + v2 + v3 + v4)

Base SQLite locale contenant 500 parties prêtes à jouer : 50 grilles de
Sudoku, 50 parties de Mastermind, 50 Nonogrammes, 50 puzzles Hashi
(Ponts), 250 niveaux du Compte est bon et 50 niveaux Cross Math. Aucune
interface n'est incluse à ce stade : uniquement la base, les données, un
script de génération et des tests de validation.

> **v2** : ajout des Nonogrammes et du Hashi.
> **v3** : ajout du Compte est bon (250 niveaux) + refonte du tirage
> aléatoire "sans type précisé" pour qu'il reste équilibré entre les
> types malgré leurs effectifs très différents.
> **v4** : ajout de Cross Math (50 niveaux) + `generate_data.py` devient
> **purement additif pour tous les types sans exception** (voir
> "Extensions" plus bas) — c'est la garantie la plus forte apportée par
> cette version : plus aucune table n'est jamais vidée/régénérée par le
> script, quel que soit le type de jeu.
>
> Dans toutes les versions, les jeux déjà présents en base ne sont ni
> supprimés ni régénérés par le script.

## Fichiers

| Fichier                       | Rôle                                                                 |
|--------------------------------|-----------------------------------------------------------------------|
| `schema.sql`                   | Définition des 6 tables (`sudoku_puzzles`, `mastermind_games`, `nonogram_puzzles`, `hashi_puzzles`, `compte_est_bon_puzzles`, `cross_math_puzzles`) |
| `db.py`                        | Connexion SQLite + initialisation du schéma                          |
| `sudoku_generator.py`          | Génération de grilles pleines + retrait de cases avec **vérification d'unicité de la solution** |
| `mastermind_generator.py`      | Génération des codes secrets selon la difficulté                     |
| `nonogram_generator.py`        | Génération de grilles + indices, avec **vérification d'unicité par solveur** |
| `hashi_generator.py`           | Génération d'îles + ponts, avec **validation robuste des règles** et unicité best-effort |
| `compte_est_bon_generator.py`  | Génération de niveaux + solution construite en même temps, avec **rejeu et vérification complète de la solution** |
| `cross_math_generator.py`      | Génération de grilles + opérateurs, avec **solveur d'unicité par permutation** et **validateur de proposition joueur** |
| `generate_data.py`             | Script de remplissage : génère et insère les 500 parties — **purement additif**, aucune table jamais vidée |
| `query.py`                     | `get_games()` / `get_random_game()` — filtrage par type (6) / difficulté / durée, **tirage équilibré en 2 étapes** |
| `test_data.py`                 | Tests de validation (comptes, cohérence, unicité, règles de chaque jeu, non-régression, équilibre du tirage) |
| `mental_training.db`           | Base SQLite générée (résultat de `generate_data.py`)                 |

## Modèle de données

### `sudoku_puzzles`
- `starting_grid` (81 caractères, `0` = case vide)
- `solution_grid` (81 caractères)
- `difficulty` : `facile` / `moyen` / `difficile`
- `estimated_duration_minutes` : 5 / 10 / 20
- `clue_count` : nombre de cases pré-remplies (indicatif, pour info/tri)

### `mastermind_games`
- `secret_code` (ex. `"2,4,1,4"`, chiffres 1..num_colors)
- `num_colors`, `num_positions`, `max_attempts`
- `difficulty` : `facile` / `moyen` / `difficile`
- `estimated_duration_minutes` : 5 / 10 / 15

Paramètres Mastermind par difficulté :

| Difficulté | Couleurs | Positions | Tentatives | Durée   |
|------------|----------|-----------|------------|---------|
| facile     | 4        | 4         | 10         | 5 min   |
| moyen      | 6        | 4         | 10         | 10 min  |
| difficile  | 8        | 5         | 12         | 15 min  |

### `nonogram_puzzles`
- `num_rows`, `num_cols`
- `solution_grid` (chaîne `0`/`1`, `num_rows*num_cols` caractères)
- `row_clues`, `col_clues` (JSON, listes de listes d'entiers — `[]` pour une ligne vide)
- `difficulty` / `estimated_duration_minutes`
- `solution_unique` : 1 si l'unicité a été confirmée par le solveur (toujours le cas dans ce jeu de données, voir plus bas)

Tailles de grille par difficulté (adaptées au téléphone) :

| Difficulté | Taille  | Durée   |
|------------|---------|---------|
| facile     | 5 × 5   | 5 min   |
| moyen      | 8 × 8   | 10 min  |
| difficile  | 10 × 10 | 20 min  |

### `hashi_puzzles`
- `num_rows`, `num_cols`
- `islands` (JSON, liste de `[row, col, valeur]`)
- `solution_bridges` (JSON, liste de `[index_île_a, index_île_b, nombre_de_ponts]`, index dans `islands`)
- `difficulty` / `estimated_duration_minutes`
- `solution_unique` : 1 si l'unicité a été confirmée par le solveur (petites grilles seulement, voir "Limites" plus bas)

Paramètres Hashi par difficulté :

| Difficulté | Grille  | Îles   | Durée   |
|------------|---------|--------|---------|
| facile     | 6 × 6   | 6-8    | 5 min   |
| moyen      | 8 × 8   | 10-14  | 10 min  |
| difficile  | 10 × 10 | 16-20  | 20 min  |

### `compte_est_bon_puzzles`
- `available_numbers` (JSON, ex. `[25, 8, 3, 7]`)
- `target` (le nombre à atteindre)
- `allowed_operations` (JSON, toujours `["+", "-", "*", "/"]` dans cette version)
- `solution_steps` (JSON, liste d'étapes rejouables, ex. `[{"a":25,"op":"+","b":8,"result":33}, ...]`)
- `solution_readable` (TEXT, la même solution en clair, une ligne par étape)
- `difficulty` / `estimated_duration_minutes`

Paramètres par difficulté :

| Difficulté | Nombres | Cible        | Durée   |
|------------|---------|--------------|---------|
| facile     | 4       | 10 à 100     | 5 min   |
| moyen      | 5       | 100 à 500    | 10 min  |
| difficile  | 6       | 200 à 999    | 20 min  |

Le jeu de nombres disponibles mélange des "petits" nombres (1 à 10) et,
à partir du niveau moyen, des "grands" nombres (25, 50, 75, 100, chacun
utilisé au plus une fois par niveau) — comme au jeu télévisé.

### `cross_math_puzzles`
- `grid_size` (k : nombre de nombres par ligne/colonne — grille k × k)
- `given_grid` (JSON k×k, nombre pré-rempli ou `null` pour une case à compléter)
- `solution_grid` (JSON k×k, la grille complète — référence uniquement, la validation n'y accède jamais directement)
- `row_operators` / `col_operators` (JSON, k listes de (k-1) opérateurs parmi `"+","-","*","/"` — les "opérateurs visibles")
- `row_results` / `col_results` (JSON, k résultats attendus par ligne/colonne)
- `available_numbers` (JSON, multi-ensemble mélangé des nombres à placer dans les cases vides)
- `difficulty` / `estimated_duration_minutes`
- `solution_unique` : 1 si l'unicité a été confirmée par le solveur (toujours le cas dans ce jeu de données)

**Règle de calcul officielle** (une seule fonction fait foi : `evaluate_chain`
dans `cross_math_generator.py`, utilisée pour la génération, le solveur
ET la validation) : chaque ligne/colonne se calcule **strictement de
gauche à droite** (lignes) ou **de haut en bas** (colonnes), **sans
priorité opératoire implicite** — pour 3 nombres et 2 opérateurs,
`résultat = (a op1 b) op2 c`, jamais `a op1 (b op2 c)`. Toute division
doit être exacte et produire un résultat strictement positif ; aucun
résultat intermédiaire ne peut être négatif.

Paramètres par difficulté :

| Difficulté | Grille | Opérateurs autorisés | Cases pré-remplies | Durée   |
|------------|--------|-----------------------|---------------------|---------|
| facile     | 3 × 3  | + −                   | ~60 % (5/9)         | 5 min   |
| moyen      | 4 × 4  | + − × ÷ (≥2 occ. ×/÷) | ~40 % (6-7/16)      | 10 min  |
| difficile  | 4 × 4  | + − × ÷ (≥4 occ. ×/÷, ≥2 ÷) | ~15 % (2-3/16) | 20 min  |

## Comment ça marche

1. **Sudoku** : une grille pleine valide est générée par backtracking
   randomisé, puis des cases sont retirées une par une (ordre aléatoire).
   Après chaque retrait, un solveur (backtracking + heuristique MRV,
   plafonné à 2 solutions) vérifie que la grille a toujours une solution
   **unique** ; sinon la case est remise. On s'arrête au nombre d'indices
   cible de la difficulté (40 / 30 / 24 environ).
2. **Mastermind** : un code secret aléatoire est tiré selon les
   paramètres de la difficulté, en évitant les doublons au sein d'une
   même difficulté.

3. **Nonogramme** : une grille binaire aléatoire est générée (densité
   contrôlée pour éviter les grilles trop vides/pleines), puis les
   indices de lignes/colonnes en sont déduits. Un solveur (génération de
   toutes les configurations de ligne compatibles + backtracking avec
   propagation par colonnes, plafonné à 2 solutions) vérifie l'unicité ;
   si elle n'est pas confirmée, on régénère une nouvelle grille.

4. **Hashi (Ponts)** : la solution est construite en premier, comme pour
   le Sudoku. Des îles sont ajoutées une à une par croissance aléatoire
   depuis une île de départ, chaque nouvelle île étant reliée en ligne
   droite à une île existante (ce qui garantit l'alignement et l'absence
   d'île intermédiaire). Les cellules traversées par chaque pont sont
   mémorisées pour interdire tout croisement futur. Des ponts
   supplémentaires sont ajoutés si possible, puis chaque pont reçoit 1 ou
   2 ponts aléatoirement ; le nombre affiché sur chaque île est la somme
   des ponts qui lui sont connectés.

5. **Le Compte est bon** : comme pour le Sudoku et le Hashi, la solution
   est construite AVANT l'énoncé. Un jeu de nombres est tiré (mélange de
   petits nombres et, selon la difficulté, de grands nombres façon jeu
   télévisé), puis un sous-ensemble (une partie ou la totalité) est
   combiné deux par deux dans un ordre aléatoire : à chaque étape, on
   liste les opérations valides pour la paire courante (addition et
   multiplication toujours possibles ; soustraction seulement si le
   résultat est strictement positif ; division seulement si elle est
   exacte) et on en choisit une au hasard, jusqu'à n'obtenir plus qu'un
   seul nombre — la cible. Si la cible obtenue sort de la plage jugée
   adaptée à la difficulté, ou si la combinaison (nombres + cible) a déjà
   été générée, on retente avec un nouveau tirage.

6. **Cross Math** : une grille k×k de nombres aléatoires est tirée en
   premier (indépendamment des opérateurs). Pour chaque ligne, puis
   chaque colonne, on énumère TOUTES les combinaisons d'opérateurs
   autorisés (au plus 4³ = 64 combinaisons pour k=4) et on choisit au
   hasard, parmi celles qui sont valides selon la règle de calcul
   officielle, une combinaison — avec une préférence pour celles
   contenant × ou ÷ afin de varier les niveaux. L'addition et la
   multiplication étant toujours valides quels que soient les nombres,
   seule la division contraint réellement ce choix ; on retente avec une
   nouvelle grille si une ligne/colonne ne trouve aucune combinaison
   valide, ou si le mélange d'opérateurs requis par la difficulté (× et ÷)
   n'est pas atteint. On choisit ensuite les cases pré-remplies selon la
   difficulté, puis un solveur (recherche exhaustive des façons de
   placer le multi-ensemble des nombres disponibles dans les cases
   vides, avec élagage dès qu'une ligne ou une colonne se complète)
   confirme l'unicité de la solution — sinon on retente. Un dernier
   contrôle écarte les doublons triviaux obtenus par simple transposition
   de la grille (lignes ↔ colonnes) par rapport aux niveaux déjà générés
   dans le même lot.

## Tirage aléatoire équilibré entre les types de jeux

**Problème** : les types de jeux n'ont pas le même nombre de niveaux en
base (250 pour le Compte est bon contre 50 pour les 5 autres types). Un
tirage aléatoire *uniforme sur l'ensemble des lignes* de la base
favoriserait donc mécaniquement le Compte est bon : avec 250 lignes sur
500, il apparaîtrait environ 50 % du temps au lieu du ≈ 17 % attendu
pour 6 types équiprobables.

**Solution** : `get_random_game()` (dans `query.py`) applique un tirage
en **deux étapes** lorsqu'aucun `game_type` n'est précisé :

1. on détermine, parmi les 6 types, ceux qui ont au moins un jeu
   correspondant aux filtres demandés (`difficulty`, `max_duration`) —
   les "types compatibles" ;
2. on choisit un type au hasard, **de façon équiprobable**, parmi ces
   types compatibles ;
3. on choisit ensuite un jeu au hasard **dans ce type**.

Résultat : chaque type de jeu compatible avec les filtres a la même
probabilité d'être proposé, quel que soit son nombre de niveaux en base.
Si un type est demandé explicitement (`game_type="cross_math"` par
exemple), ce mécanisme ne s'applique pas : le tirage reste simplement
uniforme parmi les jeux de ce type (comportement inchangé).

Ce comportement est vérifié dans `test_data.py::test_balanced_random_selection`,
qui échantillonne plusieurs milliers de tirages et vérifie que chaque
type représente bien environ 17 % des résultats (± 6 %), y compris
lorsqu'un filtre de difficulté est appliqué. L'ajout de Cross Math n'a
nécessité **aucune modification** de cette logique : comme elle itère
déjà sur le registre `TYPE_FETCHERS`, il a suffi d'y enregistrer le
nouveau type pour qu'il soit automatiquement pris en compte dans le
tirage équilibré.

## Extensions purement additives (`generate_data.py`)

Depuis la v4 (ajout de Cross Math), `generate_data.py` suit une règle
unique et sans exception pour **tous** les types de jeux : un niveau
n'est généré et inséré QUE si sa table est actuellement vide. Aucune
instruction `DELETE` ni `DROP` ne figure dans ce script (vérifié
explicitement par `test_data.py::test_other_games_untouched_by_cross_math`).
Concrètement, réexécuter `python generate_data.py` sur une base déjà
peuplée n'a aucun effet — chaque type affiche simplement
"déjà présents en base, conservés tels quels". C'est ce qui garantit que
l'ajout d'un nouveau type de jeu (comme Cross Math) ne modifie jamais les
niveaux des types déjà existants.

## Limites techniques documentées

- **Nonogramme** : la vérification d'unicité est systématique et rapide
  pour les tailles utilisées ici (5×5, 8×8, 10×10 — quelques millisecondes
  à ~0,2s par grille difficile). Le champ `solution_unique` vaut `1` pour
  les 50 grilles générées. Le générateur conserve tout de même un
  mécanisme de secours (`solution_unique = 0`) documenté au cas où une
  taille de grille beaucoup plus grande rendrait un jour la vérification
  trop coûteuse.

- **Hashi (Ponts)** : la preuve d'unicité (recherche exhaustive de toutes
  les solutions possibles) n'est tentée que pour les puzzles de 9 îles ou
  moins, ce qui correspond en pratique aux 20 puzzles **faciles**
  (6 à 8 îles) — tous confirmés uniques. Au-delà (puzzles **moyens** et
  **difficiles**, 10 à 20 îles), la recherche exhaustive deviendrait trop
  coûteuse en temps de calcul pour cette première version ; l'unicité
  n'est donc **pas** garantie pour ces 30 puzzles. En revanche, **la
  validité de la solution stockée est garantie à 100 %** pour les 50
  puzzles : chaque solution est vérifiée règle par règle (alignement,
  absence de croisement, 1 ou 2 ponts par arête, somme exacte par île,
  connexité de toutes les îles) via `validate_hashi_solution()`, et cette
  vérification est ré-exécutée dans les tests. Le champ `solution_unique`
  en base reflète honnêtement ce qui a été vérifié (1 = unicité prouvée,
  0 = solution valide mais unicité non prouvée).

- **Cross Math** : contrairement au Nonogramme ou au Hashi, l'unicité est
  ici **garantie sans exception pour les 50 niveaux** (`solution_unique`
  vaut toujours `1`). C'est possible car le solveur ne cherche pas parmi
  tous les chiffres possibles, mais uniquement parmi les **permutations
  du multi-ensemble `available_numbers`** dans les cases vides (le joueur
  place des nombres donnés, il n'en invente pas) — un espace de recherche
  bien plus restreint qu'un solveur "chiffres libres", et donc rapide à
  épuiser même pour les niveaux difficiles (14 cases à remplir, moins de
  0,5s par niveau observé en pratique). La détection de doublons ne
  couvre explicitement que la transposition (lignes ↔ colonnes) — les
  50 niveaux générés se sont révélés naturellement distincts sans avoir
  eu besoin de retenter à cause de cette vérification.

## Utilisation

```bash
# Générer la base (additif : ne touche jamais aux niveaux déjà présents)
python generate_data.py

# Vérifier que tout est valide
python test_data.py

# Exemple d'utilisation de la fonction de requête
python query.py
```

```python
from query import get_games, get_random_game

# Un jeu au hasard, tous types confondus (6 types, tirage ÉQUILIBRÉ par type
# malgré 250 niveaux de Compte est bon contre 50 pour les autres), <= 10 min
get_random_game(max_duration=10)

# Toutes les grilles de Sudoku moyennes
get_games(game_type="sudoku", difficulty="moyen")

# Une partie de Mastermind facile
get_random_game(game_type="mastermind", difficulty="facile")

# Un Nonogramme difficile (row_clues / col_clues déjà désérialisés en listes Python)
get_random_game(game_type="nonogram", difficulty="difficile")

# Un puzzle Hashi facile (islands / solution_bridges déjà désérialisés)
get_random_game(game_type="hashi", difficulty="facile")

# Un niveau du Compte est bon moyen (available_numbers / solution_steps désérialisés)
get_random_game(game_type="compte_est_bon", difficulty="moyen")

# Un niveau Cross Math moyen (given_grid / row_operators / etc. désérialisés)
get_random_game(game_type="cross_math", difficulty="moyen")
```

```python
from cross_math_generator import validate_player_grid

# Valider une proposition du joueur pour un niveau Cross Math donné
# (uniquement à partir des données stockées du niveau — jamais par
# simple comparaison à la grille solution)
errors = validate_player_grid(
    given_grid, row_operators, col_operators,
    row_results, col_results, available_numbers,
    proposed_grid,  # la grille k x k complétée par le joueur
)
is_correct = len(errors) == 0
```

## Prochaines étapes (hors périmètre de cette v1/v2/v3/v4)

- Interface de jeu (Sudoku, Mastermind, Nonogramme, Hashi, Compte est bon, Cross Math)
- Suivi de la progression / scores par utilisateur
- Solveur d'unicité Hashi plus performant pour les grilles moyennes/difficiles
- Ajout d'autres types de jeux mentaux
