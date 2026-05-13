"use client";

import html2canvas from "html2canvas";
import { forwardRef, useMemo, useRef, useState } from "react";
import { LevelShell } from "@/components/reveal/LevelShell";
import { api } from "@/lib/api";
import { InferenceData } from "@/lib/schemas";
import { CONSTRUCT_LABEL, formatValue } from "../lib/formatInference";

type Format = "vertical" | "horizontal";
const DIMENSIONS: Record<Format, { w: number; h: number; label: string }> = {
  vertical: { w: 1080, h: 1920, label: "1080 × 1920" },
  horizontal: { w: 1200, h: 630, label: "1200 × 630" },
};

const TRAIT_FULL: Record<string, string> = {
  O: "Openness",
  C: "Conscientiousness",
  E: "Extraversion",
  A: "Agreeableness",
  N: "Neuroticism",
};

type Choice = {
  id: string;
  construct: string; // "Loss aversion" or "Big Five — Openness"
  punch: string; // "A $10 loss barely registers"
  inferenceId: number | null;
};

function buildChoices(
  inferences: InferenceData[],
  overreach: InferenceData | null,
): Choice[] {
  const out: Choice[] = [];
  if (overreach) {
    const v = overreach.value as {
      big_five?: Record<string, { score?: number; blurb?: string }>;
    };
    const bf = v.big_five ?? {};
    for (const k of ["O", "C", "E", "A", "N"]) {
      const tr = bf[k];
      if (tr && typeof tr.blurb === "string") {
        out.push({
          id: `overreach.${k}`,
          construct: `Big Five — ${TRAIT_FULL[k] ?? k}`,
          punch: tr.blurb,
          inferenceId: null,
        });
      }
    }
  }
  for (const inf of inferences) {
    if (inf.tier !== "high") continue;
    const fmt = formatValue(inf);
    out.push({
      id: `inf.${inf.construct}`,
      construct: CONSTRUCT_LABEL[inf.construct] ?? inf.construct,
      punch: fmt.headline,
      inferenceId: null,
    });
  }
  return out;
}

