import { Loader2 } from "lucide-react";

export function LoadingRow({ label = "Loading…" }) {
  return (
    <div className="loading-row">
      <Loader2 size={15} className="spin" />
      <span>{label}</span>
    </div>
  );
}

export function SkeletonBlock({ height = 16, width = "100%", style }) {
  return <div className="skeleton" style={{ height, width, ...style }} />;
}

export function SkeletonLines({ count = 4 }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      {Array.from({ length: count }).map((_, i) => (
        <SkeletonBlock key={i} height={14} width={i === count - 1 ? "60%" : "100%"} />
      ))}
    </div>
  );
}
