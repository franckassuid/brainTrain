/**
 * BrainTrain - Moteur de Jeu Hashi (Ponts / Hashiwokakero)
 */

import { verifyHashiBridges, getHashiSolution } from './api.js';

export class HashiGame {
  constructor({ containerEl, onStateChange = () => {}, onVictory = () => {} }) {
    this.container = containerEl;
    this.onStateChange = onStateChange;
    this.onVictory = onVictory;

    this.gameData = null;
    this.bridges = new Map(); // "i_j" -> count (1 ou 2), avec i < j
    this.selectedIslandIdx = null;
    this.history = [];
    this.isCompleted = false;
  }

  loadGame(gameData, savedState = null) {
    this.gameData = gameData;
    this.bridges.clear();
    this.selectedIslandIdx = null;
    this.history = [];
    this.isCompleted = false;

    if (savedState && savedState.id === gameData.id) {
      if (savedState.bridges) {
        savedState.bridges.forEach(([i, j, count]) => {
          const key = this._bridgeKey(i, j);
          this.bridges.set(key, count);
        });
      }
      this.isCompleted = !!savedState.isCompleted;
    }

    this.render();
    this.saveState();
  }

  _bridgeKey(i, j) {
    const min = Math.min(i, j);
    const max = Math.max(i, j);
    return `${min}_${max}`;
  }

  _parseBridgeKey(key) {
    const [min, max] = key.split('_').map(Number);
    return [min, max];
  }

  getPotentialPartners(srcIdx) {
    const islands = this.gameData.islands;
    const [sr, sc] = islands[srcIdx];
    const partners = [];

    // Directions : haut, bas, gauche, droite
    const dirs = [
      { dr: -1, dc: 0 }, // Haut
      { dr: 1, dc: 0 },  // Bas
      { dr: 0, dc: -1 }, // Gauche
      { dr: 0, dc: 1 },  // Droite
    ];

    dirs.forEach(({ dr, dc }) => {
      let closestIdx = null;
      let closestDist = Infinity;

      islands.forEach(([r, c], idx) => {
        if (idx === srcIdx) return;

        if (dr !== 0 && c === sc) {
          const dist = (r - sr) * dr;
          if (dist > 0 && dist < closestDist) {
            closestDist = dist;
            closestIdx = idx;
          }
        } else if (dc !== 0 && r === sr) {
          const dist = (c - sc) * dc;
          if (dist > 0 && dist < closestDist) {
            closestDist = dist;
            closestIdx = idx;
          }
        }
      });

      if (closestIdx !== null) {
        partners.push(closestIdx);
      }
    });

    return partners;
  }

  canConnect(i, j) {
    const islands = this.gameData.islands;
    const [r1, c1] = islands[i];
    const [r2, c2] = islands[j];

    // 1. Doivent être alignées
    if (r1 !== r2 && c1 !== c2) return false;

    // 2. Aucune autre île intermédiaire
    if (r1 === r2) {
      const minC = Math.min(c1, c2);
      const maxC = Math.max(c1, c2);
      const hasBetween = islands.some(([ir, ic], idx) => idx !== i && idx !== j && ir === r1 && ic > minC && ic < maxC);
      if (hasBetween) return false;
    } else {
      const minR = Math.min(r1, r2);
      const maxR = Math.max(r1, r2);
      const hasBetween = islands.some(([ir, ic], idx) => idx !== i && idx !== j && ic === c1 && ir > minR && ir < maxR);
      if (hasBetween) return false;
    }

    // 3. Ne doit pas croiser un pont perpendiculaire existant
    for (const [key, count] of this.bridges.entries()) {
      if (count <= 0) continue;
      const [bi, bj] = this._parseBridgeKey(key);
      if (bi === i || bi === j || bj === i || bj === j) continue;

      const [br1, bc1] = islands[bi];
      const [br2, bc2] = islands[bj];

      // Segment 1 (i, j) horizontal et Segment 2 (bi, bj) vertical
      if (r1 === r2 && bc1 === bc2) {
        const seg1MinC = Math.min(c1, c2);
        const seg1MaxC = Math.max(c1, c2);
        const seg2MinR = Math.min(br1, br2);
        const seg2MaxR = Math.max(br1, br2);

        if (bc1 > seg1MinC && bc1 < seg1MaxC && r1 > seg2MinR && r1 < seg2MaxR) {
          return false; // Croisement
        }
      }

      // Segment 1 (i, j) vertical et Segment 2 (bi, bj) horizontal
      if (c1 === c2 && br1 === br2) {
        const seg1MinR = Math.min(r1, r2);
        const seg1MaxR = Math.max(r1, r2);
        const seg2MinC = Math.min(bc1, bc2);
        const seg2MaxC = Math.max(bc1, bc2);

        if (br1 > seg1MinR && br1 < seg1MaxR && c1 > seg2MinC && c1 < seg2MaxC) {
          return false; // Croisement
        }
      }
    }

    return true;
  }

