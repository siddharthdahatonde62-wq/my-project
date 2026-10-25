"""Rule-based deadline extraction (no LLM = fast + never hallucinates) and .ics export."""
import hashlib
import re
from datetime import date, datetime, timedelta, timezone
from pdf_loader import split_sentences

MONTHS = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "jul": 7,
          "aug": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12}
MON = (r"(january|february|march|april|may|june|july|august|september|october|november|december|"
       r"jan|feb|mar|apr|jun|jul|aug|sept|sep|oct|nov|dec)")
D1 = re.compile(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+(?:of\s+)?{MON}\b\.?,?\s*(\d{{4}})?", re.I)
D2 = re.compile(rf"\b{MON}\b\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?\b(?:,?\s*(\d{{4}}))?", re.I)
D3 = re.compile(r"\b(\d{1,2})[/.-](\d{1,2})[/.-](\d{4}|\d{2})\b")  # day-first (India)
STRONG = re.compile(r"deadline|last date|last day|due|submit|submission|on or before|no later than|"
                    r"apply|application|registration|register|closes?|before|until|latest by", re.I)


def _mk(y, m, d, today):
    try:
        if y is None:
            dt = date(today.year, m, d)
            if dt < today - timedelta(days=60):
                dt = date(today.year + 1, m, d)
            return dt
        return date(y + 2000 if y < 100 else y, m, d)
    except ValueError:
        return None


def find_dates(sentence: str, today: date) -> list[date]:
    found = []
    for m in D1.finditer(sentence):
        found.append(_mk(int(m.group(3)) if m.group(3) else None, MONTHS[m.group(2).lower()[:3]], int(m.group(1)), today))
    for m in D2.finditer(sentence):
        found.append(_mk(int(m.group(3)) if m.group(3) else None, MONTHS[m.group(1).lower()[:3]], int(m.group(2)), today))
    for m in D3.finditer(sentence):
        found.append(_mk(int(m.group(3)), int(m.group(2)), int(m.group(1)), today))
    return [d for d in found if d]


def extract(chunks: list[dict], today: date | None = None, upcoming_only: bool = True,
            deadlines_only: bool = True) -> list[dict]:
    today = today or date.today()
    seen, out = set(), []
    for c in chunks:
        for s in split_sentences(c["text"]):
            strong = bool(STRONG.search(s))
            if deadlines_only and not strong:
                continue
            for d in find_dates(s, today):
                key = (c["file"], c["page"], d)
                if key in seen:
                    continue
                seen.add(key)
                if upcoming_only and d < today:
                    continue
                out.append({
                    "id": hashlib.sha1(f"{c['file']}|{c['page']}|{d}".encode()).hexdigest()[:10],
                    "title": s[:160], "date": d.isoformat(), "days_left": (d - today).days,
                    "kind": "deadline" if strong else "date",
                    "file": c["file"], "page": c["page"], "sentence": s,
                })
    return sorted(out, key=lambda x: x["date"])


def _esc(t: str) -> str:
    return t.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def to_ics(items: list[dict]) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//CampusProof//EN", "CALSCALE:GREGORIAN"]
    for it in items:
        dt = date.fromisoformat(it["date"])
        lines += ["BEGIN:VEVENT", f"UID:{it['id']}@campusproof", f"DTSTAMP:{stamp}",
                  f"DTSTART;VALUE=DATE:{dt:%Y%m%d}", f"DTEND;VALUE=DATE:{dt + timedelta(days=1):%Y%m%d}",
                  f"SUMMARY:{_esc(it['title'][:80])}",
                  f"DESCRIPTION:{_esc('Source: ' + it['file'] + ', page ' + str(it['page']) + chr(10) + it['sentence'])}",
                  "BEGIN:VALARM", "TRIGGER:-P1D", "ACTION:DISPLAY", "DESCRIPTION:Due tomorrow", "END:VALARM",
                  "END:VEVENT"]
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"
