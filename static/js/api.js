/**
 * BrainTrain - Module Client API REST (Support 6 jeux)
 */

const API_BASE = '/api';

export async function fetchRandomGame({ type = null, difficulty = null, maxDuration = null } = {}) {
  const params = new URLSearchParams();
  if (type) params.append('type', type);
  if (difficulty) params.append('difficulty', difficulty);
  if (maxDuration) params.append('max_duration', maxDuration);

  const res = await fetch(`${API_BASE}/games/random?${params.toString()}`);
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.error || `Erreur serveur (${res.status})`);
  }
  return res.json();
}

export async function fetchGamesList({ type = null, difficulty = null, maxDuration = null } = {}) {
  const params = new URLSearchParams();
  if (type) params.append('type', type);
  if (difficulty) params.append('difficulty', difficulty);
  if (maxDuration) params.append('max_duration', maxDuration);

  const res = await fetch(`${API_BASE}/games?${params.toString()}`);
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.error || `Erreur serveur (${res.status})`);
  }
  return res.json();
}

// --- Sudoku ---
export async function verifySudokuGrid(id, gridString) {
  const res = await fetch(`${API_BASE}/games/sudoku/verify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id, grid: gridString }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.error || `Erreur de vérification Sudoku`);
  }
  return res.json();
}

export async function getSudokuSolution(id) {
  const res = await fetch(`${API_BASE}/games/sudoku/${id}/solution`);
  if (!res.ok) throw new Error('Impossible de récupérer la solution Sudoku');
  return res.json();
}

// --- Mastermind ---
export async function submitMastermindGuess(id, guessArray) {
  const res = await fetch(`${API_BASE}/games/mastermind/guess`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id, guess: guessArray }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.error || `Erreur de validation Mastermind`);
  }
  return res.json();
}

export async function revealMastermindSecret(id) {
  const res = await fetch(`${API_BASE}/games/mastermind/${id}/reveal`);
  if (!res.ok) throw new Error('Impossible de révéler le code Mastermind');
  return res.json();
}

// --- Nonogramme ---
export async function verifyNonogramGrid(id, gridString) {
  const res = await fetch(`${API_BASE}/games/nonogram/verify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id, grid: gridString }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.error || `Erreur de vérification Nonogramme`);
  }
  return res.json();
}

export async function getNonogramSolution(id) {
  const res = await fetch(`${API_BASE}/games/nonogram/${id}/solution`);
  if (!res.ok) throw new Error('Impossible de récupérer la solution Nonogramme');
  return res.json();
}

// --- Hashi (Ponts) ---
export async function verifyHashiBridges(id, bridgesList) {
  const res = await fetch(`${API_BASE}/games/hashi/verify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id, bridges: bridgesList }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.error || `Erreur de vérification Hashi`);
  }
  return res.json();
}

export async function getHashiSolution(id) {
  const res = await fetch(`${API_BASE}/games/hashi/${id}/solution`);
  if (!res.ok) throw new Error('Impossible de récupérer la solution Hashi');
  return res.json();
}

// --- Le Compte est bon ---
export async function verifyCompteEstBon(id, stepsList) {
  const res = await fetch(`${API_BASE}/games/compte_est_bon/verify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id, steps: stepsList }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.error || `Erreur de vérification Compte est bon`);
  }
  return res.json();
}

export async function getCompteEstBonSolution(id) {
  const res = await fetch(`${API_BASE}/games/compte_est_bon/${id}/solution`);
  if (!res.ok) throw new Error('Impossible de récupérer la solution du Compte est bon');
  return res.json();
}

// --- Cross Math ---
export async function verifyCrossMath(id, proposedGrid) {
  const res = await fetch(`${API_BASE}/games/cross_math/verify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id, grid: proposedGrid }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.error || `Erreur de vérification Cross Math`);
  }
  return res.json();
}

export async function getCrossMathSolution(id) {
  const res = await fetch(`${API_BASE}/games/cross_math/${id}/solution`);
  if (!res.ok) throw new Error('Impossible de récupérer la solution Cross Math');
  return res.json();
}