  handleIslandTap(idx) {
    if (this.isCompleted) return;

    if (this.selectedIslandIdx === null) {
      this.selectedIslandIdx = idx;
      this.render();
      return;
    }

    if (this.selectedIslandIdx === idx) {
      // Désélectionne si on re-clique sur la même île
      this.selectedIslandIdx = null;
      this.render();
      return;
    }

    const srcIdx = this.selectedIslandIdx;
    const targetIdx = idx;

    if (this.canConnect(srcIdx, targetIdx)) {
      this.cycleBridge(srcIdx, targetIdx);
      this.selectedIslandIdx = targetIdx; // Enchaîne naturellement pour le confort de jeu
      this.render();
      this.checkAutoCompletion();
    } else {
      // Si la connexion n'est pas possible, change la sélection vers la nouvelle île
      this.selectedIslandIdx = targetIdx;
      this.render();
    }
  }

  cycleBridge(i, j) {
    const key = this._bridgeKey(i, j);
    const prevCount = this.bridges.get(key) || 0;
    const nextCount = (prevCount + 1) % 3; // 0 -> 1 -> 2 -> 0

    this.history.push({ key, prevCount, nextCount });

    if (nextCount === 0) {
      this.bridges.delete(key);
    } else {
      this.bridges.set(key, nextCount);
    }

    this.saveState();
  }

  undo() {
    if (this.history.length === 0 || this.isCompleted) return;
    const action = this.history.pop();
    if (action.prevCount === 0) {
      this.bridges.delete(action.key);
    } else {
      this.bridges.set(action.key, action.prevCount);
    }
    this.render();
    this.saveState();
  }

  clearBridges() {
    if (this.isCompleted) return;
    this.bridges.clear();
    this.history = [];
    this.selectedIslandIdx = null;
    this.render();
    this.saveState();
  }

  getBridgesList() {
    const list = [];
    for (const [key, count] of this.bridges.entries()) {
      if (count > 0) {
        const [i, j] = this._parseBridgeKey(key);
        list.push([i, j, count]);
      }
    }
    return list;
  }

  async checkAutoCompletion() {
    try {
      const bridgesList = this.getBridgesList();
      const res = await verifyHashiBridges(this.gameData.id, bridgesList);
      if (res.is_complete) {
        this.isCompleted = true;
        this.selectedIslandIdx = null;
        this.render();
        this.saveState();
        this.onVictory(this.gameData);
      }
    } catch (e) {
      console.warn('Erreur vérification auto hashi:', e);
    }
  }

