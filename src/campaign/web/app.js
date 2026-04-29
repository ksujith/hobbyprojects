// Campaign v2 dashboard — vanilla JS, no build.
// Tabs: Campaigns · Inbox · Personas · Cost.

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

const esc = (s) =>
  (s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );

async function j(url, init) {
  const r = await fetch(url, init);
  if (!r.ok) throw new Error(`${url} → ${r.status}`);
  return r.status === 204 ? null : r.json();
}

// ─────────────────────────── Tab switching ───────────────────────────

function activateTab(name) {
  $$(".tab").forEach((t) => t.classList.toggle("active", t.dataset.tab === name));
  $$(".tab-panel").forEach((p) =>
    p.classList.toggle("active", p.id === `tab-${name}`)
  );
  history.replaceState(null, "", `#${name}`);
  // Lazy-load tab data each time it's shown.
  if (name === "inbox") loadInbox();
  if (name === "personas") loadPersonasTab();
  if (name === "cost") loadCost();
}

$$(".tab").forEach((t) =>
  t.addEventListener("click", () => activateTab(t.dataset.tab))
);

// ─────────────────────────── Campaigns tab ───────────────────────────

async function loadPersonas() {
  const rows = await j("/api/personas");
  const sel = $("#persona_id");
  sel.innerHTML = rows.length
    ? rows
        .map(
          (p) =>
            `<option value="${p.id}">${esc(p.name)} — ${esc(p.title)} @ ${esc(p.company)}</option>`
        )
        .join("")
    : '<option value="" disabled selected>no personas — create one ↓</option>';
  return rows;
}

async function loadRuns() {
  const rows = await j("/api/campaigns");
  const el = $("#runs");
  if (!rows.length) {
    el.innerHTML = '<div class="empty">No runs yet.</div>';
    return;
  }
  el.innerHTML = `<table><thead><tr><th>Lead</th><th>Priority</th><th>Status</th></tr></thead><tbody>
    ${rows
      .map(
        (c) => `<tr class="row" data-id="${c.id}">
      <td><code>${c.id.slice(0, 8)}</code></td>
      <td>${c.priority ? `<span class="pill ${c.priority}">${c.priority}</span>` : "—"}</td>
      <td><span class="pill ${c.status}">${c.status}</span></td>
    </tr>`
      )
      .join("")}</tbody></table>`;
  $$("tr.row", el).forEach((r) =>
    r.addEventListener("click", () => loadCampaignDetail(r.dataset.id))
  );
}

