import { Menu, Moon, Sun } from "lucide-react";

const TITLES = {
  "/": "Dashboard",
  "/documents": "Documents",
  "/chat": "Chat",
  "/summary": "Summarize",
  "/flashcards": "Flashcards",
};

function titleFor(pathname) {
  if (TITLES[pathname]) return TITLES[pathname];
  if (pathname.startsWith("/chat")) return "Chat";
  if (pathname.startsWith("/summary")) return "Summarize";
  if (pathname.startsWith("/flashcards")) return "Flashcards";
  return "LocalDocs AI Assistant";
}

export default function Topbar({ pathname, health, onToggleSidebar, theme, onToggleTheme }) {
  const kbReady = health?.kb_ready;
  const llmReady = health?.llm_ready;
  const reachable = health !== null;

  let statusDot = "status-dot--error";
  let statusText = "Backend unreachable";
  if (reachable) {
    if (kbReady && llmReady) {
      statusDot = "status-dot--ok";
      statusText = "Ready";
    } else if (kbReady) {
      statusDot = "status-dot--warn";
      statusText = "AI model not configured";
    } else {
      statusDot = "status-dot--warn";
      statusText = "No documents yet";
    }
  }

  return (
    <header className="topbar">
      <button className="topbar-menu-btn" onClick={onToggleSidebar} aria-label="Toggle sidebar">
        <Menu size={20} />
      </button>
      <h2 className="topbar-title">{titleFor(pathname)}</h2>
      <span className="topbar-status">
        <span className={`status-dot ${statusDot}`} />
        {statusText}
      </span>
      <button
        className="icon-btn"
        onClick={onToggleTheme}
        aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
        title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
      >
        {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
      </button>
    </header>
  );
}
