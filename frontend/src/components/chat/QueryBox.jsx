import { useState } from "react";
import { Send } from "lucide-react";

export default function QueryBox({ onAsk, disabled }) {
  const [value, setValue] = useState("");

  function handleSubmit(e) {
    e.preventDefault();
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onAsk(trimmed);
    setValue("");
  }

  return (
    <form className="query-box" onSubmit={handleSubmit}>
      <input
        type="text"
        placeholder="Ask a question about your documents…"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        disabled={disabled}
        aria-label="Ask a question"
      />
      <button type="submit" disabled={disabled || !value.trim()}>
        {disabled ? "Thinking…" : (
          <>
            <Send size={15} style={{ verticalAlign: "-2px", marginRight: 4 }} />
            Ask
          </>
        )}
      </button>
    </form>
  );
}
