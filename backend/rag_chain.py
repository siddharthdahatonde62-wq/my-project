"""Retrieve -> gate -> generate -> verify. Every answer is tied to exact source chunks."""
import re
import httpx
from config import OLLAMA_URL, LLM_MODEL, TOP_K, MIN_SIMILARITY
from embeddings import OllamaError
import vector_store as vs
from pdf_loader import split_sentences

NOT_FOUND = "I could not find this information in the provided documents."

SYSTEM = f"""You are CampusProof, a college document assistant.
Rules:
1. Answer ONLY using the numbered context passages. Never use outside knowledge.
2. If the answer is not clearly stated in the passages, reply with exactly: {NOT_FOUND}
3. Never invent rules, dates, numbers, names or policies.
4. After every sentence, cite the passage(s) it came from, like [1] or [2][3].
5. Keep the answer short, clear and student-friendly (max 4 sentences). Copy numbers and dates exactly."""


def chat(messages: list[dict]) -> str:
    try:
        r = httpx.post(f"{OLLAMA_URL}/api/chat", timeout=300, json={
            "model": LLM_MODEL, "messages": messages, "stream": False,
            "options": {"temperature": 0, "num_ctx": 4096}})
        r.raise_for_status()
        return r.json()["message"]["content"].strip()
    except httpx.ConnectError:
        raise OllamaError("Cannot reach Ollama. Start it with `ollama serve`.")
    except httpx.HTTPStatusError as e:
        raise OllamaError(f"Ollama error: {e.response.text[:200]} "
                          f"(did you run `ollama pull {LLM_MODEL}`?)")


def format_context(hits: list[dict]) -> str:
    return "\n\n".join(f"[{i}] ({h['file']}, page {h['page']})\n{h['text']}"
                       for i, h in enumerate(hits, 1))


def best_sentence(chunk: str, query: str) -> str:
    q = vs.keywords(query)
    sentences = split_sentences(chunk) or [chunk]
    return max(sentences, key=lambda s: len(q & vs.keywords(s)))


def _numbers(text: str) -> set[str]:
    return set(re.findall(r"\d+(?:\.\d+)?", text))


def not_found(reason: str, message: str = NOT_FOUND, **extra) -> dict:
    return {"answer": message, "found": False, "reason": reason, "sources": [], **extra}


def ask(question: str, debug: bool = False) -> dict:
    if vs.count() == 0:
        return not_found("no_documents", "Please upload your college documents first, then ask again.")

    hits = vs.search(question, TOP_K)
    best = max((h["similarity"] for h in hits), default=0.0)
    dbg = {"best_similarity": round(best, 3),
           "scores": [(h["file"], h["page"], round(h["similarity"], 3)) for h in hits]} if debug else {}

    # Guard 1: nothing relevant retrieved -> refuse without ever asking the LLM.
    if best < MIN_SIMILARITY:
        return not_found("low_relevance", **({"debug": dbg} if debug else {}))

    raw = chat([
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": f"Context:\n{format_context(hits)}\n\nQuestion: {question}\nAnswer:"},
    ])

    # Guard 2: the model itself says it is not in the context.
    if "could not find this information" in raw.lower():
        return not_found("model_refused", **({"debug": dbg} if debug else {}))

    cited = []
    for m in re.findall(r"\[(\d+)\]", raw):
        i = int(m)
        if 1 <= i <= len(hits) and i not in cited:
            cited.append(i)
    warnings = []
    if not cited:  # model forgot to cite -> attach the best chunks, but flag it
        cited = [1, 2][:len(hits)]
        warnings.append("The model did not cite a passage; showing the closest sources instead.")

    # Guard 3: every number in the answer must appear in the cited text.
    body = re.sub(r"\[\d+\]", "", raw)
    ctx_numbers = _numbers(" ".join(hits[i - 1]["text"] for i in cited))
    unsupported = sorted(_numbers(body) - ctx_numbers)
    verified = not unsupported and not warnings
    if unsupported:
        warnings.append(f"Could not verify these values in the cited text: {', '.join(unsupported)}. "
                        "Please check the source.")

    def label(m):
        i = int(m.group(1))
        if 1 <= i <= len(hits):
            return f"[{hits[i - 1]['file']}, page {hits[i - 1]['page']}]"
        return ""
    answer = re.sub(r"\[(\d+)\]", label, raw)

    sources = [{"id": n, "file": hits[i - 1]["file"], "page": hits[i - 1]["page"],
                "text": hits[i - 1]["text"],
                "quote": best_sentence(hits[i - 1]["text"], question + " " + body),
                "score": round(hits[i - 1]["similarity"], 3)}
               for n, i in enumerate(cited, 1)]

    out = {"answer": answer, "found": True, "verified": verified, "sources": sources, "warnings": warnings}
    if debug:
        out["debug"] = dbg
    return out


def checklist(topic: str) -> dict:
    if vs.count() == 0:
        return not_found("no_documents", "Please upload your college documents first.")
    hits = vs.search(f"{topic} required documents eligibility how to apply", 6)
    if not hits or max(h["similarity"] for h in hits) < MIN_SIMILARITY:
        return not_found("low_relevance")
    raw = chat([
        {"role": "system", "content": "You extract checklists from college documents. Use ONLY the numbered "
         "passages. Never invent items."},
        {"role": "user", "content": f"Context:\n{format_context(hits)}\n\nList every document, condition or "
         f"step required for: {topic}.\nOne item per line, each starting with '- ' and ending with its "
         f"passage number like [2]. If nothing is stated, reply exactly: {NOT_FOUND}"},
    ])
    if "could not find this information" in raw.lower():
        return not_found("model_refused")
    items = []
    for line in raw.splitlines():
        line = line.strip()
        if not line.startswith(("-", "*", "•")):
            continue
        refs = [int(x) for x in re.findall(r"\[(\d+)\]", line) if 1 <= int(x) <= len(hits)]
        text = re.sub(r"\[\d+\]", "", line.lstrip("-*• ")).strip()
        if text:
            src = hits[refs[0] - 1] if refs else None
            items.append({"item": text, "done": False,
                          "source": {"file": src["file"], "page": src["page"]} if src else None})
    if not items:
        return not_found("model_refused")
    return {"topic": topic, "found": True, "items": items}
