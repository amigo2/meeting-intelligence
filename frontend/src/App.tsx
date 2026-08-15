import { useState, type FormEvent } from "react";
import { loadSample, ask, type Intelligence, type AskResult } from "./api";
import "./App.css";

const MEETING = "demo-1";

type Turn = { q: string; a: AskResult };

export default function App() {
  const [intel, setIntel] = useState<Intelligence | null>(null);
  const [loading, setLoading] = useState(false);
  const [question, setQuestion] = useState("");
  const [chat, setChat] = useState<Turn[]>([]);
  const [asking, setAsking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleLoad(sample: string) {
    setLoading(true);
    setIntel(null);
    setChat([]);
    setError(null);
    try {
      const res = await loadSample(MEETING, sample);
      setIntel(res.intelligence);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  async function handleAsk(e: FormEvent) {
    e.preventDefault();
    const q = question.trim();
    if (!q) return;
    setQuestion("");
    setAsking(true);
    try {
      const a = await ask(MEETING, q);
      setChat((c) => [...c, { q, a }]);
    } catch (err) {
      setError(String(err));
    } finally {
      setAsking(false);
    }
  }

  return (
    <div className="app">
      <header className="topbar">
        <h1>🎙️ Meeting Intelligence</h1>
        <div className="samples">
          <button onClick={() => handleLoad("meeting")} disabled={loading}>
            Product meeting
          </button>
          <button onClick={() => handleLoad("realestate")} disabled={loading}>
            Real-estate call
          </button>
        </div>
      </header>

      {error && <p className="error">{error}</p>}
      {loading && <p className="hint">Analysing transcript…</p>}
      {!intel && !loading && (
        <p className="hint">Load a sample transcript to see the intelligence.</p>
      )}

      {intel && (
        <div className="grid">
          <section className="panel">
            <h2>📋 Summary</h2>
            <p className="summary">{intel.summary}</p>

            <h2>🎯 Decisions</h2>
            <ul className="decisions">
              {intel.decisions.map((d, i) => (
                <li key={i}>{d}</li>
              ))}
            </ul>

            <h2>✅ Action items</h2>
            <ul className="actions">
              {intel.action_items.map((a, i) => (
                <li key={i}>
                  <span className="owner">{a.owner}</span>
                  <span className="task">{a.task}</span>
                  {a.due && <span className="due">{a.due}</span>}
                </li>
              ))}
            </ul>
          </section>

          <section className="panel">
            <h2>💬 Ask about this meeting</h2>
            <div className="chat">
              {chat.length === 0 && !asking && (
                <p className="hint small">
                  Try “When is the launch?” or “What did the seller object to?”
                </p>
              )}
              {chat.map((t, i) => (
                <div key={i} className="turn">
                  <div className="bubble q">{t.q}</div>
                  <div className="bubble a">
                    {t.a.answer}
                    {t.a.verification &&
                      (t.a.verification.grounded ? (
                        <span className="trust ok" title="Every claim is supported by the transcript.">
                          ✓ Verified · grounded in transcript
                        </span>
                      ) : (
                        <span
                          className="trust warn"
                          title={
                            "Unsupported: " +
                            [
                              ...t.a.verification.unsupported,
                              ...t.a.verification.fabricated_citations.map(
                                (ts) => `invented citation ${ts}`
                              ),
                            ].join("; ")
                          }
                        >
                          ⚠ Unverified · may contain unsupported claims
                        </span>
                      ))}
                  </div>
                </div>
              ))}
              {asking && <div className="hint small">Thinking…</div>}
            </div>
            <form className="ask" onSubmit={handleAsk}>
              <input
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="Ask a question…"
              />
              <button disabled={asking}>Ask</button>
            </form>
          </section>
        </div>
      )}
    </div>
  );
}
