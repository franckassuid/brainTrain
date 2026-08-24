/**
 * BrainTrain - Moteur de Jeu Mastermind
 */

import { submitMastermindGuess, revealMastermindSecret } from './api.js';

export const COLOR_NAMES = {
  1: 'Rouge',
  2: 'Bleu',
  3: 'Vert',
  4: 'Jaune',
  5: 'Violet',
  6: 'Orange',
  7: 'Cyan',
  8: 'Rose',
};

export class MastermindGame {
  constructor({
    boardContainerEl,
    activeGuessContainerEl,
    colorPickerContainerEl,
    onStateChange = () => {},
    onGameOver = () => {},
  }) {
    this.boardContainer = boardContainerEl;
    this.activeGuessContainer = activeGuessContainerEl;
    this.colorPickerContainer = colorPickerContainerEl;
    this.onStateChange = onStateChange;
    this.onGameOver = onGameOver;

    this.gameData = null;
    this.history = []; // [{ guess: [1,2,3,4], exact: 2, misplaced: 1 }]
    this.currentGuess = [];
    this.activeSlotIndex = 0;
    this.isGameOver = false;
    this.hasWon = false;
    this.revealedSecret = null;
  }

  loadGame(gameData, savedState = null) {
    this.gameData = gameData;
    this.history = [];
    this.isGameOver = false;
    this.hasWon = false;
    this.revealedSecret = null;

    const numPositions = gameData.num_positions;
    this.currentGuess = new Array(numPositions).fill(0);
    this.activeSlotIndex = 0;

    if (savedState && savedState.id === gameData.id) {
      this.history = [...(savedState.history || [])];
      this.currentGuess = savedState.currentGuess && savedState.currentGuess.length === numPositions
        ? [...savedState.currentGuess]
        : new Array(numPositions).fill(0);
      this.isGameOver = !!savedState.isGameOver;
      this.hasWon = !!savedState.hasWon;
      this.revealedSecret = savedState.revealedSecret || null;
    }

    this.render();
    this.saveState();
  }

  selectSlot(index) {
    if (this.isGameOver) return;
    if (index >= 0 && index < this.gameData.num_positions) {
      this.activeSlotIndex = index;
      this.renderActiveRow();
    }
  }

  selectColor(colorId) {
    if (this.isGameOver) return;
    if (colorId < 1 || colorId > this.gameData.num_colors) return;

    // Place la couleur dans le slot actif
    this.currentGuess[this.activeSlotIndex] = colorId;

    // Avance automatiquement au prochain slot vide ou suivant
    const numPositions = this.gameData.num_positions;
    let nextEmpty = -1;
    for (let i = 0; i < numPositions; i++) {
      if (this.currentGuess[i] === 0) {
        nextEmpty = i;
        break;
      }
    }

    if (nextEmpty !== -1) {
      this.activeSlotIndex = nextEmpty;
    } else {
      // Si tous sont remplis, avance au slot suivant cyclique
      this.activeSlotIndex = (this.activeSlotIndex + 1) % numPositions;
    }

    this.renderActiveRow();
    this.saveState();
  }

  clearActiveSlot() {
    if (this.isGameOver) return;

    // Si le slot actif est rempli, on l'efface
    if (this.currentGuess[this.activeSlotIndex] > 0) {
      this.currentGuess[this.activeSlotIndex] = 0;
    } else if (this.activeSlotIndex > 0) {
      // Sinon on recule d'un cran et on efface
      this.activeSlotIndex -= 1;
      this.currentGuess[this.activeSlotIndex] = 0;
    }

    this.renderActiveRow();
    this.saveState();
  }

  resetCurrentGuess() {
    if (this.isGameOver) return;
    this.currentGuess = new Array(this.gameData.num_positions).fill(0);
    this.activeSlotIndex = 0;
    this.renderActiveRow();
    this.saveState();
  }

