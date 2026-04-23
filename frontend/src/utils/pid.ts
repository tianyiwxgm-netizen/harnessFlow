export const PID_STORAGE_KEY = 'harnessflow.active_pid';

export function getActivePid(): string | null {
  return localStorage.getItem(PID_STORAGE_KEY);
}

export function setActivePid(pid: string): void {
  if (!pid) {
    throw new Error('pid must be non-empty');
  }
  localStorage.setItem(PID_STORAGE_KEY, pid);
}

export function clearActivePid(): void {
  localStorage.removeItem(PID_STORAGE_KEY);
}
