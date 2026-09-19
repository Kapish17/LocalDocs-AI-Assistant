import { AlertTriangle, RotateCw } from "lucide-react";

/**
 * User-friendly error display — never renders a raw backend stack trace,
 * just the message the API already returns via HTTPException(detail=...),
 * with an optional retry action.
 */
export default function ErrorBanner({ message, onRetry }) {
  if (!message) return null;
  return (
    <div className="banner banner--error">
      <AlertTriangle size={16} />
      <span style={{ flex: 1 }}>{message}</span>
      {onRetry && (
        <button className="btn btn-ghost" onClick={onRetry} style={{ padding: "4px 10px" }}>
          <RotateCw size={13} /> Retry
        </button>
      )}
    </div>
  );
}