  async submitGuess() {
    if (this.isGameOver) return;
    if (this.currentGuess.some(v => v === 0)) {
      window.dispatchEvent(new CustomEvent('app:toast', {
        detail: { message: '⚠️ Veuillez remplir toutes les positions.' }
      }));
      return;
    }

    try {
      const res = await submitMastermindGuess(this.gameData.id, this.currentGuess);
      const attemptResult = {
        guess: [...this.currentGuess],
        exact: res.exact,
        misplaced: res.misplaced,
      };

      this.history.push(attemptResult);
      this.currentGuess = new Array(this.gameData.num_positions).fill(0);
      this.activeSlotIndex = 0;

      if (res.won) {
        this.isGameOver = true;
        this.hasWon = true;
        this.revealedSecret = res.secret_code;
        this.render();
        this.saveState();
        this.onGameOver({
          won: true,
          attemptsUsed: this.history.length,
          maxAttempts: this.gameData.max_attempts,
          secretCode: res.secret_code,
        });
      } else if (this.history.length >= this.gameData.max_attempts) {
        // Tentatives épuisées -> Défaite
        this.isGameOver = true;
        this.hasWon = false;
        const revealData = await revealMastermindSecret(this.gameData.id);
        this.revealedSecret = revealData.secret_code;
        this.render();
        this.saveState();
        this.onGameOver({
          won: false,
          attemptsUsed: this.history.length,
          maxAttempts: this.gameData.max_attempts,
          secretCode: revealData.secret_code,
        });
      } else {
        // Partie continue
        this.render();
        this.saveState();
      }
    } catch (e) {
      window.dispatchEvent(new CustomEvent('app:toast', {
        detail: { message: `Erreur : ${e.message}` }
      }));
    }
  }

  render() {
    this.renderHistory();
    this.renderActiveRow();
    this.renderColorPalette();
  }

  renderHistory() {
    this.boardContainer.innerHTML = '';

    if (this.history.length === 0) {
      const emptyMsg = document.createElement('div');
      emptyMsg.style.textAlign = 'center';
      emptyMsg.style.padding = '1.5rem 0';
      emptyMsg.style.color = 'var(--text-muted)';
      emptyMsg.style.fontSize = '0.875rem';
      emptyMsg.textContent = 'Composez votre première tentative ci-dessous !';
      this.boardContainer.appendChild(emptyMsg);
      return;
    }

    this.history.forEach((item, index) => {
      const row = document.createElement('div');
      row.className = 'attempt-row';

      const numSpan = document.createElement('span');
      numSpan.className = 'attempt-number';
      numSpan.textContent = `#${index + 1}`;
      row.appendChild(numSpan);

      const pegsDiv = document.createElement('div');
      pegsDiv.className = 'attempt-pegs';
      item.guess.forEach(colorId => {
        const peg = document.createElement('div');
        peg.className = `color-peg color-${colorId}`;
        peg.textContent = colorId;
        pegsDiv.appendChild(peg);
      });
      row.appendChild(pegsDiv);

      const verdict = document.createElement('div');
      verdict.className = 'verdict-box';

      // Bien placés (exacts)
      const exactItem = document.createElement('div');
      exactItem.className = 'verdict-item exact';
      exactItem.title = `${item.exact} bien placé(s)`;
      exactItem.innerHTML = `<span class="verdict-dot exact-dot"></span><span>${item.exact}</span>`;
      verdict.appendChild(exactItem);

      // Mal placés
      const misplacedItem = document.createElement('div');
      misplacedItem.className = 'verdict-item misplaced';
      misplacedItem.title = `${item.misplaced} mal placé(s)`;
      misplacedItem.innerHTML = `<span class="verdict-dot misplaced-dot"></span><span>${item.misplaced}</span>`;
      verdict.appendChild(misplacedItem);

      row.appendChild(verdict);
      this.boardContainer.appendChild(row);
    });

    // Auto-scroll vers le bas
    this.boardContainer.scrollTop = this.boardContainer.scrollHeight;
  }

