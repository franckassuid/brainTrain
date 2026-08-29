/**
 * BrainTrain - Module Client API Hybride (En Ligne & 100% Hors-Ligne)
 * Charge automatiquement les 1 100 puzzles en local et fonctionne sans connexion.
 */

const API_BASE = '/api';

// Cache local des puzzles pour fonctionnement 100% hors-ligne
let offlinePuzzles = null;

async function loadOfflinePuzzles() {
  if (offlinePuzzles) return offlinePuzzles;
  try {
    const res = await fetch('./data/puzzles.json');
    if (res.ok) {
      offlinePuzzles = await res.json();
      return offlinePuzzles;
    }
  } catch (e) {
    console.warn('Chargement des puzzles hors-ligne depuis le cache...', e);
  }
  return null;
}

// Préchargement immédiat
loadOfflinePuzzles().catch(() => {});

// --- Moteur de requête local hors-ligne ---
async function getOfflineGamesList({ type = null, difficulty = null } = {}) {
  const data = await loadOfflinePuzzles();
  if (!data) return { games: [], total: 0 };

  let allGames = [];
  const typesToScan = type ? [type] : Object.keys(data);

  for (const t of typesToScan) {
    if (data[t]) {
      let list = data[t];
      if (difficulty) {
        list = list.filter(g => g.difficulty === difficulty);
      }
      allGames.push(...list);
    }
  }

  return { games: allGames, total: allGames.length };
}

async function getOfflineRandomGame({ type = null, difficulty = null } = {}) {
  const data = await loadOfflinePuzzles();
  if (!data) throw new Error('Données hors-ligne non disponibles');

  let availableTypes = type ? [type] : Object.keys(data);
  // Étape 1 : filtrer les types qui ont au moins 1 jeu correspondant
  const matchingTypes = availableTypes.filter(t => {
    if (!data[t]) return false;
    if (!difficulty) return data[t].length > 0;
    return data[t].some(g => g.difficulty === difficulty);
  });

  if (matchingTypes.length === 0) {
    throw new Error('Aucun jeu trouvé pour ces critères.');
  }

  // Tirage équiprobable du TYPE
  const chosenType = matchingTypes[Math.floor(Math.random() * matchingTypes.length)];
  let candidates = data[chosenType];
  if (difficulty) {
    candidates = candidates.filter(g => g.difficulty === difficulty);
  }

  // Étape 2 : tirage au sort dans le type choisi
  const chosenGame = candidates[Math.floor(Math.random() * candidates.length)];
  return JSON.parse(JSON.stringify(chosenGame));
}

async function findOfflinePuzzle(type, id) {
  const data = await loadOfflinePuzzles();
  if (!data || !data[type]) return null;
  const numId = parseInt(id, 10);
  return data[type].find(g => g.id === numId) || null;
}

// ============================================================================
// API Publique (Tentative réseau -> Bascule transparente hors-ligne)
// ============================================================================

export async function fetchRandomGame({ type = null, difficulty = null, maxDuration = null } = {}) {
  if (!navigator.onLine) {
    return getOfflineRandomGame({ type, difficulty });
  }

  try {
    const params = new URLSearchParams();
    if (type) params.append('type', type);
    if (difficulty) params.append('difficulty', difficulty);
    if (maxDuration) params.append('max_duration', maxDuration);

    const res = await fetch(`${API_BASE}/games/random?${params.toString()}`);
    if (!res.ok) throw new Error(`Status ${res.status}`);
    return await res.json();
  } catch (e) {
    console.info('Mode hors-ligne activé pour le tirage du jeu.');
    return getOfflineRandomGame({ type, difficulty });
  }
}

export async function fetchGamesList({ type = null, difficulty = null, maxDuration = null } = {}) {
  if (!navigator.onLine) {
    return getOfflineGamesList({ type, difficulty });
  }

  try {
    const params = new URLSearchParams();
    if (type) params.append('type', type);
    if (difficulty) params.append('difficulty', difficulty);
    if (maxDuration) params.append('max_duration', maxDuration);

    const res = await fetch(`${API_BASE}/games?${params.toString()}`);
    if (!res.ok) throw new Error(`Status ${res.status}`);
    return await res.json();
  } catch (e) {
    return getOfflineGamesList({ type, difficulty });
  }
}

