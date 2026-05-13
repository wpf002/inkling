export function ConfidenceBand({ value }: { value: number }) {
  const pct = Math.max(0, Math.min(1, value)) * 100;
  // The bar is "how clearly you went one way" — not a score, not a
  // grade. A short bar means you went both ways enough that there's
  // no clear pattern to talk about.
  const explainer =
    pct < 20
      ? "You went both ways. There isn't really a clear pattern here."
      : pct < 50
        ? "You went one way more than the other, but not by much."
        : pct < 80
          ? "You pretty clearly went one way."
          : "You went one way almost every time.";
  return (
    <div className="space-y-1.5">
      <div
        className="h-1 w-full rounded-full bg-white/10"
        title="How clearly you went one way during this round"
      >
        <div
          className="h-full rounded-full bg-accent"
          style={{ width: `${pct}%` }}
        />
      </div>
      <p className="text-[11px] text-muted">{explainer}</p>
    </div>
  );
}