  renderActiveRow() {
    this.activeGuessContainer.innerHTML = '';
    const numPositions = this.gameData.num_positions;
    const attemptsLeft = this.gameData.max_attempts - this.history.length;

    const card = document.createElement('div');
    card.className = 'active-guess-card';

    // Header de la rangée active
    const header = document.createElement('div');
    header.className = 'active-guess-header';

    const title = document.createElement('div');
    title.className = 'active-guess-title';
    title.innerHTML = `<span>🎯</span> Tentative #${this.history.length + 1}`;
    header.appendChild(title);

    const badge = document.createElement('div');
    badge.className = 'attempts-left-badge';
    badge.textContent = `${attemptsLeft} restante${attemptsLeft > 1 ? 's' : ''}`;
    header.appendChild(badge);

    card.appendChild(header);

    // Slots tactiles
    const slotsContainer = document.createElement('div');
    slotsContainer.className = 'active-slots-container';

    for (let i = 0; i < numPositions; i++) {
      const slot = document.createElement('div');
      slot.className = 'guess-slot';
      if (i === this.activeSlotIndex && !this.isGameOver) {
        slot.classList.add('selected-slot');
      }

      const colorVal = this.currentGuess[i];
      if (colorVal > 0) {
        slot.classList.add('filled', `color-${colorVal}`);
        slot.textContent = colorVal.toString();
        slot.style.color = '#FFFFFF';
        slot.style.fontWeight = '800';
      }

      slot.addEventListener('click', () => this.selectSlot(i));
      slotsContainer.appendChild(slot);
    }

    card.appendChild(slotsContainer);

    // Boutons d'action
    const actions = document.createElement('div');
    actions.className = 'active-guess-actions';

    const clearBtn = document.createElement('button');
    clearBtn.className = 'btn-clear-slot';
    clearBtn.innerHTML = '⌫';
    clearBtn.title = 'Effacer';
    clearBtn.disabled = this.isGameOver;
    clearBtn.addEventListener('click', () => this.clearActiveSlot());
    actions.appendChild(clearBtn);

    const validateBtn = document.createElement('button');
    validateBtn.className = 'btn-validate-guess';
    validateBtn.textContent = 'Valider la combinaison';
    const isReady = this.currentGuess.every(v => v > 0) && !this.isGameOver;
    validateBtn.disabled = !isReady;
    validateBtn.addEventListener('click', () => this.submitGuess());
    actions.appendChild(validateBtn);

    card.appendChild(actions);
    this.activeGuessContainer.appendChild(card);
  }

  renderColorPalette() {
    this.colorPickerContainer.innerHTML = '';
    const numColors = this.gameData.num_colors;

    const card = document.createElement('div');
    card.className = 'color-picker-card';

    const title = document.createElement('div');
    title.className = 'section-title';
    title.textContent = 'Choisissez une couleur :';
    card.appendChild(title);

    const palette = document.createElement('div');
    palette.className = 'color-picker-palette';

    for (let c = 1; c <= numColors; c++) {
      const btn = document.createElement('button');
      btn.className = `color-choice-btn color-${c}`;
      btn.textContent = c.toString();
      btn.title = COLOR_NAMES[c] || `Couleur ${c}`;
      btn.disabled = this.isGameOver;
      btn.addEventListener('click', () => this.selectColor(c));
      palette.appendChild(btn);
    }

    card.appendChild(palette);
    this.colorPickerContainer.appendChild(card);
  }

  saveState() {
    if (!this.gameData) return;
    const state = {
      type: 'mastermind',
      id: this.gameData.id,
      gameData: this.gameData,
      history: [...this.history],
      currentGuess: [...this.currentGuess],
      isGameOver: this.isGameOver,
      hasWon: this.hasWon,
      revealedSecret: this.revealedSecret,
      updatedAt: Date.now(),
    };
    this.onStateChange(state);
  }
}
