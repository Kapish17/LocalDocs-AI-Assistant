import { useEffect, useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import Sidebar from "./Sidebar";
import Topbar from "./Topbar";
import { useTheme } from "../../hooks/useTheme";
import { getHealth } from "../../services/api";

const HEALTH_POLL_MS = 15000;

export default function AppShell() {
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const { theme, toggleTheme } = useTheme();
  const [health, setHealth] = useState(null);

  useEffect(() => {
    let cancelled = false;
    async function poll() {
      try {
        const h = await getHealth();
        if (!cancelled) setHealth(h);
      } catch {
        if (!cancelled) setHealth(null);
      }
    }
    poll();
    const id = setInterval(poll, HEALTH_POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  useEffect(() => {
    setMobileOpen(false);
  }, [location.pathname]);

  return (
    <div className={`app-shell${mobileOpen ? " sidebar-open" : ""}`}>
      <Sidebar onNavigate={() => setMobileOpen(false)} />
      {mobileOpen && <div className="sidebar-backdrop" onClick={() => setMobileOpen(false)} />}
      <div className="app-main">
        <Topbar
          pathname={location.pathname}
          health={health}
          onToggleSidebar={() => setMobileOpen((v) => !v)}
          theme={theme}
          onToggleTheme={toggleTheme}
        />
        <main className="app-content">
          <Outlet context={{ health, refreshHealth: () => getHealth().then(setHealth).catch(() => setHealth(null)) }} />
        </main>
      </div>
    </div>
  );
}
