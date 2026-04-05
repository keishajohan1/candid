import { useState, useRef, useEffect, useMemo } from "react";
import { sendChatMessage } from "../services/api";

function generateLocalTitle(text) {
  let cleaned = text.replace(/^(can you explain|can you|what is|what's|what are|how do|how to|why is|why are|please tell me about|tell me about|explain|describe)\b/gi, '').trim();
  cleaned = cleaned.replace(/[?.!;,]+$/g, '').trim();
  const words = cleaned.split(/\s+/).filter(w => w.length > 0);
  const titleWords = words.slice(0, 4);
  let title = titleWords.join(" ");
  if (words.length > 4) {
    title += "...";
  }
  if (title.length > 0) {
    title = title.charAt(0).toUpperCase() + title.slice(1);
  }
  return title || "New conversation";
}

export default function ChatShell() {
  const placeholders = [
    "What are you trying to understand...",
    "What's something you've been trying to make sense of...",
    "Something you've heard but never fully understood...",
    "What's the version of this story you haven't heard...",
    "What's the part of this you can't quite explain...",
    "Ask the question behind the question..."
  ];

  const [sessions, setSessions] = useState([
    { id: "1", title: "...", messages: [], topic: "" }
  ]);
  const [activeSessionId, setActiveSessionId] = useState("1");
  const [expandedRecent, setExpandedRecent] = useState(false);
  const [expandedSources, setExpandedSources] = useState(false);
  const [sessionToDelete, setSessionToDelete] = useState(null);

  const confirmDelete = () => {
    if (!sessionToDelete) return;
    
    let nextActiveId = activeSessionId;

    setSessions(prev => {
      const filtered = prev.filter(s => s.id !== sessionToDelete.id);
      if (filtered.length === 0) {
        const newId = Date.now().toString();
        setActiveSessionId(newId);
        return [{ id: newId, title: "...", messages: [], topic: "" }];
      }
      if (nextActiveId === sessionToDelete.id) {
        setActiveSessionId(filtered[0].id);
      }
      return filtered;
    });
    
    setSessionToDelete(null);
  };

  const staticSources = [
    { label: "r/changemyview", href: "https://reddit.com/r/changemyview" },
    { label: "r/politics", href: "https://reddit.com/r/politics" },
    { label: "NASA GISS", href: "https://data.giss.nasa.gov/" },
    { label: "Bureau of Economic Analysis", href: "https://www.bea.gov/" },
    { label: "US Census Bureau", href: "https://www.census.gov/" },
    { label: "Pew Research Center", href: "https://www.pewresearch.org/" },
    { label: "CDC", href: "https://www.cdc.gov/" },
    { label: "FCC", href: "https://www.fcc.gov/" },
  ];
  const [input, setInput] = useState("");

  const activeSession = sessions.find((s) => s.id === activeSessionId) || sessions[0];
  const messages = activeSession.messages;
  const topic = activeSession.topic;

  const currentPlaceholder = useMemo(() => {
    return placeholders[Math.floor(Math.random() * placeholders.length)];
  }, [activeSessionId]);

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
          return { ...s, messages: newMessages };
        }
        return s;
      })
    );
  };

  const handleNewChat = () => {
    const emptySession = sessions.find(s => s.messages.length === 0);
    if (emptySession) {
      setActiveSessionId(emptySession.id);
      setInput("");
      setError("");
      setLastDebug(null);
      return;
    }

    const newId = Date.now().toString();
    setSessions(prev => [{ id: newId, title: "...", messages: [], topic: "" }, ...prev]);
    setActiveSessionId(newId);
    setInput("");
    setError("");
    setLastDebug(null);
  };
  const [loadingState, setLoadingState] = useState(null);
  const loading = loadingState !== null;
  const [error, setError] = useState("");
  const [fetchSources, setFetchSources] = useState(false);
  const [devMode, setDevMode] = useState(false);
  const [lastDebug, setLastDebug] = useState(null);
  const listEndRef = useRef(null);
  const textareaRef = useRef(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [input]);

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

    setLoadingState("reading");
    setError("");
    setInput("");

    const userMsg = { role: "user", content: text, id: `${Date.now()}-u` };
    setMessages((prev) => [...prev, userMsg]);

    const readTimer = setTimeout(() => {
      setLoadingState("thinking");
    }, fetchSources ? 2500 : 800);

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

      if (messages.length === 0) {
        const localTitle = generateLocalTitle(text);
        setSessions(prev => 
          prev.map(s => s.id === activeSessionId ? { ...s, title: localTitle } : s)
        );
      }
    } catch (err) {
      setError(err.message || "Request failed.");
    } finally {
      clearTimeout(readTimer);
      setLoadingState(null);
    }
  }

  return (
    <div className="chatgpt-layout">
      {sessionToDelete && (
        <div className="modal-overlay" onClick={() => setSessionToDelete(null)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <h3 className="modal-title">Delete chat?</h3>
            <p className="modal-text">
              Are you sure you want to permanently delete "{sessionToDelete.title === "..." ? "New conversation" : sessionToDelete.title}"?
            </p>
            <div className="modal-actions">
              <button className="modal-btn-cancel" onClick={() => setSessionToDelete(null)}>Cancel</button>
              <button className="modal-btn-delete" onClick={confirmDelete}>Delete</button>
            </div>
          </div>
        </div>
      )}

      <aside className="chat-sidebar">
        <div className="sidebar-brand">
          candid<span className="brand-dot">.</span>
        </div>
        <hr className="sidebar-divider" />
        <p className="sidebar-tagline">information without an agenda</p>

        <button className="new-chat-btn" onClick={handleNewChat}>
          + New conversation
        </button>

        <div className="sidebar-scrollable-wrapper">
        <div className="sidebar-scrollable">
          <div className="sidebar-section">
            <h3 className="sidebar-section-label">Recent</h3>
          <ul className="sidebar-list">
            {(expandedRecent ? sessions : sessions.slice(0, 5)).map(s => (
              <li
                key={s.id}
                onClick={() => setActiveSessionId(s.id)}
                style={{ fontWeight: s.id === activeSessionId ? 600 : 400, color: s.id === activeSessionId ? '#111827' : '' }}
              >
                <div className="sidebar-list-item-content">
                  {s.title === "..." && s.id === activeSessionId && loadingState ? (
                    <span className="recent-placeholder">{loadingState === "reading" ? "Reading" : "Thinking"}
                      <span className="loading-dots">
                        <span>.</span><span>.</span><span>.</span>
                      </span>
                    </span>
                  ) : s.title === "..." ? (
                    <span className="recent-placeholder">...</span>
                  ) : (
                    s.title
                  )}
                </div>
                <button
                  className="delete-session-btn"
                  onClick={(e) => {
                    e.stopPropagation();
                    setSessionToDelete(s);
                  }}
                  title="Delete conversation"
                >
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                </button>
              </li>
            ))}
          </ul>
          {sessions.length > 5 && (
            <button className="expand-btn" onClick={() => setExpandedRecent(!expandedRecent)}>
              {expandedRecent ? "Show less" : "Show more"}
            </button>
          )}
        </div>

        <div className="sidebar-section">
          <h3 className="sidebar-section-label">OUR SOURCES</h3>
          <ul className="sidebar-list">
            {(expandedSources ? staticSources : staticSources.slice(0, 5)).map((src, i) => (
              <li key={i}><a href={src.href} target="_blank" rel="noreferrer">{src.label}</a></li>
            ))}
          </ul>
          {staticSources.length > 5 && (
            <button className="expand-btn" onClick={() => setExpandedSources(!expandedSources)}>
              {expandedSources ? "Show less" : "Show more"}
            </button>
          )}
        </div>
        </div>
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

          <div className="sidebar-legal-footer">
            No position is taken or endorsed. All responses draw from verified sources and filtered public discourse.
          </div>
        </div>
      </aside>

      <div className="chat-main">
        <div className="messages-scroll-wrapper">
        <div className="messages-scroll">
          {messages.length === 0 && (
            <div className="empty-state">
              <h2 className="empty-heading">What are you trying to understand?</h2>
              <div className="empty-chips">
                {[
                  "Explain the arguments for and against open-source AI models.",
                  "What's the nuance missing from modern climate policy debates?",
                  "Break down the socio-economic impacts of urban zoning laws."
                ].map((chip, idx) => (
                  <button
                    key={idx}
                    className="empty-chip"
                    onClick={() => {
                      setInput(chip);
                      if (textareaRef.current) {
                        textareaRef.current.focus();
                      }
                    }}
                  >
                    {chip}
                  </button>
                ))}
              </div>
            </div>
          )}
          {messages.map((m) => (
            <div
              key={m.id}
              className={`bubble ${m.role === "user" ? "bubble-user" : "bubble-assistant"}`}
            >
              <span className="bubble-role">
                {m.role === "user" ? "You" : <span className="bubble-brand">candid<span className="brand-dot">.</span></span>}
              </span>
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
              <span className="bubble-role"><span className="bubble-brand">candid<span className="brand-dot">.</span></span></span>
              <p className="bubble-text">
                {loadingState === "reading" ? "Reading" : "Thinking"}
                <span className="loading-dots">
                  <span>.</span><span>.</span><span>.</span>
                </span>
              </p>
            </div>
          )}
          <div ref={listEndRef} />
        </div>
        </div>

        {error && <p className="error-banner">{error}</p>}

        <form className="composer" onSubmit={handleSubmit}>
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSubmit(e);
              }
            }}
            rows={2}
            placeholder={currentPlaceholder}
            disabled={loading}
          />
          <button type="submit" disabled={loading || !input.trim()} title="Send message">
            {loading ? (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style={{ opacity: 0.5 }}>
                <path d="M5 12h14M12 5l7 7-7 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            ) : (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M5 12h14M12 5l7 7-7 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            )}
          </button>
        </form>

        <p className="composer-hint">Use Shift + Enter for a new line</p>

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
