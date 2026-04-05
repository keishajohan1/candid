import { useState, useRef, useEffect } from "react";
import { sendChatMessage } from "../services/api";

export default function ChatShell() {
  const [sessions, setSessions] = useState([
    { id: "1", title: "New conversation", messages: [], topic: "" }
  ]);
  const [activeSessionId, setActiveSessionId] = useState("1");
  const [input, setInput] = useState("");
  
  const activeSession = sessions.find((s) => s.id === activeSessionId) || sessions[0];
  const messages = activeSession.messages;
  const topic = activeSession.topic;

  const setTopic = (newTopic) => {
    setSessions(prev =>
      prev.map(s => s.id === activeSessionId ? { ...s, topic: typeof newTopic === 'function' ? newTopic(s.topic) : newTopic } : s)
    );
  };

  const setMessages = (updater) => {
    setSessions(prev =>
      prev.map(s => {
        if (s.id === activeSessionId) {
          const newMessages = typeof updater === 'function' ? updater(s.messages) : updater;
          let newTitle = s.title;
          if (s.messages.length === 0 && newMessages.length > 0 && newMessages[0].role === "user") {
             const text = newMessages[0].content;
             newTitle = text.length > 28 ? text.slice(0, 28) + "..." : text;
          }
          return { ...s, messages: newMessages, title: newTitle };
        }
        return s;
      })
    );
  };

  const handleNewChat = () => {
    const newId = Date.now().toString();
    setSessions(prev => [{ id: newId, title: "New conversation", messages: [], topic: "" }, ...prev]);
    setActiveSessionId(newId);
    setInput("");
    setError("");
    setLastDebug(null);
  };
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [fetchSources, setFetchSources] = useState(false);
  const [devMode, setDevMode] = useState(false);
  const [lastDebug, setLastDebug] = useState(null);
  const listEndRef = useRef(null);

  const turnIndex = messages.filter((m) => m.role === "assistant").length + 1;

  const renderMessageContent = (content) => {
    if (!content) return null;
    const parts = content.split(/(\*(?!\*)[^*]+\*|_(?!_)[^_]+_)/g);
    return parts.map((part, i) => {
      if ((part.startsWith('*') && part.endsWith('*')) || (part.startsWith('_') && part.endsWith('_'))) {
        return <em key={i}>{part.slice(1, -1)}</em>;
      }
      return part;
    });
  };

  useEffect(() => {
    listEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function handleSubmit(event) {
    event.preventDefault();
    const text = input.trim();
    if (!text || loading) return;

    const userHistory = messages
      .filter((m) => m.role === "user")
      .map((m) => m.content);

    setLoading(true);
    setError("");
    setInput("");

    const userMsg = { role: "user", content: text, id: `${Date.now()}-u` };
    setMessages((prev) => [...prev, userMsg]);

    try {
      const data = await sendChatMessage({
        message: text,
        topic: topic.trim() || null,
        turn_index: turnIndex,
        history: userHistory,
        fetch_sources: fetchSources,
      });

      setLastDebug({
        mode: data.mode,
        source_count: data.debug?.source_count ?? 0,
        reddit_item_count: data.debug?.reddit_item_count ?? 0,
        ingest_errors: data.debug?.ingest_errors ?? [],
        sources: data.sources ?? [],
      });

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.response_text,
          id: `${Date.now()}-a`,
          sources: data.sources ?? [],
        },
      ]);
    } catch (err) {
      setError(err.message || "Request failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="chatgpt-layout">
      <aside className="chat-sidebar">
        <div className="sidebar-brand">
          candid<span className="brand-dot">.</span>
        </div>
        <hr className="sidebar-divider" />
        <p className="sidebar-tagline">A space to think through what matters.</p>

        <button className="new-chat-btn" onClick={handleNewChat}>
          + New conversation
        </button>

        <div className="sidebar-section">
          <h3 className="sidebar-section-label">Recent</h3>
          <ul className="sidebar-list">
            {sessions.map(s => (
              <li 
                key={s.id} 
                onClick={() => setActiveSessionId(s.id)}
                style={{ fontWeight: s.id === activeSessionId ? 600 : 400, color: s.id === activeSessionId ? '#111827' : '' }}
              >
                {s.title}
              </li>
            ))}
          </ul>
        </div>

        <div className="sidebar-section">
          <h3 className="sidebar-section-label">Sources</h3>
          <ul className="sidebar-list">
            <li>r/changemyview</li>
            <li>r/politics</li>
          </ul>
        </div>

        <div className="sidebar-footer">
          {devMode && (
            <div className="dev-mode-panel">
              <p className="sidebar-hint">Local test UI — Socratic debate mode</p>
              <label className="sidebar-label">
                Topic (optional)
                <input
                  type="text"
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  placeholder="e.g. climate policy"
                />
              </label>
              <label className="sidebar-check">
                <input
                  type="checkbox"
                  checked={fetchSources}
                  onChange={(e) => setFetchSources(e.target.checked)}
                />
                Fetch Reddit excerpts for the prompt (may be slow)
              </label>
              <p className="sidebar-meta">Next turn_index: {turnIndex}</p>
            </div>
          )}
          
          <label className="sidebar-check" style={{ color: "#9c8c72" }}>
            <input
              type="checkbox"
              checked={devMode}
              onChange={(e) => setDevMode(e.target.checked)}
            />
            Developer Mode
          </label>
        </div>
      </aside>

      <div className="chat-main">
        <div className="messages-scroll">
          {messages.length === 0 && (
            <p className="empty-hint">
              Send a message to test the assistant. Enable source fetch to pipe
              backend-ingested snippets into the prompt (no scraping by Claude).
            </p>
          )}
          {messages.map((m) => (
            <div
              key={m.id}
              className={`bubble ${m.role === "user" ? "bubble-user" : "bubble-assistant"}`}
            >
              <span className="bubble-role">{m.role === "user" ? "You" : "Assistant"}</span>
              <p className="bubble-text">{renderMessageContent(m.content)}</p>
              {m.role === "assistant" && m.sources && m.sources.length > 0 && (
                <div className="bubble-sources">
                  {m.sources.map((s, i) => (
                    <span key={i} className="bubble-source">
                      † {s.label || s.source}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}
          {loading && (
            <div className="bubble bubble-assistant loading-bubble">
              <span className="bubble-role">Assistant</span>
              <p className="bubble-text">Thinking…</p>
            </div>
          )}
          <div ref={listEndRef} />
        </div>

        {error && <p className="error-banner">{error}</p>}

        <form className="composer" onSubmit={handleSubmit}>
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            rows={3}
            placeholder="Your message…"
            disabled={loading}
          />
          <button type="submit" disabled={loading || !input.trim()}>
            {loading ? "Sending…" : "Send"}
          </button>
        </form>

        {devMode && lastDebug && (
          <div className="debug-panel">
            <strong>Debug</strong>
            <ul>
              <li>Mode: {lastDebug.mode}</li>
              <li>Source count (returned): {lastDebug.source_count}</li>
              <li>Reddit items (ingested): {lastDebug.reddit_item_count}</li>
            </ul>
            {lastDebug.ingest_errors?.length > 0 && (
              <div className="debug-errors">
                <strong>Ingest issues</strong>
                <ul>
                  {lastDebug.ingest_errors.map((e, i) => (
                    <li key={i}>
                      {e.source}: {e.code} — {e.message}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {lastDebug.sources?.length > 0 && (
              <div className="debug-sources">
                <strong>Source labels</strong>
                <ul>
                  {lastDebug.sources.slice(0, 8).map((s, i) => (
                    <li key={i}>
                      {s.label || s.source}
                      {s.url ? (
                        <>
                          {" "}
                          <a href={s.url} target="_blank" rel="noreferrer">
                            link
                          </a>
                        </>
                      ) : null}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
