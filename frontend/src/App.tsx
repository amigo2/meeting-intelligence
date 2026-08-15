import { useState, type FormEvent } from "react";
import { loadSample, ask, type Intelligence, type AskResult } from "./api";
import "./App.css";

const MEETING = "demo-1";

type Turn = { q: string; a: AskResult };

// The transcripts the demo can load. `tricky` is adversarial — engineered to bait
// hallucinations so the grounding guardrail can be seen doing its job.
const SAMPLES: { id: string; label: string; adversarial?: boolean }[] = [
  { id: "meeting", label: "Product meeting" },
  { id: "realestate", label: "Real-estate call" },
  { id: "tricky", label: "🎯 Tricky transcript", adversarial: true },
];

// Suggested questions per transcript. For `tricky` these are the six traps from the
// robustness eval — each has a plausible wrong answer the transcript tempts you toward.
const SUGGESTIONS: Record<string, string[]> = {
  meeting: ["When is the launch?", "What did Carla commit to?", "What's the refund bug?"],
  realestate: [
    "What did Elena object to?",
    "What did they agree on?",
    "What documents does Elena need to gather?",
  ],
  tricky: [
    "What is the launch date?",
    "What is the campaign budget?",
    "What is the launch user target?",
    "Who owns the onboarding rebuild?",
    "Which analytics vendor did they choose?",
    "What is the price of the mobile app?",
  ],
};

export default function App() {
  const [intel, setIntel] = useState<Intelligence | null>(null);
  const [loaded, setLoaded] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [question, setQuestion] = useState("");
  const [chat, setChat] = useState<Turn[]>([]);
  const [asking, setAsking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isAdversarial = SAMPLES.find((s) => s.id === loaded)?.adversarial ?? false;

  async function handleLoad(sample: string) {
    setLoading(true);
    setIntel(null);
    setChat([]);
    setError(null);
    setLoaded(sample);
    try {
      const res = await loadSample(MEETING, sample);
      setIntel(res.intelligence);
    } catch (e) {
      setError(String(e));
      setLoaded(null); // don't leave a button highlighted for a load that failed
    } finally {
      setLoading(false);
    }
  }

  async function submitQuestion(q: string) {
    const trimmed = q.trim();
    if (!trimmed || asking) return;
    // Only clear the input if we're submitting what's in it — a suggestion chip must not
    // wipe text the user has half-typed.
    setQuestion((cur) => (cur.trim() === trimmed ? "" : cur));
    setAsking(true);
    try {
      const a = await ask(MEETING, trimmed);
      setChat((c) => [...c, { q: trimmed, a }]);
    } catch (err) {
      setError(String(err));
    } finally {
      setAsking(false);
    }
  }

  function handleAsk(e: FormEvent) {
    e.preventDefault();
    submitQuestion(question);
  }

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <h1>🎙️ Meeting Intelligence</h1>
          {/* Quality signal: what our offline evals measured. Details in docs/EVALUATION.md */}
          <a
            className="evalchip"
            href="https://github.com/amigo2/meeting-intelligence/blob/main/docs/EVALUATION.md"
            target="_blank"
            rel="noreferrer"
            title="Measured offline: 93% claim-level faithfulness, and 6/6 adversarial traps handled. See docs/EVALUATION.md."
          >
            🔬 Evaluated · 93% faithful · 6/6 traps
          </a>
        </div>
        <div className="samples">
          {SAMPLES.map((s) => (
            <button
              key={s.id}
              onClick={() => handleLoad(s.id)}
              disabled={loading}
              className={loaded === s.id ? "active" : ""}
            >
              {s.label}
            </button>
          ))}
        </div>
      </header>

      {error && <p className="error">{error}</p>}
      {loading && <p className="hint">Analysing transcript…</p>}
      {!intel && !loading && (
        <p className="hint">Load a sample transcript to see the intelligence — or try the 🎯 tricky one to test the AI's honesty.</p>
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

            {isAdversarial && (
              <div className="bait">
                🎯 <strong>Hallucination test drive.</strong> This transcript is booby-trapped —
                each question below has a <em>plausible but wrong</em> answer baked in. A grounded
                system gives the real answer (or refuses). Watch the badge under each reply.
              </div>
            )}

            <div className="suggest">
              <span className="suggest-label">
                {isAdversarial ? "Try to trick it:" : "Try asking:"}
              </span>
              {(SUGGESTIONS[loaded ?? ""] ?? []).map((q) => (
                <button key={q} className="chip" onClick={() => submitQuestion(q)} disabled={asking}>
                  {q}
                </button>
              ))}
            </div>

            <div className="chat">
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
                        <div className="trust-block">
                          <span className="trust warn">⚠ Unverified · some claims unsupported</span>
                          {t.a.verification.unsupported.map((u, j) => (
                            <div key={j} className="trust-detail">• {u}</div>
                          ))}
                          {t.a.verification.fabricated_citations.map((ts, j) => (
                            <div key={`c${j}`} className="trust-detail">• invented citation [{ts}]</div>
                          ))}
                        </div>
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
