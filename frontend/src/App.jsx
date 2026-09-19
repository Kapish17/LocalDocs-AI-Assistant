import { BrowserRouter, Routes, Route } from "react-router-dom";
import AppShell from "./components/layout/AppShell";
import Dashboard from "./pages/Dashboard";
import Documents from "./pages/Documents";
import Chat from "./pages/Chat";
import Summary from "./pages/Summary";
import Flashcards from "./pages/Flashcards";
import "./index.css";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppShell />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/documents" element={<Documents />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/chat/:sessionId" element={<Chat />} />
          <Route path="/summary" element={<Summary />} />
          <Route path="/summary/:documentId" element={<Summary />} />
          <Route path="/flashcards" element={<Flashcards />} />
          <Route path="/flashcards/:documentId" element={<Flashcards />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
