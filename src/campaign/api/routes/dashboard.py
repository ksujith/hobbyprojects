"""Minimal single-page dashboard — vanilla JS, one HTML blob."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy import desc, func, select

from campaign.db import models as m
from campaign.db.session import session_scope

router = APIRouter(tags=["dashboard"])


_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>Campaign v2 — B2B Outreach Agent</title>
<meta name="viewport" content="width=device-width,initial-scale=1" />
<style>
  :root {
    --bg: #0b1020; --card: #131a2e; --line: #1e2744; --muted: #8b95b2;
    --text: #eef1fb; --accent: #7ee0ff; --good: #5ee0a3; --warn: #f5a25c;
    --bad: #f06b6b; --high: #5ee0a3; --med: #f5a25c; --low: #8b95b2;
  }
  * { box-sizing: border-box; }
  body { margin: 0; font: 14px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
         background: var(--bg); color: var(--text); }
  .wrap { max-width: 1180px; margin: 0 auto; padding: 32px 22px 80px; }
  h1 { font-size: 22px; margin: 0 0 2px; letter-spacing: -0.01em; }
  h1 .v { color: var(--muted); font-weight: 400; font-size: 13px; margin-left: 8px; }
  p.sub { color: var(--muted); margin: 0 0 22px; }
  h2 { font-size: 12px; text-transform: uppercase; letter-spacing: 0.1em;
       color: var(--muted); margin: 28px 0 10px; font-weight: 600; }
  .card { background: var(--card); border: 1px solid var(--line); border-radius: 10px;
          padding: 18px; margin-bottom: 14px; }
  form { display: grid; gap: 10px; grid-template-columns: repeat(2, 1fr); }
  form .span-2 { grid-column: 1 / 3; }
  input, select, textarea {
    background: #0e1528; color: var(--text); border: 1px solid var(--line);
    border-radius: 8px; padding: 9px 11px; font: inherit; width: 100%;
  }
  textarea { min-height: 60px; resize: vertical; }
  button { background: var(--accent); color: #001a22; border: 0; border-radius: 8px;
           padding: 10px 18px; font-weight: 700; cursor: pointer; }
  button.ghost { background: transparent; color: var(--text); border: 1px solid var(--line); font-weight: 500; }
  button:disabled { opacity: 0.4; cursor: wait; }
  table { width: 100%; border-collapse: collapse; }
  th, td { text-align: left; padding: 8px 10px; border-bottom: 1px solid var(--line);
           vertical-align: top; font-size: 13.5px; }
  th { color: var(--muted); font-weight: 600; font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; }
  tr.row { cursor: pointer; }
  tr.row:hover { background: #182140; }
  .pill { display: inline-block; padding: 2px 9px; border-radius: 99px; font-size: 11px;
          font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; }
  .pill.pending   { background: #2a2f48; color: var(--muted); }
  .pill.running   { background: #1f3a5c; color: var(--accent); }
  .pill.succeeded { background: #1c3a2c; color: var(--good); }
  .pill.failed    { background: #3d1c1c; color: var(--bad); }
  .pill.high { background: #1c3a2c; color: var(--good); }
  .pill.medium { background: #3d2a1c; color: var(--warn); }
  .pill.low { background: #23283d; color: var(--muted); }
  .two-col { display: grid; grid-template-columns: 1.4fr 1fr; gap: 16px; }
  @media (max-width: 900px) { .two-col { grid-template-columns: 1fr; } form { grid-template-columns: 1fr; } }
  .draft { border-left: 2px solid var(--accent); padding: 10px 14px; margin: 10px 0;
           background: #0e1528; border-radius: 6px; white-space: pre-wrap;
           font-family: ui-monospace, Menlo, monospace; font-size: 12.5px; }
  .meta { color: var(--muted); font-size: 12px; margin: 4px 0 8px; }
  .bant { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin: 6px 0 10px; }
  .bant div { text-align: center; padding: 6px; background: #0e1528; border-radius: 6px; }
  .bant div b { display: block; font-size: 17px; }
  .bant div span { color: var(--muted); font-size: 11px; text-transform: uppercase; }
  .empty { color: var(--muted); text-align: center; padding: 18px; }
  code { font-family: ui-monospace, Menlo, monospace; font-size: 11.5px;
         background: #0e1528; padding: 1px 6px; border-radius: 4px; color: var(--accent); }
</style>
</head>
<body>
<div class="wrap">
  <h1>Campaign v2 <span class="v">— B2B Outreach Agent</span></h1>
  <p class="sub">Submit a lead with a sender persona. The agent analyzes BANT, looks up the company, and drafts personalized outreach.</p>

  <div class="two-col">
    <div>
      <h2>Start a campaign</h2>
      <div class="card">
        <form id="f">
          <select id="persona_id" required></select>
          <input id="industry" placeholder="Industry" required />
          <input id="company_name" placeholder="Company name" required class="span-2" />
          <input id="decision_maker" placeholder="Decision maker (name)" required />
          <input id="position" placeholder="Position / title" required />
          <textarea id="milestone" class="span-2" placeholder="Recent milestone (e.g. Series B funding, product launch)" required></textarea>
          <input id="prospect_email" type="email" class="span-2" placeholder="Prospect email (optional)" />
          <div class="span-2" style="display:flex;gap:10px;align-items:center">
            <button id="go" type="submit">Run campaign</button>
            <button id="new-persona" type="button" class="ghost">+ new persona</button>
          </div>
        </form>
      </div>
    </div>

    <div>
      <h2>Recent runs</h2>
      <div class="card" id="runs"></div>
    </div>
  </div>

  <div id="detail"></div>
</div>

<template id="new-persona-tpl">
  <form id="pform" style="grid-template-columns: 1fr 1fr">
    <input id="p_name" placeholder="Persona name" required />
    <input id="p_title" placeholder="Your title" required />
    <input id="p_company" placeholder="Your company" class="span-2" required />
    <textarea id="p_tone" class="span-2" placeholder="Tone guidelines (optional)"></textarea>
    <button type="submit">Save persona</button>
  </form>
</template>

<script>
const $ = (s) => document.querySelector(s);
const esc = (s) => (s ?? "").replace(/[&<>"']/g, c =>
  ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));

async function j(u, init) {
  const r = await fetch(u, init);
  if (!r.ok) throw new Error(`${u} → ${r.status}`);
  return r.status === 204 ? null : r.json();
}

async function loadPersonas() {
  const rows = await j("/api/personas");
  const sel = $("#persona_id");
  sel.innerHTML = rows.length
    ? rows.map(p => `<option value="${p.id}">${esc(p.name)} — ${esc(p.title)} @ ${esc(p.company)}</option>`).join("")
    : '<option value="" disabled selected>no personas — create one →</option>';
  return rows;
}

async function loadRuns() {
  const rows = await j("/api/campaigns");
  const el = $("#runs");
  if (!rows.length) { el.innerHTML = '<div class="empty">No runs yet.</div>'; return; }
  el.innerHTML = `<table><thead><tr><th>Lead</th><th>Priority</th><th>Status</th></tr></thead><tbody>
    ${rows.map(c => `<tr class="row" data-id="${c.id}">
      <td><code>${c.id.slice(0,8)}</code></td>
      <td>${c.priority ? `<span class="pill ${c.priority}">${c.priority}</span>` : '—'}</td>
      <td><span class="pill ${c.status}">${c.status}</span></td>
    </tr>`).join("")}</tbody></table>`;
  el.querySelectorAll("tr.row").forEach(r => r.addEventListener("click", () => loadDetail(r.dataset.id)));
}

async function loadDetail(id) {
  const [camp, analysis, drafts] = await Promise.all([
    j(`/api/campaigns/${id}`),
    j(`/api/campaigns/${id}/analysis`),
    j(`/api/campaigns/${id}/drafts`),
  ]);
  $("#detail").innerHTML = `
    <h2>Campaign · <span class="pill ${camp.status}">${camp.status}</span></h2>
    <div class="card">
      <div class="meta">id: <code>${camp.id}</code> · created ${camp.created_at?.replace('T',' ').slice(0,16)}</div>
    </div>

    <h2>Lead analysis (BANT)</h2>
    <div class="card">
      ${analysis ? `
        <div class="bant">
          <div><b>${analysis.bant.budget}</b><span>budget</span></div>
          <div><b>${analysis.bant.authority}</b><span>authority</span></div>
          <div><b>${analysis.bant.need}</b><span>need</span></div>
          <div><b>${analysis.bant.timeline}</b><span>timeline</span></div>
        </div>
        <div class="meta">priority <span class="pill ${analysis.priority}">${analysis.priority}</span>
          · fit <b>${(analysis.fit_score*100).toFixed(0)}%</b>
          · confidence ${analysis.confidence}</div>
        <div class="meta"><b>Pain points:</b> ${analysis.pain_points.map(esc).join(' · ')}</div>
        <div class="meta"><b>Value opportunities:</b> ${analysis.value_opportunities.map(esc).join(' · ')}</div>
      ` : '<div class="empty">no analysis yet</div>'}
    </div>

    <h2>Drafts (${drafts.length})</h2>
    <div class="card">
      ${drafts.map(d => `
        <div>
          <div class="meta"><b>v${d.version}</b> · personalization <b>${d.personalization_score}</b>
            · sentiment <b>${d.sentiment_score.toFixed(2)}</b>
            · words <b>${d.word_count}</b>
            ${d.ea_cc_applied ? `· <span class="pill medium">EA CC: ${esc(d.ea_cc_email)}</span>` : ''}</div>
          <div class="draft"><b>Subject:</b> ${esc(d.subject)}

${esc(d.body)}</div>
        </div>`).join('') || '<div class="empty">no drafts yet</div>'}
      ${drafts.length ? `
        <form id="refine-f" style="grid-template-columns: 1fr auto; margin-top: 10px">
          <input id="critique" placeholder="e.g. shorter, more casual, stronger CTA" />
          <button type="submit">Refine</button>
        </form>` : ''}
    </div>`;

  if (drafts.length) {
    $("#refine-f").addEventListener("submit", async (e) => {
      e.preventDefault();
      const critique = $("#critique").value.trim();
      if (!critique) return;
      await j(`/api/campaigns/${id}/drafts/refine`, {
        method: "POST", headers: {"Content-Type":"application/json"},
        body: JSON.stringify({critique}),
      });
      loadDetail(id);
    });
  }

  if (camp.status === "pending" || camp.status === "running") {
    setTimeout(() => { loadRuns(); loadDetail(id); }, 1500);
  }
}

$("#f").addEventListener("submit", async (e) => {
  e.preventDefault();
  const btn = $("#go"); btn.disabled = true; btn.textContent = "Running…";
  try {
    const payload = {
      persona_id: $("#persona_id").value,
      lead: {
        company_name: $("#company_name").value.trim(),
        industry: $("#industry").value.trim(),
        decision_maker: $("#decision_maker").value.trim(),
        position: $("#position").value.trim(),
        milestone: $("#milestone").value.trim(),
        prospect_email: $("#prospect_email").value.trim() || null,
      },
    };
    const res = await j("/api/campaigns", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify(payload),
    });
    await loadRuns();
    loadDetail(res.id);
  } finally { btn.disabled = false; btn.textContent = "Run campaign"; }
});

$("#new-persona").addEventListener("click", () => {
  const tpl = document.getElementById("new-persona-tpl").content.cloneNode(true);
  $("#f").innerHTML = "";
  $("#f").appendChild(tpl);
  $("#f").removeEventListener("submit", () => {});
  $("#pform").addEventListener("submit", async (e) => {
    e.preventDefault();
    await j("/api/personas", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({
        name: $("#p_name").value.trim(),
        title: $("#p_title").value.trim(),
        company: $("#p_company").value.trim(),
        tone_guidelines: $("#p_tone").value.trim(),
      }),
    });
    location.reload();
  });
});

(async () => {
  await loadPersonas();
  await loadRuns();
})();
</script>
</body>
</html>"""


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def dashboard() -> str:
    return _HTML


@router.get("/api/cost", include_in_schema=False)
async def cost() -> JSONResponse:
    """Aggregate LLM cost per caller."""
    async with session_scope() as db:
        rows = (
            await db.execute(
                select(
                    m.LLMCall.caller,
                    func.count(m.LLMCall.id),
                    func.sum(m.LLMCall.cost_usd),
                )
                .group_by(m.LLMCall.caller)
                .order_by(desc(func.sum(m.LLMCall.cost_usd)))
            )
        ).all()
    return JSONResponse(
        [{"caller": c, "calls": int(n), "cost_usd": round(float(s or 0), 6)} for c, n, s in rows]
    )
