# Evidence Desk

A source-first retrieval workbench for a small collection of operational documents. It ranks passages with BM25, extracts a sentence from the best passage, and exposes the source ID, paragraph, matching terms, and score.

## Run locally

Use Python 3.11+ and Node.js 24 with npm. Python has no third-party dependencies. From the cloned repository root:

```sh
cd frontend
npm ci
npm run build
cd ..
python3 backend/server.py
```

Open http://localhost:8313. On Windows, use `py` in place of `python3`. The Python server serves both the compiled React app and the REST API. No API keys, downloaded model weights, or paid services are needed. The first npm install requires internet access.

For frontend development, keep the Python server running and use a second terminal:

```sh
cd frontend
npm run dev
```

Vite runs at http://localhost:8413 and proxies `/api` to the Python server. Set `PORT` to change the backend port; update `frontend/vite.config.ts` if you also use the development proxy. The backend binds to localhost by default.

## Try it

1. Search for “How are inference requests retried?” and inspect the extracted source sentence.
2. Follow its citation to the ranked passage.
3. Try “volcano penguin orbital”. The app abstains because the collection has no matching evidence.
4. Expand **Edit the collection**, replace the JSON documents, and search again.

A document contains `title` and `text`; blank lines separate paragraphs. Titles must be unique. The collection accepts 1–100 documents with up to 50,000 characters each, subject to the 2 MB API request limit. Queries are limited to 500 characters.

## How it works

`backend/domain.py` splits paragraphs into 120-word passages with a 20-word overlap. Passage IDs hash the title, paragraph position, offset, and text, making citations repeatable for an unchanged collection.

The ranker uses BM25 with `k1=1.5` and `b=0.75`. Tokenization is lowercase alphanumeric matching with a short stop-word list and a small explicit inflection map (for example, `retried` and `retries` become `retry`). Query coverage measures how many unique query terms appear in the top passage. Below 50% coverage, the app abstains from extracting an answer.

An answer is an existing sentence, selected by query-term overlap. No generative model is called. This makes a useful retrieval baseline and keeps citations inspectable, but coverage is a heuristic, not a factuality guarantee. Lexical search misses synonyms and semantic paraphrases.

The collection is stored in memory and rebuilt per query, which is intentionally simple for these limits. Restarting restores `data/documents.json`. For a larger collection, persist a precomputed index and add retrieval evaluation cases.

The frontend is React and TypeScript; Vite builds static assets. The Python standard-library HTTP server validates JSON requests, limits payloads to 2 MB, and emits request-duration logs. Errors appear inline in the interface. React renders user text as text rather than HTML.

## API

`GET /api/health` returns a liveness check. `GET /api/state` returns the current dashboard state.

```text
POST /api/search
{"query":"invalid records quarantine","limit":5}

POST /api/documents
{"documents":[{"title":"My runbook","text":"Retry transient failures once."}]}
```

POST endpoints expect `Content-Type: application/json`. Invalid inputs return HTTP 400 with an `error` field. Oversized requests return 413. These endpoints have no authentication and are intended for local use; the standard-library server is not a production ingress server.

## Checks

```sh
python3 -m unittest discover -s backend -p 'test_*.py' -v
cd frontend
npm ci
npm run build
```

Tests exercise domain behavior and HTTP validation. The frontend build includes strict TypeScript checking. GitHub Actions runs both on pushes and pull requests.

## Docker

```sh
docker build -t evidence-desk .
docker run --rm -p 127.0.0.1:8313:8313 evidence-desk
```

The image builds the frontend and serves it from Python under a non-root user. Docker is optional.

## Platform engineering focus

The workbench demonstrates the retrieval layer of a RAG workflow, REST integration, evidence inspection, and cautious fallback behavior. Embeddings and a cited generation adapter would be natural extensions, evaluated separately from retrieval.

## Layout

```text
backend/                 API server, domain logic, and tests
frontend/src/            React interface and styles
frontend/package-lock.json  Reproducible dependency installation
data/                    Bundled fixtures
.github/workflows/       Build and test checks
```

MIT licensed. See `LICENSE`.
