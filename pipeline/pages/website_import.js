// The website import of the Dataset page: the button `Import from website` and the merge
// dialog. The lab server serves this file at /website-import.js. The routes are in
// pipeline/website_import_routes.py. Read docs/plans/21_website-import-ui.md.
(function () {
  "use strict";
  const API = "/api/website-import";
  const button = document.getElementById("website-import");
  if (!button) return;

  const style = document.createElement("style");
  style.textContent = `
.website-dialog { width: min(1040px, 100%); }
.website-dialog h3 { margin: 16px 0 6px; font-size: 14px; display: flex; flex-wrap: wrap;
  gap: 8px; align-items: baseline; }
/* The title keeps one line. A long hint wraps next to it, or below it on a narrow screen. */
.website-dialog h3 .count { flex: 1 1 160px; color: var(--muted); font-weight: 400; }
.website-dialog h3 button { font-size: 11px; padding: 1px 7px; }
.website-dialog h3 button:first-of-type { margin-left: auto; }
.website-rows { display: grid; gap: 6px; }
.website-row { display: grid; grid-template-columns: auto 64px 1fr; gap: 10px;
  align-items: center; padding: 7px 9px; background: var(--panel-2);
  border: 1px solid var(--line); border-radius: 8px; }
.website-row.conflict { grid-template-columns: 1fr; }
.website-row.unset { border-color: var(--var); }
.website-row img, .website-choice img { width: 64px; height: 64px; object-fit: contain;
  background: var(--bg); border-radius: 6px; }
.website-row .no-image { width: 64px; height: 64px; border-radius: 6px;
  background: var(--bg); }
.website-row img, .website-choice img { cursor: zoom-in; }
/* The sign lets a click through to the image, so the click opens the large view. */
.website-row .missing-image { position: relative; width: 64px; height: 64px; }
.website-row .missing-image > img, .website-row .missing-image > .no-image { display: block; }
.website-row .missing-image svg { position: absolute; inset: 0; width: 100%; height: 100%;
  pointer-events: none; }
.website-row .title { font-weight: 600; }
.website-row .meta { color: var(--muted); font-size: 12px; overflow-wrap: anywhere; }
.website-preview { position: fixed; inset: 0; z-index: 60; padding: 24px; display: flex;
  flex-direction: column; gap: 10px; align-items: center; justify-content: center;
  background: rgba(7, 8, 12, .9); cursor: zoom-out; }
.website-preview[hidden] { display: none; }
.website-preview img { max-width: 100%; max-height: calc(100vh - 110px); object-fit: contain;
  background: var(--bg); border-radius: 8px; }
.website-preview .caption { max-width: 100%; padding: 4px 10px; background: var(--panel);
  color: var(--text); border: 1px solid var(--line); border-radius: 6px; font-size: 13px;
  overflow-wrap: anywhere; }
.website-choices { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 6px; }
.website-choice { display: flex; gap: 8px; align-items: center; padding: 6px 8px;
  border: 1px solid var(--line); border-radius: 6px; cursor: pointer; }
.website-choice:has(input:checked) { border-color: var(--accent); }
/* pre-wrap shows a change of the white space alone, for example two spaces. */
.website-choice .value { overflow-wrap: anywhere; white-space: pre-wrap; }
.website-choice .side { color: var(--muted); font-size: 11px; text-transform: uppercase; }
/* The pixel size of the file under the image of a main image conflict. */
.website-thumb { display: flex; flex-direction: column; align-items: center; gap: 2px; }
.website-thumb .dims { color: var(--muted); font-size: 11px; font-variant-numeric: tabular-nums; }
.website-status { margin-top: 12px; color: var(--muted); white-space: pre-wrap; }
.website-status.error { color: var(--neg); }
.website-result { display: grid; grid-template-columns: auto 1fr; gap: 3px 12px;
  margin-top: 8px; }
.website-result dt { color: var(--muted); }
.website-result dd { margin: 0; overflow-wrap: anywhere; }
`;
  document.head.appendChild(style);

  const modal = document.createElement("div");
  modal.className = "modal";
  modal.hidden = true;
  modal.setAttribute("role", "dialog");
  modal.setAttribute("aria-modal", "true");
  modal.setAttribute("aria-labelledby", "website-title");
  modal.innerHTML = `<div class="validation-dialog website-dialog">
  <div class="validation-head"><h2 id="website-title">Import from vino-svoe.ru</h2>
    <button type="button" data-website="close" aria-label="Close">×</button></div>
  <div id="website-body"></div>
  <div class="website-status" id="website-status"></div>
  <div class="validation-actions" id="website-actions"></div>
</div>`;
  document.body.appendChild(modal);
  const body = modal.querySelector("#website-body");
  const status = modal.querySelector("#website-status");
  const actions = modal.querySelector("#website-actions");

  // The large view of one image. A click or Esc closes it.
  const preview = document.createElement("div");
  preview.className = "website-preview";
  preview.hidden = true;
  preview.innerHTML = `<img alt=""><div class="caption"></div>`;
  document.body.appendChild(preview);
  preview.addEventListener("click", () => { preview.hidden = true; });

  // The same address as `SITE_WINE_URL` of dataset.html.
  const SITE_WINE_URL = "https://vino-svoe.ru/wines/";
  const KINDS = [
    ["new", "New wines on website", "Add the wine as Active, with its main image."],
    ["missing", "Missing on the website", "Set the wine Removed."],
    ["back", "Back on the website", "Set the wine Active again."],
    ["main", "Missing main images, taken from website",
     "The database has no main image for these wines. Apply stores the website image as the main image."],
  ];
  // The path of the page while the dialog is open (owner message of
  // 2026-09-26T08:00:00+0300). A link to it or a reload of it opens the dialog.
  const PATH = "/dataset/website-import";
  let state = null;
  let diff = null;
  let timer = null;
  let openWhenReady = false;

  function esc(value) {
    return String(value ?? "").replace(/[&<>"']/g, c => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
  }
  async function getJson(url, options) {
    const response = await fetch(url, options);
    const answer = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(answer.error || `${response.status} ${response.statusText}`);
    return answer;
  }
  function changeCount(counts) {
    return Object.values((counts && counts.changes) || {}).reduce((a, b) => a + b, 0);
  }
  function label(s) {
    if (!s || s.state === "none" || s.state === "applied") return "Import from website";
    if (s.state === "running") {
      return s.phase === "apply" ? "Website: applying…" : `Website: ${s.progress || "starting…"}`;
    }
    if (s.state === "prepared") {
      return `Website: ${s.counts.conflicts} conflicts, ${changeCount(s.counts)} changes`;
    }
    return "Website: failed";
  }
  function setStatus(text, error) {
    status.textContent = text || "";
    status.classList.toggle("error", Boolean(error));
  }

  async function poll() {
    clearTimeout(timer);
    try {
      state = await getJson(API);
    } catch (error) {
      button.textContent = "Website: no answer";
      timer = setTimeout(poll, 5000);
      return;
    }
    button.textContent = label(state);
    button.classList.toggle("running", state.state === "running");
    if (state.state === "running") {
      timer = setTimeout(poll, 2000);
      if (!modal.hidden) showRunning();
      return;
    }
    if (!modal.hidden || openWhenReady) {
      openWhenReady = false;
      await show();
    }
  }

  function open() {
    modal.hidden = false;
    document.body.style.overflow = "hidden";
    if (location.pathname !== PATH) history.pushState({websiteImport: true}, "", PATH);
  }
  function hide() {
    modal.hidden = true;
    document.body.style.overflow = "";
  }
  // Close the dialog and give the page its path `/dataset` again. The entry that `open`
  // pushed goes away with Back, so Forward opens the dialog again.
  function close() {
    hide();
    if (history.state && history.state.websiteImport) history.back();
    else if (location.pathname === PATH) history.replaceState(null, "", "/dataset");
  }

  function showRunning() {
    const what = state.phase === "apply" ? "The apply runs." : "The compare runs.";
    body.innerHTML = `<p class="validation-intro">${what} It reads the list, the sitemap, and
      the original image of each wine of vino-svoe.ru. A full compare takes about 10 minutes.
      You can close this dialog; the job goes on.</p>`;
    setStatus(state.progress || "starting…");
    actions.innerHTML = `<button type="button" data-website="stop">Stop</button>
      <button type="button" data-website="close">Close</button>`;
  }

  function showStart(note) {
    diff = null;
    body.innerHTML = `<p class="validation-intro">${note ? esc(note) + " " : ""}Compare the
      database with vino-svoe.ru. The compare changes nothing. After it, this dialog lists
      each conflict and each change, and you choose what to apply.</p>`;
    setStatus("");
    actions.innerHTML = `<button type="button" data-website="close">Cancel</button>
      <button type="button" class="primary" data-website="start">Compare</button>`;
  }

  function image(url, file) {
    return url ? `<img src="${esc(url)}" alt="" loading="lazy" data-preview
      data-caption="${esc(file)}">` : `<div class="no-image"></div>`;
  }
  function showPreview(picture) {
    preview.querySelector("img").src = picture.currentSrc || picture.src;
    preview.querySelector(".caption").textContent = picture.dataset.caption || "";
    preview.hidden = false;
  }
  function runUrl(file) {
    return file ? `/website-import/${diff.run}/${file}` : null;
  }
  function slugHtml(entry) {
    // A missing wine has no page on the website.
    if (entry.kind === "missing") return esc(entry.slug);
    return `<a href="${esc(SITE_WINE_URL + encodeURIComponent(entry.slug))}" target="_blank"
      rel="noopener">${esc(entry.slug)}</a>`;
  }
  function wineTitle(entry) {
    return `<div><div class="title">${esc(entry.name || entry.slug)}</div>
      <div class="meta">${slugHtml(entry)}${entry.producer ? " · " + esc(entry.producer) : ""}${
        entry.state ? " · " + esc(entry.state) : ""}</div></div>`;
  }
  // The conflicts of one wine, in the order of the diff.
  function conflictGroups(conflicts) {
    const groups = new Map();
    for (const entry of conflicts) {
      if (!groups.has(entry.slug)) groups.set(entry.slug, []);
      groups.get(entry.slug).push(entry);
    }
    return [...groups.values()];
  }
  function conflictHtml(entries) {
    return `<div class="website-row conflict unset" data-row="${esc(entries[0].slug)}">
      ${wineTitle(entries[0])}${entries.map(choicesHtml).join("")}</div>`;
  }
  function choicesHtml(entry) {
    const name = `conflict-${entry.id}`;
    let sides;
    if (entry.kind === "text") {
      sides = [["database", entry.database], ["website", entry.website]].map(([side, value]) =>
        `<label class="website-choice"><input type="radio" name="${esc(name)}" value="${side}"
          data-conflict="${esc(entry.id)}"><span><span class="side">${side}</span><br>
          <span class="value">${value === null ? "<em>empty</em>" : esc(value)}</span></span></label>`);
    } else {
      sides = [["database", entry.database.url, entry.database.source_name],
               ["website", runUrl(entry.website.file), entry.website.name]].map(
        ([side, url, file]) => `<label class="website-choice"><input type="radio"
          name="${esc(name)}" value="${side}" data-conflict="${esc(entry.id)}"><span
          class="website-thumb">${image(url, file)}<span class="dims"></span></span>
          <span><span class="side">${side}</span><br><span class="value">${esc(file)}</span></span></label>`);
    }
    const what = entry.kind === "text" ? `the field <strong>${esc(entry.field)}</strong>`
      : "the <strong>main image</strong>";
    return `<div class="website-conflict"><div class="meta">vino-svoe.ru changed ${what}.</div>
      <div class="website-choices">${sides.join("")}</div></div>`;
  }
  // A prohibition sign on top of the image of a wine that is missing on the website.
  const MISSING_SIGN = `<svg viewBox="0 0 100 100" role="img" aria-label="Missing on the website">
    <circle cx="50" cy="50" r="42" fill="none" stroke="#e30613" stroke-width="10"/>
    <line x1="20.3" y1="20.3" x2="79.7" y2="79.7" stroke="#e30613" stroke-width="10"/></svg>`;
  function changeHtml(entry) {
    const url = entry.image ? runUrl(entry.image.file) : entry.stored && entry.stored.url;
    const file = entry.image ? entry.image.name : entry.stored && entry.stored.source_name;
    const picture = entry.kind === "missing"
      ? `<span class="missing-image">${image(url, file)}${MISSING_SIGN}</span>` : image(url, file);
    return `<label class="website-row"><input type="checkbox" checked
      data-change="${esc(entry.id)}">${picture}${wineTitle(entry)}</label>`;
  }

  function showDiff() {
    const conflicts = diff.conflicts;
    const groups = conflictGroups(conflicts);
    let html = `<p class="validation-intro">Compared at ${esc(diff.created_at)}:
      ${diff.website} wines on vino-svoe.ru, ${diff.images} images.
      ${diff.refused ? `${diff.refused} conflicts or changes stay refused by an earlier choice.` : ""}
      A choice <em>database</em> and a cleared checkbox are remembered: a later import skips
      them while the website keeps the value.</p>`;
    if (conflicts.length) {
      html += `<h3>Conflicts <span class="count">${conflicts.length} · ${groups.length} wines</span>
        <button type="button" data-website="all" data-side="database">all database</button>
        <button type="button" data-website="all" data-side="website">all website</button></h3>
        <div class="website-rows">${groups.map(conflictHtml).join("")}</div>`;
    }
    for (const [kind, title, hint] of KINDS) {
      const entries = diff.changes.filter(entry => entry.kind === kind);
      if (!entries.length) continue;
      html += `<h3>${esc(title)} <span class="count">${entries.length} · ${esc(hint)}</span>
        <button type="button" data-website="tick" data-kind="${kind}" data-on="1">all</button>
        <button type="button" data-website="tick" data-kind="${kind}" data-on="">none</button></h3>
        <div class="website-rows">${entries.map(changeHtml).join("")}</div>`;
    }
    if (!conflicts.length && !diff.changes.length) {
      html += `<p class="empty">The database matches vino-svoe.ru. Apply writes the website
        times alone.</p>`;
    }
    body.innerHTML = html;
    actions.innerHTML = `<button type="button" data-website="restart">Compare again</button>
      <button type="button" data-website="close">Close</button>
      <button type="button" class="primary" data-website="apply">Apply</button>`;
    refreshApply();
  }

  function unset() {
    return diff.conflicts.filter(entry =>
      !body.querySelector(`input[data-conflict="${CSS.escape(entry.id)}"]:checked`)).length;
  }
  function refreshApply() {
    const left = unset();
    const apply = actions.querySelector('[data-website="apply"]');
    if (apply) apply.disabled = left > 0;
    for (const row of body.querySelectorAll(".website-row.conflict")) {
      row.classList.toggle("unset", [...row.querySelectorAll(".website-conflict")].some(
        part => !part.querySelector("input:checked")));
    }
    setStatus(left ? `${left} conflicts need a choice.` : "Each conflict has a choice.");
  }

  function showResult() {
    const r = state.result || {};
    const rows = [["added", r.added], ["removed", r.removed], ["restored", r.restored],
      ["main images stored", r.mains], ["text from the website", r.texts],
      ["main images replaced", r.replaced], ["refusals written", r.refusals]];
    body.innerHTML = `<p class="validation-intro">The import is written.</p>
      <dl class="website-result">${rows.map(([name, list]) =>
        `<dt>${esc(name)}</dt><dd>${(list || []).length}${(list || []).length
          ? ": " + esc(list.slice(0, 12).join(", ")) + (list.length > 12 ? ", …" : "") : ""}</dd>`).join("")}
      <dt>website times written</dt><dd>${r.times || 0}</dd>
      <dt>comments added</dt><dd>${r.comments || 0}</dd>
      <dt>processed images</dt><dd>${esc(JSON.stringify(r.processed || {}))}${
        r.no_sam3 ? `; ${r.no_sam3} with no SAM3 answer` : ""}</dd></dl>`;
    setStatus("");
    actions.innerHTML = `<button type="button" data-website="start">New compare</button>
      <button type="button" data-website="close">Close</button>
      <button type="button" class="primary" data-website="reload">Reload the page</button>`;
  }

  async function show() {
    open();
    if (!state || state.state === "none") return showStart();
    if (state.state === "running") return showRunning();
    if (state.state === "applied") return showResult();
    if (state.state === "failed" && state.phase === "prepare") {
      showStart();
      return setStatus(`The last compare failed:\n${state.error || ""}`, true);
    }
    try {
      diff = await getJson(`${API}/${state.run}/diff`);
    } catch (error) {
      showStart();
      return setStatus(`Cannot read the diff: ${error.message}`, true);
    }
    showDiff();
    if (state.state === "failed") setStatus(`The last apply failed:\n${state.error || ""}`, true);
  }

  async function start() {
    try {
      await getJson(`${API}/start`, {method: "POST"});
    } catch (error) {
      return setStatus(`Cannot start the compare: ${error.message}`, true);
    }
    openWhenReady = true;
    await poll();
  }

  async function apply() {
    const choices = {conflicts: {}, changes: {}};
    for (const input of body.querySelectorAll("input[data-conflict]:checked")) {
      choices.conflicts[input.dataset.conflict] = input.value;
    }
    for (const input of body.querySelectorAll("input[data-change]")) {
      choices.changes[input.dataset.change] = input.checked;
    }
    try {
      await getJson(`${API}/${diff.run}/apply`, {method: "POST",
        headers: {"Content-Type": "application/json"}, body: JSON.stringify(choices)});
    } catch (error) {
      return setStatus(`Cannot start the apply: ${error.message}`, true);
    }
    await poll();
  }

  modal.addEventListener("click", async event => {
    if (event.target === modal) return close();
    const picture = event.target.closest("img[data-preview]");
    if (picture) {
      // The image is in a label. The default action changes its radio button or checkbox.
      event.preventDefault();
      return showPreview(picture);
    }
    const target = event.target.closest("[data-website]");
    if (!target) return;
    const action = target.dataset.website;
    if (action === "close") close();
    else if (action === "start" || action === "restart") {
      if (action === "restart" && !confirm("Compare again? The choices of this dialog are lost.")) return;
      await start();
    } else if (action === "stop") {
      try { await getJson(`${API}/stop`, {method: "POST"}); } catch (error) { setStatus(error.message, true); }
      await poll();
    } else if (action === "apply") await apply();
    else if (action === "reload") {
      // The page loads again as `/dataset`, so the dialog does not open again.
      history.replaceState(null, "", "/dataset");
      location.reload();
    }
    else if (action === "all") {
      for (const input of body.querySelectorAll(`input[data-conflict][value="${target.dataset.side}"]`)) {
        input.checked = true;
      }
      refreshApply();
    } else if (action === "tick") {
      for (const entry of diff.changes.filter(e => e.kind === target.dataset.kind)) {
        const input = body.querySelector(`input[data-change="${CSS.escape(entry.id)}"]`);
        if (input) input.checked = Boolean(target.dataset.on);
      }
    }
  });
  modal.addEventListener("change", event => {
    if (event.target.matches("input[data-conflict]")) refreshApply();
  });
  // The load event does not bubble, so the listener catches it in the capture phase.
  modal.addEventListener("load", event => {
    const dims = event.target.closest(".website-thumb img") && event.target.nextElementSibling;
    if (dims) dims.textContent = `${event.target.naturalWidth}×${event.target.naturalHeight}`;
  }, true);
  document.addEventListener("keydown", event => {
    if (event.key !== "Escape") return;
    if (!preview.hidden) {
      event.stopPropagation();
      preview.hidden = true;
    } else if (!modal.hidden) {
      event.stopPropagation();
      close();
    }
  }, true);
  button.addEventListener("click", () => show());
  // Back and Forward open or close the dialog that the page path names.
  window.addEventListener("popstate", () => {
    if (location.pathname !== PATH) {
      if (!modal.hidden) hide();
    } else if (modal.hidden && !button.hidden) show();
  });

  // The button appears only on a server with the website import. The review tool of
  // scripts/review_server.py serves the same page with no such route.
  fetch(API).then(response => {
    if (!response.ok) return;
    button.hidden = false;
    poll().then(() => { if (location.pathname === PATH && modal.hidden) show(); });
  }).catch(() => {});
})();
