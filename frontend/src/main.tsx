import { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./style.css";
interface Document {
  title: string;
  text: string;
}
interface Passage {
  id: string;
  title: string;
  paragraph: number;
  text: string;
  score: number;
  matched: string[];
}
interface Result {
  query: string;
  hits: Passage[];
  coverage: number;
  answer: {
    text: string;
    citation: string;
    title: string;
    paragraph: number;
  } | null;
  reason: string;
}
interface Dashboard {
  documents: Document[];
  passages: number;
  examples: string[];
}
type Api = { state: Dashboard; search: Result; documents: Dashboard };
type Action = Exclude<keyof Api, "state">;
async function api<K extends keyof Api>(
  path: K,
  body?: Record<string, unknown>,
): Promise<Api[K]> {
  const response = await fetch(
    `/api/${path}`,
    body
      ? {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        }
      : undefined,
  );
  const value = await response.json();
  if (!response.ok) throw new Error(value.error || "Request failed");
  return value;
}
function Stat({ value, label }: { value: string | number; label: string }) {
  return (
    <div className="stat">
      <b>{value}</b>
      <span>{label}</span>
    </div>
  );
}
function App() {
  const [state, setState] = useState<Partial<Dashboard>>({});
  const [result, setResult] = useState<Result | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    api("state")
      .then(setState)
      .catch((e) => setError(e.message));
  }, []);
  async function run(path: Action, body: Record<string, unknown>) {
    setBusy(true);
    setError("");
    try {
      const data = await api(path, body);
      setResult(path === "search" ? (data as Result) : null);
      setState(await api("state"));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setBusy(false);
    }
  }
  const [query, setQuery] = useState("How are inference requests retried?");
  const [source, setSource] = useState<string | null>(null);
  function reindex() {
    try {
      void run("documents", {
        documents: JSON.parse(source ?? JSON.stringify(state.documents)),
      });
    } catch {
      setError("Documents must be valid JSON");
    }
  }
  return (
    <>
      <header>
        <strong>Evidence Desk</strong>
        <span>Retrieval workbench / source inspection</span>
      </header>
      <main>
        <div className="eyebrow">Search · cite · abstain</div>
        <h1>Every answer has a paper trail.</h1>
        <p>
          A local BM25 retrieval workbench. Answers are source sentences, with
          passage IDs you can inspect.
        </p>
        <div className="stats">
          <Stat
            value={state.documents?.length || 0}
            label="Documents in the collection"
          />
          <Stat value={state.passages || 0} label="Indexed passages" />
          <Stat
            value={
              result?.coverage !== undefined
                ? `${(result.coverage * 100).toFixed(0)}%`
                : "—"
            }
            label="Top passage query coverage"
          />
        </div>
        <div className="grid">
          <section className="panel">
            <h2>Ask the collection</h2>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                void run("search", { query });
              }}
            >
              <label htmlFor="query">Question or search terms</label>
              <input
                id="query"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                maxLength={500}
              />
              <div className="row">
                <button disabled={busy || !state.documents}>
                  {busy ? "Working…" : "Find evidence"}
                </button>
              </div>
            </form>
            <div className="row">
              {state.examples?.map((q: string) => (
                <button
                  className="secondary"
                  key={q}
                  onClick={() => setQuery(q)}
                >
                  {q}
                </button>
              ))}
            </div>
            <details style={{ marginTop: 30 }}>
              <summary>Edit the collection</summary>
              <label htmlFor="docs">Documents · title and text</label>
              <textarea
                id="docs"
                value={source ?? JSON.stringify(state.documents || [], null, 2)}
                onChange={(e) => setSource(e.target.value)}
              />
              <div className="row">
                <button disabled={busy} onClick={reindex}>
                  Replace collection
                </button>
              </div>
              <p>Collection edits last for this server session.</p>
            </details>
          </section>
          <section className="panel">
            <h2>Evidence-backed extract</h2>
            {result?.hits ? (
              <>
                <p>{result.reason}</p>
                {result.answer && (
                  <div className="passage">
                    <p>{result.answer.text}</p>
                    <a href={`#${result.answer.citation}`}>
                      {result.answer.title} · paragraph{" "}
                      {result.answer.paragraph} ↗
                    </a>
                  </div>
                )}
                <h2 style={{ marginTop: 28 }}>Ranked passages</h2>
                {result.hits.map((h) => (
                  <article className="passage" id={h.id} key={h.id}>
                    <span className="badge">
                      BM25 {h.score.toFixed(3)} · {h.id}
                    </span>
                    <h3>
                      {h.title} / ¶{h.paragraph}
                    </h3>
                    <p>{h.text}</p>
                    <span className="muted">
                      Matched: {h.matched.join(", ")}
                    </span>
                  </article>
                ))}
                {!result.hits.length && (
                  <p>
                    No matching passages. Try terms that occur in the
                    collection.
                  </p>
                )}
              </>
            ) : (
              <p>
                Search the runbooks to inspect scores, matching terms, and
                source citations.
              </p>
            )}
          </section>
        </div>
        {error && (
          <p role="alert" className="error">
            {error}
          </p>
        )}
        <footer>
          Lexical retrieval · 120-word chunks · 20-word overlap · no external
          services
        </footer>
      </main>
    </>
  );
}
createRoot(document.getElementById("root")!).render(<App />);
