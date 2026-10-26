"""Embeddings through the local Ollama server (nomic-embed-text by default)."""
import httpx
from config import OLLAMA_URL, EMBED_MODEL


class OllamaError(RuntimeError):
    pass


def embed(texts: list[str], kind: str = "document") -> list[list[float]]:
    """kind = 'document' or 'query'. nomic-embed-text works best with task prefixes."""
    if not texts:
        return []
    prefix = ""
    if "nomic" in EMBED_MODEL:
        prefix = "search_document: " if kind == "document" else "search_query: "
    vectors = []
    try:
        for i in range(0, len(texts), 32):
            batch = [prefix + t for t in texts[i:i + 32]]
            r = httpx.post(f"{OLLAMA_URL}/api/embed",
                           json={"model": EMBED_MODEL, "input": batch}, timeout=300)
            r.raise_for_status()
            vectors.extend(r.json()["embeddings"])
    except httpx.ConnectError:
        raise OllamaError("Cannot reach Ollama. Start it with `ollama serve`.")
    except httpx.HTTPStatusError as e:
        raise OllamaError(f"Ollama error: {e.response.text[:200]} "
                          f"(did you run `ollama pull {EMBED_MODEL}`?)")
    return vectors