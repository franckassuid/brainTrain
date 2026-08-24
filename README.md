# 🧠 BrainTrain — Application d'Entraînement Mental (v4)

Interface web mobile-first moderne, soignée et ultra-rapide pour l'entraînement cérébral quotidien, proposant **6 jeux** jouables directement dans le navigateur :
1. 🔢 **Sudoku** (50 grilles)
2. 🎨 **Mastermind** (50 parties)
3. 🖼️ **Nonogramme / Picross** (50 grilles : 5×5, 8×8, 10×10)
4. 🌉 **Hashi / Ponts** (50 puzzles : 6×6, 8×8, 10×10 avec quadrillage)
5. 🧮 **Le Compte est bon** (250 niveaux avec tuiles interactives)
6. ➕ **Cross Math** (50 niveaux : équations croisées 3×3 et 4×4)

L'application s'appuie sur la base de données SQLite `files/mental_training.db` préexistante (**500 parties au total**) et intègre un **tirage aléatoire équilibré en deux étapes** pour garantir une chance égale à chaque type de jeu (~16.7%).

---

## ✨ Les 6 Jeux Disponibles

- **Sudoku** : Grille 9x9 tactile, surbrillances, pavé 1-9 responsive mobile, mode crayon, annulation, indices.
- **Mastermind** : Pions de couleur différenciés (4, 6 ou 8 couleurs), fentes tactiles, verdict immédiat.
- **Nonogramme** : Grilles avec découpage symétrique par blocs, coins arrondis nets, modes Remplir/Croix.
- **Hashi (Ponts)** : Quadrillage d'alignement en arrière-plan, dimensionnement proportionnel des îles anti-chevauchement, diagnostic pas à pas.
- **Le Compte est bon** : Sélection de 2 nombres et 1 opérateur -> remplacement automatique par la tuile résultat.
- **Cross Math** : Grille croisée d'équations avec calcul strict de gauche à droite et de haut en bas, réserve de nombres disponibles, validation en temps réel de chaque ligne et colonne.

---

## 🚀 Démarrage Rapide

```bash
python3 server.py
```

👉 Accessible sur : **[http://localhost:8000](http://localhost:8000)**

---

## 🧪 Tests et Validation

```bash
# Validation complète des 500 parties SQLite
python3 files/test_data.py

# Validation de l'API et de l'intégration
python3 -m unittest discover -s tests -p "test_*.py"
```
