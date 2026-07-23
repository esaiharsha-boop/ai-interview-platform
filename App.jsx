import { useState, useRef, useEffect } from "react";

const API_BASE = import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

const colors = {
  bg: "#0b0e14",
  panel: "#12161f",
  border: "#232a35",
  borderStrong: "#323b4a",
  text: "#e6edf3",
  textMuted: "#7c8794",
  accent: "#58a6ff",
  success: "#3fb950",
  warning: "#d29922",
  danger: "#f85149",
};

const mono = "'JetBrains Mono', 'SF Mono', Menlo, Consolas, monospace";
const sans = "-apple-system, 'Segoe UI', Roboto, sans-serif";

function scoreColor(score) {
  if (score == null) return colors.textMuted;
  if (score >= 7) return colors.success;
  if (score >= 4) return colors.warning;
  return colors.danger;
}

export default function App() {
  const [screen, setScreen] = useState("auth"); // auth | dashboard
  const [authMode, setAuthMode] = useState("login"); // login | signup
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [token, setToken] = useState(null);
  const [authError, setAuthError] = useState("");
  const [authLoading, setAuthLoading] = useState(false);

  const [topic, setTopic] = useState("");
  const [session, setSession] = useState(null); // { sessionId, questionId, roundNumber, maxRounds }
  const [transcript, setTranscript] = useState([]); // { type: 'question'|'answer'|'feedback', text, score, followUp }
  const [answerText, setAnswerText] = useState("");
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [summary, setSummary] = useState(null); // set when the interview ends

  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [transcript]);

  async function handleAuth(e) {
    e.preventDefault();
    setAuthError("");
    setAuthLoading(true);
    try {
      if (authMode === "signup") {
        const signupRes = await fetch(`${API_BASE}/auth/signup`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name, email, password }),
        });
        if (!signupRes.ok) {
          const errData = await signupRes.json().catch(() => ({}));
          throw new Error(errData.detail || "Signup failed");
        }
      }

      const loginRes = await fetch(`${API_BASE}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!loginRes.ok) {
        const errData = await loginRes.json().catch(() => ({}));
        throw new Error(errData.detail || "Login failed");
      }
      const data = await loginRes.json();
      setToken(data.access_token);
      setScreen("dashboard");
    } catch (err) {
      if (err.name === "TypeError" || err.message === "Load failed" || err.message === "Failed to fetch") {
        setAuthError(`Unable to connect to server at ${API_BASE}. Please ensure the backend is running.`);
      } else {
        setAuthError(err.message || "Something went wrong. Check the server is running.");
      }
    } finally {
      setAuthLoading(false);
    }
  }

  async function handleStartInterview(e) {
    e.preventDefault();
    if (!topic.trim()) return;
    setErrorMsg("");
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/interview/start`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ topic }),
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || "Could not start interview");
      }
      const data = await res.json();
      setSession({
        sessionId: data.session_id,
        questionId: data.question_id,
        roundNumber: data.round_number,
        maxRounds: data.max_rounds,
      });
      setTranscript([{ type: "question", text: data.question_text }]);
    } catch (err) {
      setErrorMsg(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleSubmitAnswer(e) {
    e.preventDefault();
    if (!answerText.trim() || !session) return;
    setErrorMsg("");
    setLoading(true);

    const submittedAnswer = answerText;
    setTranscript((t) => [...t, { type: "answer", text: submittedAnswer }]);
    setAnswerText("");

    try {
      const res = await fetch(`${API_BASE}/interview/answer`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          session_id: session.sessionId,
          question_id: session.questionId,
          answer_text: submittedAnswer,
        }),
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || "Could not submit answer");
      }
      const data = await res.json();
      setTranscript((t) => [
        ...t,
        {
          type: "feedback",
          score: data.score,
          text: data.feedback,
          followUp: data.follow_up_question,
        },
      ]);

      if (data.session_completed) {
        await loadSummary(session.sessionId);
      } else {
        setSession((s) => ({
          ...s,
          questionId: data.next_question_id,
          roundNumber: data.round_number,
        }));
      }
    } catch (err) {
      setErrorMsg(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function loadSummary(sessionId) {
    try {
      const res = await fetch(`${API_BASE}/interview/${sessionId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Could not load interview summary");
      const data = await res.json();
      setSummary(data);
    } catch (err) {
      setErrorMsg(err.message);
    }
  }

  async function handleEndInterview() {
    if (!session) return;
    setErrorMsg("");
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/interview/${session.sessionId}/end`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || "Could not end interview");
      }
      const data = await res.json();
      setSummary(data);
    } catch (err) {
      setErrorMsg(err.message);
    } finally {
      setLoading(false);
    }
  }

  function handleNewInterview() {
    setSession(null);
    setTranscript([]);
    setTopic("");
    setErrorMsg("");
    setSummary(null);
  }

  function handleLogout() {
    setToken(null);
    setScreen("auth");
    setEmail("");
    setPassword("");
    setName("");
    handleNewInterview();
  }

  const containerStyle = {
    minHeight: "100vh",
    background: colors.bg,
    color: colors.text,
    fontFamily: sans,
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    padding: "2rem 1rem",
  };

  if (screen === "auth") {
    return (
      <div style={containerStyle}>
        <div style={{ width: "100%", maxWidth: 420, marginTop: "4rem" }}>
          <div style={{ textAlign: "center", marginBottom: "2rem" }}>
            <div
              style={{
                fontFamily: mono,
                fontSize: 13,
                color: colors.accent,
                letterSpacing: 1,
                marginBottom: 8,
              }}
            >
              {"//"} ai_interview_platform
            </div>
            <h1
              style={{
                fontFamily: mono,
                fontSize: 24,
                fontWeight: 700,
                margin: 0,
                color: colors.text,
              }}
            >
              {authMode === "login" ? "sign in" : "create account"}
            </h1>
          </div>

          <div
            style={{
              background: colors.panel,
              border: `1px solid ${colors.border}`,
              borderRadius: 8,
              padding: "1.5rem",
            }}
          >
            <div style={{ display: "flex", marginBottom: "1.25rem", gap: 4 }}>
              <button
                onClick={() => setAuthMode("login")}
                style={{
                  flex: 1,
                  padding: "8px 0",
                  background: authMode === "login" ? colors.border : "transparent",
                  color: authMode === "login" ? colors.text : colors.textMuted,
                  border: "none",
                  borderRadius: 6,
                  fontFamily: mono,
                  fontSize: 13,
                  cursor: "pointer",
                }}
              >
                login
              </button>
              <button
                onClick={() => setAuthMode("signup")}
                style={{
                  flex: 1,
                  padding: "8px 0",
                  background: authMode === "signup" ? colors.border : "transparent",
                  color: authMode === "signup" ? colors.text : colors.textMuted,
                  border: "none",
                  borderRadius: 6,
                  fontFamily: mono,
                  fontSize: 13,
                  cursor: "pointer",
                }}
              >
                signup
              </button>
            </div>

            <form onSubmit={handleAuth} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {authMode === "signup" && (
                <input
                  placeholder="name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                  style={inputStyle}
                />
              )}
              <input
                type="email"
                placeholder="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                style={inputStyle}
              />
              <input
                type="password"
                placeholder="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                style={inputStyle}
              />

              {authError && (
                <div
                  style={{
                    fontFamily: mono,
                    fontSize: 12,
                    color: colors.danger,
                    borderLeft: `2px solid ${colors.danger}`,
                    paddingLeft: 8,
                  }}
                >
                  {authError}
                </div>
              )}

              <button
                type="submit"
                disabled={authLoading}
                style={{
                  marginTop: 4,
                  padding: "10px 0",
                  background: colors.accent,
                  color: "#0b0e14",
                  border: "none",
                  borderRadius: 6,
                  fontFamily: mono,
                  fontSize: 13,
                  fontWeight: 700,
                  cursor: authLoading ? "default" : "pointer",
                  opacity: authLoading ? 0.6 : 1,
                }}
              >
                {authLoading ? "working..." : authMode === "login" ? "sign in" : "create account"}
              </button>
            </form>
          </div>

          <p
            style={{
              fontFamily: mono,
              fontSize: 11,
              color: colors.textMuted,
              textAlign: "center",
              marginTop: 16,
            }}
          >
            server: {API_BASE}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div style={containerStyle}>
      <div style={{ width: "100%", maxWidth: 720 }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: "1.5rem",
          }}
        >
          <div style={{ fontFamily: mono, fontSize: 13, color: colors.accent }}>
            {"//"} ai_interview_platform
          </div>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            {session && !summary && (
              <span style={{ fontFamily: mono, fontSize: 12, color: colors.textMuted }}>
                round {session.roundNumber}/{session.maxRounds}
              </span>
            )}
            {session && !summary && (
              <button onClick={handleEndInterview} style={ghostButtonStyle}>
                end interview
              </button>
            )}
            {session && (
              <button onClick={handleNewInterview} style={ghostButtonStyle}>
                new session
              </button>
            )}
            <button onClick={handleLogout} style={ghostButtonStyle}>
              logout
            </button>
          </div>
        </div>

        {summary ? (
          <SummaryView summary={summary} />
        ) : !session ? (
          <div
            style={{
              background: colors.panel,
              border: `1px solid ${colors.border}`,
              borderRadius: 8,
              padding: "1.75rem",
            }}
          >
            <div style={{ fontFamily: mono, fontSize: 12, color: colors.textMuted, marginBottom: 12 }}>
              start_interview(topic)
            </div>
            <form onSubmit={handleStartInterview} style={{ display: "flex", gap: 8 }}>
              <input
                placeholder="e.g. binary trees, system design, SQL"
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                style={{ ...inputStyle, flex: 1 }}
              />
              <button
                type="submit"
                disabled={loading}
                style={{
                  padding: "0 20px",
                  background: colors.accent,
                  color: "#0b0e14",
                  border: "none",
                  borderRadius: 6,
                  fontFamily: mono,
                  fontSize: 13,
                  fontWeight: 700,
                  cursor: loading ? "default" : "pointer",
                  opacity: loading ? 0.6 : 1,
                }}
              >
                {loading ? "..." : "start"}
              </button>
            </form>
            {errorMsg && (
              <div
                style={{
                  fontFamily: mono,
                  fontSize: 12,
                  color: colors.danger,
                  borderLeft: `2px solid ${colors.danger}`,
                  paddingLeft: 8,
                  marginTop: 12,
                }}
              >
                {errorMsg}
              </div>
            )}
          </div>
        ) : (
          <>
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              {transcript.map((entry, i) => (
                <TranscriptEntry key={i} entry={entry} />
              ))}
              <div ref={bottomRef} />
            </div>

            <form
              onSubmit={handleSubmitAnswer}
              style={{
                marginTop: 20,
                background: colors.panel,
                border: `1px solid ${colors.border}`,
                borderRadius: 8,
                padding: "1rem",
              }}
            >
              <div style={{ fontFamily: mono, fontSize: 12, color: colors.textMuted, marginBottom: 8 }}>
                your_answer
              </div>
              <textarea
                value={answerText}
                onChange={(e) => setAnswerText(e.target.value)}
                placeholder="Type your answer here..."
                rows={4}
                style={{
                  width: "100%",
                  background: colors.bg,
                  border: `1px solid ${colors.border}`,
                  borderRadius: 6,
                  color: colors.text,
                  fontFamily: sans,
                  fontSize: 14,
                  padding: 10,
                  resize: "vertical",
                  boxSizing: "border-box",
                }}
              />
              <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 10 }}>
                <button
                  type="submit"
                  disabled={loading || !answerText.trim()}
                  style={{
                    padding: "8px 20px",
                    background: colors.accent,
                    color: "#0b0e14",
                    border: "none",
                    borderRadius: 6,
                    fontFamily: mono,
                    fontSize: 13,
                    fontWeight: 700,
                    cursor: loading ? "default" : "pointer",
                    opacity: loading || !answerText.trim() ? 0.5 : 1,
                  }}
                >
                  {loading ? "evaluating..." : "submit answer"}
                </button>
              </div>
              {errorMsg && (
                <div
                  style={{
                    fontFamily: mono,
                    fontSize: 12,
                    color: colors.danger,
                    borderLeft: `2px solid ${colors.danger}`,
                    paddingLeft: 8,
                    marginTop: 10,
                  }}
                >
                  {errorMsg}
                </div>
              )}
            </form>
          </>
        )}
      </div>
    </div>
  );
}