// --- Sudoku ---
export async function verifySudokuGrid(id, gridString) {
  try {
    const res = await fetch(`${API_BASE}/games/sudoku/verify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id, grid: gridString }),
    });
    if (res.ok) return await res.json();
  } catch (e) {}

  // Fallback hors-ligne
  const p = await findOfflinePuzzle('sudoku', id);
  if (!p) throw new Error('Puzzle Sudoku introuvable hors-ligne');
  const isComplete = !gridString.includes('0');
  const isValid = isComplete && gridString === p.solution_grid;
  return {
    is_valid: isValid,
    is_complete: isComplete,
    errors: isValid ? [] : ['Grille incorrecte ou incomplète']
  };
}

export async function getSudokuSolution(id) {
  try {
    const res = await fetch(`${API_BASE}/games/sudoku/${id}/solution`);
    if (res.ok) return await res.json();
  } catch (e) {}

  const p = await findOfflinePuzzle('sudoku', id);
  if (!p) throw new Error('Solution Sudoku introuvable hors-ligne');
  return { id: p.id, solution_grid: p.solution_grid };
}

// --- Mastermind ---
export async function submitMastermindGuess(id, guessArray) {
  try {
    const res = await fetch(`${API_BASE}/games/mastermind/guess`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id, guess: guessArray }),
    });
    if (res.ok) return await res.json();
  } catch (e) {}

  // Fallback hors-ligne
  const p = await findOfflinePuzzle('mastermind', id);
  if (!p) throw new Error('Partie Mastermind introuvable hors-ligne');
  const secret = p.secret_code.split(',').map(n => parseInt(n.trim(), 10));

  let exact = 0;
  const secretRemaining = [];
  const guessRemaining = [];

  for (let i = 0; i < secret.length; i++) {
    if (guessArray[i] === secret[i]) {
      exact++;
    } else {
      secretRemaining.push(secret[i]);
      guessRemaining.push(guessArray[i]);
    }
  }

  let misplaced = 0;
  const secretCounts = {};
  for (const c of secretRemaining) {
    secretCounts[c] = (secretCounts[c] || 0) + 1;
  }
  for (const c of guessRemaining) {
    if (secretCounts[c] && secretCounts[c] > 0) {
      misplaced++;
      secretCounts[c]--;
    }
  }

  const won = exact === secret.length;
  return {
    exact,
    misplaced,
    won,
    secret_code: won ? p.secret_code : undefined
  };
}

export async function revealMastermindSecret(id) {
  try {
    const res = await fetch(`${API_BASE}/games/mastermind/${id}/reveal`);
    if (res.ok) return await res.json();
  } catch (e) {}

  const p = await findOfflinePuzzle('mastermind', id);
  if (!p) throw new Error('Code Mastermind introuvable hors-ligne');
  return { id: p.id, secret_code: p.secret_code };
}

// --- Nonogramme ---
export async function verifyNonogramGrid(id, gridString) {
  try {
    const res = await fetch(`${API_BASE}/games/nonogram/verify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id, grid: gridString }),
    });
    if (res.ok) return await res.json();
  } catch (e) {}

  const p = await findOfflinePuzzle('nonogram', id);
  if (!p) throw new Error('Nonogramme introuvable hors-ligne');
  const is_valid = gridString === p.solution_grid;
  return { is_valid, is_complete: is_valid, errors: is_valid ? [] : ['Grille incorrecte'] };
}

export async function getNonogramSolution(id) {
  try {
    const res = await fetch(`${API_BASE}/games/nonogram/${id}/solution`);
    if (res.ok) return await res.json();
  } catch (e) {}

  const p = await findOfflinePuzzle('nonogram', id);
  if (!p) throw new Error('Solution Nonogramme introuvable hors-ligne');
  return { id: p.id, solution_grid: p.solution_grid };
}

