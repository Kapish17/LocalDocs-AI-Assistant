import { useState } from "react";

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
      />
      <button type="submit" disabled={disabled || !value.trim()}>
        {disabled ? "Thinking…" : "Ask"}
      </button>
    </form>
  );
}