function SummaryView({ summary }) {
  const sc = scoreColor(summary.overall_score);
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div
        style={{
          background: colors.panel,
          border: `1px solid ${colors.border}`,
          borderLeft: `3px solid ${sc}`,
          borderRadius: 8,
          padding: "1.5rem",
        }}
      >
        <div style={{ fontFamily: mono, fontSize: 12, color: colors.textMuted, marginBottom: 8 }}>
          interview_complete
        </div>
        <div style={{ fontFamily: mono, fontSize: 28, fontWeight: 700, color: sc, marginBottom: 8 }}>
          {summary.overall_score != null ? summary.overall_score.toFixed(1) : "n/a"} / 10
        </div>
        <div style={{ fontSize: 14, color: colors.textMuted }}>
          {summary.feedback_summary || `Topic: ${summary.topic}`}
        </div>
      </div>

      <div style={{ fontFamily: mono, fontSize: 12, color: colors.textMuted, marginTop: 8 }}>
        full_transcript
      </div>

      {summary.questions.map((q, i) => (
        <div
          key={q.id}
          style={{
            background: colors.panel,
            border: `1px solid ${colors.border}`,
            borderRadius: 8,
            padding: "1rem 1.25rem",
            display: "flex",
            flexDirection: "column",
            gap: 10,
          }}
        >
          <div style={{ fontFamily: mono, fontSize: 12, color: colors.accent }}>
            q{i + 1} {"$"} {q.question_text}
          </div>
          {q.user_answer && (
            <div style={{ fontSize: 14, color: colors.text, paddingLeft: 12, borderLeft: `2px solid ${colors.border}` }}>
              {q.user_answer}
            </div>
          )}
          {q.score != null && (
            <div style={{ fontFamily: mono, fontSize: 12, fontWeight: 700, color: scoreColor(q.score) }}>
              score → {q.score}/10
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function TranscriptEntry({ entry }) {
  if (entry.type === "question") {
    return (
      <div
        style={{
          background: colors.panel,
          border: `1px solid ${colors.border}`,
          borderRadius: 8,
          padding: "1rem 1.25rem",
        }}
      >
        <div style={{ fontFamily: mono, fontSize: 12, color: colors.accent, marginBottom: 6 }}>
          interviewer $
        </div>
        <div style={{ fontSize: 15, lineHeight: 1.5 }}>{entry.text}</div>
      </div>
    );
  }

  if (entry.type === "answer") {
    return (
      <div
        style={{
          background: "transparent",
          border: `1px solid ${colors.border}`,
          borderRadius: 8,
          padding: "1rem 1.25rem",
          marginLeft: 24,
        }}
      >
        <div style={{ fontFamily: mono, fontSize: 12, color: colors.textMuted, marginBottom: 6 }}>
          you {">"}
        </div>
        <div style={{ fontSize: 15, lineHeight: 1.5, color: colors.text }}>{entry.text}</div>
      </div>
    );
  }

  const sc = scoreColor(entry.score);
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <div
        style={{
          background: colors.panel,
          border: `1px solid ${colors.border}`,
          borderLeft: `3px solid ${sc}`,
          borderRadius: 8,
          padding: "1rem 1.25rem",
        }}
      >
        <div
          style={{
            fontFamily: mono,
            fontSize: 13,
            fontWeight: 700,
            color: sc,
            marginBottom: 8,
          }}
        >
          score → {entry.score != null ? `${entry.score}/10` : "n/a"}
        </div>
        <div style={{ fontSize: 14, lineHeight: 1.6, color: colors.text }}>{entry.text}</div>
      </div>

      {entry.followUp && (
        <div
          style={{
            background: colors.panel,
            border: `1px solid ${colors.border}`,
            borderRadius: 8,
            padding: "1rem 1.25rem",
          }}
        >
          <div style={{ fontFamily: mono, fontSize: 12, color: colors.warning, marginBottom: 6 }}>
            interviewer (follow-up) $
          </div>
          <div style={{ fontSize: 15, lineHeight: 1.5 }}>{entry.followUp}</div>
        </div>
      )}
    </div>
  );
}

const inputStyle = {
  width: "100%",
  background: colors.bg,
  border: `1px solid ${colors.border}`,
  borderRadius: 6,
  color: colors.text,
  fontFamily: sans,
  fontSize: 14,
  padding: "10px 12px",
  boxSizing: "border-box",
  outline: "none",
};

const ghostButtonStyle = {
  padding: "6px 14px",
  background: "transparent",
  color: colors.textMuted,
  border: `1px solid ${colors.border}`,
  borderRadius: 6,
  fontFamily: mono,
  fontSize: 12,
  cursor: "pointer",
};
