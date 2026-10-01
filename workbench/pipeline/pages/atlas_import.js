// "New from Atlas" of the Dataset page (plan 95): the button `New from Atlas` and its
// dialog. The lab server serves this file at /atlas-import.js. The routes are in
// pipeline/atlas_import_routes.py. Read docs/plans/95_new-from-atlas.md.
//
// The dialog asks for the URL of a Drink Atlas product. `Prepare` sends
// `POST /api/atlas-import/advance` again every 3 s until each Atlas step is terminal. The
// server keeps no job: a repeated `advance` sends only the missing Atlas requests. Then
// the dialog shows the best photo of each group of similar photos. `Create` and
// `Create now` open the form `Add wine` of dataset.html in its Atlas mode
// (`openAtlasWineForm`), with no main photo.
//
// The button `load photos` of an Atlas product of a card opens the same dialog in the
// add mode (owner messages of 2026-09-30T23:01 and 23:20). The URL is filled in. The add
// mode runs no Atlas step: it shows the photos that Atlas has now, and `Import` sends
// `POST /api/atlas-import/add`: the photos become additional photos of that wine.
//
// Owner message of 2026-10-01T08:21:51 and answers of 08:27: a click on a photo of the
// dialog shows it in the image preview of dataset.html. `Import` closes the dialog at
// once. The page sends the imports one after another, and the box `#atlas-jobs` in the
// lower right corner shows each import.
(function () {
  "use strict";
  const API = "/api/atlas-import";
  const button = document.getElementById("atlas-new");
  if (!button) return;
  const POLL_MS = 3000;
  // The address of an Atlas product: the link `open` of a card (`atlasBindingEditor`).
  const PRODUCT_URL = "http://127.0.0.1:8157/products/";
  const TEXTS = {
    new: {title: "New from Atlas", now: "Create now", go: "Create", prepare: "Prepare",
      intro: `Prepare runs the three steps of the Atlas product page: Удалить белые поля и
        полосы, Извлечь изображения из PDF, then Распознать штрихкоды. The new wine gets no
        main photo. The largest photo of each group of similar photos becomes an additional
        photo.`},
    add: {title: "Load photos from Atlas", now: "", go: "Import", prepare: "Reload",
      intro: `Import adds the photos that Atlas has now: the largest photo of each group of
        similar photos becomes an additional photo of the wine. No Atlas step runs. The main
        photo and the patch do not change. A photo that the wine has already is not added
        again. The dialog closes at once, and the box in the lower right corner shows the
        import.`}};

  const style = document.createElement("style");
  style.textContent = `
.atlas-dialog { width: min(860px, 100%); }
.atlas-url { display: flex; gap: 8px; align-items: end; flex-wrap: wrap; margin: 10px 0; }
.atlas-url label { flex: 1 1 320px; display: grid; gap: 4px; font-size: 12px;
  color: var(--muted); }
.atlas-url input { width: 100%; box-sizing: border-box; }
.atlas-name { margin: 6px 0 10px; font-weight: 600; overflow-wrap: anywhere; }
.atlas-steps { width: 100%; border-collapse: collapse; font-size: 12px; }
.atlas-steps th, .atlas-steps td { padding: 4px 6px; border-bottom: 1px solid var(--line);
  text-align: left; }
.atlas-steps th { color: var(--muted); font-weight: 600; }
.atlas-steps .state-succeeded { color: var(--pos, var(--accent)); }
.atlas-steps .state-failed, .atlas-steps .state-stale, .atlas-steps .state-blocked,
.atlas-steps .state-input_unavailable { color: var(--neg); }
.atlas-photos { display: grid; grid-template-columns: repeat(auto-fill, minmax(112px, 1fr));
  gap: 8px; margin-top: 12px; }
.atlas-photo { display: grid; gap: 3px; justify-items: center; padding: 6px;
  background: var(--panel-2); border: 1px solid var(--line); border-radius: 8px;
  font-size: 11px; color: var(--muted); text-align: center; cursor: zoom-in; }
.atlas-photo img { width: 100px; height: 100px; object-fit: contain; background: var(--bg);
  border-radius: 6px; }
.atlas-status { margin-top: 10px; color: var(--muted); white-space: pre-wrap; }
/* The Atlas photos in the image area of the form Add wine (the Atlas mode). The area
   takes no file then, but it keeps its full colour. */
.wine-form-drop:disabled { opacity: 1; cursor: default; }
.wine-form-atlas { display: flex; flex-wrap: wrap; gap: 6px; justify-content: center; }
.wine-form-drop .wine-form-atlas img { width: 72px; height: 72px; object-fit: contain;
  background: var(--bg); border-radius: 6px; }
.atlas-status.error { color: var(--neg); }
/* The box of the background imports. Its z-index keeps it below the dialogs. */
.atlas-jobs { position: fixed; right: 16px; bottom: 16px; z-index: 45; display: grid;
  gap: 6px; width: min(360px, calc(100vw - 32px)); }
.atlas-jobs:empty { display: none; }
.atlas-job { display: flex; gap: 8px; align-items: flex-start; padding: 8px 10px;
  background: var(--panel); border: 1px solid var(--line); border-radius: 8px;
  box-shadow: 0 4px 14px rgba(0, 0, 0, .25); font-size: 12px; }
.atlas-job.failed { border-color: var(--neg); }
.atlas-job-text { flex: 1 1 auto; min-width: 0; display: grid; gap: 2px;
  overflow-wrap: anywhere; }
.atlas-job-text small { color: var(--muted); }
.atlas-job-message { white-space: pre-wrap; }
.atlas-job.failed .atlas-job-message { color: var(--neg); }
.atlas-job button { flex: none; padding: 0 6px; font-size: 14px; }
`;
  document.head.appendChild(style);

  const modal = document.createElement("div");
  modal.className = "modal";
  modal.id = "atlas-modal";
  modal.hidden = true;
  modal.setAttribute("role", "dialog");
  modal.setAttribute("aria-modal", "true");
  modal.setAttribute("aria-labelledby", "atlas-title");
  modal.innerHTML = `<div class="validation-dialog atlas-dialog">
  <div class="validation-head"><h2 id="atlas-title">New from Atlas</h2>
    <button type="button" data-atlas="close" aria-label="Close">×</button></div>
  <p class="validation-intro" id="atlas-intro"></p>
  <form class="atlas-url" id="atlas-form" novalidate>
    <label>Atlas product URL <input id="atlas-url" type="url" autocomplete="off"
      spellcheck="false" placeholder="http://127.0.0.1:8157/products/<uuid>"></label>
    <button type="submit" class="primary" id="atlas-prepare">Prepare</button>
  </form>
  <div class="atlas-name" id="atlas-name"></div>
  <div id="atlas-steps"></div>
  <div class="atlas-photos" id="atlas-photos"></div>
  <div class="atlas-status" id="atlas-status" role="status" aria-live="polite"></div>
  <div class="validation-actions">
    <button type="button" data-atlas="close">Close</button>
    <button type="button" id="atlas-now" data-atlas="now" disabled>Create now</button>
    <button type="button" class="primary" id="atlas-create" data-atlas="create"
      disabled>Create</button>
  </div>
</div>`;
  // The dialog comes before the image preview of dataset.html in the page. Both have the
  // same z-index, so the preview of a photo is shown above the dialog.
  const preview = document.getElementById("image-preview-modal");
  if (preview) preview.before(modal);
  else document.body.appendChild(modal);
  const $ = selector => modal.querySelector(selector);
  const box = document.createElement("div");
  box.className = "atlas-jobs";
  box.id = "atlas-jobs";
  box.setAttribute("role", "status");
  box.setAttribute("aria-live", "polite");
  document.body.appendChild(box);

  // `run` counts the Prepare clicks. A poll of an older run stops. `target` is the wine of
  // the add mode, {slug, name}, or null for a new wine.
  let run = 0;
  let target = null;
  let timer = null;
  let url = "";
  let state = null;
  let photos = null;
  let busy = false;
  // The background imports, oldest first: {id, slug, name, url, ids, state, text}. The
  // state is `waiting`, `running`, `done`, or `failed`. `queue` runs one import at a time.
  // A done import with no note leaves the box after JOB_DONE_MS.
  const JOB_DONE_MS = 8000;
  const jobs = [];
  let jobCount = 0;
  let queue = Promise.resolve();

  function esc(value) {
    return String(value ?? "").replace(/[&<>"']/g, c => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
  }
  async function getJson(path, options) {
    const response = await fetch(path, options);
    const answer = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(answer.error || `${response.status} ${response.statusText}`);
    return answer;
  }
  function setStatus(text, error) {
    $("#atlas-status").textContent = text || "";
    $("#atlas-status").classList.toggle("error", !!error);
  }
  function updateButtons() {
    $("#atlas-prepare").disabled = busy;
    // The add mode runs no Atlas step, so its photos are ready at once.
    const ready = !!(photos && photos.length) && (!!target || !!(state && state.done));
    $("#atlas-now").disabled = busy || !state;
    $("#atlas-create").disabled = busy || !ready;
  }
  function setMode(wine) {
    target = wine;
    const texts = TEXTS[wine ? "add" : "new"];
    $("#atlas-title").textContent = wine ? `${texts.title}: ${wine.name}` : texts.title;
    $("#atlas-intro").textContent = texts.intro.replace(/\s+/g, " ");
    $("#atlas-now").textContent = texts.now;
    $("#atlas-now").hidden = !!wine;
    $("#atlas-create").textContent = texts.go;
    $("#atlas-prepare").textContent = texts.prepare;
  }
  // A new mode or a new product forgets the old run.
  function reset() {
    clearTimeout(timer);
    timer = null;
    run += 1;
    state = null;
    photos = null;
    busy = false;
    renderSteps();
    renderPhotos();
    setStatus("");
  }
  function renderSteps() {
    if (!state) { $("#atlas-steps").innerHTML = ""; $("#atlas-name").textContent = ""; return; }
    $("#atlas-name").textContent = state.product.display_name || state.product_uuid;
    const rows = state.steps.map(step => {
      const queue = step.status === "queued" && step.queue_position != null
        ? ` · queue ${step.queue_position}` : "";
      return `<tr><td>${esc(step.label)}</td><td>${esc(step.media_id)}</td>
        <td>${esc(step.task_id ?? "—")}</td>
        <td class="state-${esc(step.status)}">${esc(step.status)}${esc(queue)}${
          step.submitted ? " · sent now" : ""}</td></tr>`;
    }).join("");
    $("#atlas-steps").innerHTML = `<table class="atlas-steps"><thead><tr><th>Step</th>
      <th>Media</th><th>Task</th><th>State</th></tr></thead><tbody>${rows}</tbody></table>`;
  }
  // Each photo is a button: a click shows it in the image preview (`showPhoto`).
  function renderPhotos() {
    $("#atlas-photos").innerHTML = (photos || []).map((photo, index) => `<button
      type="button" class="atlas-photo" data-atlas-photo="${index}"
      title="media ${esc(photo.media_id)}; group: ${esc(photo.group.join(", "))}">
      <img src="${esc(photo.thumbnail_url)}" alt="media ${esc(photo.media_id)}" loading="lazy">
      <span>${esc(photo.width)}×${esc(photo.height)}${photo.pdf ? " · PDF" : ""}</span>
      <span>${photo.group.length > 1 ? `best of ${photo.group.length}` : "single"}</span>
    </button>`).join("");
  }
  function stageText() {
    if (!state) return "";
    if (state.done) return "Each Atlas step is terminal.";
    const waiting = state.steps.filter(step => step.status === "queued").length;
    const hint = waiting ? " A queued task runs only while an Atlas enrichment worker runs." : "";
    return `Atlas stage: ${state.stage}. The dialog checks again every 3 s.${hint}`;
  }
  async function loadPhotos(current) {
    const answer = await getJson(`${API}/photos?url=${encodeURIComponent(url)}`);
    if (current !== run) return;
    photos = answer.photos || [];
    if (target) $("#atlas-name").textContent = (answer.product || {}).display_name || "";
    renderPhotos();
  }
  // The add mode runs no Atlas step: it shows the photos that Atlas has now.
  async function loadForWine(current) {
    try {
      await loadPhotos(current);
      if (current !== run) return;
      setStatus(photos.length ? `${photos.length} photos are selected.`
        : "The Atlas product has no image.", !photos.length);
    } catch (error) {
      if (current === run) setStatus(`Cannot read the Atlas photos: ${error.message}`, true);
    } finally {
      if (current === run) { busy = false; updateButtons(); }
    }
  }
  async function advance(current) {
    timer = null;
    try {
      state = await getJson(`${API}/advance`, {
        method: "POST", headers: {"Content-Type": "application/json"},
        body: JSON.stringify({url})});
      if (current !== run) return;
      renderSteps();
      if (state.done) {
        await loadPhotos(current);
        if (current !== run) return;
        setStatus(`${stageText()} ${photos.length} photos are selected.`);
      } else {
        setStatus(stageText());
        if (!modal.hidden) timer = setTimeout(() => advance(current), POLL_MS);
      }
    } catch (error) {
      if (current !== run) return;
      setStatus(`Cannot read the Atlas steps: ${error.message}`, true);
    } finally {
      if (current === run) { busy = false; updateButtons(); }
    }
  }
  function prepare() {
    const value = $("#atlas-url").value.trim();
    if (!value) { setStatus("Paste the URL of an Atlas product.", true); return; }
    clearTimeout(timer);
    run += 1;
    url = value;
    state = null;
    photos = null;
    busy = true;
    renderSteps();
    renderPhotos();
    setStatus(target ? "Reading the Atlas photos…" : "Reading the Atlas product…");
    updateButtons();
    if (target) loadForWine(run);
    else advance(run);
  }
  async function create(now) {
    const current = run;
    busy = true;
    updateButtons();
    try {
      if (now || !photos) {
        setStatus("Selecting the photos…");
        await loadPhotos(current);
        if (current !== run) return;
      }
      if (!photos.length) throw new Error("the Atlas product has no image");
      clearTimeout(timer);
      timer = null;
      if (target) {
        queueImport(target, url, photos.map(photo => photo.media_id));
        close();
        return;
      }
      modal.hidden = true;
      openAtlasWineForm({url, prefill: state.prefill, photos,
                         name: state.product.display_name || ""});
    } catch (error) {
      setStatus(`Cannot ${target ? "import" : "select"} the photos: ${error.message}`, true);
    } finally {
      if (current === run) { busy = false; updateButtons(); }
    }
  }
  // `Import` of the add mode: the import of the photos `ids` of the product `url` waits in
  // `queue`, and the dialog closes at once.
  function queueImport(wine, url, ids) {
    const job = {id: ++jobCount, slug: wine.slug, name: wine.name, url, ids,
      state: "waiting", text: `${ids.length} photos wait for the import.`};
    jobs.push(job);
    renderJobs();
    queue = queue.then(() => runImport(job));
  }
  // One import: the photos become additional photos of the wine `job.slug`. A card in the
  // list shows them at once. A card that the filters hide shows them after the next render
  // of the list: for such a card, `renderCard` renders the whole list.
  async function runImport(job) {
    job.state = "running";
    job.text = `Importing ${job.ids.length} photos…`;
    renderJobs();
    try {
      const out = await getJson(`${API}/add`, {
        method: "POST", headers: {"Content-Type": "application/json"},
        body: JSON.stringify({slug: job.slug, url: job.url, media_ids: job.ids})});
      const record = DATA.records.find(r => r.slug === job.slug);
      if (record && out.record) Object.assign(record, out.record);
      if (record && document.getElementById(job.slug)) renderCard(job.slug);
      const kept = job.ids.length - out.added;
      job.state = "done";
      job.text = `${out.added} photos added to the wine.${kept > 0
        ? ` ${kept} were not added: the wine has them already, or the store refused them.` : ""}${
        out.warning ? `\n${out.warning}` : ""}`;
      if (kept <= 0 && !out.warning) setTimeout(() => dismissJob(job.id), JOB_DONE_MS);
    } catch (error) {
      job.state = "failed";
      job.text = `Cannot import the photos: ${error.message}`;
    }
    renderJobs();
  }
  // The box shows each import. A done or failed import has a × button.
  function renderJobs() {
    box.innerHTML = jobs.map(job => `<div class="atlas-job ${job.state}"><div
      class="atlas-job-text"><b>${esc(job.name)}</b>${job.name !== job.slug
      ? `<small>${esc(job.slug)}</small>` : ""}<span class="atlas-job-message">${
      esc(job.text)}</span></div>${job.state === "done" || job.state === "failed"
      ? `<button type="button" data-atlas-job="${job.id}" title="Close"
        aria-label="Close">×</button>` : ""}</div>`).join("");
  }
  function dismissJob(id) {
    const index = jobs.findIndex(job => job.id === id);
    if (index < 0) return;
    jobs.splice(index, 1);
    renderJobs();
  }
  // A click on a photo shows it in the image preview of dataset.html alone, as
  // `showDetailFailurePreview` of dataset.html does: no arrows, no thumbnails, and no
  // change of the page path. The preview loads the Atlas rendition `display` (1600 px at
  // most); `open raw image` is the original (`content`). The photos of the dialog hold
  // `thumbnail_url` alone, so the last path part of that URL changes.
  function showPhoto(photo) {
    const part = name => photo.thumbnail_url.replace(/\/thumbnail(?=\?|$)/, `/${name}`);
    const page = id => document.getElementById(id);
    const label = `Atlas photo · ${$("#atlas-name").textContent || "Atlas product"}`;
    IMAGE_PREVIEW = null;
    page("image-preview-title").textContent = label;
    page("image-preview-file").textContent = `media ${photo.media_id}${
      photo.group.length > 1 ? ` · best of ${photo.group.length}` : ""}`;
    page("image-preview-position").textContent = "";
    page("image-preview-previous").disabled = page("image-preview-next").disabled = true;
    page("image-preview-thumbs").innerHTML = "";
    page("image-preview-raw").href = part("content");
    page("image-preview-size").textContent = "reading size…";
    const image = page("image-preview-image");
    image.alt = label;
    image.onload = () => {
      const size = `${image.naturalWidth} × ${image.naturalHeight} px`;
      page("image-preview-size").textContent = photo.width && photo.width !== image.naturalWidth
        ? `${size} (preview of ${photo.width} × ${photo.height})` : size;
    };
    image.onerror = () => { page("image-preview-size").textContent = "image load failed"; };
    image.src = part("display");
    page("image-preview-modal").hidden = false;
    document.body.style.overflow = "hidden";
    page("image-preview-close").focus();
  }
  // The button `load photos` of an Atlas product of a card.
  function openForWine(slug, product) {
    const record = DATA.records.find(r => r.slug === slug);
    reset();
    setMode({slug, name: (record && record.name) || slug});
    $("#atlas-url").value = PRODUCT_URL + product;
    modal.hidden = false;
    prepare();
  }
  function open() {
    if (target) {
      reset();
      setMode(null);
      $("#atlas-url").value = "";
    }
    modal.hidden = false;
    updateButtons();
    // A reopened dialog of an unfinished run checks the steps again.
    if (state && !state.done && !timer && !busy) {
      busy = true;
      updateButtons();
      advance(run);
    }
    $("#atlas-url").focus();
  }
  function close() {
    modal.hidden = true;
    clearTimeout(timer);
    timer = null;
  }

  setMode(null);
  button.addEventListener("click", open);
  document.getElementById("list")?.addEventListener("click", event => {
    const load = event.target.closest("button[data-atlas-load]");
    if (load) openForWine(load.dataset.slug, load.dataset.atlasLoad);
  });
  $("#atlas-form").addEventListener("submit", event => { event.preventDefault(); prepare(); });
  modal.addEventListener("click", event => {
    const tile = event.target.closest("[data-atlas-photo]");
    const photo = tile && photos ? photos[Number(tile.dataset.atlasPhoto)] : null;
    if (photo) { showPhoto(photo); return; }
    const action = event.target.closest("[data-atlas]")?.dataset.atlas;
    if (event.target === modal || action === "close") close();
    else if (action === "now") create(true);
    else if (action === "create") create(false);
  });
  box.addEventListener("click", event => {
    const control = event.target.closest("[data-atlas-job]");
    if (control) dismissJob(Number(control.dataset.atlasJob));
  });
  // The image preview of dataset.html takes Escape first and calls preventDefault. Then
  // the dialog below the preview stays open.
  document.addEventListener("keydown", event => {
    if (event.key === "Escape" && !modal.hidden && !event.defaultPrevented) close();
  });
  // A page reload loses a waiting import. A running import ends on the server.
  window.addEventListener("beforeunload", event => {
    if (!jobs.some(job => job.state === "waiting" || job.state === "running")) return;
    event.preventDefault();
    event.returnValue = "";
  });
})();
