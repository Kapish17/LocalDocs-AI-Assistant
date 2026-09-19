import { useCallback, useEffect, useState } from "react";
import { listSessions, createSession, deleteSession as apiDeleteSession } from "../services/api";
import { notifySessionsChanged, onSessionsChanged } from "../utils/sessionEvents";

/**
 * Shared session-list state for the chat sidebar — create/switch/delete,
 * each session's own isolated history is fetched separately (getSession)
 * by the Chat page when it becomes the active one.
 */
export function useSessions() {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const list = await listSessions();
      setSessions(list);
    } catch (err) {
      setError(err.message || "Could not load chat sessions.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    return onSessionsChanged(refresh);
  }, [refresh]);

  async function addSession(title) {
    const session = await createSession(title);
    await refresh();
    notifySessionsChanged();
    return session;
  }

  async function removeSession(sessionId) {
    await apiDeleteSession(sessionId);
    await refresh();
    notifySessionsChanged();
  }

  return { sessions, loading, error, refresh, addSession, removeSession };
}
