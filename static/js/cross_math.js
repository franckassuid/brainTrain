/**
 * BrainTrain - Moteur de Jeu Cross Math (Grille Croisée d'Équations)
 */

import { verifyCrossMath, getCrossMathSolution } from './api.js';

const OP_DISPLAY = {
  '+': '+',
  '-': '−',
  '*': '×',
  '/': '÷',
};

export class CrossMathGame {
  constructor({
    boardContainerEl,
    bankContainerEl,
    onStateChange = () => {},
    onVictory = () => {},
  }) {
    this.boardContainer = boardContainerEl;
    this.bankContainer = bankContainerEl;
    this.onStateChange = onStateChange;
    this.onVictory = onVictory;

    this.gameData = null;
    this.currentGrid = []; // k x k
    this.selectedCell = null; // { r, c }
    this.history = []; // stack of { r, c, prevVal, newVal }
    this.isCompleted = false;
    this.sortMode = 'asc'; // 'asc' (du plus petit au plus grand) ou 'original'
  }

  loadGame(gameData, savedState = null) {
    this.gameData = gameData;
    const k = gameData.grid_size;
    this.selectedCell = null;
    this.history = [];
    this.isCompleted = false;

    if (savedState && savedState.id === gameData.id && savedState.grid) {
      this.currentGrid = savedState.grid.map(row => [...row]);
      this.isCompleted = !!savedState.isCompleted;
      if (savedState.sortMode) this.sortMode = savedState.sortMode;
    } else {
      this.currentGrid = gameData.given_grid.map(row => [...row]);
    }

    this.updateSortButtonUI();
    this.render();
    this.saveState();
  }

  toggleSortMode() {
    if (this.sortMode === 'asc') {
      this.sortMode = 'desc';
    } else if (this.sortMode === 'desc') {
      this.sortMode = 'original';
    } else {
      this.sortMode = 'asc';
    }
    this.updateSortButtonUI();
    this.render();
    this.saveState();

    let msg = '🔢 Nombres triés par ordre croissant';
    if (this.sortMode === 'desc') msg = '🔢 Nombres triés par ordre décroissant';
    else if (this.sortMode === 'original') msg = '🔀 Nombres dans l’ordre du tirage';

    window.dispatchEvent(new CustomEvent('app:toast', {
      detail: { message: msg }
    }));
  }

  updateSortButtonUI() {
    const icon = document.getElementById('cm-sort-icon');
    const label = document.getElementById('cm-sort-label');
    if (icon && label) {
      if (this.sortMode === 'asc') {
        icon.textContent = '⬆️';
        label.textContent = 'Trier : Croissant';
      } else if (this.sortMode === 'desc') {
        icon.textContent = '⬇️';
        label.textContent = 'Trier : Décroissant';
      } else {
        icon.textContent = '🔀';
        label.textContent = 'Ordre : Tirage';
      }
    }
  }

  handleCellTap(r, c) {
    if (this.isCompleted) return;
    if (this.gameData.given_grid[r][c] !== null) return; // Case donnée non modifiable

    if (this.selectedCell && this.selectedCell.r === r && this.selectedCell.c === c) {
      // Si la case contient déjà un nombre, la vider
      if (this.currentGrid[r][c] !== null) {
        this.setCell(r, c, null);
      } else {
        this.selectedCell = null;
      }
    } else {
      this.selectedCell = { r, c };
    }

    this.render();
  }

  handleBankTileTap(val) {
    if (this.isCompleted) return;

    let targetCell = this.selectedCell;

    // Si aucune case n'est sélectionnée, trouver la 1ère case vide
    if (!targetCell || this.gameData.given_grid[targetCell.r][targetCell.c] !== null) {
      const k = this.gameData.grid_size;
      for (let r = 0; r < k; r++) {
        for (let c = 0; c < k; c++) {
          if (this.gameData.given_grid[r][c] === null && this.currentGrid[r][c] === null) {
            targetCell = { r, c };
            break;
          }
        }
        if (targetCell) break;
      }
    }

    if (targetCell) {
      this.setCell(targetCell.r, targetCell.c, val);

      // Auto-sélectionne la prochaine case vide pour enchaîner fluidement
      const k = this.gameData.grid_size;
      let nextEmpty = null;
      for (let r = 0; r < k; r++) {
        for (let c = 0; c < k; c++) {
          if (this.gameData.given_grid[r][c] === null && this.currentGrid[r][c] === null) {
            nextEmpty = { r, c };
            break;
          }
        }
        if (nextEmpty) break;
      }
      this.selectedCell = nextEmpty;
      this.render();
      this.checkCompletion();
    }
  }

  setCell(r, c, newVal) {
    const prevVal = this.currentGrid[r][c];
    if (prevVal === newVal) return;

    this.history.push({ r, c, prevVal, newVal });
    this.currentGrid[r][c] = newVal;
    this.saveState();
  }