  async verifyGrid() {
    if (this.isCompleted) return;
    try {
      const islands = this.gameData.islands;
      const bridgeCounts = new Array(islands.length).fill(0);
      for (const [key, count] of this.bridges.entries()) {
        const [i, j] = this._parseBridgeKey(key);
        bridgeCounts[i] += count;
        bridgeCounts[j] += count;
      }

      // 1. Vérification des îles en surcapacité
      const overIslands = [];
      const incompleteIslands = [];
      let missingBridgesTotal = 0;

      islands.forEach(([r, c, targetVal], idx) => {
        if (bridgeCounts[idx] > targetVal) {
          overIslands.push(idx + 1);
        } else if (bridgeCounts[idx] < targetVal) {
          incompleteIslands.push(idx);
          missingBridgesTotal += (targetVal - bridgeCounts[idx]);
        }
      });

      if (overIslands.length > 0) {
        window.dispatchEvent(new CustomEvent('app:toast', {
          detail: { message: `⚠️ Trop de ponts sur l'île #${overIslands[0]} (retirez des ponts).` }
        }));
        return;
      }

      // 2. Appel de l'API pour validation complète
      const bridgesList = this.getBridgesList();
      const res = await verifyHashiBridges(this.gameData.id, bridgesList);

      if (res.is_complete) {
        this.isCompleted = true;
        this.saveState();
        this.onVictory(this.gameData);
        return;
      }

      // 3. Vérification de connexité (réseau isolé)
      if (incompleteIslands.length === 0) {
        // Tous les nombres sont atteints mais le graphe n'est pas connexe
        window.dispatchEvent(new CustomEvent('app:toast', {
          detail: { message: '⚠️ Toutes les valeurs sont atteintes mais les îles forment des groupes isolés. Reliez toutes les îles en un seul réseau !' }
        }));
        return;
      }

      // 4. Mise en valeur visuelle des îles incomplètes
      const islandEls = this.container.querySelectorAll('.hashi-island');
      incompleteIslands.forEach(idx => {
        if (islandEls[idx]) {
          islandEls[idx].classList.add('status-incomplete-highlight');
          setTimeout(() => islandEls[idx]?.classList.remove('status-incomplete-highlight'), 2200);
        }
      });

      const countIncomplete = incompleteIslands.length;
      window.dispatchEvent(new CustomEvent('app:toast', {
        detail: {
          message: `🔍 ${countIncomplete} île${countIncomplete > 1 ? 's' : ''} à compléter (${missingBridgesTotal / 2} ponts restants). Les ponts existants sont valides.`
        }
      }));

    } catch (e) {
      window.dispatchEvent(new CustomEvent('app:toast', { detail: { message: e.message } }));
    }
  }

  async giveHint() {
    if (this.isCompleted) return;
    try {
      const solData = await getHashiSolution(this.gameData.id);
      const solBridges = solData.solution_bridges; // [[i, j, count], ...]

      // Cherche un pont de la solution qui manque ou est erroné
      for (const [i, j, count] of solBridges) {
        const key = this._bridgeKey(i, j);
        const currentCount = this.bridges.get(key) || 0;
        if (currentCount !== count) {
          this.history.push({ key, prevCount: currentCount, nextCount: count });
          this.bridges.set(key, count);
          this.render();
          this.saveState();
          this.checkAutoCompletion();

          window.dispatchEvent(new CustomEvent('app:toast', {
            detail: { message: `💡 Indice : pont placé entre les îles #${i + 1} et #${j + 1} !` }
          }));
          return;
        }
      }
    } catch (e) {
      window.dispatchEvent(new CustomEvent('app:toast', { detail: { message: e.message } }));
    }
  }

