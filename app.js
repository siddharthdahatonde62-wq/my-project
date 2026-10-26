/* CampusProof - connects the static pages to the FastAPI backend.
   Add <script src="app.js"></script> before </body> in ask.html, documents.html, deadlines.html */
(() => {
  const API = location.port === "8000" ? "" : "http://127.0.0.1:8000";
  const ORIGIN = API || location.origin;
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const trunc = (s, n) => (s.length > n ? s.slice(0, n - 1) + "…" : s);
  const time = () => new Date().toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  const fileUrl = (f, p) => `${ORIGIN}/documents/${encodeURIComponent(f)}/file${p ? "#page=" + p : ""}`;

  async function api(path, opts) {
    let r;
    try { r = await fetch(API + path, opts); }
    catch { throw new Error(`Cannot reach the backend at ${ORIGIN}. Is uvicorn running?`); }
    let data = null;
    try { data = await r.json(); } catch {}
    if (!r.ok) throw new Error((data && data.detail) || `Server error ${r.status}`);
    return data;
  }

  /* ------------------------------------------------------------ ASK */
  function initAsk() {
    const body = $(".chat-body"), form = $(".composer-field"), panel = $(".source-panel");
    if (!body || !form) return;
    const input = $("input", form), btn = $("button", form);
    const stale = $(".page-heading + .notice"); if (stale) stale.style.display = "none";
    const tag = $(".demo-tag"); if (tag) { tag.textContent = "LIVE"; tag.style.background = "#dcfce7"; tag.style.color = "#15803d"; }
    const sub = $(".chat-header small"); if (sub) sub.innerHTML = '<span class="offline-dot"></span>Local model · Answers only from your documents';
    const help = $(".composer-help"); if (help) help.textContent = "Answers come only from your uploaded documents. Always check the cited source.";
    input.removeAttribute("readonly"); input.autocomplete = "off";
    btn.type = "submit"; btn.removeAttribute("title"); btn.setAttribute("aria-label", "Send question");
    body.innerHTML = "";

    const scroll = () => { body.scrollTop = body.scrollHeight; window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" }); };
    const addUser = t => { body.insertAdjacentHTML("beforeend", `<div class="chat-message user"><div><div class="chat-bubble">${esc(t)}</div><div class="chat-time" style="text-align:right">You · ${time()}</div></div></div>`); scroll(); };
    const addAI = html => {
      const el = document.createElement("div"); el.className = "chat-message ai";
      el.innerHTML = `<span class="ai-avatar">✦</span><div><div class="chat-bubble">${html}</div><div class="chat-time">CampusProof Assistant · ${time()}</div></div>`;
      body.appendChild(el); scroll(); return el;
    };

    const highlight = (text, quote) => {
      const t = esc(text), q = esc(quote), i = t.indexOf(q);
      if (!quote || i < 0) return t;
      return t.slice(0, i) + `<mark style="background:#fde68a;border-radius:3px;padding:0 2px">${q}</mark>` + t.slice(i + q.length);
    };
    const setPanel = sources => {
      const cards = sources.length ? sources.map(s => `
        <div class="source-preview">
          <div class="source-preview-head"><span class="file-icon file-pdf">PDF</span><strong>${esc(s.file)}</strong><span class="page-badge">PAGE ${s.page}</span></div>
          <p style="font-size:13px;line-height:1.6;margin-bottom:10px">${highlight(s.text, s.quote)}</p>
          <a class="text-link" href="${fileUrl(s.file, s.page)}" target="_blank" rel="noopener">Open PDF at page ${s.page} →</a>
        </div>`).join("")
        : `<div class="source-preview"><p style="color:#6b7285;font-size:13px">No sources — nothing in your documents matched this question.</p></div>`;
      panel.innerHTML = `<h2>Sources in this answer</h2><p>Every answer should make its evidence easy to inspect.</p>${cards}
        <div class="legend"><span><i></i> Citation reference</span><span><i></i> Highlighted excerpt</span></div>`;
    };

    const note = (txt, color) => `<p style="margin-top:8px;font-size:12px;color:${color}">${txt}</p>`;
    function render(r, q, el) {
      const bubble = $(".chat-bubble", el);
      if (!r.found) {
        bubble.innerHTML = `<p>${esc(r.answer)}</p>` + (r.reason === "no_documents"
          ? note('Go to <a class="text-link" href="documents.html">Documents</a> to upload PDFs first.', "#6b7285")
          : note("⚠ Not found in your documents — CampusProof will not guess.", "#b45309")
            + note("Tip: ask a specific question, e.g. “What is the attendance requirement?”", "#6b7285"));
        return;
      }
      let h = `<p style="white-space:pre-wrap">${esc(r.answer)}</p>`;
      if (r.verified) h += note("✓ Numbers and dates verified against the cited text", "#15803d");
      (r.warnings || []).forEach(w => h += note("⚠ " + esc(w), "#b45309"));
      r.sources.forEach(s => h += `
        <a class="citation-card" href="${fileUrl(s.file, s.page)}" target="_blank" rel="noopener">
          <span class="file-icon file-pdf">PDF</span>
          <div><strong>${esc(s.file)}</strong><small>“${esc(trunc(s.quote, 110))}”</small></div>
          <span class="citation-number">[${s.id}] p. ${s.page}</span>
        </a>`);
      h += `<div class="fb" style="display:flex;gap:8px;margin-top:12px">
        <button type="button" data-v="1" class="button button-secondary" style="padding:4px 10px;font-size:12px">👍 Helpful</button>
        <button type="button" data-v="0" class="button button-secondary" style="padding:4px 10px;font-size:12px">👎 Not helpful</button></div>`;
      bubble.innerHTML = h;
      $(".fb", bubble).addEventListener("click", async e => {
        const b = e.target.closest("button"); if (!b) return;
        try {
          await api("/feedback", { method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question: q, answer: r.answer, helpful: b.dataset.v === "1" }) });
          $(".fb", bubble).innerHTML = '<small>Thanks for the feedback ✓</small>';
        } catch {}
      });
    }

    let busy = false;
    async function send(q) {
      q = q.trim(); if (!q || busy) return;
      busy = true; input.value = ""; btn.disabled = true;
      addUser(q);
      const el = addAI('<span style="color:#6b7285">Searching your documents…</span>');
      try {
        const r = await api("/ask", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question: q }) });
        render(r, q, el); setPanel(r.found ? r.sources : []);
      } catch (e) {
        $(".chat-bubble", el).innerHTML = `<p style="color:#b91c1c">⚠ ${esc(e.message)}</p>` + note("Check that the backend terminal is running and the Ollama app is open.", "#6b7285");
      } finally { busy = false; btn.disabled = false; input.focus(); scroll(); }
    }
    form.addEventListener("submit", e => { e.preventDefault(); send(input.value); });

    // welcome message + suggestions
    (async () => {
      let msg = "Hi! Ask me anything about your uploaded college documents. I only answer from them, and I show you the exact source.";
      try {
        const h = await api("/health");
        if (!h.chunks) msg = 'No documents yet. Upload your college PDFs on the <a class="text-link" href="documents.html">Documents</a> page first.';
        else if (h.status !== "ok") msg += `<br><small style="color:#b45309">⚠ Ollama issue: ${h.ollama ? "missing models " + esc(h.models_missing.join(", ")) : "Ollama is not running"}.</small>`;
      } catch (e) { msg = `<span style="color:#b91c1c">⚠ ${esc(e.message)}</span>`; }
      addAI(`<p>${msg}</p>`);
      try {
        const s = await api("/suggestions");
        const box = document.createElement("div");
        box.style.cssText = "display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px";
        s.suggestions.forEach(t => {
          const c = document.createElement("button"); c.type = "button"; c.textContent = t;
          c.style.cssText = "background:#f3f4fa;border:1px solid #e8eaf2;color:#49506a;padding:6px 12px;border-radius:999px;font-size:12px;cursor:pointer";
          c.onclick = () => send(t); box.appendChild(c);
        });
        $(".chat-composer").insertBefore(box, form);
      } catch {}
    })();
  }

  /* ------------------------------------------------------------ DOCUMENTS */
  function initDocs() {
    const grid = $(".doc-grid"); if (!grid) return;
    const notice = $(".page-heading + .notice"), empty = $("#upload-note");
    const countEl = $(".section-head h2 span"), badge = $(".section-head .status");
    const picker = Object.assign(document.createElement("input"), { type: "file", accept: ".pdf,application/pdf", multiple: true, hidden: true });
    document.body.appendChild(picker);
    const say = (title, text, color) => { notice.innerHTML = `<span class="notice-icon" ${color ? `style="color:${color}"` : ""}>ⓘ</span><div><strong>${title}</strong>${text}</div>`; };
    say("Live — connected to your local backend", "PDFs are processed on this machine. Upload official college documents, then ask questions on the Ask AI page.");
    const up = $(".page-heading .button-primary"); up.addEventListener("click", e => { e.preventDefault(); picker.click(); });
    if (empty) {
      $("h3", empty).textContent = "Drop PDF files here";
      $("p", empty).textContent = "Or click to choose files. Text-based PDFs only (scanned PDFs need OCR).";
      const b = $(".button", empty); b.textContent = "Choose PDF files"; b.style.cursor = "pointer";
      empty.style.cursor = "pointer"; empty.addEventListener("click", () => picker.click());
      ["dragover", "dragenter"].forEach(ev => empty.addEventListener(ev, e => { e.preventDefault(); empty.style.background = "#f8f7ff"; }));
      empty.addEventListener("dragleave", () => empty.style.background = "#fff");
      empty.addEventListener("drop", e => { e.preventDefault(); empty.style.background = "#fff"; upload(e.dataTransfer.files); });
    }
    picker.addEventListener("change", () => upload(picker.files));

    async function upload(files) {
      files = [...files]; if (!files.length) return;
      say("Uploading and indexing…", `Processing ${files.length} file(s). The first run can take a minute while the embedding model loads.`, "#d97706");
      const fd = new FormData(); files.forEach(f => fd.append("files", f));
      try {
        const r = await api("/upload", { method: "POST", body: fd });
        const errs = (r.errors || []).map(e => `${esc(e.file)}: ${esc(e.error)}`).join("<br>");
        say(r.files_processed ? `Done — ${r.files_processed} file(s) indexed (${r.chunks_created} chunks)` : "Upload failed", errs || "You can now ask questions about them.", r.files_processed ? "#16a34a" : "#dc2626");
      } catch (e) { say("Upload failed", esc(e.message), "#dc2626"); }
      picker.value = ""; load();
    }
    const size = b => b == null ? "" : b > 1048576 ? (b / 1048576).toFixed(1) + " MB" : Math.max(1, Math.round(b / 1024)) + " KB";
    async function load() {
      let docs = [];
      try { docs = (await api("/documents")).documents; } catch (e) { say("Backend not reachable", esc(e.message), "#dc2626"); }
      countEl.textContent = `(${docs.length} document${docs.length === 1 ? "" : "s"})`;
      badge.textContent = `${docs.length} ready`;
      grid.innerHTML = docs.length ? docs.map(d => `
        <article class="card document-card">
          <div class="document-top"><span class="file-icon file-pdf">PDF</span><span class="more" data-f="${esc(d.file)}" title="Delete document" style="cursor:pointer">•••</span></div>
          <h3><a href="${fileUrl(d.file)}" target="_blank" rel="noopener">${esc(d.file)}</a></h3>
          <p>${d.pages} page${d.pages === 1 ? "" : "s"} · ${d.chunks} searchable chunks</p>
          <div class="document-bottom"><small>${size(d.size_bytes)}</small><span class="status status-ready">Ready</span></div>
        </article>`).join("") : `<p style="color:#6b7285;grid-column:1/-1">No documents yet — upload your first PDF below.</p>`;
    }
    grid.addEventListener("click", async e => {
      const m = e.target.closest(".more"); if (!m) return;
      if (confirm(`Delete "${m.dataset.f}" from CampusProof?`)) { try { await api(`/documents/${encodeURIComponent(m.dataset.f)}`, { method: "DELETE" }); } catch (err) { alert(err.message); } load(); }
    });
    load();
  }

  /* ------------------------------------------------------------ DEADLINES */
  function initDeadlines() {
    const card = $$(".section-card")[0]; if (!card || !$(".deadline-full")) return;
    const notice = $(".page-heading + .notice");
    notice.innerHTML = '<span class="notice-icon">ⓘ</span><div><strong>Extracted from your uploaded documents</strong>Dates are found by pattern matching, so they are never invented. Each one links to its source page.</div>';
    const done = $$(".section-card")[1]; if (done) done.style.display = "none";
    $$(".deadline-full", card).forEach(x => x.remove());
    const list = document.createElement("div"); card.appendChild(list);
    const headRight = $(".section-head", card);
    headRight.insertAdjacentHTML("beforeend", `<a class="button button-soft" href="${ORIGIN}/deadlines/ics">⬇ All (.ics)</a>`);
    list.innerHTML = '<p style="color:#6b7285">Loading…</p>';

    api("/deadlines").then(({ deadlines }) => {
      const today = new Date(); today.setHours(0, 0, 0, 0);
      const stats = $$(".stat-value");
      if (stats[0]) stats[0].textContent = deadlines.filter(d => d.days_left <= 14).length;
      if (stats[1]) stats[1].textContent = deadlines.filter(d => d.days_left <= 7).length;
      if (stats[2]) stats[2].textContent = "—"; if (stats[3]) stats[3].textContent = "—";
      $$(".calendar-day.has-event").forEach(x => x.classList.remove("has-event"));
      deadlines.forEach(d => {
        const dt = new Date(d.date + "T00:00:00");
        if (dt.getFullYear() === 2026 && dt.getMonth() === 9)
          $$(".calendar-day:not(.muted)").find(x => x.textContent.trim() === String(dt.getDate()))?.classList.add("has-event");
      });
      if (!deadlines.length) { list.innerHTML = '<p style="color:#6b7285">No upcoming deadlines found. Upload notices or circulars that contain dates like “submit by 30 October”.</p>'; return; }
      list.innerHTML = deadlines.map(d => {
        const dt = new Date(d.date + "T00:00:00");
        const pr = d.days_left <= 3 ? ["high", "High"] : d.days_left <= 10 ? ["medium", "Medium"] : ["low", "Low"];
        const when = d.days_left === 0 ? "Due today" : `Due in ${d.days_left} day${d.days_left === 1 ? "" : "s"}`;
        return `<div class="deadline-full card">
          <div class="deadline-full-head">
            <div class="date-box"><strong>${String(dt.getDate()).padStart(2, "0")}</strong><small>${dt.toLocaleString("en", { month: "short" })}</small></div>
            <div><h3>${esc(trunc(d.title, 90))}</h3><p>${esc(d.file)} · p. ${d.page}</p></div>
            <span class="priority priority-${pr[0]}">${pr[1]}</span>
          </div>
          <div class="deadline-full-foot"><span>${when}</span>
            <span><a class="text-link" href="${fileUrl(d.file, d.page)}" target="_blank" rel="noopener">View source</a> · <a class="text-link" href="${ORIGIN}/deadlines/ics?id=${d.id}">Add to calendar</a></span></div>
        </div>`;
      }).join("");
    }).catch(e => { list.innerHTML = `<p style="color:#b91c1c">⚠ ${esc(e.message)}</p>`; });
  }

  /* ------------------------------------------------------------ PREFERENCES (all pages) */
  const PREF_KEY = "cp_prefs";
  const prefs = () => { try { return JSON.parse(localStorage.getItem(PREF_KEY)) || {}; } catch { return {}; } };
  const savePrefs = p => { try { localStorage.setItem(PREF_KEY, JSON.stringify(p)); } catch {} };
  const initials = n => n.trim().split(/\s+/).map(w => w[0]).join("").slice(0, 2).toUpperCase();

  function applyPrefs() {
    if (!$("#cp-style")) {
      const st = document.createElement("style"); st.id = "cp-style";
      st.textContent = `
        html.dark{filter:invert(.93) hue-rotate(180deg);background:#0b0d17}
        html.dark .avatar,html.dark .brand-mark,html.dark .ai-avatar,html.dark .file-icon,html.dark .ask-banner,
        html.dark .button-primary,html.dark .chat-message.user .chat-bubble,html.dark .stat-icon,
        html.dark .composer-field button,html.dark .calendar-day.selected,html.dark .calendar-day.has-event,
        html.dark mark,html.dark .toggle.on{filter:invert(1) hue-rotate(180deg)}
        body.compact .section-card,body.compact .stat-card,body.compact .document-card,body.compact .settings-card,
        body.compact .answer-card,body.compact .calendar-card{padding:12px}
        body.compact .grid,body.compact .stack{gap:10px}
        body.compact .chat-body{gap:10px;padding:14px}
        body.reduce-motion *{transition:none!important;animation:none!important;scroll-behavior:auto!important}
        .toggle{cursor:pointer}`;
      document.head.appendChild(st);
    }
    const p = prefs();
    document.documentElement.classList.toggle("dark", !!p.dark);
    document.body.classList.toggle("compact", !!p.compact);
    document.body.classList.toggle("reduce-motion", !!p.reduce);
    if (p.name) {
      $$(".user-mini strong").forEach(e => e.textContent = p.name);
      $$(".avatar").forEach(e => e.textContent = initials(p.name));
    }
    const oc = $(".offline-card p"); if (oc) oc.textContent = "Your documents are processed on this machine by a local open-weight model.";
    const ft = $(".footer-note"); if (ft) ft.textContent = "CampusProof · Offline-first by design · Open-source AI (Ollama + ChromaDB)";
  }

  /* ------------------------------------------------------------ DASHBOARD */
  function initDashboard() {
    const p = prefs(), name = (p.name || "Pranav Chavan").split(" ")[0];
    const hr = new Date().getHours(), greet = hr < 12 ? "Good morning" : hr < 17 ? "Good afternoon" : "Good evening";
    const eb = $(".page-heading .eyebrow"); if (eb) eb.textContent = new Date().toLocaleDateString("en-US", { weekday: "long", year: "numeric", month: "long", day: "numeric" });
    const h1 = $(".page-heading h1"); if (h1) h1.innerHTML = `${greet}, ${esc(name)} <span aria-hidden="true">✦</span>`;
    const stats = $$(".stat-value"), notes = $$(".stat-note");
    api("/documents").then(({ documents }) => {
      if (stats[0]) stats[0].textContent = documents.length;
      if (notes[0]) notes[0].textContent = "In your library";
      const list = $(".doc-list");
      if (list) list.innerHTML = documents.length ? documents.slice(0, 3).map(d => `
        <div class="doc-row"><span class="file-icon file-pdf">PDF</span>
          <div class="row-main"><strong>${esc(d.file)}</strong><small>PDF · ${d.pages} page${d.pages === 1 ? "" : "s"} · ${d.chunks} chunks</small></div>
          <span class="status status-ready">Ready</span></div>`).join("")
        : '<p style="color:#6b7285;padding:8px 0">No documents yet. <a class="text-link" href="documents.html">Upload your first PDF →</a></p>';
    }).catch(() => {});
    api("/deadlines").then(({ deadlines }) => {
      if (stats[3]) stats[3].textContent = deadlines.length;
      if (notes[3]) notes[3].textContent = deadlines.length ? `Next due in ${deadlines[0].days_left} day${deadlines[0].days_left === 1 ? "" : "s"}` : "Nothing due";
      const dl = $(".deadline-list");
      if (dl) dl.innerHTML = deadlines.length ? deadlines.slice(0, 3).map(d => {
        const dt = new Date(d.date + "T00:00:00"), pr = d.days_left <= 3 ? ["high", "High"] : d.days_left <= 10 ? ["medium", "Medium"] : ["low", "Low"];
        return `<div class="deadline-item"><div class="date-box"><strong>${String(dt.getDate()).padStart(2, "0")}</strong><small>${dt.toLocaleString("en", { month: "short" })}</small></div>
          <div class="deadline-info"><strong>${esc(trunc(d.title, 48))}</strong><small>${esc(d.file)}</small></div><span class="priority priority-${pr[0]}">${pr[1]}</span></div>`;
      }).join("") : '<p style="color:#6b7285;padding:8px 0">No upcoming deadlines found in your documents.</p>';
    }).catch(() => {});
  }

  /* ------------------------------------------------------------ SETTINGS */
  function initSettings() {
    const p = prefs();
    const notice = $(".page-heading + .notice");
    const say = (t, m, c) => { notice.innerHTML = `<span class="notice-icon" ${c ? `style="color:${c}"` : ""}>ⓘ</span><div><strong>${t}</strong>${m}</div>`; };
    say("Your preferences are saved in this browser", "Profile and appearance changes apply to every page instantly.");

    // profile
    const name = $("#full-name"), email = $("#student-email"), course = $("#course"), year = $("#year");
    [name, email, course].forEach(i => i.removeAttribute("readonly"));
    year.disabled = false;
    year.innerHTML = ["First year", "Second year", "Third year", "Fourth year"].map(y => `<option>${y}</option>`).join("");
    if (p.name) name.value = p.name; if (p.email) email.value = p.email; if (p.course) course.value = p.course;
    year.value = p.year || "Second year";
    const save = $("form button.button");
    save.textContent = "Save profile";
    save.addEventListener("click", () => {
      const v = name.value.trim() || "Student";
      savePrefs({ ...prefs(), name: v, email: email.value.trim(), course: course.value.trim(), year: year.value });
      applyPrefs(); save.textContent = "Saved ✓"; setTimeout(() => save.textContent = "Save profile", 1500);
    });

    // toggles
    const row = label => $$(".setting-row").find(r => $("strong", r) && $("strong", r).textContent.trim() === label);
    const bind = (label, key, invert) => {
      const t = $(".toggle", row(label)); if (!t) return;
      t.setAttribute("role", "switch");
      const paint = () => t.classList.toggle("on", invert ? !prefs()[key] : !!prefs()[key]);
      paint();
      t.addEventListener("click", () => { const q = prefs(); q[key] = !q[key]; savePrefs(q); applyPrefs(); paint(); });
    };
    bind("Light appearance", "dark", true); bind("Reduce motion", "reduce", false); bind("Compact cards", "compact", false);

    // live status
    const setStatus = (label, text, ok, desc) => {
      const r = row(label); if (!r) return;
      const s = $(".status", r); if (s) { s.textContent = text; s.className = "status " + (ok ? "status-ready" : "status-processing"); }
      if (desc) $("p", r).textContent = desc;
    };
    setStatus("Offline workspace", "Active", true, "The interface runs from your own local server.");
    setStatus("Network access", "Local only", true, "Only talks to the Ollama server on localhost. No cloud calls.");
    api("/health").then(h => {
      setStatus("Local document processing", h.ollama && !h.models_missing.length ? "Active" : "Needs attention", h.ollama && !h.models_missing.length,
        h.ollama ? "PDFs and embeddings stay on this device." : "Ollama is not running — start the Ollama app.");
      const about = $$(".settings-card").find(c => $("h2", c) && $("h2", c).textContent.trim() === "About CampusProof");
      if (about) {
        const vr = row("Version");
        if (vr) { $("p", vr).textContent = "CampusProof 1.0"; const s = $("span", vr); if (s) s.textContent = "FastAPI + ChromaDB"; }
        about.insertAdjacentHTML("beforeend", `<div class="setting-row"><div><strong>AI model</strong><p>${esc(h.model)} · embeddings: ${esc(h.embedding_model)}</p></div><span class="status status-ready">Open-weight</span></div>`);
        const para = $("p", about); if (para) para.textContent = "CampusProof is an offline, citation-first assistant that answers only from your own college documents, with traceable sources.";
      }
    }).catch(() => setStatus("Local document processing", "Backend offline", false, "Start the backend (uvicorn) to enable document processing."));
    const stor = $$(".settings-card").find(c => $("h2", c) && $("h2", c).textContent.trim() === "Storage");
    if (stor) api("/documents").then(({ documents }) => {
      const bytes = documents.reduce((a, d) => a + (d.size_bytes || 0), 0), mb = bytes / 1048576;
      const chunks = documents.reduce((a, d) => a + d.chunks, 0);
      $("h2 + p", stor).textContent = "Your uploaded documents";
      const top = $("div[style*='justify-content']", stor);
      if (top) top.innerHTML = `<strong style="font-size:13px">${mb >= 1 ? mb.toFixed(1) + " MB" : Math.round(bytes / 1024) + " KB"} used</strong><span style="font-size:11px;color:var(--muted)">${documents.length} document${documents.length === 1 ? "" : "s"}</span>`;
      const m = $(".storage-meter span", stor); if (m) m.style.width = Math.min(100, Math.max(3, mb)) + "%";
      const det = $(".storage-details", stor); if (det) det.innerHTML = `<span>PDFs · ${documents.length}</span><span>Searchable chunks · ${chunks}</span>`;
      const small = $("p[style*='font-size:10px']", stor); if (small) small.textContent = "Calculated from the files you uploaded.";
    }).catch(() => {});
  }

  const page = location.pathname.split("/").pop();
  applyPrefs();
  if (page === "" || page === "index.html") initDashboard();
  else if (page === "settings.html") initSettings();
  else if (page === "ask.html") initAsk();
  else if (page === "documents.html") initDocs();
  else if (page === "deadlines.html") initDeadlines();
})();