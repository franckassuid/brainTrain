/**
 * BrainTrain - Application Principale & Routeur SPA (6 Jeux)
 */

import { fetchRandomGame, fetchGamesList } from './api.js';
import { GameTimer, formatTime } from './timer.js';
import { SudokuGame } from './sudoku.js';
import { MastermindGame, COLOR_NAMES } from './mastermind.js';
import { NonogramGame } from './nonogram.js';
import { HashiGame } from './hashi.js';
import { CompteEstBonGame } from './compte_est_bon.js';
import { CrossMathGame } from './cross_math.js';

const STORAGE_KEY_SESSION = 'braintrain_active_session';
const STORAGE_KEY_STATS = 'braintrain_stats';

const GAME_NAMES = {
  sudoku: 'Sudoku',
  mastermind: 'Mastermind',
  nonogram: 'Nonogramme',
  hashi: 'Hashi (Ponts)',
  compte_est_bon: 'Le Compte est bon',
  cross_math: 'Cross Math',
};

class BrainTrainApp {
  constructor() {
    this.currentFilter = {
      type: null,
      maxDuration: null,
      difficulty: null,
    };

    this.activeSession = null;
    this.timer = null;
    this.sudokuEngine = null;
    this.mastermindEngine = null;
    this.nonogramEngine = null;
    this.hashiEngine = null;
    this.compteEstBonEngine = null;
    this.crossMathEngine = null;

    this.initElements();
    this.initEngines();
    this.bindEvents();
    this.checkSavedSession();
    this.updateMatchCount();
  }

  initElements() {
    // Vues
    this.viewHome = document.getElementById('view-home');
    this.viewSudoku = document.getElementById('view-sudoku');
    this.viewMastermind = document.getElementById('view-mastermind');
    this.viewNonogram = document.getElementById('view-nonogram');
    this.viewHashi = document.getElementById('view-hashi');
    this.viewCompteEstBon = document.getElementById('view-compte-est-bon');
    this.viewCrossMath = document.getElementById('view-cross-math');

    // Éléments Accueil
    this.resumeBanner = document.getElementById('resume-banner');
    this.resumeDesc = document.getElementById('resume-desc');
    this.btnResume = document.getElementById('btn-resume-session');
    this.btnDiscardResume = document.getElementById('btn-discard-session');
    this.btnLaunch = document.getElementById('btn-launch-game');
    this.matchCountSpan = document.getElementById('match-count');

    // Éléments Modals & Toasts
    this.modalOverlay = document.getElementById('modal-overlay');
    this.modalTitle = document.getElementById('modal-title');
    this.modalBody = document.getElementById('modal-body');
    this.modalIcon = document.getElementById('modal-icon');
    this.modalStats = document.getElementById('modal-stats');
    this.btnModalPrimary = document.getElementById('btn-modal-primary');
    this.btnModalSecondary = document.getElementById('btn-modal-secondary');
    this.toastContainer = document.getElementById('toast-container');
  }

