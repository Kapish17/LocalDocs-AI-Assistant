// Sidebar's session list and the Chat page each hold their own independent
// useSessions() state (no global store in this small app) — so when Chat
// creates a session directly via the API (e.g. on sending the first
// message before any session exists), the Sidebar's copy would otherwise
// go stale until an unrelated re-render happened to refetch it. This tiny
// event bus lets any part of the app say "the session list changed" and
// every useSessions() instance (including the Sidebar's) refetches.
const EVENT_NAME = "localdocs:sessions-changed";

export function notifySessionsChanged() {
  window.dispatchEvent(new Event(EVENT_NAME));
}

export function onSessionsChanged(handler) {
  window.addEventListener(EVENT_NAME, handler);
  return () => window.removeEventListener(EVENT_NAME, handler);
}
