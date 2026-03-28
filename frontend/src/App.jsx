import ChatShell from "./components/ChatShell";

export default function App() {
  return (
    <div className="app-root">
      <header className="app-topbar">
        <h1>Candid — local chat test</h1>
        <p>Socratic debate engine · backend must be on port 8000 (or set VITE_API_BASE_URL)</p>
      </header>
      <ChatShell />
    </div>
  );
}
