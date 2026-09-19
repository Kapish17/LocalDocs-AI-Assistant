import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { clearStaleSessionUrl } from "./utils/clearStaleSessionUrl";

// Must run before <App/> mounts, synchronously, so React Router's very
// first route match already sees a cleaned-up URL instead of a stale
// document/chat-session id surviving a full browser refresh — see
// utils/clearStaleSessionUrl.js for why this is needed and why it is safe
// (it never touches normal in-app navigation).
clearStaleSessionUrl();

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
