"""Central settings. Override any of them with environment variables."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
CHROMA_DIR = BASE_DIR / "chroma_db"
def _find_frontend() -> Path:
    """frontend/ next to backend/ (preferred), else the project root if index.html lives there."""
    env = os.getenv("FRONTEND_DIR")
    if env:
        return Path(env)
    for cand in (BASE_DIR.parent / "frontend", BASE_DIR.parent):
        if (cand / "index.html").exists():
            return cand
    return BASE_DIR.parent / "frontend"


FRONTEND_DIR = _find_frontend()
FEEDBACK_FILE = BASE_DIR / "feedback.jsonl"

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen2.5:3b")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")

CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 700))      # characters
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 100))
TOP_K = int(os.getenv("TOP_K", 5))                  # chunks sent to the LLM
CANDIDATES = int(os.getenv("CANDIDATES", 20))       # chunks fetched before re-ranking

# If the best chunk is less similar than this, we refuse WITHOUT calling the LLM.
# Tune with /ask?debug=true and evaluate.py (typical nomic-embed-text range: 0.40-0.55).
MIN_SIMILARITY = float(os.getenv("MIN_SIMILARITY", 0.45))

# A question sharing NO keyword with any retrieved chunk must be a very strong semantic match to be answered.
STRONG_SIMILARITY = float(os.getenv("STRONG_SIMILARITY", 0.60))

UPLOAD_DIR.mkdir(exist_ok=True)