  undo() {
    if (this.history.length === 0 || this.isCompleted) return;
    const action = this.history.pop();
    this.currentGrid[action.r][action.c] = action.prevVal;
    this.selectedCell = { r: action.r, c: action.c };
    this.render();
    this.saveState();
  }

  clear() {
    if (this.isCompleted) return;
    if (this.selectedCell && this.gameData.given_grid[this.selectedCell.r][this.selectedCell.c] === null) {
      if (this.currentGrid[this.selectedCell.r][this.selectedCell.c] !== null) {
        this.setCell(this.selectedCell.r, this.selectedCell.c, null);
        this.render();
        this.saveState();
        return;
      }
    }

    // Si aucune case sélectionnée ou case déjà vide, effacer le dernier coup
    if (this.history.length > 0) {
      this.undo();
    }
  }

  resetAll() {
    if (this.isCompleted) return;
    this.currentGrid = this.gameData.given_grid.map(row => [...row]);
    this.history = [];
    this.selectedCell = null;
    this.render();
    this.saveState();
    window.dispatchEvent(new CustomEvent('app:toast', {
      detail: { message: '🔄 Grille réinitialisée' }
    }));
  }

  evaluateChain(numbers, operators) {
    if (numbers.some(n => n === null || n === undefined)) return null;
    let res = numbers[0];
    for (let i = 0; i < operators.length; i++) {
      const op = operators[i];
      const next = numbers[i + 1];
      if (op === '+') res = res + next;
      else if (op === '-') res = res - next;
      else if (op === '*') res = res * next;
      else if (op === '/') {
        if (next === 0 || res % next !== 0) return null;
        res = res / next;
      }
      if (res < 0) return null;
    }
    return res;
  }

  async checkCompletion() {
    const k = this.gameData.grid_size;
    const isFull = this.currentGrid.every(row => row.every(v => v !== null));
    if (!isFull) return;

    try {
      const res = await verifyCrossMath(this.gameData.id, this.currentGrid);
      if (res.is_complete) {
        this.isCompleted = true;
        this.selectedCell = null;
        this.render();
        this.saveState();
        this.onVictory(this.gameData);
      }
    } catch (e) {
      console.warn('Erreur vérification Cross Math:', e);
    }
  }

  async verifyGrid() {
    if (this.isCompleted) return;
    try {
      const res = await verifyCrossMath(this.gameData.id, this.currentGrid);
      if (res.is_complete) {
        this.isCompleted = true;
        this.selectedCell = null;
        this.render();
        this.saveState();
        this.onVictory(this.gameData);
      } else if (res.errors && res.errors.length > 0) {
        window.dispatchEvent(new CustomEvent('app:toast', {
          detail: { message: `⚠️ ${res.errors[0]}` }
        }));
      } else {
        window.dispatchEvent(new CustomEvent('app:toast', {
          detail: { message: '✨ Toutes les équations complétées sont valides !' }
        }));
      }
    } catch (e) {
      window.dispatchEvent(new CustomEvent('app:toast', { detail: { message: e.message } }));
    }
  }

  async giveHint() {
    if (this.isCompleted) return;
    try {
      const sol = await getCrossMathSolution(this.gameData.id);
      const solGrid = sol.solution_grid;
      const k = this.gameData.grid_size;

      // Trouve une case vide ou erronée
      for (let r = 0; r < k; r++) {
        for (let c = 0; c < k; c++) {
          if (this.gameData.given_grid[r][c] === null && this.currentGrid[r][c] !== solGrid[r][c]) {
            const correctVal = solGrid[r][c];
            this.setCell(r, c, correctVal);
            this.selectedCell = { r, c };
            this.render();
            this.saveState();
            this.checkCompletion();

            window.dispatchEvent(new CustomEvent('app:toast', {
              detail: { message: `💡 Indice placé : ${correctVal} en ligne ${r + 1}, colonne ${c + 1} !` }
            }));
            return;
          }
        }
      }
    } catch (e) {
      window.dispatchEvent(new CustomEvent('app:toast', { detail: { message: e.message } }));
    }
  }

