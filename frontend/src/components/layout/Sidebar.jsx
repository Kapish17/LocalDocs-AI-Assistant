import { NavLink, useLocation, useNavigate } from "react-router-dom";
import {
  LayoutDashboard,
  FileStack,
  MessageSquare,
  NotebookText,
  Layers,
  Plus,
  Trash2,
  BookOpenCheck,
} from "lucide-react";
import { useSessions } from "../../hooks/useSessions";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/documents", label: "Documents", icon: FileStack },
  { to: "/chat", label: "Chat", icon: MessageSquare },
  { to: "/summary", label: "Summarize", icon: NotebookText },
  { to: "/flashcards", label: "Flashcards", icon: Layers },
];

export default function Sidebar({ onNavigate }) {
  const location = useLocation();
  const navigate = useNavigate();
  const onChatRoute = location.pathname.startsWith("/chat");
  const { sessions, addSession, removeSession } = useSessions();

  async function handleNewSession() {
    const session = await addSession();
    navigate(`/chat/${session.session_id}`);
    if (onNavigate) onNavigate();
  }

  async function handleDeleteSession(e, sessionId) {
    e.preventDefault();
    e.stopPropagation();
    await removeSession(sessionId);
    if (location.pathname === `/chat/${sessionId}`) navigate("/chat");
  }

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <BookOpenCheck size={20} className="sidebar-brand-icon" />
        <span>LocalDocs AI</span>
      </div>

      <nav className="sidebar-nav">
        {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            onClick={onNavigate}
            className={({ isActive }) => `sidebar-link${isActive ? " active" : ""}`}
          >
            <Icon size={17} />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>

      {onChatRoute && (
        <>
          <div className="sidebar-section-title">
            <span>Chat sessions</span>
            <button className="sidebar-new-session" onClick={handleNewSession} aria-label="New chat session">
              <Plus size={13} /> New
            </button>
          </div>
          <div className="sidebar-sessions">
            {sessions.length === 0 && (
              <p style={{ color: "var(--text-faint)", fontSize: "0.8rem", padding: "4px 8px" }}>
                No sessions yet.
              </p>
            )}
            {sessions.map((s) => (
              <div
                key={s.session_id}
                className={`session-row${location.pathname === `/chat/${s.session_id}` ? " active" : ""}`}
              >
                <NavLink to={`/chat/${s.session_id}`} onClick={onNavigate} className="session-row-link">
                  {s.title}
                </NavLink>
                <button
                  className="session-row-delete"
                  aria-label={`Delete session ${s.title}`}
                  onClick={(e) => handleDeleteSession(e, s.session_id)}
                >
                  <Trash2 size={14} />
                </button>
              </div>
            ))}
          </div>
        </>
      )}

      <div className="sidebar-footer">RAG over your own documents, with citations.</div>
    </aside>
  );
}
