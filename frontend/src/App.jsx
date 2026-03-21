import ChatShell from "./components/ChatShell";

export default function App() {
  return (
    <main className="app-shell">
      <header className="app-header">
        <h1>Candid</h1>
        <p>Neutral educational chatbot MVP scaffold</p>
      </header>
      <ChatShell />
    </main>
  );
}
