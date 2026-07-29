"""
web/app.py
Tier 2 — Flask Web UI for the Research Analysis Toolkit

A browser-based interface that lets you:
  - Create a project session
  - Upload a guideline (drag & drop)
  - Write / revise individual chapters
  - Generate datasets and run analysis
  - Download the full Word document

Run with:
    python web/app.py
Then open: http://localhost:5000

Requires:
    pip install flask
"""
from __future__ import annotations

import os
import sys
import json
import uuid
import traceback
from pathlib import Path
from datetime import datetime

# Add project root to path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from flask import (
    Flask, render_template_string, request, jsonify,
    redirect, url_for, send_file, flash, session as flask_session
)

from research_engine.writer import (
    ProjectSession, ProjectMetadata, EducationLevel,
    extract_text, parse_guideline, write_chapter, revise_chapter,
    generate_references, save_study_files, write_chapter4_with_data,
    CHAPTER_TITLES,
)
from research_engine.exporters.project_docx_exporter import export_project_docx

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "rat-dev-secret-2026")

SESSIONS_DIR = ROOT / "sessions"
SESSIONS_DIR.mkdir(exist_ok=True)

OUTPUT_DIR   = ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

UPLOAD_DIR   = ROOT / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_EXT  = {".docx", ".pdf", ".txt", ".md"}


# ── Helpers ───────────────────────────────────────────────────

def _load(sid: str) -> ProjectSession | None:
    path = SESSIONS_DIR / f"{sid}.json"
    if not path.exists(): return None
    return ProjectSession.from_file(path)

