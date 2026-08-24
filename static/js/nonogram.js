/**
 * BrainTrain - Moteur de Jeu Nonogramme (Picross)
 */

import { verifyNonogramGrid, getNonogramSolution } from './api.js';

export class NonogramGame {
  constructor({ containerEl, onStateChange = () => {}, onVictory = () => {} }) {
    this.container = containerEl;
    this.onStateChange = onStateChange;
    this.onVictory = onVictory;

    this.gameData = null;
    this.grid = []; // 0 = vide, 1 = rempli, 2 = croix
    this.mode = 'fill'; // 'fill' ou 'cross'
    this.history = [];
    this.isCompleted = false;
    this.isMouseDown = false;
  }

  loadGame(gameData, savedState = null) {
    this.gameData = gameData;
    const totalCells = gameData.num_rows * gameData.num_cols;
    this.history = [];
    this.isCompleted = false;
    this.mode = 'fill';

    if (savedState && savedState.id === gameData.id) {
      this.grid = [...savedState.grid];
      this.mode = savedState.mode || 'fill';
      this.isCompleted = !!savedState.isCompleted;
    } else {
      this.grid = new Array(totalCells).fill(0);
    }

    this.render();
    this.saveState();
  }

  setMode(newMode) {
    this.mode = newMode;
    document.querySelectorAll('.nono-mode-btn').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.mode === newMode);
    });
  }

  handleCellTap(pos) {
    if (this.isCompleted) return;
    const currentVal = this.grid[pos];
    const prevVal = currentVal;
    let nextVal = 0;

    if (this.mode === 'fill') {
      nextVal = currentVal === 1 ? 0 : 1;
    } else {
      nextVal = currentVal === 2 ? 0 : 2;
    }

    this.history.push({ pos, prevVal, nextVal });
    this.grid[pos] = nextVal;
    this.renderCell(pos);
    this.updateCluesStatus();
    this.saveState();
    this.checkAutoCompletion();
  }

  undo() {
    if (this.history.length === 0 || this.isCompleted) return;
    const action = this.history.pop();
    this.grid[action.pos] = action.prevVal;
    this.renderCell(action.pos);
    this.updateCluesStatus();
    this.saveState();
  }

  clearGrid() {
    if (this.isCompleted) return;
    this.grid = new Array(this.gameData.num_rows * this.gameData.num_cols).fill(0);
    this.history = [];
    this.render();
    this.saveState();
  }

  async checkAutoCompletion() {
    // Vérifie si la grille soumise correspond à la solution
    try {
      const binaryGrid = this.grid.map(v => (v === 1 ? '1' : '0')).join('');
      const res = await verifyNonogramGrid(this.gameData.id, binaryGrid);
      if (res.is_complete) {
        this.isCompleted = true;
        this.saveState();
        this.onVictory(this.gameData);
      }
    } catch (e) {
      console.warn('Erreur vérification auto nonogramme:', e);
    }
  }

  async verifyGrid() {
    if (this.isCompleted) return;
    try {
      const binaryGrid = this.grid.map(v => (v === 1 ? '1' : '0')).join('');
      const res = await verifyNonogramGrid(this.gameData.id, binaryGrid);

      // Met en évidence les erreurs temporairement
      if (res.errors && res.errors.length > 0) {
        res.errors.forEach(pos => {
          const cell = this.container.querySelector(`.nono-cell[data-pos="${pos}"]`);
          if (cell) cell.classList.add('error');
        });
        setTimeout(() => {
          this.container.querySelectorAll('.nono-cell.error').forEach(c => c.classList.remove('error'));
        }, 1500);

        window.dispatchEvent(new CustomEvent('app:toast', {
          detail: { message: `⚠️ ${res.errors.length} case(s) cochée(s) en trop.` }
        }));
      } else if (res.is_complete) {
        this.isCompleted = true;
        this.saveState();
        this.onVictory(this.gameData);
      } else {
        window.dispatchEvent(new CustomEvent('app:toast', {
          detail: { message: '✨ Aucune erreur parmi vos cases noircies !' }
        }));
      }
    } catch (e) {
      window.dispatchEvent(new CustomEvent('app:toast', { detail: { message: e.message } }));
    }
  }

  async giveHint() {
    if (this.isCompleted) return;
    try {
      const solData = await getNonogramSolution(this.gameData.id);
      const sol = solData.solution_grid;

      // Cherche une case de la solution qui n'est pas encore noircie
      const unplaced = [];
      for (let i = 0; i < sol.length; i++) {
        if (sol[i] === '1' && this.grid[i] !== 1) {
          unplaced.push(i);
        }
      }

      if (unplaced.length > 0) {
        const hintPos = unplaced[Math.floor(Math.random() * unplaced.length)];
        this.grid[hintPos] = 1;
        this.renderCell(hintPos);
        this.updateCluesStatus();
        this.saveState();
        this.checkAutoCompletion();

        const r = Math.floor(hintPos / this.gameData.num_cols) + 1;
        const c = (hintPos % this.gameData.num_cols) + 1;
        window.dispatchEvent(new CustomEvent('app:toast', {
          detail: { message: `💡 Case révélée en ligne ${r}, colonne ${c} !` }
        }));
      }
    } catch (e) {
      window.dispatchEvent(new CustomEvent('app:toast', { detail: { message: e.message } }));
    }
  }

  render() {
    this.container.innerHTML = '';
    const { num_rows, num_cols, row_clues, col_clues } = this.gameData;

    const minCellPx = num_cols === 5 ? 36 : (num_cols === 8 ? 29 : 26);
    const table = document.createElement('div');
    table.className = 'nonogram-table';
    table.style.gridTemplateColumns = `max-content repeat(${num_cols}, minmax(clamp(${minCellPx}px, 6vw, 42px), 1fr))`;
    table.style.gridTemplateRows = `max-content repeat(${num_rows}, minmax(clamp(${minCellPx}px, 6vw, 42px), 1fr))`;

    // 1. Coin supérieur gauche
    const corner = document.createElement('div');
    corner.className = 'nono-corner';
    table.appendChild(corner);

    const colBlockSize = num_cols === 8 ? 4 : 5;
    const rowBlockSize = num_rows === 8 ? 4 : 5;

    // 2. En-têtes Colonnes
    for (let c = 0; c < num_cols; c++) {
      const colHeader = document.createElement('div');
      colHeader.className = 'nono-col-header';
      colHeader.dataset.col = c;
      if (num_cols > 5 && (c + 1) % colBlockSize === 0 && c < num_cols - 1) {
        colHeader.classList.add('border-right-thick');
      }

      const clues = col_clues[c] && col_clues[c].length > 0 ? col_clues[c] : [0];
      clues.forEach((num, idx) => {
        const span = document.createElement('span');
        span.className = 'nono-clue-num';
        span.dataset.clueIdx = idx;
        span.textContent = num.toString();
        colHeader.appendChild(span);
      });
      table.appendChild(colHeader);
    }

    // 3. Lignes avec En-tête Ligne + Cellules
    for (let r = 0; r < num_rows; r++) {
      // En-tête Ligne
      const rowHeader = document.createElement('div');
      rowHeader.className = 'nono-row-header';
      rowHeader.dataset.row = r;
      if (num_rows > 5 && (r + 1) % rowBlockSize === 0 && r < num_rows - 1) {
        rowHeader.classList.add('border-bottom-thick');
      }

      const clues = row_clues[r] && row_clues[r].length > 0 ? row_clues[r] : [0];
      clues.forEach((num, idx) => {
        const span = document.createElement('span');
        span.className = 'nono-clue-num';
        span.dataset.clueIdx = idx;
        span.textContent = num.toString();
        rowHeader.appendChild(span);
      });
      table.appendChild(rowHeader);

      // Cellules de la ligne
      for (let c = 0; c < num_cols; c++) {
        const pos = r * num_cols + c;
        const cell = document.createElement('div');
        cell.className = 'nono-cell';
        cell.dataset.pos = pos;
        cell.dataset.row = r;
        cell.dataset.col = c;

        if (num_cols > 5 && (c + 1) % colBlockSize === 0 && c < num_cols - 1) cell.classList.add('border-right-thick');
        if (num_rows > 5 && (r + 1) % rowBlockSize === 0 && r < num_rows - 1) cell.classList.add('border-bottom-thick');

        cell.addEventListener('click', () => this.handleCellTap(pos));
        table.appendChild(cell);
      }
    }

    this.container.appendChild(table);

    // Rendu des valeurs actuelles
    for (let i = 0; i < num_rows * num_cols; i++) {
      this.renderCell(i);
    }

    this.updateCluesStatus();
  }

  renderCell(pos) {
    const cell = this.container.querySelector(`.nono-cell[data-pos="${pos}"]`);
    if (!cell) return;

    cell.classList.remove('filled', 'crossed');
    const val = this.grid[pos];
    if (val === 1) {
      cell.classList.add('filled');
    } else if (val === 2) {
      cell.classList.add('crossed');
    }
  }

  updateCluesStatus() {
    const { num_rows, num_cols, row_clues, col_clues } = this.gameData;

    // Vérification des lignes
    for (let r = 0; r < num_rows; r++) {
      const rowSlice = [];
      for (let c = 0; c < num_cols; c++) {
        rowSlice.push(this.grid[r * num_cols + c] === 1 ? 1 : 0);
      }
      const actualClues = this._calcLineClues(rowSlice);
      const targetClues = row_clues[r] || [];
      const match = JSON.stringify(actualClues) === JSON.stringify(targetClues);

      const header = this.container.querySelector(`.nono-row-header[data-row="${r}"]`);
      if (header) {
        header.querySelectorAll('.nono-clue-num').forEach(span => {
          span.classList.toggle('completed', match && targetClues.length > 0 && targetClues[0] > 0);
        });
      }
    }

    // Vérification des colonnes
    for (let c = 0; c < num_cols; c++) {
      const colSlice = [];
      for (let r = 0; r < num_rows; r++) {
        colSlice.push(this.grid[r * num_cols + c] === 1 ? 1 : 0);
      }
      const actualClues = this._calcLineClues(colSlice);
      const targetClues = col_clues[c] || [];
      const match = JSON.stringify(actualClues) === JSON.stringify(targetClues);

      const header = this.container.querySelector(`.nono-col-header[data-col="${c}"]`);
      if (header) {
        header.querySelectorAll('.nono-clue-num').forEach(span => {
          span.classList.toggle('completed', match && targetClues.length > 0 && targetClues[0] > 0);
        });
      }
    }
  }

  _calcLineClues(line) {
    const res = [];
    let count = 0;
    for (const v of line) {
      if (v === 1) {
        count++;
      } else {
        if (count > 0) res.push(count);
        count = 0;
      }
    }
    if (count > 0) res.push(count);
    return res;
  }

  saveState() {
    if (!this.gameData) return;
    const state = {
      type: 'nonogram',
      id: this.gameData.id,
      gameData: this.gameData,
      grid: [...this.grid],
      mode: this.mode,
      isCompleted: this.isCompleted,
      updatedAt: Date.now(),
    };
    this.onStateChange(state);
  }
}
