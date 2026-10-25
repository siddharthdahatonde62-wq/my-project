"""CampusProof API.  Run from this folder:  uvicorn app:app --reload --port 8000"""
import json
import shutil
import time
from pathlib import Path

import httpx
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import deadlines as dl
import rag_chain
import vector_store as vs
from config import (EMBED_MODEL, FEEDBACK_FILE, FRONTEND_DIR, LLM_MODEL,
                    OLLAMA_URL, UPLOAD_DIR)
from embeddings import OllamaError
from pdf_loader import build_chunks, load_pdf, read_page

app = FastAPI(title="CampusProof API", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.exception_handler(OllamaError)
async def ollama_down(_, exc: OllamaError):
    return JSONResponse(status_code=503, content={"detail": str(exc)})


def safe_name(name: str) -> str:
    return Path(name).name


# ---------------------------------------------------------------- health
@app.get("/health")
def health():
    missing, ollama_ok = [], False
    try:
        tags = httpx.get(f"{OLLAMA_URL}/api/tags", timeout=3).json()
        have = {m["name"] for m in tags.get("models", [])}
        ollama_ok = True
        for want in (LLM_MODEL, EMBED_MODEL):
            if not any(h == want or h.startswith(want + ":") or h.split(":")[0] == want for h in have):
                missing.append(want)
    except Exception:
        pass
    return {"status": "ok" if ollama_ok and not missing else "degraded",
            "model": LLM_MODEL, "embedding_model": EMBED_MODEL, "ollama": ollama_ok,
            "models_missing": missing,
            "vector_store": "ready" if vs.count() else "empty",
            "documents": len(vs.list_documents()), "chunks": vs.count()}


# ---------------------------------------------------------------- documents
@app.post("/upload")
def upload(files: list[UploadFile] = File(...)):
    processed, total_chunks, details, errors = 0, 0, [], []
    for f in files:
        name = safe_name(f.filename or "")
        if not name.lower().endswith(".pdf"):
            errors.append({"file": name, "error": "Only PDF files are supported."})
            continue
        dest = UPLOAD_DIR / name
        with dest.open("wb") as out:
            shutil.copyfileobj(f.file, out)
        try:
            pages = load_pdf(dest)
            if not pages:
                errors.append({"file": name, "error": "No selectable text found (scanned PDF?). OCR is not supported yet."})
                continue
            vs.delete_file(name)  # re-uploading replaces the old version
            n = vs.add_chunks(build_chunks(name, pages))
        except OllamaError:
            raise
        except Exception as e:
            errors.append({"file": name, "error": f"Could not read PDF: {e}"})
            continue
        processed += 1
        total_chunks += n
        details.append({"file": name, "pages": len(pages), "chunks": n})
    return {"status": "success" if processed else "failed", "files_processed": processed,
            "chunks_created": total_chunks, "details": details, "errors": errors}


@app.get("/documents")
def documents():
    return {"documents": vs.list_documents()}


@app.delete("/documents/{name}")
def delete_document(name: str):
    name = safe_name(name)
    vs.delete_file(name)
    (UPLOAD_DIR / name).unlink(missing_ok=True)
    return {"status": "deleted", "file": name}


@app.get("/documents/{name}/file")
def document_file(name: str):
    """Open at a page in the browser viewer: /documents/X.pdf/file#page=7"""
    p = UPLOAD_DIR / safe_name(name)
    if not p.exists():
        raise HTTPException(404, "Document not found")
    return FileResponse(p, media_type="application/pdf")


@app.get("/documents/{name}/pages/{page}")
def document_page(name: str, page: int):
    """Full text of one page, for the 'source panel' beside the answer."""
    p = UPLOAD_DIR / safe_name(name)
    if not p.exists():
        raise HTTPException(404, "Document not found")
    try:
        return {"file": p.name, "page": page, "text": read_page(p, page)}
    except IndexError:
        raise HTTPException(404, "Page out of range")


# ---------------------------------------------------------------- Q&A
class AskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=500)


@app.post("/ask")
def ask(req: AskRequest, debug: bool = Query(False)):
    t0 = time.time()
    result = rag_chain.ask(req.question, debug=debug)
    result["latency_ms"] = int((time.time() - t0) * 1000)
    return result


SUGGESTIONS = {
    "exam": ["What are the exam rules?", "What is the minimum attendance needed for exams?"],
    "attend": ["What is the minimum attendance required?"],
    "hostel": ["What are the hostel timings?", "What are the hostel rules?"],
    "scholar": ["Which documents are required for the scholarship?", "When is the scholarship form due?"],
    "lab": ["What are the lab safety rules?"],
    "time": ["When is the next exam?"],
    "leave": ["How do I apply for leave?"],
}


@app.get("/suggestions")
def suggestions():
    names = " ".join(d["file"].lower() for d in vs.list_documents())
    out = [q for key, qs in SUGGESTIONS.items() if key in names for q in qs]
    return {"suggestions": out[:6] or ["What are the exam rules?", "What are the hostel timings?",
                                       "What documents are required for the scholarship?"]}


class ChecklistRequest(BaseModel):
    topic: str = Field(min_length=2, max_length=200)


@app.post("/checklist")
def checklist(req: ChecklistRequest):
    return rag_chain.checklist(req.topic)


# ---------------------------------------------------------------- deadlines
@app.get("/deadlines")
def deadlines(upcoming_only: bool = True, include_events: bool = False):
    items = dl.extract(vs.all_chunks(), upcoming_only=upcoming_only, deadlines_only=not include_events)
    return {"deadlines": items, "count": len(items)}


@app.get("/deadlines/ics")
def deadlines_ics(id: str | None = None):
    items = dl.extract(vs.all_chunks())
    if id:
        items = [i for i in items if i["id"] == id]
        if not items:
            raise HTTPException(404, "Deadline not found")
    return Response(dl.to_ics(items), media_type="text/calendar",
                    headers={"Content-Disposition": 'attachment; filename="campusproof.ics"'})


# ---------------------------------------------------------------- feedback
class Feedback(BaseModel):
    question: str
    answer: str = ""
    helpful: bool


@app.post("/feedback")
def feedback(fb: Feedback):
    with FEEDBACK_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps({**fb.model_dump(), "ts": time.time()}) + "\n")
    return {"status": "saved"}


# Serve the frontend from the same origin if the folder exists (no CORS headaches at the demo).
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
