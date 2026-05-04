export interface RateLimitOpts {
  intervalMs: number;
  now?: number;
}

export function tryAcquire(
  store: Map<string, number>,
  key: string,
  opts: RateLimitOpts,
): boolean {
  const now = opts.now ?? Date.now();
  const last = store.get(key);
  if (last !== undefined && now - last < opts.intervalMs) return false;
  store.set(key, now);
  return true;
}
