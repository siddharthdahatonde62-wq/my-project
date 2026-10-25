# CampusProof
Offline, citation-first AI assistant for college documents (RAG).
**Open-weight model:** Qwen2.5 (3B) via Ollama · **Embeddings:** nomic-embed-text · **Vector DB:** ChromaDB · **API:** FastAPI

## Run
```bash
ollama pull qwen2.5:3b && ollama pull nomic-embed-text
cd backend
python -m venv venv && source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --reload --port 8000
```
Open http://localhost:8000/docs for the interactive API, `GET /health` to verify models.
If a `frontend/` folder exists next to `backend/`, it is served at http://localhost:8000/.

## API
| Method | Path | Purpose |
|---|---|---|
| POST | `/upload` | Upload PDFs (multipart, field `files`) |
| POST | `/ask` | `{"question": "..."}` -> answer + sources (+ `?debug=true`) |
| GET | `/documents`, DELETE `/documents/{name}` | Library |
| GET | `/documents/{name}/file#page=N` | Open the original PDF |
| GET | `/documents/{name}/pages/{n}` | Page text for the source panel |
| POST | `/checklist` | `{"topic": "scholarship"}` -> cited checklist |
| GET | `/deadlines`, `/deadlines/ics?id=` | Extracted deadlines, calendar download |
| GET | `/suggestions` | Suggested questions |
| POST | `/feedback` | Helpful / not helpful |

## How hallucinations are prevented
1. Retrieval gate: below `MIN_SIMILARITY` -> refuse without calling the LLM.
2. Strict prompt: context-only, numbered passages, mandatory citations, exact refusal sentence.
3. Citation mapping: `[n]` markers become real `[file, page]` references.
4. Number check: figures in the answer must appear in the cited text, otherwise the answer is flagged `verified: false`.

## Evaluate
`python evaluate.py tests.json` (edit `tests.json` for your PDFs).

MIT licensed.