def _save(s: ProjectSession):
    (SESSIONS_DIR / f"{s.session_id}.json").write_text(
        json.dumps(s._to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")

def _all_sessions() -> list[ProjectSession]:
    out = []
    for p in sorted(SESSIONS_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try: out.append(ProjectSession.from_file(p))
        except Exception: pass
    return out

def _api_key():
    return os.environ.get("OPENAI_API_KEY", "")


# ════════════════════════════════════════════════════════════════
# HTML templates (inline — no separate templates/ directory needed)
# ════════════════════════════════════════════════════════════════

BASE_STYLE = """
<style>
  :root {
    --bg:      #0f0f1a;
    --panel:   #1a1a2e;
    --card:    #16213e;
    --gold:    #F59E0B;
    --gold2:   #FCD34D;
    --purple:  #7C3AED;
    --white:   #F1F5F9;
    --grey:    #64748B;
    --light:   #94A3B8;
    --green:   #22C55E;
    --red:     #EF4444;
    --radius:  10px;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: var(--bg); color: var(--white); font-family: 'Segoe UI', sans-serif; min-height: 100vh; }
  a { color: var(--gold); text-decoration: none; }
  a:hover { color: var(--gold2); }

  /* Nav */
  nav { background: var(--panel); border-bottom: 1px solid #2d2d4e; padding: 0 2rem; display: flex; align-items: center; gap: 2rem; height: 56px; }
  nav .brand { font-size: 1.2rem; font-weight: 700; color: var(--gold); letter-spacing: 0.5px; }
  nav .brand span { color: var(--white); font-weight: 400; }
  nav a { color: var(--light); font-size: 0.9rem; }
  nav a:hover { color: var(--gold); }

  /* Layout */
  .container { max-width: 1100px; margin: 0 auto; padding: 2rem 1.5rem; }
  .page-title { font-size: 1.6rem; font-weight: 700; color: var(--gold); margin-bottom: 0.4rem; }
  .page-sub   { color: var(--light); font-size: 0.9rem; margin-bottom: 2rem; }

  /* Cards */
  .card { background: var(--card); border: 1px solid #2d2d4e; border-radius: var(--radius); padding: 1.5rem; margin-bottom: 1.2rem; }
  .card-title { font-size: 1rem; font-weight: 600; color: var(--gold); margin-bottom: 0.8rem; }

  /* Buttons */
  .btn { display: inline-flex; align-items: center; gap: 0.4rem; padding: 0.5rem 1.2rem; border-radius: 6px; font-size: 0.875rem; font-weight: 600; border: none; cursor: pointer; transition: all 0.15s; }
  .btn-gold   { background: var(--gold); color: #0f0f1a; }
  .btn-gold:hover { background: var(--gold2); }
  .btn-ghost  { background: transparent; border: 1px solid var(--grey); color: var(--light); }
  .btn-ghost:hover { border-color: var(--gold); color: var(--gold); }
  .btn-danger { background: var(--red); color: white; }
  .btn-green  { background: var(--green); color: #0f0f1a; }
  .btn-purple { background: var(--purple); color: white; }
  .btn-purple:hover { background: #6D28D9; }
  .btn:disabled { opacity: 0.4; cursor: not-allowed; }
  .btn-sm { padding: 0.35rem 0.8rem; font-size: 0.8rem; }

  /* Forms */
  .form-group { margin-bottom: 1.2rem; }
  label { display: block; font-size: 0.85rem; color: var(--light); margin-bottom: 0.4rem; }
  input[type=text], input[type=file], select, textarea {
    width: 100%; background: var(--panel); border: 1px solid #2d2d4e; border-radius: 6px;
    color: var(--white); padding: 0.6rem 0.9rem; font-size: 0.9rem; outline: none;
  }
  input:focus, select:focus, textarea:focus { border-color: var(--gold); }
  textarea { resize: vertical; min-height: 120px; font-family: inherit; }

  /* Chapter grid */
  .ch-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 1rem; margin-top: 1rem; }
  .ch-card { background: var(--panel); border: 1px solid #2d2d4e; border-radius: var(--radius); padding: 1rem; }
  .ch-card.done { border-color: var(--green); }
  .ch-card .ch-num { font-size: 0.75rem; color: var(--grey); }
  .ch-card .ch-title { font-size: 0.9rem; font-weight: 600; margin: 0.3rem 0; }
  .ch-card .ch-wc { font-size: 0.78rem; color: var(--light); }
  .ch-card .ch-actions { margin-top: 0.8rem; display: flex; gap: 0.5rem; flex-wrap: wrap; }

  /* Badges */
  .badge { display: inline-block; padding: 0.15rem 0.6rem; border-radius: 20px; font-size: 0.72rem; font-weight: 600; }
  .badge-done    { background: #14532d; color: var(--green); }
  .badge-pending { background: #1e1b4b; color: var(--purple); }
  .badge-gold    { background: #451a03; color: var(--gold); }

  /* Table */
  table { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
  th { background: var(--panel); color: var(--light); font-weight: 600; padding: 0.6rem 0.8rem; text-align: left; border-bottom: 1px solid #2d2d4e; }
  td { padding: 0.6rem 0.8rem; border-bottom: 1px solid #1e1e38; }
  tr:hover td { background: #1e1e38; }

  /* Alert */
  .alert { padding: 0.8rem 1rem; border-radius: 6px; font-size: 0.875rem; margin-bottom: 1rem; }
  .alert-success { background: #14532d; color: var(--green); border: 1px solid #166534; }
  .alert-error   { background: #450a0a; color: var(--red);   border: 1px solid #7f1d1d; }
  .alert-info    { background: #1e1b4b; color: #a5b4fc;      border: 1px solid #3730a3; }

  /* Spinner */
  .spinner { display: none; width: 18px; height: 18px; border: 2px solid #333; border-top-color: var(--gold); border-radius: 50%; animation: spin 0.6s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }

  /* Drop zone */
  .drop-zone { border: 2px dashed #2d2d4e; border-radius: var(--radius); padding: 2.5rem; text-align: center; cursor: pointer; transition: all 0.2s; }
  .drop-zone:hover, .drop-zone.dragover { border-color: var(--gold); background: #1a1a2e; }
  .drop-zone .icon { font-size: 2.5rem; margin-bottom: 0.5rem; }
  .drop-zone .dz-text { color: var(--light); font-size: 0.9rem; }

  /* Progress bar */
  .progress { background: #2d2d4e; border-radius: 20px; height: 8px; overflow: hidden; margin: 0.5rem 0; }
  .progress-bar { height: 100%; background: var(--gold); border-radius: 20px; transition: width 0.3s; }

  /* Divider */
  hr { border: none; border-top: 1px solid #2d2d4e; margin: 1.5rem 0; }
  .text-gold { color: var(--gold); } .text-light { color: var(--light); } .text-green { color: var(--green); }
  .mt-1 { margin-top: 0.5rem; } .mt-2 { margin-top: 1rem; } .flex { display: flex; } .gap-2 { gap: 0.75rem; } .items-center { align-items: center; }
  .text-sm { font-size: 0.85rem; } .font-mono { font-family: monospace; }
  #loading-overlay { display:none; position:fixed; inset:0; background:rgba(0,0,0,0.7); z-index:9999; place-items:center; }
  #loading-overlay.show { display:grid; }
  #loading-overlay .box { background: var(--card); padding: 2rem 2.5rem; border-radius: var(--radius); text-align: center; }
  #loading-overlay .box p { color: var(--light); margin-top: 0.8rem; font-size: 0.9rem; }
</style>
"""

NAV = """
<nav>
  <span class="brand">RAT <span>Research Assistant</span></span>
  <a href="/">Dashboard</a>
  <a href="/new">New Project</a>
</nav>
<div id="loading-overlay">
  <div class="box">
    <div class="spinner" style="display:block;margin:0 auto;width:36px;height:36px;border-width:3px"></div>
    <p id="loading-msg">Working… this may take 30–60 seconds</p>
  </div>
</div>
"""

def _flash_html():
    msgs = flask_session.pop("_flashes", []) if "_flashes" in flask_session else []
    html = ""
    for cat, msg in msgs:
        cls = "alert-success" if cat == "success" else "alert-error" if cat == "error" else "alert-info"
        html += f'<div class="alert {cls}">{msg}</div>'
    return html


# ════════════════════════════════════════════════════════════════
# Routes
# ════════════════════════════════════════════════════════════════

@app.route("/")
def index():
    sessions = _all_sessions()
    rows = ""
    for s in sessions:
        done  = len(s.chapters_done)
        total = 5
        pct   = int(done / total * 100)
        rows += f"""
        <tr>
          <td><a href="/session/{s.session_id}">{s.session_id}</a></td>
          <td>{s.metadata.title[:50] or '—'}</td>
          <td><span class="badge badge-gold">{s.metadata.level.value.upper()}</span></td>
          <td>
            <div class="progress"><div class="progress-bar" style="width:{pct}%"></div></div>
            <span class="text-sm text-light">{done}/5 chapters</span>
          </td>
          <td>{s.updated_at[:10]}</td>
          <td>
            <a href="/session/{s.session_id}" class="btn btn-ghost btn-sm">Open</a>
          </td>
        </tr>"""

    if not rows:
        rows = '<tr><td colspan="6" style="text-align:center;color:var(--grey);padding:2rem">No projects yet — <a href="/new">Create your first project</a></td></tr>'

    return render_template_string(f"""<!DOCTYPE html><html><head>
<title>RAT — Research Assistant</title>{BASE_STYLE}</head><body>
{NAV}
<div class="container">
  <div class="page-title">Your Projects</div>
  <div class="page-sub">AI-powered research project assistant</div>
  <div style="margin-bottom:1.5rem">
    <a href="/new" class="btn btn-gold">+ New Project</a>
  </div>
  <div class="card">
    <table>
      <thead><tr>
        <th>Session ID</th><th>Title</th><th>Level</th>
        <th>Progress</th><th>Updated</th><th></th>
      </tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </div>
</div></body></html>""")


@app.route("/new", methods=["GET", "POST"])
def new_project():
    if request.method == "POST":
        title     = request.form.get("title", "").strip()
        level     = request.form.get("level", "bsc")
        file      = request.files.get("guideline")
        s = ProjectSession.new(title=title, level=level)

        if file and file.filename:
            ext = Path(file.filename).suffix.lower()
            if ext in ALLOWED_EXT:
                tmp = UPLOAD_DIR / f"{s.session_id}_{file.filename}"
                file.save(str(tmp))
                try:
                    text = extract_text(tmp)
                    s.guideline_raw = text
                    s.add_file(file.filename, text)
                    meta = parse_guideline(text)
                    if title: meta.title = title
                    if level:
                        meta.level = EducationLevel.detect(level)
                    s.metadata = meta
                    if title: s.metadata.title = title
                except Exception as e:
                    pass
        _save(s)
        return redirect(url_for("session_view", sid=s.session_id))

    levels = [("ond","OND"),("hnd","HND"),("bsc","B.Sc"),
              ("pgd","PGD"),("msc","M.Sc"),("phd","Ph.D")]
    opts = "".join(f'<option value="{v}"{"selected" if v=="bsc" else ""}>{l}</option>'
                   for v, l in levels)

    return render_template_string(f"""<!DOCTYPE html><html><head>
<title>New Project — RAT</title>{BASE_STYLE}</head><body>
{NAV}
<div class="container" style="max-width:700px">
  <div class="page-title">New Research Project</div>
  <div class="page-sub">Start by entering your study title and optionally uploading a guideline</div>
  <div class="card">
    <form method="POST" enctype="multipart/form-data">
      <div class="form-group">
        <label>Study Title</label>
        <input type="text" name="title" placeholder="e.g. Pattern of Caregiver Satisfaction with Immunization Services…" required>
      </div>
      <div class="form-group">
        <label>Academic Level</label>
        <select name="level">{opts}</select>
      </div>
      <div class="form-group">
        <label>Project Guideline (optional — .docx, .pdf, .txt, .md)</label>
        <div class="drop-zone" onclick="document.getElementById('gfile').click()"
             ondragover="this.classList.add('dragover');event.preventDefault()"
             ondragleave="this.classList.remove('dragover')"
             ondrop="this.classList.remove('dragover');document.getElementById('gfile').files=event.dataTransfer.files;event.preventDefault()">
          <div class="icon">📄</div>
          <div class="dz-text">Drag & drop your guideline here, or click to browse</div>
          <input type="file" id="gfile" name="guideline" accept=".docx,.pdf,.txt,.md" style="display:none">
        </div>
      </div>
      <button type="submit" class="btn btn-gold" onclick="document.getElementById('loading-overlay').classList.add('show');document.getElementById('loading-msg').textContent='Creating session…'">
        Create Project →
      </button>
    </form>
  </div>
</div></body></html>""")


@app.route("/session/<sid>")
def session_view(sid):
    s = _load(sid)
    if not s:
        return redirect(url_for("index"))

    m = s.metadata
    ch_cards = ""
    for n in range(1, 6):
        ch    = s.chapters.get(n)
        title = CHAPTER_TITLES[n]
        if ch:
            wc    = f"{ch.word_count:,} words"
            badge = '<span class="badge badge-done">✓ Done</span>'
            actions = f"""
              <a href="/session/{sid}/chapter/{n}" class="btn btn-ghost btn-sm">View</a>
              <a href="/session/{sid}/revise/{n}" class="btn btn-ghost btn-sm">Revise</a>"""
        else:
            wc    = "Not written"
            badge = '<span class="badge badge-pending">Pending</span>'
            actions = f"""
              <a href="/session/{sid}/write/{n}" class="btn btn-gold btn-sm"
                 onclick="showLoading('Writing Chapter {n}… this takes ~30s')">Write</a>"""

        ch_cards += f"""
        <div class="ch-card {'done' if ch else ''}">
          <div class="ch-num">Chapter {n}</div>
          <div class="ch-title">{title}</div>
          <div class="ch-wc text-sm">{wc}</div>
          <div style="margin-top:0.4rem">{badge}</div>
          <div class="ch-actions">{actions}</div>
        </div>"""

    done_count = len(s.chapters_done)
    pct = int(done_count / 5 * 100)

    return render_template_string(f"""<!DOCTYPE html><html><head>
<title>{m.title[:40] or sid} — RAT</title>{BASE_STYLE}</head><body>
{NAV}
<script>
function showLoading(msg) {{
  document.getElementById('loading-overlay').classList.add('show');
  document.getElementById('loading-msg').textContent = msg || 'Working…';
}}
</script>
<div class="container">
  <div style="display:flex;justify-content:space-between;align-items:start;flex-wrap:wrap;gap:1rem">
    <div>
      <div class="page-title">{m.title or '(Untitled Project)'}</div>
      <div class="page-sub">
        <span class="badge badge-gold">{m.level.value.upper()}</span>&nbsp;
        {m.institution or ''}&nbsp;·&nbsp;Session: <code class="font-mono">{sid}</code>
      </div>
    </div>
    <div style="display:flex;gap:0.6rem;flex-wrap:wrap">
      <a href="/session/{sid}/upload" class="btn btn-ghost btn-sm">📎 Upload File</a>
      <a href="/session/{sid}/feedback" class="btn btn-ghost btn-sm">💬 Feedback</a>
      <a href="/session/{sid}/syncspss" class="btn btn-ghost btn-sm"
         onclick="showLoading('Syncing SPSS…')">🔄 Sync SPSS</a>
      <a href="/session/{sid}/build" class="btn btn-ghost btn-sm"
         onclick="showLoading('Generating study files…')">🔨 Build Dataset</a>
      <a href="/session/{sid}/ch4data" class="btn btn-purple btn-sm"
         onclick="showLoading('Writing Ch4 with real data… ~45s')">📊 Ch4 + Data</a>
      <a href="/session/{sid}/similarity" class="btn btn-ghost btn-sm">Similarity</a>
      <a href="/session/{sid}/apareport" class="btn btn-ghost btn-sm" onclick="showLoading('Generating APA report...')">APA Report</a>
      <a href="/session/{sid}/citecheck" class="btn btn-ghost btn-sm">📊 Cite Check</a>
      <a href="/session/{sid}/pdfexport" class="btn btn-ghost btn-sm"
         onclick="showLoading('Exporting PDF…')">📄 PDF Export</a>
      <a href="/session/{sid}/exportrefs?format=bib" class="btn btn-ghost btn-sm">📚 BibTeX</a>
      <a href="/session/{sid}/exportrefs?format=ris" class="btn btn-ghost btn-sm">📚 RIS</a>
      <a href="/session/{sid}/references" class="btn btn-ghost btn-sm"
         onclick="showLoading('Generating references…')">📚 References</a>
      <a href="/session/{sid}/fullexport" class="btn btn-green btn-sm"
         onclick="showLoading('Exporting full document…')">⬇ Export .docx</a>
    </div>
  </div>

  <div class="card mt-2">
    <div style="display:flex;justify-content:space-between;align-items:center">
      <span class="text-sm text-light">{done_count}/5 chapters complete</span>
      <span class="text-sm text-gold">{pct}%</span>
    </div>
    <div class="progress mt-1"><div class="progress-bar" style="width:{pct}%"></div></div>
  </div>

  <div class="card">
    <div class="card-title">Chapters</div>
    <div class="ch-grid">{ch_cards}</div>
  </div>

  <div class="card">
    <div class="card-title">Project Metadata</div>
    <table>
      <tr><th>Field</th><th>Value</th></tr>
      <tr><td>Level</td><td>{m.level.value.upper()}</td></tr>
      <tr><td>Research Design</td><td>{m.research_design.value.replace("_"," ").title()}</td></tr>
      <tr><td>Institution</td><td>{m.institution or '—'}</td></tr>
      <tr><td>Department</td><td>{m.department or '—'}</td></tr>
      <tr><td>Population</td><td>{m.population or '—'}</td></tr>
      <tr><td>Citation Style</td><td>{m.citation_style}</td></tr>
      <tr><td>Objectives</td><td>{len(m.objectives)} defined</td></tr>
      <tr><td>Uploaded Files</td><td>{', '.join(s.uploaded_files.keys()) or 'None'}</td></tr>
      <tr><td>Pipeline Run</td><td>{'✅ Yes' if s.pipeline_run else '❌ No'}</td></tr>
    </table>
  </div>
</div></body></html>""")


@app.route("/session/<sid>/write/<int:n>")
def write_ch(sid, n):
    s = _load(sid)
    if not s: return redirect(url_for("index"))
    api_key = _api_key()
    if not api_key:
        flash("OPENAI_API_KEY not set in environment.", "error")
        return redirect(url_for("session_view", sid=sid))
    try:
        write_chapter(s, n, api_key=api_key)
        _save(s)
        flash(f"Chapter {n} written successfully ({s.chapters[n].word_count:,} words).", "success")
    except Exception as exc:
        flash(f"Error writing Chapter {n}: {exc}", "error")
    return redirect(url_for("session_view", sid=sid))


@app.route("/session/<sid>/chapter/<int:n>")
def view_chapter(sid, n):
    s  = _load(sid)
    if not s: return redirect(url_for("index"))
    ch = s.get_chapter(n)
    if not ch:
        flash("Chapter not written yet.", "error")
        return redirect(url_for("session_view", sid=sid))

    content_html = ch.content.replace("\n", "<br>").replace("## ", "<h3 style='color:var(--gold);margin:1rem 0 0.3rem'>").replace("# ", "<h2 style='color:var(--gold);margin:1.5rem 0 0.5rem'>")

    return render_template_string(f"""<!DOCTYPE html><html><head>
<title>Ch {n} — RAT</title>{BASE_STYLE}</head><body>
{NAV}
<div class="container">
  <div style="display:flex;justify-content:space-between;align-items:center">
    <div class="page-title">Chapter {n}: {CHAPTER_TITLES[n]}</div>
    <div style="display:flex;gap:0.6rem">
      <a href="/session/{sid}/revise/{n}" class="btn btn-ghost btn-sm">✏️ Revise</a>
      <a href="/session/{sid}" class="btn btn-ghost btn-sm">← Back</a>
    </div>
  </div>
  <div class="page-sub">{ch.word_count:,} words · {ch.generated_at[:10]} · {ch.status}</div>
  <div class="card" style="line-height:1.8;font-size:0.95rem">
    {content_html}
  </div>
  <div class="text-sm text-light" style="margin-top:0.5rem">{ch.model_notes}</div>
</div></body></html>""")


@app.route("/session/<sid>/revise/<int:n>", methods=["GET", "POST"])
def revise_ch(sid, n):
    s  = _load(sid)
    if not s: return redirect(url_for("index"))

    if request.method == "POST":
        instruction = request.form.get("instruction", "").strip()
        if not instruction:
            flash("Please enter a revision instruction.", "error")
            return redirect(url_for("revise_ch", sid=sid, n=n))
        api_key = _api_key()
        if not api_key:
            flash("OPENAI_API_KEY not set.", "error")
            return redirect(url_for("session_view", sid=sid))
        try:
            revise_chapter(s, n, instruction, api_key=api_key)
            _save(s)
            flash(f"Chapter {n} revised successfully.", "success")
            return redirect(url_for("view_chapter", sid=sid, n=n))
        except Exception as exc:
            flash(f"Revision failed: {exc}", "error")
            return redirect(url_for("session_view", sid=sid))

    return render_template_string(f"""<!DOCTYPE html><html><head>
<title>Revise Ch {n} — RAT</title>{BASE_STYLE}</head><body>
{NAV}
<script>
function showLoading(msg) {{
  document.getElementById('loading-overlay').classList.add('show');
  document.getElementById('loading-msg').textContent = msg || 'Working…';
}}
</script>
<div class="container" style="max-width:700px">
  <div class="page-title">Revise Chapter {n}: {CHAPTER_TITLES[n]}</div>
  <div class="page-sub">Enter an instruction describing exactly what to change</div>
  <div class="card">
    <form method="POST">
      <div class="form-group">
        <label>Revision Instruction</label>
        <textarea name="instruction" placeholder="Examples:
• Make the problem statement more specific and focused
• Add more detail to the methodology section about sampling
• Supervisor says the literature review is too descriptive — make it more critical
• Expand the significance of the study section
• Improve the hypothesis testing in line with cross-sectional design" required></textarea>
      </div>
      <button type="submit" class="btn btn-gold"
        onclick="showLoading('Revising Chapter {n}… ~30 seconds')">
        Apply Revision →
      </button>
      <a href="/session/{sid}/chapter/{n}" class="btn btn-ghost" style="margin-left:0.5rem">Cancel</a>
    </form>
  </div>
</div></body></html>""")


@app.route("/session/<sid>/upload", methods=["GET", "POST"])
def upload_file(sid):
    s = _load(sid)
    if not s: return redirect(url_for("index"))

    if request.method == "POST":
        file = request.files.get("file")
        if file and file.filename:
            ext = Path(file.filename).suffix.lower()
            if ext in ALLOWED_EXT:
                tmp = UPLOAD_DIR / f"{sid}_{file.filename}"
                file.save(str(tmp))
                try:
                    text = extract_text(tmp)
                    s.add_file(file.filename, text)
                    if not s.guideline_raw:
                        s.guideline_raw = text
                        meta = parse_guideline(text)
                        for attr in ("objectives","research_questions","hypotheses",
                                     "institution","department","population"):
                            if not getattr(s.metadata, attr) and getattr(meta, attr):
                                setattr(s.metadata, attr, getattr(meta, attr))
                    _save(s)
                    flash(f"File '{file.filename}' uploaded and processed.", "success")
                except Exception as exc:
                    flash(f"Upload failed: {exc}", "error")
            else:
                flash(f"Unsupported file type: {ext}. Use .docx/.pdf/.txt/.md", "error")
        return redirect(url_for("session_view", sid=sid))

    return render_template_string(f"""<!DOCTYPE html><html><head>
<title>Upload — RAT</title>{BASE_STYLE}</head><body>
{NAV}
<div class="container" style="max-width:600px">
  <div class="page-title">Upload File</div>
  <div class="page-sub">Add a guideline, existing draft, or reference document</div>
  <div class="card">
    <form method="POST" enctype="multipart/form-data">
      <div class="form-group">
        <label>File (.docx, .pdf, .txt, .md)</label>
        <input type="file" name="file" accept=".docx,.pdf,.txt,.md" required>
      </div>
      <button type="submit" class="btn btn-gold">Upload →</button>
      <a href="/session/{sid}" class="btn btn-ghost" style="margin-left:0.5rem">Cancel</a>
    </form>
  </div>
</div></body></html>""")


@app.route("/session/<sid>/build")
def build_dataset(sid):
    s = _load(sid)
    if not s: return redirect(url_for("index"))
    api_key = _api_key()
    try:
        from research_engine.writer.questionnaire_builder import save_study_files
        created = save_study_files(s, ROOT, api_key=api_key)
        _save(s)
        flash(f"Study files created: {', '.join(created.keys())}. Run 'python main.py run --study project_{sid}' to generate dataset.", "success")
    except Exception as exc:
        flash(f"Build failed: {exc}", "error")
    return redirect(url_for("session_view", sid=sid))


@app.route("/session/<sid>/ch4data")
def ch4_with_data(sid):
    s = _load(sid)
    if not s: return redirect(url_for("index"))
    api_key = _api_key()
    if not api_key:
        flash("OPENAI_API_KEY not set.", "error")
        return redirect(url_for("session_view", sid=sid))
    try:
        from research_engine.writer.chapter4_bridge import write_chapter4_with_data
        write_chapter4_with_data(s, ROOT, api_key=api_key)
        _save(s)
        flash("Chapter 4 written with real analysis data.", "success")
    except Exception as exc:
        flash(f"Ch4 generation failed: {exc}", "error")
    return redirect(url_for("session_view", sid=sid))


@app.route("/session/<sid>/references")
def gen_references(sid):
    s = _load(sid)
    if not s: return redirect(url_for("index"))
    api_key = _api_key()
    try:
        refs = generate_references(s, api_key=api_key)
        out  = OUTPUT_DIR / f"project_{sid}" 
        out.mkdir(exist_ok=True)
        path = out / "references.txt"
        path.write_text(refs.to_text(), encoding="utf-8")
        flash(f"{len(refs)} references generated. Download at /session/{sid}/dl/references", "success")
    except Exception as exc:
        flash(f"Reference generation failed: {exc}", "error")
    return redirect(url_for("session_view", sid=sid))


@app.route("/session/<sid>/fullexport")
def full_export(sid):
    s = _load(sid)
    if not s: return redirect(url_for("index"))
    api_key = _api_key()
    try:
        refs = generate_references(s, api_key=api_key) if s.chapters else None
        out  = OUTPUT_DIR / f"project_{sid}"
        out.mkdir(exist_ok=True)
        path = out / f"{sid}_project.docx"
        export_project_docx(s, path, reference_list=refs)
        return send_file(str(path), as_attachment=True,
                        download_name=f"{sid}_research_project.docx")
    except Exception as exc:
        flash(f"Export failed: {exc}", "error")
        return redirect(url_for("session_view", sid=sid))



@app.route("/session/<sid>/feedback", methods=["GET", "POST"])
def supervisor_feedback(sid):
    s = _load(sid)
    if not s: return redirect(url_for("index"))

    if request.method == "POST":
        text = request.form.get("feedback_text", "").strip()
        file = request.files.get("feedback_file")
        if file and file.filename:
            try:
                from research_engine.writer import extract_text
                tmp = UPLOAD_DIR / f"{sid}_feedback_{file.filename}"
                file.save(str(tmp))
                text = extract_text(tmp)
            except Exception as exc:
                flash(f"Could not read file: {exc}", "error")
                return redirect(url_for("supervisor_feedback", sid=sid))

        if not text:
            flash("Please enter feedback text or upload a file.", "error")
            return redirect(url_for("supervisor_feedback", sid=sid))

        api_key = _api_key()
        if not api_key:
            flash("OPENAI_API_KEY not set.", "error")
            return redirect(url_for("session_view", sid=sid))

        try:
            from research_engine.writer import parse_feedback, apply_feedback
            items   = parse_feedback(text)
            revised = apply_feedback(s, items, api_key=api_key)
            _save(s)
            flash(f"Applied {len(items)} feedback items. Revised chapters: {list(revised.keys())}.", "success")
        except Exception as exc:
            flash(f"Feedback processing failed: {exc}", "error")
        return redirect(url_for("session_view", sid=sid))

    return render_template_string(f"""<!DOCTYPE html><html><head>
<title>Supervisor Feedback — RAT</title>{BASE_STYLE}</head><body>
{NAV}
<script>function showLoading(m){{document.getElementById("loading-overlay").classList.add("show");document.getElementById("loading-msg").textContent=m||"Working…";}}</script>
<div class="container" style="max-width:700px">
  <div class="page-title">💬 Supervisor Feedback</div>
  <div class="page-sub">Paste your supervisor's comments — each item will be mapped to the right chapter and revised automatically</div>
  <div class="card">
    <form method="POST" enctype="multipart/form-data">
      <div class="form-group">
        <label>Paste Feedback (numbered list works best)</label>
        <textarea name="feedback_text" placeholder="Examples:
1. The problem statement in chapter one is too broad
2. The literature review lacks critical synthesis
3. Show the Yamane formula with actual values in methodology
4. Table 4.3 needs a proper heading and source note
5. The conclusion must draw implications, not just restate findings" style="min-height:200px"></textarea>
      </div>
      <div class="form-group">
        <label>Or Upload Feedback File (.docx / .txt)</label>
        <input type="file" name="feedback_file" accept=".docx,.txt,.pdf">
      </div>
      <button type="submit" class="btn btn-gold"
        onclick="showLoading('Applying supervisor feedback… ~60 seconds')">
        Apply Feedback →
      </button>
      <a href="/session/{sid}" class="btn btn-ghost" style="margin-left:0.5rem">Cancel</a>
    </form>
  </div>
  <div class="card" style="margin-top:1rem">
    <div class="card-title">How it works</div>
    <div class="text-sm text-light" style="line-height:1.8">
      Each feedback item is automatically mapped to its chapter based on keywords
      ("literature review" → Ch 2, "methodology" → Ch 3, etc.). Items for the same
      chapter are combined into one revision call to save time and credits.
    </div>
  </div>
</div></body></html>""")


@app.route("/session/<sid>/syncspss")
def sync_spss(sid):
    s = _load(sid)
    if not s: return redirect(url_for("index"))
    api_key = _api_key()
    study_dir = ROOT / "studies" / f"project_{sid}"
    if not study_dir.exists():
        flash("No study directory found. Run 'Build Dataset' first.", "error")
        return redirect(url_for("session_view", sid=sid))
    try:
        from research_engine.writer import write_methods_section
        write_methods_section(s, study_dir, api_key=api_key)
        _save(s)
        flash("Chapter 3 instrument section synced with questionnaire data.", "success")
    except Exception as exc:
        flash(f"Sync failed: {exc}", "error")
    return redirect(url_for("session_view", sid=sid))



@app.route("/session/<sid>/citecheck")
def citecheck(sid):
    s = _load(sid)
    if not s: return redirect(url_for("index"))
    from research_engine.writer import score_session, suggest_improvements
    reports = score_session(s)
    html_parts = []
    for n in sorted(reports.keys()):
        r = reports[n]
        grade_color = "var(--green)" if r.score >= 70 else "var(--gold)" if r.score >= 50 else "var(--red)"
        html_parts.append(f"""
        <div class="card">
          <div style="display:flex;justify-content:space-between;align-items:center">
            <span class="card-title">Chapter {n}</span>
            <span style="font-size:1.4rem;font-weight:700;color:{grade_color}">{r.score:.0f} <span style="font-size:0.9rem">({r.grade})</span></span>
          </div>
          <div class="text-sm text-light" style="margin-top:0.5rem">
            Citations: {r.total_citations} | Unique authors: {r.unique_authors} | Per 200 words: {r.citations_per_200:.2f}
          </div>
          {"".join(f'<div class="alert alert-error" style="margin-top:0.5rem">{i}</div>' for i in r.issues) if r.issues else '<div class="alert alert-success" style="margin-top:0.5rem">No issues found ✅</div>'}
        </div>""")
    body = "".join(html_parts) or '<div class="card"><p class="text-light">No chapters written yet.</p></div>'
    return render_template_string(f"""<!DOCTYPE html><html><head>
<title>Citation Report — RAT</title>{BASE_STYLE}</head><body>
{NAV}
<div class="container">
  <div class="page-title">📊 Citation Diversity Report</div>
  <div class="page-sub">Plagiarism-safe citation analysis across all chapters</div>
  {body}
  <a href="/session/{sid}" class="btn btn-ghost" style="margin-top:1rem">← Back to Project</a>
</div></body></html>""")


@app.route("/session/<sid>/pdfexport")
def pdf_export_route(sid):
    s = _load(sid)
    if not s: return redirect(url_for("index"))
    api_key = _api_key()
    try:
        from research_engine.exporters.pdf_exporter import export_project_pdf
        from research_engine.writer import generate_references
        refs = generate_references(s, api_key=api_key) if s.chapters else None
        out = OUTPUT_DIR / f"project_{sid}"
        out.mkdir(exist_ok=True)
        path = out / f"{sid}_project.pdf"
        export_project_pdf(s, path, reference_list=refs)
        return send_file(str(path), as_attachment=True, download_name=f"{sid}_research_project.pdf")
    except Exception as exc:
        flash(f"PDF export failed: {exc}", "error")
        return redirect(url_for("session_view", sid=sid))



@app.route("/session/<sid>/similarity")
def similarity_check(sid):
    s = _load(sid)
    if not s: return redirect(url_for("index"))
    from research_engine.writer import estimate_session
    reports = estimate_session(s)
    parts = []
    for n in sorted(reports.keys()):
        r = reports[n]
        color = "var(--green)" if r.estimated_similarity < 15 else "var(--gold)" if r.estimated_similarity < 35 else "var(--red)"
        flags_html = ""
        if r.flags:
            for f in r.flags[:5]:
                flags_html += '<div class="alert alert-error" style="margin-top:0.3rem;font-size:0.8rem"><b>[' + format(f.score, ".0%") + ']</b> ' + f.text[:70] + '...<br><span class="text-light">' + f.reason + '</span></div>'
        parts.append('<div class="card"><div style="display:flex;justify-content:space-between;align-items:center"><span class="card-title">Chapter ' + str(n) + '</span><span style="font-size:1.4rem;font-weight:700;color:' + color + '">~' + format(r.estimated_similarity, ".0f") + '% <span style="font-size:0.9rem">(' + r.grade + ')</span></span></div><div class="text-sm text-light" style="margin-top:0.5rem">Sentences: ' + str(r.total_sentences) + ' | Flagged: ' + str(r.flagged_sentences) + ' | High risk: ' + str(r.high_risk_sentences) + '</div><div class="text-sm" style="margin-top:0.3rem">' + r.recommendation + '</div>' + flags_html + '</div>')
    body = "".join(parts) or '<div class="card"><p class="text-light">No chapters written yet.</p></div>'
    return render_template_string('<!DOCTYPE html><html><head><title>Similarity Check - RAT</title>' + BASE_STYLE + '</head><body>' + NAV + '<div class="container"><div class="page-title">Similarity Estimation</div><div class="page-sub">Heuristic estimate of likely Turnitin similarity</div>' + body + '<a href="/session/' + sid + '" class="btn btn-ghost" style="margin-top:1rem">Back</a></div></body></html>')


@app.route("/session/<sid>/apareport")
def apa_report_route(sid):
    s = _load(sid)
    if not s: return redirect(url_for("index"))
    try:
        from research_engine.exporters.apa_report import generate_apa_report
        from research_engine.workflow import Pipeline
        import importlib.util
        study_dir = ROOT / "studies" / ("project_" + sid)
        if not study_dir.exists():
            flash("No study directory found. Run Build Dataset first.", "error")
            return redirect(url_for("session_view", sid=sid))
        run_path = study_dir / "run.py"
        if run_path.exists():
            spec = importlib.util.spec_from_file_location("run", str(run_path))
            runmod = importlib.util.module_from_spec(spec); spec.loader.exec_module(runmod)
            pipeline = Pipeline(study_dir, output_dir=OUTPUT_DIR / ("project_" + sid), seed=42,
                              ordinal_maps=runmod.ORDINAL_MAPS, spss_maps=runmod.SPSS_MAPS,
                              crosstab_pairs=runmod.CROSSTAB_PAIRS)
        else:
            pipeline = Pipeline(study_dir, output_dir=OUTPUT_DIR / ("project_" + sid), seed=42)
        pipeline.analyse()
        apa = generate_apa_report(pipeline, session=s)
        safe_text = apa.full_text.replace("<", "&lt;").replace(">", "&gt;")
        return render_template_string('<!DOCTYPE html><html><head><title>APA Report - RAT</title>' + BASE_STYLE + '</head><body>' + NAV + '<div class="container"><div class="page-title">APA Statistical Report</div><div class="page-sub">' + str(apa.word_count) + ' words - APA 7th edition format</div><div class="card" style="line-height:1.8;font-size:0.9rem;white-space:pre-wrap">' + safe_text + '</div><a href="/session/' + sid + '" class="btn btn-ghost" style="margin-top:1rem">Back</a></div></body></html>')
    except Exception as exc:
        flash("APA report failed: " + str(exc), "error")
        return redirect(url_for("session_view", sid=sid))



@app.route("/session/<sid>/exportrefs")
def export_refs_route(sid):
    s = _load(sid)
    if not s: return redirect(url_for("index"))
    fmt = request.args.get("format", "bib")
    try:
        from research_engine.writer import generate_references
        from research_engine.writer.reference_manager import (
            export_bibtex, export_ris, export_to_zotero, export_to_mendeley
        )
        api_key = _api_key()
        ref_list = generate_references(s, api_key=api_key)
        out = OUTPUT_DIR / ("project_" + sid)
        out.mkdir(exist_ok=True)
        if fmt in ("bib", "bibtex", "zotero"):
            path = export_bibtex(ref_list, out / "references.bib")
            return send_file(str(path), as_attachment=True, download_name="references.bib")
        elif fmt in ("ris", "mendeley"):
            path = export_ris(ref_list, out / "references.ris")
            return send_file(str(path), as_attachment=True, download_name="references.ris")
        flash("Unknown format. Use ?format=bib or ?format=ris", "error")
        return redirect(url_for("session_view", sid=sid))
    except Exception as exc:
        flash("Export failed: " + str(exc), "error")
        return redirect(url_for("session_view", sid=sid))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"\n  🔬 Research Analysis Toolkit — Web UI")
    print(f"  Open: http://localhost:{port}\n")
    if not _api_key():
        print("  ⚠️  OPENAI_API_KEY not set — chapter writing will not work")
        print("     Set it with: export OPENAI_API_KEY=sk-...\n")
    app.run(host="0.0.0.0", port=port, debug=False)
