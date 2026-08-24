# 🧠 BrainTrain — Application d'Entraînement Mental (v3)

Interface web mobile-first moderne, soignée et rapide pour l'entraînement cérébral quotidien, proposant **5 jeux** jouables directement dans le navigateur :
1. 🔢 **Sudoku** (50 grilles)
2. 🎨 **Mastermind** (50 parties)
3. 🖼️ **Nonogramme / Picross** (50 grilles : 5×5, 8×8, 10×10)
4. 🌉 **Hashi / Ponts** (50 puzzles : 6×6, 8×8, 10×10)
5. 🧮 **Le Compte est bon** (250 niveaux : 4, 5 ou 6 nombres avec cible)

L'application s'appuie sur la base de données SQLite `files/mental_training.db` préexistante (**450 parties au total**) et intègre un **tirage aléatoire équilibré en deux étapes** pour garantir une chance égale à chaque type de jeu.

---

## ✨ Fonctionnalités

- **Écran d'accueil rapide (lancement en 2 clics)** :
  - Choix du jeu : *Tous (Aléatoire équilibré)*, *Sudoku*, *Mastermind*, *Nonogramme*, *Hashi*, *Le Compte est bon*.
  - Choix du temps disponible : *5 min*, *10 min*, *20 min*, ou *Sans limite*.
  - Choix du niveau de difficulté : *Facile*, *Moyen*, *Difficile*.
  - Compteur dynamique en temps réel des parties correspondantes (sur les 450 parties en base).
- **Le Compte est bon** :
  - Bannière cible élégante, zone de calcul tactile avec 3 emplacements dynamiques.
  - Tuiles de nombres interactives (les nombres utilisés sont remplacés par la tuile résultat).
  - 4 opérateurs tactiles (+, −, ×, ÷) avec validation stricte (pas de division non entière, pas de résultat négatif).
  - Historique complet des calculs, Annulation (Undo), Réinitialisation et Révélation de solution.
- **Sudoku, Mastermind, Nonogramme, Hashi** :
  - Toutes les fonctionnalités tactiles, vérifications en direct et aides de jeu.
- **Sauvegarde locale automatique (`localStorage`)** :
  - Reprise transparente de n'importe lequel des 5 jeux dès la réouverture de la page.

---

## 🚀 Démarrage Rapide

```bash
python3 server.py
```

👉 Accessible sur : **[http://localhost:8000](http://localhost:8000)**

---

## 🧪 Tests et Validation

```bash
# Validation complète des 450 parties SQLite
python3 files/test_data.py

# Validation de l'API et de l'intégration
python3 -m unittest discover -s tests -p "test_*.py"
```
