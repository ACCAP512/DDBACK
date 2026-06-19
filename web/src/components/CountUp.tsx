import { useEffect, useRef, useState } from "react";

interface Props {
  value: number;
  /** duration in ms */
  duration?: number;
}

/**
 * Count-up animation for the hero number. Renders whole dollars in a large
 * monospace face with a dimmed ".cc" cents suffix. Respects reduced-motion.
 */
export default function CountUp({ value, duration = 1100 }: Props) {
  const [n, setN] = useState(0);
  const raf = useRef<number | null>(null);

  useEffect(() => {
    const reduce =
      typeof window !== "undefined" &&
      window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    if (reduce) {
      setN(value);
      return;
    }
    const start = performance.now();
    const from = 0;
    const tick = (t: number) => {
      const p = Math.min(1, (t - start) / duration);
      // easeOutExpo for a satisfying decel
      const e = p === 1 ? 1 : 1 - Math.pow(2, -10 * p);
      setN(from + (value - from) * e);
      if (p < 1) raf.current = requestAnimationFrame(tick);
    };
    raf.current = requestAnimationFrame(tick);
    return () => {
      if (raf.current) cancelAnimationFrame(raf.current);
    };
  }, [value, duration]);

  const whole = Math.floor(n);
  const cents = Math.round((n - whole) * 100)
    .toString()
    .padStart(2, "0");
  const dollars = whole.toLocaleString("en-US");

  return (
    <span className="big">
      ${dollars}
      <span className="cents">.{cents}</span>
    </span>
  );
}