  render() {
    this.container.innerHTML = '';
    const { num_rows, num_cols, islands } = this.gameData;

    const board = document.createElement('div');
    board.className = 'hashi-board';

    // Calcul du degré actuel de chaque île (nombre de ponts connectés)
    const bridgeCounts = new Array(islands.length).fill(0);
    for (const [key, count] of this.bridges.entries()) {
      const [i, j] = this._parseBridgeKey(key);
      bridgeCounts[i] += count;
      bridgeCounts[j] += count;
    }

    // 1. Calque SVG pour le quadrillage et les ponts
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('class', 'hashi-svg-layer');
    svg.setAttribute('viewBox', `0 0 ${num_cols * 100} ${num_rows * 100}`);

    // --- A. QUADRILLAGE D'ALIGNEMENT ---
    const gridGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    gridGroup.setAttribute('class', 'hashi-grid-background');

    // Lignes horizontales
    for (let r = 0; r < num_rows; r++) {
      const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
      line.setAttribute('x1', 25);
      line.setAttribute('y1', r * 100 + 50);
      line.setAttribute('x2', num_cols * 100 - 25);
      line.setAttribute('y2', r * 100 + 50);
      line.setAttribute('class', 'hashi-grid-line');
      gridGroup.appendChild(line);
    }

    // Lignes verticales
    for (let c = 0; c < num_cols; c++) {
      const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
      line.setAttribute('x1', c * 100 + 50);
      line.setAttribute('y1', 25);
      line.setAttribute('x2', c * 100 + 50);
      line.setAttribute('y2', num_rows * 100 - 25);
      line.setAttribute('class', 'hashi-grid-line');
      gridGroup.appendChild(line);
    }

    // Points d'intersection subtils
    for (let r = 0; r < num_rows; r++) {
      for (let c = 0; c < num_cols; c++) {
        const dot = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        dot.setAttribute('cx', c * 100 + 50);
        dot.setAttribute('cy', r * 100 + 50);
        dot.setAttribute('r', 2.5);
        dot.setAttribute('class', 'hashi-grid-dot');
        gridGroup.appendChild(dot);
      }
    }
    svg.appendChild(gridGroup);

    // --- B. PRÉVISUALISATION DES PONTS POTENTIELS ---
    const potentialPartners = this.selectedIslandIdx !== null
      ? this.getPotentialPartners(this.selectedIslandIdx).filter(p => this.canConnect(this.selectedIslandIdx, p))
      : [];

    if (this.selectedIslandIdx !== null) {
      const [sr, sc] = islands[this.selectedIslandIdx];
      const sx = sc * 100 + 50;
      const sy = sr * 100 + 50;

      potentialPartners.forEach(pIdx => {
        const [pr, pc] = islands[pIdx];
        const px = pc * 100 + 50;
        const py = pr * 100 + 50;

        const prevLine = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        prevLine.setAttribute('x1', sx);
        prevLine.setAttribute('y1', sy);
        prevLine.setAttribute('x2', px);
        prevLine.setAttribute('y2', py);
        prevLine.setAttribute('class', 'hashi-bridge-preview');
        svg.appendChild(prevLine);
      });
    }

    // --- C. RENDU DES PONTS PLACÉS ---
    for (const [key, count] of this.bridges.entries()) {
      if (count <= 0) continue;
      const [i, j] = this._parseBridgeKey(key);
      const [r1, c1] = islands[i];
      const [r2, c2] = islands[j];

      const x1 = c1 * 100 + 50;
      const y1 = r1 * 100 + 50;
      const x2 = c2 * 100 + 50;
      const y2 = r2 * 100 + 50;

      const group = document.createElementNS('http://www.w3.org/2000/svg', 'g');
      group.setAttribute('class', 'hashi-bridge-group');
      group.addEventListener('click', (e) => {
        e.stopPropagation();
        this.cycleBridge(i, j);
        this.render();
        this.checkAutoCompletion();
      });

      // Hitbox large pour faciliter le clic/tap mobile
      const hitbox = document.createElementNS('http://www.w3.org/2000/svg', 'line');
      hitbox.setAttribute('x1', x1);
      hitbox.setAttribute('y1', y1);
      hitbox.setAttribute('x2', x2);
      hitbox.setAttribute('y2', y2);
      hitbox.setAttribute('class', 'hashi-bridge-hitbox');
      group.appendChild(hitbox);

      if (count === 1) {
        const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        line.setAttribute('x1', x1);
        line.setAttribute('y1', y1);
        line.setAttribute('x2', x2);
        line.setAttribute('y2', y2);
        line.setAttribute('class', 'hashi-bridge-line');
        group.appendChild(line);
      } else if (count === 2) {
        const offset = 8;
        if (r1 === r2) {
          // Pont horizontal double
          const l1 = document.createElementNS('http://www.w3.org/2000/svg', 'line');
          l1.setAttribute('x1', x1);
          l1.setAttribute('y1', y1 - offset);
          l1.setAttribute('x2', x2);
          l1.setAttribute('y2', y2 - offset);
          l1.setAttribute('class', 'hashi-bridge-line');

          const l2 = document.createElementNS('http://www.w3.org/2000/svg', 'line');
          l2.setAttribute('x1', x1);
          l2.setAttribute('y1', y1 + offset);
          l2.setAttribute('x2', x2);
          l2.setAttribute('y2', y2 + offset);
          l2.setAttribute('class', 'hashi-bridge-line');

          group.appendChild(l1);
          group.appendChild(l2);
        } else {
          // Pont vertical double
          const l1 = document.createElementNS('http://www.w3.org/2000/svg', 'line');
          l1.setAttribute('x1', x1 - offset);
          l1.setAttribute('y1', y1);
          l1.setAttribute('x2', x2 - offset);
          l1.setAttribute('y2', y2);
          l1.setAttribute('class', 'hashi-bridge-line');

          const l2 = document.createElementNS('http://www.w3.org/2000/svg', 'line');
          l2.setAttribute('x1', x1 + offset);
          l2.setAttribute('y1', y1);
          l2.setAttribute('x2', x2 + offset);
          l2.setAttribute('y2', y2);
          l2.setAttribute('class', 'hashi-bridge-line');

          group.appendChild(l1);
          group.appendChild(l2);
        }
      }

      svg.appendChild(group);
    }

    board.appendChild(svg);

    // 2. Calque HTML des Îles (taille proportionnelle au quadrillage pour éviter tout chevauchement)
    const islandsLayer = document.createElement('div');
    islandsLayer.className = 'hashi-islands-layer';

    // Dimension d'île dynamique : 66% de la cellule max
    const maxGridDim = Math.max(num_rows, num_cols);
    const islandSizePct = (100 / maxGridDim) * 0.68;
    const fontSizeRem = Math.max(0.75, Math.min(1.2, 11 / maxGridDim));

    islands.forEach(([r, c, targetVal], idx) => {
      const island = document.createElement('div');
      island.className = 'hashi-island';
      island.dataset.idx = idx;

      // Taille proportionnelle au nombre de cases de la grille
      island.style.width = `min(${islandSizePct}%, 44px)`;
      island.style.height = `min(${islandSizePct}%, 44px)`;
      island.style.fontSize = `${fontSizeRem}rem`;

      // Positionnement précis au centre de la case
      const topPct = ((r + 0.5) / num_rows) * 100;
      const leftPct = ((c + 0.5) / num_cols) * 100;
      island.style.top = `${topPct}%`;
      island.style.left = `${leftPct}%`;

      const currentCount = bridgeCounts[idx];
      island.textContent = targetVal.toString();

      // Statut couleur
      if (currentCount === targetVal) {
        island.classList.add('status-exact');
      } else if (currentCount > targetVal) {
        island.classList.add('status-over');
      }

      // Sélection active & cibles potentielles
      if (idx === this.selectedIslandIdx) {
        island.classList.add('selected');
      } else if (potentialPartners.includes(idx)) {
        island.classList.add('target-candidate');
      }

      island.addEventListener('click', (e) => {
        e.stopPropagation();
        this.handleIslandTap(idx);
      });

      islandsLayer.appendChild(island);
    });

    board.appendChild(islandsLayer);
    this.container.appendChild(board);
  }

  saveState() {
    if (!this.gameData) return;
    const state = {
      type: 'hashi',
      id: this.gameData.id,
      gameData: this.gameData,
      bridges: this.getBridgesList(),
      isCompleted: this.isCompleted,
      updatedAt: Date.now(),
    };
    this.onStateChange(state);
  }
}
