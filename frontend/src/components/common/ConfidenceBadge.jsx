import { Gauge } from "lucide-react";

/**
 * Confidence here is a RETRIEVAL-quality signal (average similarity of the
 * chunks used to answer), not an objective probability the answer is
 * correct — the label and tooltip say that explicitly rather than implying
 * false precision.
 */
export default function ConfidenceBadge({ confidence }) {
  if (confidence === null || confidence === undefined) return null;
  const pct = Math.max(0, Math.min(100, Math.round(confidence * 100)));
  const level = pct >= 70 ? "high" : pct >= 40 ? "medium" : "low";
  const label = level === "high" ? "High" : level === "medium" ? "Medium" : "Low";
  return (
    <span
      className={`confidence-badge confidence-badge--${level}`}
      title="How closely the retrieved document text matched this question — not a guarantee the answer is fully correct."
    >
      <Gauge size={12} />
      {label} confidence ({pct}%)
    </span>
  );
}