async function loadCampaignDetail(id) {
  const [camp, analysis, drafts, inbox] = await Promise.all([
    j(`/api/campaigns/${id}`),
    j(`/api/campaigns/${id}/analysis`),
    j(`/api/campaigns/${id}/drafts`),
    j(`/api/campaigns/${id}/inbox`),
  ]);

  $("#campaign-detail").innerHTML = `
    <h2>Campaign · <span class="pill ${camp.status}">${camp.status}</span></h2>
    <div class="card">
      <div class="meta">id: <code>${camp.id}</code> · created ${camp.created_at?.replace("T", " ").slice(0, 16)}</div>
    </div>

    <h2>Lead analysis (BANT)</h2>
    <div class="card">
      ${
        analysis
          ? `
        <div class="bant">
          <div><b>${analysis.bant.budget}</b><span>budget</span></div>
          <div><b>${analysis.bant.authority}</b><span>authority</span></div>
          <div><b>${analysis.bant.need}</b><span>need</span></div>
          <div><b>${analysis.bant.timeline}</b><span>timeline</span></div>
        </div>
        <div class="meta">priority <span class="pill ${analysis.priority}">${analysis.priority}</span>
          · fit <b>${(analysis.fit_score * 100).toFixed(0)}%</b>
          · confidence ${analysis.confidence}</div>
        <div class="meta"><b>Pain points:</b> ${analysis.pain_points.map(esc).join(" · ")}</div>
        <div class="meta"><b>Value opportunities:</b> ${analysis.value_opportunities.map(esc).join(" · ")}</div>
      `
          : '<div class="empty">no analysis yet</div>'
      }
    </div>

    <h2>Drafts (${drafts.length})</h2>
    <div class="card">
      ${drafts.length
        ? drafts.map((d) => renderDraft(d)).join("")
        : '<div class="empty">no drafts yet</div>'}

      ${drafts.length
        ? `<form id="refine-f" style="grid-template-columns: 1fr auto; margin-top: 10px">
             <input id="critique" placeholder="e.g. shorter, more casual, stronger CTA" />
             <button type="submit">Refine</button>
           </form>`
        : ""}

      ${drafts.length
        ? `<div class="sim-row">
             <span class="muted" style="margin-right:6px">Simulate reply →</span>
             ${["positive_interest", "needs_info", "not_interested", "out_of_office", "bounce"]
               .map(
                 (k) =>
                   `<button class="small ghost" data-sim="${k}">${k.replace(/_/g, " ")}</button>`
               )
               .join("")}
           </div>`
        : ""}
    </div>

    <h2>Thread replies (${inbox.length})</h2>
    <div class="card" id="thread-inbox">
      ${
        inbox.length
          ? inbox.map((m) => renderInbound(m, true)).join("")
          : '<div class="empty">no replies yet — use the Simulate reply buttons above</div>'
      }
    </div>`;

  // Refine
  if (drafts.length) {
    $("#refine-f").addEventListener("submit", async (e) => {
      e.preventDefault();
      const critique = $("#critique").value.trim();
      if (!critique) return;
      await j(`/api/campaigns/${id}/drafts/refine`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ critique }),
      });
      loadCampaignDetail(id);
    });

    $$(".sim-row button").forEach((b) =>
      b.addEventListener("click", async () => {
        await j(`/api/campaigns/${id}/inbox/simulate?kind=${b.dataset.sim}`, {
          method: "POST",
        });
        refreshInboxBadge();
        loadCampaignDetail(id);
      })
    );
  }

  // Send buttons on drafts
  $$("[data-send]").forEach((b) =>
    b.addEventListener("click", async () => {
      b.disabled = true;
      try {
        const r = await j(`/api/drafts/${b.dataset.send}/send`, { method: "POST" });
        b.textContent = r.simulated ? "✓ sent (simulated)" : "✓ sent";
      } catch {
        b.textContent = "✗ failed";
      }
    })
  );

  // Suggest reply buttons on inbound rows
  $$("[data-suggest]").forEach((b) =>
    b.addEventListener("click", async () => {
      b.disabled = true;
      try {
        await j(`/api/inbox/${b.dataset.suggest}/suggest-reply`, { method: "POST" });
        loadCampaignDetail(id);
      } catch {
        b.textContent = "✗ failed";
        b.disabled = false;
      }
    })
  );

  if (camp.status === "pending" || camp.status === "running") {
    setTimeout(() => {
      loadRuns();
      loadCampaignDetail(id);
    }, 1500);
  }
}

function renderDraft(d) {
  const eaTag = d.ea_cc_applied
    ? `· <span class="pill medium">EA CC: ${esc(d.ea_cc_email)}</span>`
    : "";
  return `<div>
    <div class="meta"><b>v${d.version}</b> · personalization <b>${d.personalization_score}</b>
      · sentiment <b>${d.sentiment_score.toFixed(2)}</b>
      · words <b>${d.word_count}</b> ${eaTag}
      <button class="small" data-send="${d.id}" style="margin-left:8px">Send</button>
    </div>
    <div class="draft"><b>Subject:</b> ${esc(d.subject)}

${esc(d.body)}</div>
  </div>`;
}

function renderInbound(m, withSuggest = false) {
  const from = m.from_name ? `${esc(m.from_name)} <${esc(m.from_email)}>` : esc(m.from_email);
  const body = esc(m.body).slice(0, 240) + (m.body.length > 240 ? "…" : "");
  const sug = withSuggest && m.needs_action && !m.suggested_reply_draft_id
    ? `<button class="small" data-suggest="${m.id}">Suggest reply</button>`
    : m.suggested_reply_draft_id
    ? `<span class="pill succeeded">reply drafted</span>`
    : "";
  return `<div class="inbox-item">
    <span class="pill ${m.classification}">${m.classification.replace(/_/g, " ")}</span>
    <div>
      <div class="from">${from}</div>
      <div class="meta">${esc(m.subject)}</div>
      <div class="preview">${body}</div>
    </div>
    <div class="right">
      <div class="meta">${(m.received_at ?? "").replace("T", " ").slice(0, 16)}</div>
      ${sug}
    </div>
  </div>`;
}

// Campaign submit
$("#camp-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const btn = $("#go");
  btn.disabled = true;
  btn.textContent = "Running…";
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
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    await loadRuns();
    loadCampaignDetail(res.id);
  } finally {
    btn.disabled = false;
    btn.textContent = "Run campaign";
  }
});

// Persona panel
function showPersonaPanel(show) {
  $("#persona-panel").hidden = !show;
  if (show) $("#p_name").focus();
}
$("#new-persona").addEventListener("click", () => showPersonaPanel(true));
$("#cancel-persona").addEventListener("click", () => showPersonaPanel(false));

