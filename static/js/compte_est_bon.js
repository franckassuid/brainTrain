/**
 * BrainTrain - Moteur de Jeu "Le Compte est bon"
 */

import { verifyCompteEstBon, getCompteEstBonSolution } from './api.js';

const OP_DISPLAY = {
  '+': '+',
  '-': '−',
  '*': '×',
  '/': '÷',
};

export class CompteEstBonGame {
  constructor({
    targetEl,
    builderEl,
    tilesEl,
    operatorsEl,
    historyEl,
    onStateChange = () => {},
    onVictory = () => {},
  }) {
    this.targetEl = targetEl;
    this.builderEl = builderEl;
    this.tilesEl = tilesEl;
    this.operatorsEl = operatorsEl;
    this.historyEl = historyEl;
    this.onStateChange = onStateChange;
    this.onVictory = onVictory;

    this.gameData = null;
    this.currentTiles = []; // [{ id: 1, value: 25, isResult: false }]
    this.steps = []; // [{ a: 25, op: "+", b: 8, result: 33 }]
    this.history = []; // stack for undo
    this.selectedTileA = null;
    this.selectedOp = null;
    this.isCompleted = false;
    this.nextTileId = 1;
  }

  loadGame(gameData, savedState = null) {
    this.gameData = gameData;
    this.nextTileId = 1;
    this.selectedTileA = null;
    this.selectedOp = null;
    this.steps = [];
    this.history = [];
    this.isCompleted = false;

    if (savedState && savedState.id === gameData.id) {
      this.currentTiles = [...savedState.currentTiles];
      this.steps = [...(savedState.steps || [])];
      this.history = [...(savedState.history || [])];
      this.isCompleted = !!savedState.isCompleted;
      this.nextTileId = savedState.nextTileId || 100;
    } else {
      this.currentTiles = gameData.available_numbers.map(v => ({
        id: this.nextTileId++,
        value: v,
        isResult: false,
      }));
    }

    this.render();
    this.saveState();
  }

  handleTileTap(tile) {
    if (this.isCompleted) return;

    if (!this.selectedTileA) {
      // 1ère sélection
      this.selectedTileA = tile;
    } else if (this.selectedTileA.id === tile.id) {
      // Désélection si on re-clique
      this.selectedTileA = null;
    } else if (this.selectedOp) {
      // 2ème sélection -> Déclenche le calcul
      this.executeOperation(this.selectedTileA, this.selectedOp, tile);
      this.selectedTileA = null;
      this.selectedOp = null;
    } else {
      // Change le premier nombre sélectionné
      this.selectedTileA = tile;
    }

    this.render();
  }

  handleOpTap(op) {
    if (this.isCompleted) return;

    if (this.selectedOp === op) {
      this.selectedOp = null;
    } else {
      this.selectedOp = op;
    }
    this.render();
  }

  executeOperation(tileA, op, tileB) {
    const a = tileA.value;
    const b = tileB.value;
    let result = null;

    if (op === '+') {
      result = a + b;
    } else if (op === '-') {
      if (a < b) {
        window.dispatchEvent(new CustomEvent('app:toast', {
          detail: { message: `⚠️ Soustraction impossible : ${a} − ${b} donnerait un résultat négatif.` }
        }));
        return;
      } else if (a === b) {
        window.dispatchEvent(new CustomEvent('app:toast', {
          detail: { message: `⚠️ Le résultat d'une opération doit être strictement positif.` }
        }));
        return;
      }
      result = a - b;
    } else if (op === '*') {
      result = a * b;
    } else if (op === '/') {
      if (b === 0 || a % b !== 0) {
        window.dispatchEvent(new CustomEvent('app:toast', {
          detail: { message: `⚠️ Division impossible : ${a} ÷ ${b} n'est pas un nombre entier exact.` }
        }));
        return;
      }
      result = a / b;
    }

    const resultTile = {
      id: this.nextTileId++,
      value: result,
      isResult: true,
    };

    const step = { a, op, b, result };

    // Retrait des tuiles utilisées et ajout de la nouvelle
    this.currentTiles = this.currentTiles.filter(t => t.id !== tileA.id && t.id !== tileB.id);
    this.currentTiles.push(resultTile);

    this.steps.push(step);
    this.history.push({
      tileA,
      tileB,
      op,
      resultTile,
      step,
    });

    this.saveState();
    this.render();

    // Vérification de la cible atteinte
    if (result === this.gameData.target) {
      this.isCompleted = true;
      this.saveState();
      this.onVictory(this.gameData);
    }
  }

  undo() {
    if (this.history.length === 0 || this.isCompleted) return;
    const action = this.history.pop();
    this.steps.pop();

    // Retire la tuile résultat et remet les tuiles d'origine
    this.currentTiles = this.currentTiles.filter(t => t.id !== action.resultTile.id);
    this.currentTiles.push(action.tileA, action.tileB);

    this.selectedTileA = null;
    this.selectedOp = null;

    this.render();
    this.saveState();
  }