  initEngines() {
    // Chronomètre global
    this.timer = new GameTimer({
      onTick: (secs, formatted) => {
        ['sudoku', 'mastermind', 'nonogram', 'hashi', 'ceb', 'cm'].forEach(t => {
          const el = document.getElementById(`${t}-timer-text`);
          if (el) el.textContent = formatted;
        });

        if (this.activeSession) {
          this.activeSession.timerSeconds = secs;
          this.saveSession();
        }
      },
    });

    // 1. Moteur Sudoku
    this.sudokuEngine = new SudokuGame({
      containerEl: document.getElementById('sudoku-board-container'),
      onStateChange: (gameState) => {
        if (this.activeSession && this.activeSession.type === 'sudoku') {
          this.activeSession.gameState = gameState;
          this.saveSession();
        }
      },
      onVictory: (gameData) => this.handleVictory('sudoku', gameData, '🎉 Grille de Sudoku résolue avec succès !'),
    });

    // 2. Moteur Mastermind
    this.mastermindEngine = new MastermindGame({
      boardContainerEl: document.getElementById('mastermind-history-container'),
      activeGuessContainerEl: document.getElementById('mastermind-active-container'),
      colorPickerContainerEl: document.getElementById('mastermind-picker-container'),
      onStateChange: (gameState) => {
        if (this.activeSession && this.activeSession.type === 'mastermind') {
          this.activeSession.gameState = gameState;
          this.saveSession();
        }
      },
      onGameOver: ({ won, attemptsUsed, maxAttempts, secretCode }) => {
        this.timer.pause();
        const durationSecs = this.timer.getSeconds();
        if (won) {
          this.recordCompletion('mastermind', this.activeSession.gameData.difficulty, durationSecs);
        }
        this.clearSession();

        const codeFormatted = secretCode.map(c => COLOR_NAMES[c] || c).join(' - ');

        this.showModal({
          icon: won ? '🏆' : '💡',
          title: won ? 'Code Secret Déchiffré !' : 'Partie Terminée',
          body: won
            ? `Excellent esprit de déduction ! Vous avez trouvé la combinaison secrète.`
            : `Le code secret était : <strong>${codeFormatted}</strong>. Entraînez-vous encore !`,
          stats: [
            { label: 'Essais', value: `${attemptsUsed} / ${maxAttempts}` },
            { label: 'Temps', value: formatTime(durationSecs) },
          ],
          primaryAction: {
            text: 'Rejouer une partie',
            onClick: () => {
              this.hideModal();
              this.launchGame({ type: 'mastermind' });
            },
          },
          secondaryAction: {
            text: "Retour à l'accueil",
            onClick: () => {
              this.hideModal();
              this.showView('home');
            },
          },
        });
      },
    });

    // 3. Moteur Nonogramme
    this.nonogramEngine = new NonogramGame({
      containerEl: document.getElementById('nonogram-board-container'),
      onStateChange: (gameState) => {
        if (this.activeSession && this.activeSession.type === 'nonogram') {
          this.activeSession.gameState = gameState;
          this.saveSession();
        }
      },
      onVictory: (gameData) => this.handleVictory('nonogram', gameData, '🖼️ Superbe ! Vous avez reconstitué le dessin du Nonogramme !'),
    });

    // 4. Moteur Hashi
    this.hashiEngine = new HashiGame({
      containerEl: document.getElementById('hashi-board-container'),
      onStateChange: (gameState) => {
        if (this.activeSession && this.activeSession.type === 'hashi') {
          this.activeSession.gameState = gameState;
          this.saveSession();
        }
      },
      onVictory: (gameData) => this.handleVictory('hashi', gameData, '🌉 Parfait ! Toutes les îles sont reliées selon les règles !'),
    });

    // 5. Moteur Le Compte est bon
    this.compteEstBonEngine = new CompteEstBonGame({
      targetEl: document.getElementById('ceb-target-display'),
      builderEl: document.getElementById('ceb-builder-slots'),
      tilesEl: document.getElementById('ceb-numbers-pool'),
      operatorsEl: document.getElementById('ceb-operators-bar'),
      historyEl: document.getElementById('ceb-history-list'),
      onStateChange: (gameState) => {
        if (this.activeSession && this.activeSession.type === 'compte_est_bon') {
          this.activeSession.gameState = gameState;
          this.saveSession();
        }
      },
      onVictory: (gameData) => this.handleVictory('compte_est_bon', gameData, '🎯 Le compte est bon ! Vous avez exactement atteint le nombre cible !'),
    });

    // 6. Moteur Cross Math
    this.crossMathEngine = new CrossMathGame({
      boardContainerEl: document.getElementById('cm-board-container'),
      bankContainerEl: document.getElementById('cm-bank-container'),
      onStateChange: (gameState) => {
        if (this.activeSession && this.activeSession.type === 'cross_math') {
          this.activeSession.gameState = gameState;
          this.saveSession();
        }
      },
      onVictory: (gameData) => this.handleVictory('cross_math', gameData, '➕ Bravo ! Toutes les équations horizontales et verticales sont résolues !'),
    });
  }

