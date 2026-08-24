/**
 * BrainTrain - Utilitaire de Chronomètre
 */

export function formatTime(totalSeconds) {
  const mins = Math.floor(totalSeconds / 60);
  const secs = totalSeconds % 60;
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

export class GameTimer {
  constructor({ onTick = () => {}, initialSeconds = 0 } = {}) {
    this.seconds = initialSeconds;
    this.onTick = onTick;
    this.intervalId = null;
    this.isRunning = false;
  }

  start() {
    if (this.isRunning) return;
    this.isRunning = true;
    this.onTick(this.seconds, this.getFormatted());
    this.intervalId = setInterval(() => {
      this.seconds += 1;
      this.onTick(this.seconds, this.getFormatted());
    }, 1000);
  }

  pause() {
    if (!this.isRunning) return;
    this.isRunning = false;
    clearInterval(this.intervalId);
    this.intervalId = null;
  }

  resume() {
    this.start();
  }

  reset(newSeconds = 0) {
    this.pause();
    this.seconds = newSeconds;
    this.onTick(this.seconds, this.getFormatted());
  }

  getSeconds() {
    return this.seconds;
  }

  getFormatted() {
    return formatTime(this.seconds);
  }
}
