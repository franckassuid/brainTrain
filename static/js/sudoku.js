/**
 * BrainTrain - Moteur de Jeu Sudoku
 */

import { verifySudokuGrid, getSudokuSolution } from './api.js';

export class SudokuGame {
  constructor({ containerEl, onStateChange = () => {}, onVictory = () => {} }) {
    this.container = containerEl;
    this.onStateChange = onStateChange;
    this.onVictory = onVictory;

    this.gameData = null;
    this.grid = new Array(81).fill(0);
    this.notes = Array.from({ length: 81 }, () => new Set());
    this.clues = new Set(); // Indices des cases de départ (non modifiables)
    this.selectedPos = null;
    this.notesMode = false;
    this.history = [];
    this.errorPositions = new Set();
    this.isCompleted = false;

    this._bindEvents();
  }

  loadGame(gameData, savedState = null) {
    this.gameData = gameData;
    this.clues.clear();
    this.history = [];
    this.errorPositions.clear();
    this.isCompleted = false;
    this.selectedPos = null;
    this.notesMode = false;

    // Définition des indices de départ
    const startStr = gameData.starting_grid;
    for (let i = 0; i < 81; i++) {
      const val = parseInt(startStr[i], 10);
      if (val > 0) {
        this.clues.add(i);
      }
    }

    if (savedState && savedState.id === gameData.id) {
      // Restauration de la sauvegarde
      this.grid = [...savedState.grid];
      this.notes = savedState.notes.map(nArr => new Set(nArr));
      this.notesMode = !!savedState.notesMode;
      this.isCompleted = !!savedState.isCompleted;
    } else {
      // Nouvelle partie
      this.grid = Array.from(startStr, ch => parseInt(ch, 10));
      this.notes = Array.from({ length: 81 }, () => new Set());
    }

    this.render();
    this.saveState();
  }

  _bindEvents() {
    // Événements clavier pour les utilisateurs desktop
    window.addEventListener('keydown', (e) => {
      if (!this.container.closest('.view.active') || this.selectedPos === null || this.isCompleted) return;

      if (e.key >= '1' && e.key <= '9') {
        e.preventDefault();
        this.handleDigit(parseInt(e.key, 10));
      } else if (e.key === 'Backspace' || e.key === 'Delete' || e.key === '0') {
        e.preventDefault();
        this.clearSelectedCell();
      } else if (e.key === 'n' || e.key === 'N') {
        e.preventDefault();
        this.toggleNotesMode();
      } else if ((e.ctrlKey || e.metaKey) && e.key === 'z') {
        e.preventDefault();
        this.undo();
      } else if (e.key === 'ArrowUp' && this.selectedPos >= 9) {
        e.preventDefault();
        this.selectCell(this.selectedPos - 9);
      } else if (e.key === 'ArrowDown' && this.selectedPos <= 71) {
        e.preventDefault();
        this.selectCell(this.selectedPos + 9);
      } else if (e.key === 'ArrowLeft' && this.selectedPos % 9 > 0) {
        e.preventDefault();
        this.selectCell(this.selectedPos - 1);
      } else if (e.key === 'ArrowRight' && this.selectedPos % 9 < 8) {
        e.preventDefault();
        this.selectCell(this.selectedPos + 1);
      }
    });
  }

  selectCell(pos) {
    if (pos < 0 || pos >= 81) return;
    this.selectedPos = pos;
    this.updateHighlights();
  }

  handleDigit(digit) {
    if (this.selectedPos === null || this.isCompleted) return;
    if (this.clues.has(this.selectedPos)) return; // Indice initial protégé

    const pos = this.selectedPos;

    if (this.notesMode) {
      // Mode crayon / notes
      const cellNotes = this.notes[pos];
      const prevNotes = Array.from(cellNotes);

      if (cellNotes.has(digit)) {
        cellNotes.delete(digit);
      } else {
        cellNotes.add(digit);
      }

      this.history.push({
        type: 'note',
        pos,
        prevNotes,
        nextNotes: Array.from(cellNotes),
      });

      this.renderCell(pos);
    } else {
      // Mode chiffre normal
      const prevVal = this.grid[pos];
      const prevNotes = Array.from(this.notes[pos]);
      const nextVal = prevVal === digit ? 0 : digit; // Si on reclique sur le même chiffre, on l'efface

      this.history.push({
        type: 'value',
        pos,
        prevVal,
        nextVal,
        prevNotes,
      });

      this.grid[pos] = nextVal;
      this.notes[pos].clear();
      this.errorPositions.delete(pos);

      // Si un chiffre est posé, on le retire des notes des cases voisines
      if (nextVal > 0) {
        this.removeDigitFromPeersNotes(pos, nextVal);
      }

      this.renderCell(pos);
      this.checkAutoCompletion();
    }

    this.updateHighlights();
    this.updateKeypadCounts();
    this.saveState();
  }

