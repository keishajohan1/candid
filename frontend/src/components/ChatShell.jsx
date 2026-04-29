import { useEffect, useMemo, useRef, useState } from "react";
import { sendChatMessage } from "../services/api";

const PLACEHOLDERS = [
  "What are you trying to understand...",
  "What's something you've been trying to make sense of...",
  "Something you've heard but never fully understood...",
  "What's the version of this story you haven't heard...",
  "What's the part of this you can't quite explain...",
  "Ask the question behind the question..."
];

export default function ChatShell() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [error, setError] = useState("");
  const [loadingState, setLoadingState] = useState(null);
  const loading = loadingState !== null;
  const listEndRef = useRef(null);
  const textareaRef = useRef(null);

  const currentPlaceholder = useMemo(
    () => PLACEHOLDERS[Math.floor(Math.random() * PLACEHOLDERS.length)],
    []
  );

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [input]);

  useEffect(() => {
    listEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const turnIndex = messages.filter((m) => m.role === "assistant").length + 1;

  const renderMessageContent = (content) => {
    if (!content) return null;
    const parts = content.split(/(\*(?!\*)[^*]+\*|_(?!_)[^_]+_|\[\d+\])/g);
    return parts.map((part, i) => {
      if (!part) return null;
      if ((part.startsWith("*") && part.endsWith("*")) || (part.startsWith("_") && part.endsWith("_"))) {
        return <em key={i}>{part.slice(1, -1)}</em>;
      }
      if (/^\[\d+\]$/.test(part)) {
        return (
          <sup key={i} className="citation-superscript">
            {part}
          </sup>
        );
      }
      return part;
    });
  };

  async function handleSubmit(event) {
    event.preventDefault();
    const text = input.trim();
    if (!text || loading) return;

    const userHistory = messages.filter((m) => m.role === "user").map((m) => m.content);

    setLoadingState("reading");
    setError("");
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: text, id: `${Date.now()}-u` }]);

    const readTimer = setTimeout(() => {
      setLoadingState("thinking");
    }, 2200);

    try {
      const data = await sendChatMessage({
        message: text,
        turn_index: turnIndex,
        history: userHistory
      });

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.response_text,
          id: `${Date.now()}-a`,
          sources: data.sources ?? []
        }
      ]);
    } catch (err) {
      setError(err.message || "Request failed.");
    } finally {
      clearTimeout(readTimer);
      setLoadingState(null);
    }
  }

  return (
    <div className="chat-main">
      <div className="messages-scroll-wrapper">
        <div className="messages-scroll">
          {messages.map((m) => (
            <div key={m.id} className={`bubble ${m.role === "user" ? "bubble-user" : "bubble-assistant"}`}>
              <span className="bubble-role">
                {m.role === "user" ? "You" : <span className="bubble-brand">candid<span className="brand-dot">.</span></span>}
              </span>
              <p className="bubble-text">{renderMessageContent(m.content)}</p>
              {m.role === "assistant" && m.sources && m.sources.length > 0 && (
                <div className="bubble-sources">
                  {m.sources.map((s, i) => (
                    <span key={i} className="bubble-source">
                      [{i + 1}] {s.label || s.source}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}
          {loading && (
            <div className="bubble bubble-assistant loading-bubble">
              <span className="bubble-role">
                <span className="bubble-brand">candid<span className="brand-dot">.</span></span>
              </span>
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
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M5 12h14M12 5l7 7-7 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
      </form>
    </div>
  );
}