export function Level7({
  inferences,
  overreach,
  onContinue,
}: {
  inferences: InferenceData[];
  overreach: InferenceData | null;
  onContinue: () => void;
}) {
  const choices = useMemo(
    () => buildChoices(inferences, overreach),
    [inferences, overreach],
  );
  const [chosenId, setChosenId] = useState<string>(choices[0]?.id ?? "");
  const [format, setFormat] = useState<Format>("vertical");
  const [busy, setBusy] = useState(false);
  const [downloaded, setDownloaded] = useState(false);
  const cardRef = useRef<HTMLDivElement>(null);

  const chosen = choices.find((c) => c.id === chosenId) ?? choices[0];
  const dim = DIMENSIONS[format];

  const persist = async (headline: string) => {
    const token = localStorage.getItem("inkling.session_token");
    if (!token) return;
    try {
      await api.postShareCard(token, {
        image_dimensions: `${dim.w}x${dim.h}`,
        headline,
        inference_id: chosen?.inferenceId ?? null,
      });
    } catch {
      // best-effort metadata logging, non-blocking
    }
  };

  const captureCanvas = async (): Promise<HTMLCanvasElement | null> => {
    if (!cardRef.current) return null;
    return html2canvas(cardRef.current, {
      backgroundColor: "#08090b",
      scale: 2,
      useCORS: true,
    });
  };

  const onDownload = async () => {
    if (!chosen) return;
    setBusy(true);
    try {
      const canvas = await captureCanvas();
      if (!canvas) return;
      const link = document.createElement("a");
      link.download = `inkling-${format}.png`;
      link.href = canvas.toDataURL("image/png");
      link.click();
      setDownloaded(true);
      await persist(`${chosen.construct}: ${chosen.punch}`);
    } finally {
      setBusy(false);
    }
  };

  const onCopy = async () => {
    if (!chosen) return;
    setBusy(true);
    try {
      const canvas = await captureCanvas();
      if (!canvas) return;
      const blob: Blob | null = await new Promise((resolve) =>
        canvas.toBlob((b) => resolve(b), "image/png"),
      );
      if (!blob) return;
      try {
        await navigator.clipboard.write([
          new ClipboardItem({ "image/png": blob }),
        ]);
      } catch {
        // clipboard image write may fail in some browsers
      }
      await persist(`${chosen.construct}: ${chosen.punch}`);
    } finally {
      setBusy(false);
    }
  };

  const onShare = async () => {
    if (!chosen) return;
    setBusy(true);
    try {
      const canvas = await captureCanvas();
      if (!canvas) return;
      const blob: Blob | null = await new Promise((resolve) =>
        canvas.toBlob((b) => resolve(b), "image/png"),
      );
      if (!blob) return;
      const file = new File([blob], "inkling.png", { type: "image/png" });
      type ShareNav = Navigator & {
        share?: (data: { files: File[]; text?: string }) => Promise<void>;
      };
      const nav = navigator as ShareNav;
      if (nav.share && typeof nav.share === "function") {
        await nav.share({
          files: [file],
          text: "Inkling guessed about me after 15 minutes.",
        });
      } else {
        await onCopy();
      }
      await persist(`${chosen.construct}: ${chosen.punch}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <LevelShell
      level={7}
      title="Take it with you"
      eyebrow="Level 7 of 7 · Show a friend"
      onContinue={onContinue}
      continueLabel="I'm done"
    >
      <p className="text-sm leading-relaxed text-muted">
        Pick the line that lands hardest — the one that nails it or the one
        that's wildest. The image is built right here in your browser.
        Nothing leaves your device unless you share it.
      </p>

      <div className="space-y-4">
        <div className="space-y-2">
          <label className="block text-xs uppercase tracking-[0.18em] text-muted">
            What goes on the card
          </label>
          <select
            className="w-full rounded-md border border-white/10 bg-white/2 px-3 py-2 text-sm text-foreground"
            value={chosenId}
            onChange={(e) => {
              setChosenId(e.target.value);
              setDownloaded(false);
            }}
          >
            {choices.map((c) => (
              <option key={c.id} value={c.id}>
                {c.construct} — {c.punch}
              </option>
            ))}
          </select>
        </div>

        <div className="flex gap-2">
          {(["vertical", "horizontal"] as const).map((f) => (
            <button
              key={f}
              type="button"
              onClick={() => setFormat(f)}
              className={`rounded-full border px-3 py-1.5 text-xs uppercase tracking-[0.18em] transition ${
                format === f
                  ? "border-accent bg-accent/10 text-accent"
                  : "border-white/10 text-muted"
              }`}
            >
              {f === "vertical" ? "Tall" : "Wide"} · {DIMENSIONS[f].label}
            </button>
          ))}
        </div>
      </div>

      <ShareCardPreview
        ref={cardRef}
        construct={chosen?.construct ?? ""}
        punch={chosen?.punch ?? ""}
        format={format}
      />

      <div className="flex flex-wrap gap-3 pt-2">
        <button
          type="button"
          onClick={onDownload}
          disabled={busy || !chosen}
          className="rounded-full bg-accent px-5 py-2 text-sm font-medium text-black transition hover:opacity-90 disabled:opacity-50"
        >
          {downloaded ? "Saved — save again" : "Save the image"}
        </button>
        <button
          type="button"
          onClick={onCopy}
          disabled={busy || !chosen}
          className="rounded-full border border-white/15 px-5 py-2 text-sm text-foreground transition hover:bg-white/5 disabled:opacity-50"
        >
          Copy it
        </button>
        <button
          type="button"
          onClick={onShare}
          disabled={busy || !chosen}
          className="rounded-full border border-white/15 px-5 py-2 text-sm text-foreground transition hover:bg-white/5 disabled:opacity-50"
        >
          Share it
        </button>
      </div>
    </LevelShell>
  );
}

const ShareCardPreview = forwardRef<
  HTMLDivElement,
  { construct: string; punch: string; format: Format }
>(function ShareCardPreview({ construct, punch, format }, ref) {
  const isTall = format === "vertical";
  const aspect = isTall ? "9 / 16" : "1200 / 630";
  const previewWidth = isTall ? 300 : 540;
  const punchSize = isTall ? "text-[34px] leading-[1.05]" : "text-[28px] leading-[1.05]";

  return (
    <div className="flex justify-center">
      <div
        ref={ref}
        className="relative overflow-hidden rounded-2xl"
        style={{
          aspectRatio: aspect,
          width: `${previewWidth}px`,
          maxWidth: "100%",
          background:
            "radial-gradient(120% 80% at 90% 10%, rgba(34, 211, 238, 0.22) 0%, rgba(34, 211, 238, 0.06) 35%, transparent 65%), #08090b",
          border: "1px solid rgba(34, 211, 238, 0.35)",
          fontFamily: "Inter, system-ui, sans-serif",
          color: "#e5e7eb",
        }}
      >
        <div
          className="flex h-full flex-col justify-between"
          style={{ padding: isTall ? "44px 36px" : "36px 44px" }}
        >
          {/* Top: wordmark */}
          <div className="flex items-center justify-between">
            <span
              className="font-semibold tracking-[0.22em]"
              style={{ fontSize: "12px", color: "#67e8f9" }}
            >
              INKLING
            </span>
            <span
              style={{
                fontSize: "11px",
                color: "rgba(229, 231, 235, 0.55)",
              }}
            >
              15 min · 6 rounds
            </span>
          </div>

          {/* Middle: the guess */}
          <div className="space-y-4">
            <div
              className="inline-flex items-center gap-2 rounded-full px-3 py-1"
              style={{
                border: "1px solid rgba(34, 211, 238, 0.45)",
                background: "rgba(34, 211, 238, 0.08)",
                width: "fit-content",
              }}
            >
              <span
                style={{
                  width: "5px",
                  height: "5px",
                  borderRadius: "9999px",
                  background: "#67e8f9",
                }}
              />
              <span
                style={{
                  fontSize: "10px",
                  letterSpacing: "0.18em",
                  textTransform: "uppercase",
                  color: "#67e8f9",
                }}
              >
                {construct || "Inkling's read"}
              </span>
            </div>

            <p
              className={`font-semibold tracking-tight ${punchSize}`}
              style={{ color: "#f3f4f6" }}
            >
              {punch || "Inkling read something about me."}
            </p>

            <p
              style={{
                fontSize: "12px",
                lineHeight: 1.5,
                color: "rgba(229, 231, 235, 0.65)",
                maxWidth: "32ch",
              }}
            >
              Inkling guessed this about me from 15 minutes of play, with my
              permission, after showing me what it saw.
            </p>
          </div>

          {/* Bottom: lockup */}
          <div className="flex items-end justify-between">
            <span
              style={{
                fontSize: "12px",
                letterSpacing: "0.18em",
                textTransform: "uppercase",
                color: "#67e8f9",
              }}
            >
              inkling.app
            </span>
            <span
              style={{
                fontSize: "10px",
                color: "rgba(229, 231, 235, 0.4)",
              }}
            >
              consent first · no targeting
            </span>
          </div>
        </div>
      </div>
    </div>
  );
});