  render() {
    const k = this.gameData.grid_size;
    const { given_grid, row_operators, col_operators, row_results, col_results, available_numbers } = this.gameData;

    // 1. Calcul des nombres placés pour la réserve
    const placedCounts = {};
    for (let r = 0; r < k; r++) {
      for (let c = 0; c < k; c++) {
        if (given_grid[r][c] === null && this.currentGrid[r][c] !== null) {
          const v = this.currentGrid[r][c];
          placedCounts[v] = (placedCounts[v] || 0) + 1;
        }
      }
    }

    // 2. Rendu de la grille Cross Math
    this.boardContainer.innerHTML = '';
    const gridEl = document.createElement('div');
    gridEl.className = 'cm-grid';

    // Grille de dimensions : (2k + 1) colonnes x (2k + 1) lignes
    const totalCols = (2 * k - 1) + 2;
    const totalRows = (2 * k - 1) + 2;
    gridEl.style.gridTemplateColumns = `repeat(${totalCols}, max-content)`;
    gridEl.style.gridTemplateRows = `repeat(${totalRows}, max-content)`;

    for (let gr = 0; gr < totalRows; gr++) {
      for (let gc = 0; gc < totalCols; gc++) {
        const isNumRow = gr % 2 === 0 && gr < 2 * k - 1;
        const isNumCol = gc % 2 === 0 && gc < 2 * k - 1;

        const isOpRow = gr % 2 === 1 && gr < 2 * k - 1;
        const isOpCol = gc % 2 === 1 && gc < 2 * k - 1;

        const isRowEqualCol = gc === 2 * k - 1 && isNumRow;
        const isRowResultCol = gc === 2 * k && isNumRow;

        const isColEqualRow = gr === 2 * k - 1 && isNumCol;
        const isColResultRow = gr === 2 * k && isNumCol;

        const item = document.createElement('div');

        if (isNumRow && isNumCol) {
          // Case de Nombre (Cellule de grille)
          const r = gr / 2;
          const c = gc / 2;
          const isGiven = given_grid[r][c] !== null;
          const val = this.currentGrid[r][c];

          item.className = `cm-cell ${isGiven ? 'given' : 'blank'}`;
          if (!isGiven && val !== null) item.classList.add('filled');
          if (this.selectedCell && this.selectedCell.r === r && this.selectedCell.c === c) {
            item.classList.add('selected');
          }

          item.textContent = val !== null ? val.toString() : '';
          item.addEventListener('click', () => this.handleCellTap(r, c));
        } else if (isNumRow && isOpCol) {
          // Opérateur Horizontal de ligne
          const r = gr / 2;
          const opIdx = Math.floor(gc / 2);
          item.className = 'cm-op';
          item.textContent = OP_DISPLAY[row_operators[r][opIdx]] || '';
        } else if (isOpRow && isNumCol) {
          // Opérateur Vertical de colonne
          const opIdx = Math.floor(gr / 2);
          const c = gc / 2;
          item.className = 'cm-op';
          item.textContent = OP_DISPLAY[col_operators[c][opIdx]] || '';
        } else if (isRowEqualCol) {
          item.className = 'cm-equal';
          item.textContent = '=';
        } else if (isRowResultCol) {
          // Résultat de ligne
          const r = gr / 2;
          const target = row_results[r];
          const actual = this.evaluateChain(this.currentGrid[r], row_operators[r]);

          item.className = 'cm-result';
          if (actual !== null) {
            item.classList.add(actual === target ? 'status-valid' : 'status-invalid');
          }
          item.textContent = target.toString();
        } else if (isColEqualRow) {
          item.className = 'cm-equal';
          item.textContent = '=';
        } else if (isColResultRow) {
          // Résultat de colonne
          const c = gc / 2;
          const target = col_results[c];
          const colNums = this.currentGrid.map(row => row[c]);
          const actual = this.evaluateChain(colNums, col_operators[c]);

          item.className = 'cm-result';
          if (actual !== null) {
            item.classList.add(actual === target ? 'status-valid' : 'status-invalid');
          }
          item.textContent = target.toString();
        } else {
          // Espace vide de jonction
          item.style.visibility = 'hidden';
        }

        gridEl.appendChild(item);
      }
    }

    this.boardContainer.appendChild(gridEl);

    // 3. Rendu de la réserve de Nombres Disponibles (utilisés à la fin)
    this.bankContainer.innerHTML = '';
    const tempPlaced = { ...placedCounts };
    const unused = [];
    const used = [];

    for (const val of available_numbers) {
      if (tempPlaced[val] && tempPlaced[val] > 0) {
        used.push(val);
        tempPlaced[val]--;
      } else {
        unused.push(val);
      }
    }

    if (this.sortMode === 'asc') {
      unused.sort((a, b) => a - b);
      used.sort((a, b) => a - b);
    } else if (this.sortMode === 'desc') {
      unused.sort((a, b) => b - a);
      used.sort((a, b) => b - a);
    }

    // 1. Nombres disponibles (utilisables) en premier
    unused.forEach((val) => {
      const tile = document.createElement('button');
      tile.className = 'cm-bank-tile';
      tile.textContent = val.toString();
      tile.addEventListener('click', () => this.handleBankTileTap(val));
      this.bankContainer.appendChild(tile);
    });

    // 2. Nombres déjà utilisés placés à la fin de la liste
    used.forEach((val) => {
      const tile = document.createElement('button');
      tile.className = 'cm-bank-tile used';
      tile.textContent = val.toString();
      this.bankContainer.appendChild(tile);
    });
  }

  saveState() {
    if (!this.gameData) return;
    const state = {
      type: 'cross_math',
      id: this.gameData.id,
      gameData: this.gameData,
      grid: this.currentGrid.map(row => [...row]),
      sortMode: this.sortMode,
      isCompleted: this.isCompleted,
      updatedAt: Date.now(),
    };
    this.onStateChange(state);
  }
}