  clearSelectedCell() {
    if (this.selectedPos === null || this.isCompleted) return;
    if (this.clues.has(this.selectedPos)) return;

    const pos = this.selectedPos;
    const prevVal = this.grid[pos];
    const prevNotes = Array.from(this.notes[pos]);

    if (prevVal === 0 && prevNotes.length === 0) return;

    this.history.push({
      type: 'value',
      pos,
      prevVal,
      nextVal: 0,
      prevNotes,
    });

    this.grid[pos] = 0;
    this.notes[pos].clear();
    this.errorPositions.delete(pos);

    this.renderCell(pos);
    this.updateHighlights();
    this.updateKeypadCounts();
    this.saveState();
  }

  toggleNotesMode() {
    this.notesMode = !this.notesMode;
    const btn = document.getElementById('btn-sudoku-notes');
    if (btn) {
      btn.classList.toggle('active', this.notesMode);
    }
    this.saveState();
  }

  undo() {
    if (this.history.length === 0 || this.isCompleted) return;
    const action = this.history.pop();

    if (action.type === 'value') {
      this.grid[action.pos] = action.prevVal;
      this.notes[action.pos] = new Set(action.prevNotes);
    } else if (action.type === 'note') {
      this.notes[action.pos] = new Set(action.prevNotes);
    }

    this.errorPositions.delete(action.pos);
    this.renderCell(action.pos);
    this.selectCell(action.pos);
    this.updateKeypadCounts();
    this.saveState();
  }

  removeDigitFromPeersNotes(pos, digit) {
    const r = Math.floor(pos / 9);
    const c = pos % 9;
    const br = Math.floor(r / 3) * 3;
    const bc = Math.floor(c / 3) * 3;

    for (let i = 0; i < 81; i++) {
      const ir = Math.floor(i / 9);
      const ic = i % 9;
      const sameRow = ir === r;
      const sameCol = ic === c;
      const sameBox = Math.floor(ir / 3) * 3 === br && Math.floor(ic / 3) * 3 === bc;

      if ((sameRow || sameCol || sameBox) && i !== pos) {
        if (this.notes[i].has(digit)) {
          this.notes[i].delete(digit);
          this.renderCell(i);
        }
      }
    }
  }

  async checkAutoCompletion() {
    // Vérifie si la grille est entièrement remplie (aucun 0)
    const isFull = this.grid.every(v => v > 0);
    if (!isFull) return;

    try {
      const gridStr = this.grid.join('');
      const res = await verifySudokuGrid(this.gameData.id, gridStr);
      if (res.is_complete && res.is_valid) {
        this.isCompleted = true;
        this.saveState();
        this.onVictory(this.gameData);
      } else if (res.errors && res.errors.length > 0) {
        this.errorPositions = new Set(res.errors);
        this.updateHighlights();
      }
    } catch (e) {
      console.warn('Erreur lors de la vérification auto:', e);
    }
  }

  async verifyGrid() {
    if (this.isCompleted) return;
    try {
      const gridStr = this.grid.join('');
      const res = await verifySudokuGrid(this.gameData.id, gridStr);

      this.errorPositions = new Set(res.errors || []);
      this.updateHighlights();

      if (res.is_complete && res.is_valid) {
        this.isCompleted = true;
        this.saveState();
        this.onVictory(this.gameData);
      } else if (res.errors && res.errors.length > 0) {
        // Notification d'erreurs
        window.dispatchEvent(new CustomEvent('app:toast', {
          detail: { message: `⚠️ ${res.errors.length} case(s) incorrecte(s)` }
        }));
      } else {
        window.dispatchEvent(new CustomEvent('app:toast', {
          detail: { message: '✨ Aucun conflit détecté pour le moment !' }
        }));
      }
    } catch (e) {
      window.dispatchEvent(new CustomEvent('app:toast', {
        detail: { message: `Erreur : ${e.message}` }
      }));
    }
  }

  async giveHint() {
    if (this.isCompleted) return;
    try {
      const solData = await getSudokuSolution(this.gameData.id);
      const sol = solData.solution_grid;

      // Cherche en priorité la case sélectionnée si elle est vide ou fausse
      let targetPos = null;
      if (this.selectedPos !== null && !this.clues.has(this.selectedPos)) {
        if (this.grid[this.selectedPos] === 0 || this.grid[this.selectedPos] !== parseInt(sol[this.selectedPos], 10)) {
          targetPos = this.selectedPos;
        }
      }

      // Sinon cherche la première case vide
      if (targetPos === null) {
        for (let i = 0; i < 81; i++) {
          if (!this.clues.has(i) && this.grid[i] !== parseInt(sol[i], 10)) {
            targetPos = i;
            break;
          }
        }
      }

      if (targetPos !== null) {
        const correctVal = parseInt(sol[targetPos], 10);
        this.selectCell(targetPos);
        this.handleDigit(correctVal);
        this.clues.add(targetPos); // Fixe l'indice donné
        this.renderCell(targetPos);
        window.dispatchEvent(new CustomEvent('app:toast', {
          detail: { message: `💡 Indice placé en case (${Math.floor(targetPos/9)+1}, ${(targetPos%9)+1})` }
        }));
      }
    } catch (e) {
      window.dispatchEvent(new CustomEvent('app:toast', { detail: { message: e.message } }));
    }
  }