  clear() {
    if (this.isCompleted) return;
    this.nextTileId = 1;
    this.currentTiles = this.gameData.available_numbers.map(v => ({
      id: this.nextTileId++,
      value: v,
      isResult: false,
    }));
    this.steps = [];
    this.history = [];
    this.selectedTileA = null;
    this.selectedOp = null;

    this.render();
    this.saveState();
  }

  async giveHint() {
    if (this.isCompleted) return;
    try {
      const sol = await getCompteEstBonSolution(this.gameData.id);
      const solSteps = sol.solution_steps; // [{ a, op, b, result }, ...]

      // Trouve la prochaine étape applicable avec les tuiles actuelles
      for (const step of solSteps) {
        const tileA = this.currentTiles.find(t => t.value === step.a);
        const tileB = this.currentTiles.find(t => t.value === step.b && t.id !== (tileA ? tileA.id : null));

        if (tileA && tileB) {
          this.executeOperation(tileA, step.op, tileB);
          window.dispatchEvent(new CustomEvent('app:toast', {
            detail: { message: `💡 Indice appliqué : ${step.a} ${OP_DISPLAY[step.op]} ${step.b} = ${step.result}` }
          }));
          return;
        }
      }

      // Si aucune étape directe n'est disponible, affiche une indication
      window.dispatchEvent(new CustomEvent('app:toast', {
        detail: { message: `💡 Conseil : essayez d'approcher ${this.gameData.target} en multipliant les plus grands nombres.` }
      }));
    } catch (e) {
      window.dispatchEvent(new CustomEvent('app:toast', { detail: { message: e.message } }));
    }
  }

  async showSolutionModal() {
    try {
      const sol = await getCompteEstBonSolution(this.gameData.id);
      const stepsHtml = sol.solution_steps
        .map((s, idx) => `<div>Étape ${idx + 1} : <strong>${s.a} ${OP_DISPLAY[s.op]} ${s.b} = ${s.result}</strong></div>`)
        .join('');

      window.dispatchEvent(new CustomEvent('app:modal', {
        detail: {
          icon: '💡',
          title: 'Solution du Compte est bon',
          body: `<div style="text-align: left; line-height: 1.6; font-size: 0.9375rem;">${stepsHtml}</div>`,
          stats: [{ label: 'Cible', value: this.gameData.target }],
          primaryAction: { text: 'Compris', onClick: () => window.app.hideModal() },
        }
      }));
    } catch (e) {
      window.dispatchEvent(new CustomEvent('app:toast', { detail: { message: e.message } }));
    }
  }

  render() {
    // 1. Cible
    this.targetEl.textContent = this.gameData.target.toString();

    // 2. Builder Actif
    this.builderEl.innerHTML = '';
    const slotA = document.createElement('div');
    slotA.className = `ceb-slot ${this.selectedTileA ? 'filled' : ''}`;
    slotA.textContent = this.selectedTileA ? this.selectedTileA.value : '?';
    this.builderEl.appendChild(slotA);

    const slotOp = document.createElement('div');
    slotOp.className = `ceb-slot op-slot ${this.selectedOp ? 'filled' : ''}`;
    slotOp.textContent = this.selectedOp ? OP_DISPLAY[this.selectedOp] : '...';
    this.builderEl.appendChild(slotOp);

    const slotB = document.createElement('div');
    slotB.className = 'ceb-slot';
    slotB.textContent = '?';
    this.builderEl.appendChild(slotB);

    // 3. Tuiles Nombres Disponibles
    this.tilesEl.innerHTML = '';
    this.currentTiles.forEach(tile => {
      const btn = document.createElement('button');
      btn.className = `ceb-num-tile ${tile.isResult ? 'is-result' : ''}`;
      if (this.selectedTileA && this.selectedTileA.id === tile.id) {
        btn.classList.add('selected');
      }
      btn.textContent = tile.value.toString();
      btn.addEventListener('click', () => this.handleTileTap(tile));
      this.tilesEl.appendChild(btn);
    });

    // 4. Opérateurs
    this.operatorsEl.querySelectorAll('.ceb-op-btn').forEach(btn => {
      btn.classList.toggle('selected', btn.dataset.op === this.selectedOp);
    });

    // 5. Historique
    this.historyEl.innerHTML = '';
    if (this.steps.length === 0) {
      this.historyEl.innerHTML = '<div style="text-align:center; color:var(--text-muted); font-size:0.8125rem;">Combinez deux nombres avec un opérateur.</div>';
    } else {
      this.steps.forEach((step, idx) => {
        const item = document.createElement('div');
        item.className = 'ceb-step-item';
        item.innerHTML = `
          <span class="ceb-step-num">#${idx + 1}</span>
          <span>${step.a} ${OP_DISPLAY[step.op]} ${step.b} = <strong>${step.result}</strong></span>
        `;
        this.historyEl.appendChild(item);
      });
    }
  }

  saveState() {
    if (!this.gameData) return;
    const state = {
      type: 'compte_est_bon',
      id: this.gameData.id,
      gameData: this.gameData,
      currentTiles: [...this.currentTiles],
      steps: [...this.steps],
      history: [...this.history],
      nextTileId: this.nextTileId,
      isCompleted: this.isCompleted,
      updatedAt: Date.now(),
    };
    this.onStateChange(state);
  }
}