// --- Hashi (Ponts) ---
export async function verifyHashiBridges(id, bridgesList) {
  try {
    const res = await fetch(`${API_BASE}/games/hashi/verify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id, bridges: bridgesList }),
    });
    if (res.ok) return await res.json();
  } catch (e) {}

  const p = await findOfflinePuzzle('hashi', id);
  if (!p) throw new Error('Hashi introuvable hors-ligne');
  // Comparaison canonique des arêtes
  const normSol = (p.solution_bridges || []).map(b => b.join(',')).sort().join('|');
  const normProp = (bridgesList || []).map(b => b.join(',')).sort().join('|');
  const is_valid = normSol === normProp;
  return { is_valid, is_complete: is_valid, errors: is_valid ? [] : ['Ponts incomplets ou incorrects'] };
}

export async function getHashiSolution(id) {
  try {
    const res = await fetch(`${API_BASE}/games/hashi/${id}/solution`);
    if (res.ok) return await res.json();
  } catch (e) {}

  const p = await findOfflinePuzzle('hashi', id);
  if (!p) throw new Error('Solution Hashi introuvable hors-ligne');
  return { id: p.id, solution_bridges: p.solution_bridges };
}

// --- Le Compte est bon ---
export async function verifyCompteEstBon(id, stepsList) {
  try {
    const res = await fetch(`${API_BASE}/games/compte_est_bon/verify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id, steps: stepsList }),
    });
    if (res.ok) return await res.json();
  } catch (e) {}

  const p = await findOfflinePuzzle('compte_est_bon', id);
  if (!p) throw new Error('Compte est bon introuvable hors-ligne');
  if (!stepsList || stepsList.length === 0) {
    return { is_valid: false, is_complete: false, current_value: null, target: p.target_number };
  }
  const lastStep = stepsList[stepsList.length - 1];
  const lastVal = lastStep[3];
  const is_complete = lastVal === p.target_number;
  return { is_valid: true, is_complete, current_value: lastVal, target: p.target_number };
}

export async function getCompteEstBonSolution(id) {
  try {
    const res = await fetch(`${API_BASE}/games/compte_est_bon/${id}/solution`);
    if (res.ok) return await res.json();
  } catch (e) {}

  const p = await findOfflinePuzzle('compte_est_bon', id);
  if (!p) throw new Error('Solution Compte est bon introuvable hors-ligne');
  return { id: p.id, target: p.target_number, solution_steps: p.solution_steps };
}

// --- Cross Math ---
export async function verifyCrossMath(id, proposedGrid) {
  try {
    const res = await fetch(`${API_BASE}/games/cross_math/verify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id, grid: proposedGrid }),
    });
    if (res.ok) return await res.json();
  } catch (e) {}

  const p = await findOfflinePuzzle('cross_math', id);
  if (!p) throw new Error('Cross Math introuvable hors-ligne');

  const k = p.grid_size;
  const isFull = proposedGrid.every(r => r.every(v => v !== null && v !== undefined));
  let is_complete = isFull;
  const errors = [];

  function evalChain(nums, ops) {
    if (nums.some(n => n === null || n === undefined)) return null;
    let res = nums[0];
    for (let i = 0; i < ops.length; i++) {
      const op = ops[i];
      const next = nums[i + 1];
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

  for (let r = 0; r < k; r++) {
    const actual = evalChain(proposedGrid[r], p.row_operators[r]);
    if (actual !== null && actual !== p.row_results[r]) {
      errors.push(`Ligne ${r + 1} : résultat incorrect (${actual} ≠ ${p.row_results[r]})`);
      is_complete = false;
    }
  }

  for (let c = 0; c < k; c++) {
    const colNums = proposedGrid.map(row => row[c]);
    const actual = evalChain(colNums, p.col_operators[c]);
    if (actual !== null && actual !== p.col_results[c]) {
      errors.push(`Colonne ${c + 1} : résultat incorrect (${actual} ≠ ${p.col_results[c]})`);
      is_complete = false;
    }
  }

  return { is_valid: errors.length === 0, is_complete, errors };
}

export async function getCrossMathSolution(id) {
  try {
    const res = await fetch(`${API_BASE}/games/cross_math/${id}/solution`);
    if (res.ok) return await res.json();
  } catch (e) {}

  const p = await findOfflinePuzzle('cross_math', id);
  if (!p) throw new Error('Solution Cross Math introuvable hors-ligne');
  return { id: p.id, solution_grid: p.solution_grid };
}