  handleVictory(gameType, gameData, customMessage) {
    this.timer.pause();
    const durationSecs = this.timer.getSeconds();
    this.recordCompletion(gameType, gameData.difficulty, durationSecs);
    this.clearSession();

    this.showModal({
      icon: '🎉',
      title: `${GAME_NAMES[gameType]} Gagné !`,
      body: customMessage,
      stats: [
        { label: 'Temps', value: formatTime(durationSecs) },
        { label: 'Difficulté', value: gameData.difficulty },
      ],
      primaryAction: {
        text: 'Rejouer une partie',
        onClick: () => {
          this.hideModal();
          this.launchGame({ type: gameType, difficulty: gameData.difficulty });
        },
      },
      secondaryAction: {
        text: "Retour à l'accueil",
        onClick: () => {
          this.hideModal();
          this.showView('home');
        },
      },
    });
  }

  bindEvents() {
    // Sélecteur de Jeu
    document.querySelectorAll('.game-option').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.game-option').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const val = btn.dataset.game;
        this.currentFilter.type = val === 'all' ? null : val;
        this.updateMatchCount();
      });
    });

    // Sélecteur de Temps
    document.querySelectorAll('#pill-duration .pill-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('#pill-duration .pill-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const val = btn.dataset.duration;
        this.currentFilter.maxDuration = val === 'all' ? null : parseInt(val, 10);
        this.updateMatchCount();
      });
    });

    // Sélecteur de Difficulté
    document.querySelectorAll('#pill-difficulty .pill-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('#pill-difficulty .pill-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const val = btn.dataset.difficulty;
        this.currentFilter.difficulty = val === 'all' ? null : val;
        this.updateMatchCount();
      });
    });

    // Bouton Lancer
    this.btnLaunch.addEventListener('click', () => this.launchGame());

    // Reprendre / Abandonner
    this.btnResume?.addEventListener('click', () => this.resumeActiveSession());
    this.btnDiscardResume?.addEventListener('click', () => {
      this.clearSession();
      this.checkSavedSession();
      this.showToast('Partie abandonnée.');
    });

    // Boutons Retour Accueil
    document.getElementById('btn-sudoku-back')?.addEventListener('click', () => this.confirmExitGame());
    document.getElementById('btn-mastermind-back')?.addEventListener('click', () => this.confirmExitGame());
    document.getElementById('btn-nonogram-back')?.addEventListener('click', () => this.confirmExitGame());
    document.getElementById('btn-hashi-back')?.addEventListener('click', () => this.confirmExitGame());
    document.getElementById('btn-ceb-back')?.addEventListener('click', () => this.confirmExitGame());
    document.getElementById('btn-cm-back')?.addEventListener('click', () => this.confirmExitGame());

    // Contrôles Sudoku
    document.getElementById('btn-sudoku-notes')?.addEventListener('click', () => this.sudokuEngine.toggleNotesMode());
    document.getElementById('btn-sudoku-undo')?.addEventListener('click', () => this.sudokuEngine.undo());
    document.getElementById('btn-sudoku-clear')?.addEventListener('click', () => this.sudokuEngine.clearSelectedCell());
    document.getElementById('btn-sudoku-check')?.addEventListener('click', () => this.sudokuEngine.verifyGrid());
    document.getElementById('btn-sudoku-hint')?.addEventListener('click', () => this.sudokuEngine.giveHint());
    document.querySelectorAll('.keypad-btn').forEach(btn => {
      btn.addEventListener('click', () => this.sudokuEngine.handleDigit(parseInt(btn.dataset.digit, 10)));
    });

    // Contrôles Nonogramme
    document.querySelectorAll('.nono-mode-btn').forEach(btn => {
      btn.addEventListener('click', () => this.nonogramEngine.setMode(btn.dataset.mode));
    });
    document.getElementById('btn-nono-undo')?.addEventListener('click', () => this.nonogramEngine.undo());
    document.getElementById('btn-nono-clear')?.addEventListener('click', () => this.nonogramEngine.clearGrid());
    document.getElementById('btn-nono-check')?.addEventListener('click', () => this.nonogramEngine.verifyGrid());
    document.getElementById('btn-nono-hint')?.addEventListener('click', () => this.nonogramEngine.giveHint());

    // Contrôles Hashi
    document.getElementById('btn-hashi-undo')?.addEventListener('click', () => this.hashiEngine.undo());
    document.getElementById('btn-hashi-clear')?.addEventListener('click', () => this.hashiEngine.clearBridges());
    document.getElementById('btn-hashi-check')?.addEventListener('click', () => this.hashiEngine.verifyGrid());
    document.getElementById('btn-hashi-hint')?.addEventListener('click', () => this.hashiEngine.giveHint());

    // Contrôles Le Compte est bon
    document.querySelectorAll('.ceb-op-btn').forEach(btn => {
      btn.addEventListener('click', () => this.compteEstBonEngine.handleOpTap(btn.dataset.op));
    });
    document.getElementById('btn-ceb-undo')?.addEventListener('click', () => this.compteEstBonEngine.undo());
    document.getElementById('btn-ceb-clear')?.addEventListener('click', () => this.compteEstBonEngine.clear());
    document.getElementById('btn-ceb-hint')?.addEventListener('click', () => this.compteEstBonEngine.giveHint());
    document.getElementById('btn-ceb-solution')?.addEventListener('click', () => this.compteEstBonEngine.showSolutionModal());

    // Contrôles Cross Math
    document.getElementById('btn-cm-sort')?.addEventListener('click', () => this.crossMathEngine.toggleSortMode());
    document.getElementById('btn-cm-undo')?.addEventListener('click', () => this.crossMathEngine.undo());
    document.getElementById('btn-cm-clear')?.addEventListener('click', () => this.crossMathEngine.clear());
    document.getElementById('btn-cm-hint')?.addEventListener('click', () => this.crossMathEngine.giveHint());
    document.getElementById('btn-cm-check')?.addEventListener('click', () => this.crossMathEngine.verifyGrid());

    // Toast listener
    window.addEventListener('app:toast', (e) => this.showToast(e.detail.message));

    // Custom Modal listener
    window.addEventListener('app:modal', (e) => this.showModal(e.detail));
  }

  showView(viewName) {
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    if (viewName === 'home') {
      this.viewHome.classList.add('active');
      this.timer.pause();
      this.checkSavedSession();
      this.updateMatchCount();
    } else if (viewName === 'sudoku') {
      this.viewSudoku.classList.add('active');
    } else if (viewName === 'mastermind') {
      this.viewMastermind.classList.add('active');
    } else if (viewName === 'nonogram') {
      this.viewNonogram.classList.add('active');
    } else if (viewName === 'hashi') {
      this.viewHashi.classList.add('active');
    } else if (viewName === 'compte_est_bon') {
      this.viewCompteEstBon.classList.add('active');
    } else if (viewName === 'cross_math') {
      this.viewCrossMath.classList.add('active');
    }
  }

  async updateMatchCount() {
    try {
      const res = await fetchGamesList(this.currentFilter);
      const total = res.total || 0;
      this.matchCountSpan.textContent = `${total} partie${total > 1 ? 's' : ''} disponible${total > 1 ? 's' : ''}`;
      this.btnLaunch.disabled = total === 0;
    } catch (e) {
      console.warn('Erreur décompte:', e);
    }
  }

  async launchGame(customFilter = null) {
    const filter = customFilter || this.currentFilter;
    this.btnLaunch.disabled = true;
    this.btnLaunch.textContent = 'Chargement...';

    try {
      const gameData = await fetchRandomGame(filter);

      this.activeSession = {
        type: gameData.type,
        id: gameData.id,
        gameData,
        timerSeconds: 0,
        gameState: null,
      };

      this.saveSession();

      if (gameData.type === 'sudoku') {
        this.setupGameHeader('sudoku', gameData, `${gameData.clue_count} indices • ~${gameData.estimated_duration_minutes} min`);
        this.sudokuEngine.loadGame(gameData);
        this.showView('sudoku');
      } else if (gameData.type === 'mastermind') {
        this.setupGameHeader('mastermind', gameData, `${gameData.num_positions} positions • ${gameData.num_colors} couleurs`);
        this.mastermindEngine.loadGame(gameData);
        this.showView('mastermind');
      } else if (gameData.type === 'nonogram') {
        this.setupGameHeader('nonogram', gameData, `Grille ${gameData.num_rows}×${gameData.num_cols} • ~${gameData.estimated_duration_minutes} min`);
        this.nonogramEngine.loadGame(gameData);
        this.showView('nonogram');
      } else if (gameData.type === 'hashi') {
        this.setupGameHeader('hashi', gameData, `${gameData.islands.length} îles • Grille ${gameData.num_rows}×${gameData.num_cols}`);
        this.hashiEngine.loadGame(gameData);
        this.showView('hashi');
      } else if (gameData.type === 'compte_est_bon') {
        this.setupGameHeader('ceb', gameData, `${gameData.available_numbers.length} nombres • Cible ${gameData.target}`);
        this.compteEstBonEngine.loadGame(gameData);
        this.showView('compte_est_bon');
      } else if (gameData.type === 'cross_math') {
        this.setupGameHeader('cm', gameData, `Grille ${gameData.grid_size}×${gameData.grid_size} • ~${gameData.estimated_duration_minutes} min`);
        this.crossMathEngine.loadGame(gameData);
        this.showView('cross_math');
      }

      this.timer.reset(0);
      this.timer.start();
    } catch (e) {
      this.showToast(`Impossible de lancer le jeu : ${e.message}`);
    } finally {
      this.btnLaunch.disabled = false;
      this.btnLaunch.innerHTML = '<span>🚀</span> Lancer une partie';
    }
  }

  setupGameHeader(type, gameData, infoText) {
    const diffBadge = document.getElementById(`${type}-difficulty-badge`);
    if (diffBadge) {
      diffBadge.textContent = gameData.difficulty;
      diffBadge.className = `badge-difficulty badge-${gameData.difficulty}`;
    }
    const infoEl = document.getElementById(`${type}-info-text`);
    if (infoEl) {
      infoEl.textContent = infoText;
    }
  }

  checkSavedSession() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY_SESSION);
      if (raw) {
        this.activeSession = JSON.parse(raw);
        const g = this.activeSession.gameData;
        const name = GAME_NAMES[g.type] || g.type;
        this.resumeDesc.textContent = `${name} (${g.difficulty}) • ${formatTime(this.activeSession.timerSeconds || 0)}`;
        this.resumeBanner.style.display = 'flex';
      } else {
        this.activeSession = null;
        this.resumeBanner.style.display = 'none';
      }
    } catch (e) {
      this.activeSession = null;
      this.resumeBanner.style.display = 'none';
    }
  }

  resumeActiveSession() {
    if (!this.activeSession) return;
    const { type, gameData, timerSeconds, gameState } = this.activeSession;

    if (type === 'sudoku') {
      this.setupGameHeader('sudoku', gameData, `${gameData.clue_count} indices`);
      this.sudokuEngine.loadGame(gameData, gameState);
      this.showView('sudoku');
    } else if (type === 'mastermind') {
      this.setupGameHeader('mastermind', gameData, `${gameData.num_positions} positions`);
      this.mastermindEngine.loadGame(gameData, gameState);
      this.showView('mastermind');
    } else if (type === 'nonogram') {
      this.setupGameHeader('nonogram', gameData, `Grille ${gameData.num_rows}×${gameData.num_cols}`);
      this.nonogramEngine.loadGame(gameData, gameState);
      this.showView('nonogram');
    } else if (type === 'hashi') {
      this.setupGameHeader('hashi', gameData, `${gameData.islands.length} îles`);
      this.hashiEngine.loadGame(gameData, gameState);
      this.showView('hashi');
    } else if (type === 'compte_est_bon') {
      this.setupGameHeader('ceb', gameData, `${gameData.available_numbers.length} nombres`);
      this.compteEstBonEngine.loadGame(gameData, gameState);
      this.showView('compte_est_bon');
    } else if (type === 'cross_math') {
      this.setupGameHeader('cm', gameData, `Grille ${gameData.grid_size}×${gameData.grid_size}`);
      this.crossMathEngine.loadGame(gameData, gameState);
      this.showView('cross_math');
    }

    this.timer.reset(timerSeconds || 0);
    this.timer.start();
  }

  confirmExitGame() {
    this.timer.pause();
    this.showModal({
      icon: '⏸️',
      title: 'Partie en pause',
      body: 'Votre progression est sauvegardée localement. Vous pourrez la reprendre à tout moment.',
      primaryAction: {
        text: 'Reprendre la partie',
        onClick: () => {
          this.hideModal();
          this.timer.resume();
        },
      },
      secondaryAction: {
        text: "Quitter vers l'accueil",
        onClick: () => {
          this.hideModal();
          this.showView('home');
        },
      },
    });
  }

  saveSession() {
    if (!this.activeSession) return;
    try {
      localStorage.setItem(STORAGE_KEY_SESSION, JSON.stringify(this.activeSession));
    } catch (e) {
      console.warn('Erreur localStorage save:', e);
    }
  }

  clearSession() {
    this.activeSession = null;
    try {
      localStorage.removeItem(STORAGE_KEY_SESSION);
    } catch (e) {}
  }

  recordCompletion(gameType, difficulty, durationSecs) {
    try {
      const raw = localStorage.getItem(STORAGE_KEY_STATS) || '[]';
      const stats = JSON.parse(raw);
      stats.push({
        gameType,
        difficulty,
        durationSecs,
        date: new Date().toISOString(),
      });
      localStorage.setItem(STORAGE_KEY_STATS, JSON.stringify(stats));
    } catch (e) {}
  }

  showModal({ icon, title, body, stats = [], primaryAction, secondaryAction }) {
    this.modalIcon.textContent = icon;
    this.modalTitle.textContent = title;
    this.modalBody.innerHTML = body;

    this.modalStats.innerHTML = '';
    if (stats.length > 0) {
      this.modalStats.style.display = 'flex';
      stats.forEach(s => {
        const item = document.createElement('div');
        item.className = 'stat-item';
        item.innerHTML = `<span class="stat-label">${s.label}</span><span class="stat-value">${s.value}</span>`;
        this.modalStats.appendChild(item);
      });
    } else {
      this.modalStats.style.display = 'none';
    }

    if (primaryAction) {
      this.btnModalPrimary.style.display = 'block';
      this.btnModalPrimary.textContent = primaryAction.text;
      this.btnModalPrimary.onclick = primaryAction.onClick;
    } else {
      this.btnModalPrimary.style.display = 'none';
    }

    if (secondaryAction) {
      this.btnModalSecondary.style.display = 'block';
      this.btnModalSecondary.textContent = secondaryAction.text;
      this.btnModalSecondary.onclick = secondaryAction.onClick;
    } else {
      this.btnModalSecondary.style.display = 'none';
    }

    this.modalOverlay.classList.add('active');
  }

  hideModal() {
    this.modalOverlay.classList.remove('active');
  }

  showToast(message) {
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;
    this.toastContainer.appendChild(toast);
    setTimeout(() => {
      toast.remove();
    }, 2800);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  window.app = new BrainTrainApp();
});
