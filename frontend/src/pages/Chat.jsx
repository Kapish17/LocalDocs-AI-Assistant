import { useEffect, useRef, useState } from "react";
import { useNavigate, useOutletContext, useParams, useSearchParams } from "react-router-dom";
import ChatMessage from "../components/chat/ChatMessage";
import QueryBox from "../components/chat/QueryBox";
import ErrorBanner from "../components/common/ErrorBanner";
import EmptyState from "../components/common/EmptyState";
import { MessageSquare, FileText } from "lucide-react";
import { askQuestion, createSession, getSession } from "../services/api";
import { useDocuments } from "../hooks/useDocuments";
import { notifySessionsChanged } from "../utils/sessionEvents";

export default function Chat() {
  const { sessionId: sessionIdParam } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const { documents } = useDocuments();
  const { health } = useOutletContext() || {};
  const kbReady = health?.kb_ready;
  const llmReady = health?.llm_ready;

  const [sessionId, setSessionId] = useState(sessionIdParam || null);
  const [messages, setMessages] = useState([]);
  const [asking, setAsking] = useState(false);
  const [loadError, setLoadError] = useState(null);
  const [documentId, setDocumentId] = useState(searchParams.get("doc") || "");

  // handleAsk navigates to /chat/:sessionId as soon as a session is lazily
  // created (so the URL is shareable/refreshable), but that navigation
  // fires *before* the in-flight answer resolves. Without this guard, the
  // route-change effect below would immediately re-fetch that brand-new
  // (still empty) session from the server and wipe out the optimistic
  // user message — and possibly the assistant's reply too, depending on
  // timing — that's already in local state. When a session id we just
  // created ourselves shows up as the route param, skip the fetch once:
  // local state is already the source of truth for it.
  const justCreatedSessionId = useRef(null);

  useEffect(() => {
    setSessionId(sessionIdParam || null);
    if (!sessionIdParam) {
      setMessages([]);
      return;
    }
    if (justCreatedSessionId.current === sessionIdParam) {
      justCreatedSessionId.current = null;
      return;
    }
    let cancelled = false;
    getSession(sessionIdParam)
      .then((detail) => {
        if (cancelled) return;
        setMessages(
          detail.messages.map((m) => ({
            role: m.role,
            content: m.content,
            confidence: m.confidence,
            retrieved_documents: m.sources,
          }))
        );
        setLoadError(null);
      })
      .catch((err) => {
        if (!cancelled) setLoadError(err.message || "Could not load this chat session.");
      });
    return () => {
      cancelled = true;
    };
  }, [sessionIdParam]);

  async function handleAsk(question) {
    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setAsking(true);
    try {
      let activeSessionId = sessionId;
      if (!activeSessionId) {
        const created = await createSession();
        activeSessionId = created.session_id;
        setSessionId(activeSessionId);
        justCreatedSessionId.current = activeSessionId;
        notifySessionsChanged();
        navigate(`/chat/${activeSessionId}${documentId ? `?doc=${encodeURIComponent(documentId)}` : ""}`, {
          replace: true,
        });
      }
      const result = await askQuestion(question, { documentId: documentId || undefined, sessionId: activeSessionId });
      notifySessionsChanged();
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

  function handleDocumentChange(e) {
    const value = e.target.value;
    setDocumentId(value);
    const params = new URLSearchParams(searchParams);
    if (value) params.set("doc", value);
    else params.delete("doc");
    setSearchParams(params, { replace: true });
  }

  return (
    <div className="chat-page">
      <div className="chat-context-bar">
        <FileText size={15} style={{ color: "var(--text-dim)" }} />
        <select className="chat-context-select" value={documentId} onChange={handleDocumentChange}>
          <option value="">All documents</option>
          {documents.map((d) => (
            <option key={d.document_id} value={d.document_id}>
              {d.filename}
            </option>
          ))}
        </select>
        {documentId && (
          <span style={{ fontSize: "0.78rem", color: "var(--text-faint)" }}>
            Answers scoped to this document only
          </span>
        )}
      </div>

      <ErrorBanner message={loadError} />
      {health && !kbReady && (
        <div className="banner banner--info">Upload a document to start chatting.</div>
      )}
      {health && kbReady && !llmReady && (
        <div className="banner banner--warning">
          The AI model isn't configured on the backend{health.llm_error ? `: ${health.llm_error}` : "."}
        </div>
      )}

      <div className="chat-window">
        {messages.length === 0 && (
          <EmptyState
            icon={MessageSquare}
            title="No messages yet"
            hint="Ask a question about your uploaded documents below. Pick a document above to scope the conversation to just that file."
          />
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
