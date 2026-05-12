"use client";

import { useEffect, useRef, useState } from "react";

type Props = {
  durationMs: number;
  onExpire: () => void;
  paused?: boolean;
  size?: number;
  strokeWidth?: number;
};

const RADIUS = 36;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;
const TICK_MS = 50;

/**
 * Round-agnostic countdown ring. Calls onExpire exactly once when the
 * elapsed time reaches durationMs.
 */
export function CountdownRing({
  durationMs,
  onExpire,
  paused = false,
  size = 96,
  strokeWidth = 6,
}: Props) {
  const [elapsed, setElapsed] = useState(0);
  const startedAtRef = useRef<number | null>(null);
  const expiredRef = useRef(false);
  const onExpireRef = useRef(onExpire);

  useEffect(() => {
    onExpireRef.current = onExpire;
  }, [onExpire]);

  useEffect(() => {
    expiredRef.current = false;
    setElapsed(0);
    startedAtRef.current = performance.now();
  }, [durationMs]);

  useEffect(() => {
    if (paused) return;
    let raf = 0;
    const tick = () => {
      const start = startedAtRef.current ?? performance.now();
      const e = performance.now() - start;
      setElapsed(Math.min(e, durationMs));
      if (e >= durationMs) {
        if (!expiredRef.current) {
          expiredRef.current = true;
          onExpireRef.current();
        }
        return;
      }
      raf = window.setTimeout(tick, TICK_MS) as unknown as number;
    };
    tick();
    return () => {
      window.clearTimeout(raf);
    };
  }, [durationMs, paused]);

  const remaining = Math.max(0, durationMs - elapsed);
  const fraction = Math.min(1, elapsed / durationMs);
  const offset = CIRCUMFERENCE * fraction;

  return (
    <svg
      role="timer"
      aria-label={`${Math.ceil(remaining / 100) / 10} seconds`}
      width={size}
      height={size}
      viewBox="0 0 80 80"
      className="-rotate-90"
    >
      <circle
        cx="40"
        cy="40"
        r={RADIUS}
        fill="transparent"
        stroke="rgba(255,255,255,0.08)"
        strokeWidth={strokeWidth}
      />
      <circle
        cx="40"
        cy="40"
        r={RADIUS}
        fill="transparent"
        stroke="var(--color-accent)"
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeDasharray={CIRCUMFERENCE}
        strokeDashoffset={offset}
        style={{ transition: `stroke-dashoffset ${TICK_MS}ms linear` }}
      />
    </svg>
  );
}
