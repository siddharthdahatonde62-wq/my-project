"""ChromaDB storage + hybrid (vector + keyword) retrieval."""
import re
import chromadb
from config import CHROMA_DIR, CANDIDATES, UPLOAD_DIR
from embeddings import embed

_client = chromadb.PersistentClient(path=str(CHROMA_DIR))
_col = _client.get_or_create_collection("campusproof", metadata={"hnsw:space": "cosine"})

STOP = set("""a an the is are was were be been of to in on at for and or but if what which who whom when where
why how do does did can could should would will shall may might i me my we you your it its this that these
those with from by as about into than then there their they them have has had not no any all""".split())


def keywords(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9%]+", text.lower()) if w not in STOP and len(w) > 1}


def count() -> int:
    return _col.count()


def delete_file(name: str) -> None:
    _col.delete(where={"file": name})


def add_chunks(chunks: list[dict]) -> int:
    if not chunks:
        return 0
    vectors = embed([c["text"] for c in chunks], "document")
    for i in range(0, len(chunks), 200):
        part = chunks[i:i + 200]
        _col.upsert(
            ids=[c["id"] for c in part],
            embeddings=vectors[i:i + 200],
            documents=[c["text"] for c in part],
            metadatas=[{"file": c["file"], "page": c["page"], "chunk": c["chunk"]} for c in part],
        )
    return len(chunks)


def search(question: str, k: int) -> list[dict]:
    n = _col.count()
    if n == 0:
        return []
    qv = embed([question], "query")[0]
    res = _col.query(query_embeddings=[qv], n_results=min(CANDIDATES, n),
                     include=["documents", "metadatas", "distances"])
    q_words = keywords(question)
    hits = []
    for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
        sim = 1.0 - dist
        lex = len(q_words & keywords(doc)) / len(q_words) if q_words else 0.0
        hits.append({"file": meta["file"], "page": meta["page"], "text": doc,
                     "similarity": sim, "lexical": lex, "score": 0.75 * sim + 0.25 * lex})
    hits.sort(key=lambda h: h["score"], reverse=True)
    return hits[:k]


def all_chunks() -> list[dict]:
    res = _col.get(include=["documents", "metadatas"])
    return [{"file": m["file"], "page": m["page"], "text": d}
            for d, m in zip(res["documents"], res["metadatas"])]


def list_documents() -> list[dict]:
    res = _col.get(include=["metadatas"])
    docs: dict[str, dict] = {}
    for m in res["metadatas"]:
        d = docs.setdefault(m["file"], {"file": m["file"], "chunks": 0, "pages": 0})
        d["chunks"] += 1
        d["pages"] = max(d["pages"], m["page"])
    for name, d in docs.items():
        p = UPLOAD_DIR / name
        d["size_bytes"] = p.stat().st_size if p.exists() else None
        d["status"] = "ready"
    return sorted(docs.values(), key=lambda d: d["file"].lower())
