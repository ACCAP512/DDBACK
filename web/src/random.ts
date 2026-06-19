// Deterministic PRNG for the uncertainty explorer's Monte Carlo. A FIXED seed
// makes the quantile dotplot stable across renders (research §2.3 asks for a
// deterministic picture — never Math.random for the trials).

/** mulberry32 — tiny, fast, deterministic 32-bit PRNG. Returns [0, 1). */
export function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return function () {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