  render() {
    this.container.innerHTML = '';
    const board = document.createElement('div');
    board.className = 'sudoku-board';

    for (let i = 0; i < 81; i++) {
      const cell = document.createElement('div');
      cell.className = 'sudoku-cell';
      cell.dataset.pos = i;
      cell.dataset.row = Math.floor(i / 9);
      cell.dataset.col = i % 9;

      if (this.clues.has(i)) {
        cell.classList.add('clue');
      }

      cell.addEventListener('click', () => this.selectCell(i));
      board.appendChild(cell);
    }

    this.container.appendChild(board);

    // Rendu du contenu de chaque case
    for (let i = 0; i < 81; i++) {
      this.renderCell(i);
    }

    this.updateHighlights();
    this.updateKeypadCounts();

    const notesBtn = document.getElementById('btn-sudoku-notes');
    if (notesBtn) {
      notesBtn.classList.toggle('active', this.notesMode);
    }
  }

  renderCell(pos) {
    const cell = this.container.querySelector(`.sudoku-cell[data-pos="${pos}"]`);
    if (!cell) return;

    cell.innerHTML = '';
    const val = this.grid[pos];

    if (val > 0) {
      cell.textContent = val.toString();
    } else {
      const cellNotes = this.notes[pos];
      if (cellNotes.size > 0) {
        const notesGrid = document.createElement('div');
        notesGrid.className = 'sudoku-notes-grid';
        for (let d = 1; d <= 9; d++) {
          const digitSpan = document.createElement('span');
          digitSpan.className = 'note-digit';
          digitSpan.textContent = cellNotes.has(d) ? d.toString() : '';
          notesGrid.appendChild(digitSpan);
        }
        cell.appendChild(notesGrid);
      }
    }
  }

  updateHighlights() {
    const cells = this.container.querySelectorAll('.sudoku-cell');
    const selectedVal = this.selectedPos !== null ? this.grid[this.selectedPos] : 0;
    const selR = this.selectedPos !== null ? Math.floor(this.selectedPos / 9) : null;
    const selC = this.selectedPos !== null ? this.selectedPos % 9 : null;
    const selB = this.selectedPos !== null ? Math.floor(selR / 3) * 3 + Math.floor(selC / 3) : null;

    cells.forEach((cell, i) => {
      const r = Math.floor(i / 9);
      const c = i % 9;
      const b = Math.floor(r / 3) * 3 + Math.floor(c / 3);
      const val = this.grid[i];

      cell.classList.remove('selected', 'highlight-peer', 'highlight-same-val', 'error');

      if (i === this.selectedPos) {
        cell.classList.add('selected');
      } else if (this.selectedPos !== null && (r === selR || c === selC || b === selB)) {
        cell.classList.add('highlight-peer');
      }

      if (selectedVal > 0 && val === selectedVal && i !== this.selectedPos) {
        cell.classList.add('highlight-same-val');
      }

      if (this.errorPositions.has(i)) {
        cell.classList.add('error');
      }
    });
  }

  updateKeypadCounts() {
    const counts = {};
    for (let d = 1; d <= 9; d++) counts[d] = 0;
    for (let i = 0; i < 81; i++) {
      if (this.grid[i] > 0) {
        counts[this.grid[i]] = (counts[this.grid[i]] || 0) + 1;
      }
    }

    for (let d = 1; d <= 9; d++) {
      const btn = document.querySelector(`.keypad-btn[data-digit="${d}"]`);
      if (btn) {
        const remaining = 9 - (counts[d] || 0);
        const countSpan = btn.querySelector('.keypad-count');
        if (countSpan) {
          countSpan.textContent = remaining > 0 ? `${remaining}` : '✓';
        }
        btn.classList.toggle('completed', remaining === 0);
      }
    }
  }

  saveState() {
    if (!this.gameData) return;
    const state = {
      type: 'sudoku',
      id: this.gameData.id,
      gameData: this.gameData,
      grid: [...this.grid],
      notes: this.notes.map(s => Array.from(s)),
      notesMode: this.notesMode,
      isCompleted: this.isCompleted,
      updatedAt: Date.now(),
    };
    this.onStateChange(state);
  }
}