$("#pform").addEventListener("submit", async (e) => {
  e.preventDefault();
  const payload = {
    name: $("#p_name").value.trim(),
    title: $("#p_title").value.trim(),
    company: $("#p_company").value.trim(),
    tone_guidelines: $("#p_tone").value.trim(),
  };
  const created = await j("/api/personas", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  $("#pform").reset();
  showPersonaPanel(false);
  await loadPersonas();
  $("#persona_id").value = created.id;
});

// ─────────────────────────── Inbox tab ───────────────────────────

async function loadInbox() {
  const filter = $("#inbox-filter").checked;
  const rows = await j(`/api/inbox?needs_action_only=${filter}`);
  $("#inbox-list").innerHTML = rows.length
    ? rows.map((m) => renderInbound(m, true)).join("")
    : '<div class="empty">inbox empty — trigger a "Simulate reply" from a campaign.</div>';
  refreshInboxBadge(rows);

  $$("#inbox-list [data-suggest]").forEach((b) =>
    b.addEventListener("click", async () => {
      b.disabled = true;
      try {
        await j(`/api/inbox/${b.dataset.suggest}/suggest-reply`, { method: "POST" });
        loadInbox();
      } catch {
        b.textContent = "✗ failed";
        b.disabled = false;
      }
    })
  );
}
$("#inbox-filter").addEventListener("change", loadInbox);

async function refreshInboxBadge(rows) {
  if (!rows) rows = await j("/api/inbox?needs_action_only=true");
  const badge = $("#inbox-badge");
  badge.hidden = !rows.some((m) => m.needs_action);
}

// ─────────────────────────── Personas / settings tab ───────────────────────────

async function loadPersonasTab() {
  const rows = await j("/api/personas");
  if (!rows.length) {
    $("#personas-list").innerHTML =
      '<div class="empty">No personas yet. Create one from the Campaigns tab.</div>';
    return;
  }

  const eaMap = {};
  for (const p of rows) {
    try {
      eaMap[p.id] = await j(`/api/personas/${p.id}/ea`);
    } catch {
      eaMap[p.id] = null;
    }
  }

  $("#personas-list").innerHTML = rows
    .map((p) => {
      const ea = eaMap[p.id];
      return `<div class="persona-row" data-persona="${p.id}">
        <div class="body">
          <span class="name">${esc(p.name)}</span>
          <span class="detail">${esc(p.title)} @ ${esc(p.company)}</span>
          <span class="detail">tone: ${esc(p.tone_guidelines || "—")}</span>
        </div>
        <div>
          <form class="ea-form" data-ea-form="${p.id}">
            <label class="toggle"><input type="checkbox" ${ea?.enabled ? "checked" : ""} /> Enable EA auto-CC</label>
            <input type="email" placeholder="ea@your-co.com" value="${esc(ea?.ea_email || "")}" />
            <button type="submit" class="small">Save</button>
          </form>
        </div>
      </div>`;
    })
    .join("");

  $$("[data-ea-form]").forEach((f) =>
    f.addEventListener("submit", async (e) => {
      e.preventDefault();
      const pid = f.dataset.eaForm;
      const enabled = f.querySelector("input[type=checkbox]").checked;
      const email = f.querySelector("input[type=email]").value.trim() || null;
      await j(`/api/personas/${pid}/ea`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled, ea_email: email }),
      });
      f.querySelector("button").textContent = "✓ saved";
      setTimeout(() => (f.querySelector("button").textContent = "Save"), 1200);
    })
  );
}

// ─────────────────────────── Cost tab ───────────────────────────

async function loadCost() {
  const rows = await j("/api/cost");
  const total = rows.reduce((s, r) => s + r.cost_usd, 0);
  $("#cost-badge").textContent = `$${total.toFixed(6)}`;
  $("#cost-list").innerHTML = rows.length
    ? `<table><thead><tr><th>Caller</th><th>Calls</th><th>Cost (USD)</th></tr></thead><tbody>
         ${rows
           .map(
             (r) => `<tr>
           <td><code>${esc(r.caller)}</code></td>
           <td>${r.calls}</td>
           <td>$${r.cost_usd.toFixed(6)}</td>
         </tr>`
           )
           .join("")}
       </tbody></table>`
    : '<div class="empty">no LLM calls recorded — set ANTHROPIC_API_KEY to exit demo mode.</div>';
}

// ─────────────────────────── Boot ───────────────────────────

(async () => {
  const personas = await loadPersonas();
  await loadRuns();
  await refreshInboxBadge();
  await loadCost();    // populates cost badge at top
  // Route from the URL hash so reloads preserve tab.
  const hash = location.hash.replace("#", "");
  if (["campaigns", "inbox", "personas", "cost"].includes(hash)) activateTab(hash);
  // First-visit UX: if no personas, open the create-persona panel.
  if (!personas.length) showPersonaPanel(true);
})();
