import { useEffect, useState } from "react";
import ChatMessage from "../components/ChatMessage";
import QueryBox from "../components/QueryBox";
import UploadPanel from "../components/UploadPanel";
import { askQuestion, getHealth } from "../services/api";

export default function Home() {
  const [messages, setMessages] = useState([]);
  const [asking, setAsking] = useState(false);
  const [health, setHealth] = useState(null);
  const [healthError, setHealthError] = useState(null);

  async function refreshHealth() {
    try {
      const h = await getHealth();
      setHealth(h);
      setHealthError(null);
    } catch (err) {
      setHealthError(err.message || "Could not reach the backend.");
      setHealth(null);
    }
  }

  useEffect(() => {
    refreshHealth();
  }, []);

  async function handleAsk(question) {
    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setAsking(true);
    try {
      const result = await askQuestion(question);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: result.answer,
          confidence: result.confidence,
          sources: result.sources,
          retrieved_documents: result.retrieved_documents,
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: err.message || "Something went wrong.", error: true },
      ]);
    } finally {
      setAsking(false);
    }
  }

  const kbReady = health?.kb_ready;
  const llmReady = health?.llm_ready;

  return (
    <div className="page">
      <header className="page-header">
        <h1>📚 LocalDocs AI Assistant</h1>
        <p className="subtitle">Ask questions about your own documents, grounded with citations.</p>
      </header>

      {healthError && (
        <div className="banner banner--error">
          ⚠️ Can't reach the backend at the configured API URL. {healthError}
        </div>
      )}

      {health && !kbReady && (
        <div className="banner banner--info">
          ℹ️ No knowledge base yet — upload a document below to get started.
        </div>
      )}

      {health && kbReady && !llmReady && (
        <div className="banner banner--warning">
          ⚠️ The AI model isn't configured on the backend
          {health.llm_error ? `: ${health.llm_error}` : "."}
        </div>
      )}

      <UploadPanel onUploaded={refreshHealth} disabled={asking} />

      <div className="chat-window">
        {messages.length === 0 && (
          <div className="empty-state">
            <p>No messages yet. Upload a document, then ask a question below.</p>
          </div>
        )}
        {messages.map((m, i) => (
          <ChatMessage key={i} message={m} />
        ))}
        {asking && (
          <div className="chat-message chat-message--assistant">
            <div className="chat-message-avatar">🤖</div>
            <div className="chat-message-body">
              <p className="chat-message-text chat-message-text--loading">Searching your documents…</p>
            </div>
          </div>
        )}
      </div>

      <QueryBox onAsk={handleAsk} disabled={asking || !kbReady || !llmReady} />
    </div>
  );
}
