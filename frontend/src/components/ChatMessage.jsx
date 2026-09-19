import SourceList from "./SourceList";

function ConfidenceBar({ confidence }) {
  if (confidence === null || confidence === undefined) return null;
  const pct = Math.max(0, Math.min(100, Math.round(confidence * 100)));
  const level = pct >= 70 ? "high" : pct >= 40 ? "medium" : "low";
  return (
    <div className="confidence-bar" title={`Confidence: ${pct}%`}>
      <div className={`confidence-bar-fill confidence-bar-fill--${level}`} style={{ width: `${pct}%` }} />
      <span className="confidence-label">{pct}% confidence</span>
    </div>
  );
}

export default function ChatMessage({ message }) {
  const isUser = message.role === "user";
  return (
    <div className={`chat-message chat-message--${isUser ? "user" : "assistant"}`}>
      <div className="chat-message-avatar">{isUser ? "🧑" : "🤖"}</div>
      <div className="chat-message-body">
        <p className="chat-message-text">{message.content}</p>
        {!isUser && !message.error && <ConfidenceBar confidence={message.confidence} />}
        {!isUser && !message.error && <SourceList retrievedDocuments={message.retrieved_documents} />}
      </div>
    </div>
  );
}
