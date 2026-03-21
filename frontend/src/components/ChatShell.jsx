import { useState } from "react";
import { sendChatMessage } from "../services/api";

export default function ChatShell() {
  const [message, setMessage] = useState("");
  const [response, setResponse] = useState("");
  const [mode, setMode] = useState("mock");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event) {
    event.preventDefault();
    if (!message.trim()) return;

    setLoading(true);
    setError("");
    try {
      const data = await sendChatMessage({ message: message.trim() });
      setResponse(data.response_text);
      setMode(data.mode);
    } catch (err) {
      setError(err.message || "Request failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="chat-shell">
      <form onSubmit={handleSubmit} className="chat-form">
        <label htmlFor="chat-input">Ask a topic question</label>
        <textarea
          id="chat-input"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          rows={4}
          placeholder="e.g., Explain different economic views on inflation."
        />
        <button type="submit" disabled={loading}>
          {loading ? "Thinking..." : "Send"}
        </button>
      </form>

      <article className="chat-output">
        <h2>Response ({mode})</h2>
        {error ? <p className="error">{error}</p> : <p>{response || "No response yet."}</p>}
      </article>
    </section>
  );
}
