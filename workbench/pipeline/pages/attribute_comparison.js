/* Read stored comparisons. Queue inference only through explicit write actions. */
const ATTRIBUTE_RESULTS = {match:"Match", conflict:"Conflict", image_only:"Image only",
  metadata_only:"Metadata only", unknown:"Unknown"};
const ATTRIBUTE_CLAIMS_OPEN = new Set();
let ATTRIBUTE_TIMER = null, ATTRIBUTE_REQUEST = null, ATTRIBUTE_FAILURES = 0;
function attributeInputs(r) {
  return [r.name || "", r.category || "", r.color || "", r.grapes || "", r.description || "",
    r._tags || [], r._beverage_type_code || ""];
}
function attributeOf(r) {
  const comp = r._attribute_comparison;
  const image = shaOfUrl(r._patch_url || r.main_image_original_url);
  if (!comp || comp.sha256 !== (image || null)
      || JSON.stringify(comp.metadata_inputs) !== JSON.stringify(attributeInputs(r))) return null;
  return comp;
}
function attributeRows(r) {
  return attributeOf(r)?.rows || [];
}
function inAttributeView(r) {
  if (!DATA.attribute_comparison) return true;
  const kind = $("#attribute-filter").value, field = $("#attribute-field").value;
  if (kind === "all") return true;
  const comp = attributeOf(r);
  if (!comp) return false;
  if (kind === "pending") return ["pending","running"].includes(comp.state) || comp.stale;
  if (kind === "failed") return comp.state === "failed";
  return comp.rows.some(row => (field === "all" || row.field === field)
    && (kind === "conflict" ? row.result === "conflict"
      : kind === "images_differ" ? row.image_disagreement : ["image_only","metadata_only"].includes(row.result)));
}
function updateAttributeQueueControls() {
  $("#attribute-pause").textContent = DATA.attribute_counts?.paused ? "Resume image facts" : "Pause image facts";
}
function updateAttributeCounts() {
  if (!DATA.attribute_comparison) return;
  const field = $("#attribute-field").value;
  const counts = {conflict:0,additional:0,images_differ:0};
  for (const r of DATA.records) {
    if (r.state === "Removed") continue;
    const rows = attributeRows(r).filter(row => field === "all" || row.field === field);
    counts.conflict += Number(rows.some(row => row.result === "conflict"));
    counts.additional += Number(rows.some(row => ["image_only","metadata_only"].includes(row.result)));
    counts.images_differ += Number(rows.some(row => row.image_disagreement));
  }
  for (const [key,label] of [["conflict","Conflicts"],["additional","Additional information"],["images_differ","Main / patch disagree"]]) {
    $("#attribute-filter option[value='"+key+"']").textContent = `${label} (${counts[key]})`;
  }
}
function attributeBadge(result) {
  return `<span class="attribute-result attribute-${esc(result)}">${esc(ATTRIBUTE_RESULTS[result] || "Unknown")}</span>`;
}
function attributeTable(r) {
  if (!DATA.attribute_comparison) return "";
  let comp = attributeOf(r);
  if (!comp) {
    scheduleAttributePoll(true);
    comp = {source:r._patch_url ? "Patch image" : "Main image",sha256:shaOfUrl(r._patch_url || r.main_image_original_url),
      state:"updating",stale:false,conflicts:0,additional:0,
      rows:[["grape","Grape",r.grapes],["sweetness","Sweetness",null],["colour","Wine colour",r.category || r.color],["vintage","Vintage",null]]
        .map(([field,label,value])=>({field,label,metadata:value ? [value] : [],image:[],evidence:"",image_state:"unknown",result:"unknown",image_disagreement:false}))};
  }
  if (["pending","running","not_queued"].includes(comp.state)) scheduleAttributePoll();
  const isPatch = comp.source === "Patch image";
  const showAll = ATTRIBUTE_CLAIMS_OPEN.has(r.slug);
  const rows = comp.rows.filter((row, i) => i < 4 || showAll || row.metadata.some(Boolean) || row.image.length);
  const sourceText = comp.state === "running" ? "Analysing image…" : comp.state === "pending" ? "Pending extraction"
    : comp.state === "failed" ? "Extraction failed" : comp.state === "missing" ? "No image"
    : comp.state === "updating" ? "Updating comparison…" : comp.state === "not_tracked" ? "Image is not tracked"
    : comp.state === "not_queued" ? "Not extracted" : comp.state === "older_extractor" ? "Older extraction · re-extract to update"
    : comp.extraction_source === "description" ? "From saved label text" : "From image analysis";
  const evidence = row => row.evidence ? `<details><summary>${esc(row.image.join(", ") || "Not observed")}</summary>
    <blockquote>${esc(row.evidence)}</blockquote>${row.image_disagreement
      ? `<p>Main image: ${esc((row.main_image_values || []).join(", "))}</p>` : ""}</details>`
    : esc(row.image_state === "unreadable" ? "Unreadable" : row.image_state === "not_visible" ? "Not visible" : "Unknown");
  const summary = comp.conflicts ? `<button type="button" class="attribute-conflict-link"
    data-attribute-conflicts="${esc(r.slug)}">${comp.conflicts} conflict${comp.conflicts === 1 ? "" : "s"}</button>` : "";
  return `<section class="attribute-comparison" aria-label="Metadata and image comparison">
    <div class="attribute-heading"><strong>Metadata / image</strong>${summary}</div>
    <table class="attribute-table"><thead><tr><th scope="col">Attribute</th><th scope="col">svoe-vino metadata</th>
      <th scope="col"><button type="button" data-attribute-image="${esc(r.slug)}"
        data-attribute-kind="${isPatch ? "patch" : "catalog"}" ${comp.sha256 ? "" : "disabled"}>${esc(comp.source)}</button></th>
      <th scope="col">Result</th></tr></thead><tbody>${rows.map((row,i) =>
        `${i === 4 ? '<tr class="attribute-group"><th colspan="4">Marks / claims</th></tr>' : ""}
        <tr><th scope="row">${esc(row.label)}</th><td>${esc(row.metadata.filter(Boolean).join("; ") || "Not specified")}</td>
        <td>${evidence(row)}</td><td>${attributeBadge(row.result)}${row.image_disagreement
          ? '<span class="attribute-result attribute-conflict">Images differ</span>' : ""}</td></tr>`).join("")}</tbody></table>
    <div class="attribute-footer"><button type="button" data-attribute-claims="${esc(r.slug)}"
      aria-expanded="${showAll}">${showAll ? "Hide unknown claims" : "Show all claims"}</button>
      <span class="attribute-source">${esc(sourceText)}${comp.stale ? " · Previous evidence is stale" : ""}</span>
      ${comp.sha256 ? `<button type="button" data-attribute-refresh="${esc(comp.sha256)}"
        ${["pending","running"].includes(comp.state) ? "disabled" : ""}>${comp.state === "failed" ? "Retry" : "Re-extract"}</button>` : ""}
    </div>${comp.error ? `<p class="attribute-error">${esc(comp.error)}</p>` : ""}
    ${comp.extracted_at ? `<small>Extracted ${esc(comp.extracted_at)}${comp.model ? " · " + esc(comp.model) : ""}</small>` : ""}
  </section>`;
}
function attributeWorkerActive() {
  const state = DATA.attribute_counts || {};
  const fresh = Object.prototype.hasOwnProperty.call(state,"heartbeat_at")
    ? !!state.heartbeat_at && Date.now() - Date.parse(state.heartbeat_at) < 90000
    : !!state.worker_active;
  return fresh && !state.paused;
}
function scheduleAttributePoll(force = false) {
  if ((!force && !attributeWorkerActive()) || ATTRIBUTE_TIMER || ATTRIBUTE_REQUEST) return;
  ATTRIBUTE_TIMER = setTimeout(() => {ATTRIBUTE_TIMER = null; refreshAttributes();}, Math.min(30000,3000 * 2 ** ATTRIBUTE_FAILURES));
}
async function refreshAttributes() {
  if (!DATA.attribute_comparison || ATTRIBUTE_REQUEST) return;
  let retry = false;
  ATTRIBUTE_REQUEST = (async () => {
    try {
      const response = await fetch("/api/dataset", {cache:"no-store"});
      if (!response.ok) throw Error("Cannot refresh comparison");
      const beforeSlugs = ROWS.map(r=>r.slug).join("\0");
      const out = await response.json(), bySlug = new Map(out.records.map(r => [r.slug,r]));
      for (const r of DATA.records) {
        const fresh = bySlug.get(r.slug);
        if (fresh && JSON.stringify(attributeInputs(r)) === JSON.stringify(attributeInputs(fresh))
            && (r._patch_url || r.main_image_original_url) === (fresh._patch_url || fresh.main_image_original_url)) {
          r._attribute_comparison = fresh._attribute_comparison;
        }
      }
      DATA.attribute_counts = out.attribute_counts;
      ATTRIBUTE_FAILURES = 0;
      // Replace only comparison sections. Keep editors, uploads, focus and drafts intact.
      for (const card of document.querySelectorAll("article.wine:not([data-deferred])")) {
        const r = DATA.records.find(record => record.slug === card.id);
        const old = card.querySelector(".attribute-comparison");
        if (r && old && !old.contains(document.activeElement) && !old.querySelector("details[open]")) {
          const fragment = document.createElement("template"); fragment.innerHTML = attributeTable(r);
          old.replaceWith(fragment.content.firstElementChild);
        }
      }
      if ($("#attribute-filter").value !== "all") {
        applyView();
        const changed = beforeSlugs !== ROWS.map(r=>r.slug).join("\0");
        const editing = [...document.querySelectorAll("article.wine:not([data-deferred])")].some(keepCardMounted);
        if (changed && !editing) render();
      }
      updateAttributeQueueControls();
      updateAttributeCounts();
    } catch (error) {
      $("#attribute-queue-status").textContent = error.message + " · retrying";
      retry = true; ATTRIBUTE_FAILURES = Math.min(ATTRIBUTE_FAILURES+1,4);
    }
  })();
  try {await ATTRIBUTE_REQUEST;} finally {
    ATTRIBUTE_REQUEST = null;
    if (retry) scheduleAttributePoll(true);
    else if (attributeWorkerActive() && DATA.records.some(r => r.state !== "Removed" && ["pending","running","not_queued"].includes(attributeOf(r)?.state))) scheduleAttributePoll();
  }
}
async function queueAttributes(body, button) {
  button.disabled = true;
  const status = $("#attribute-queue-status");
  try {
    const response = await fetch("/api/dataset-attributes", {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
    const out = await response.json();
    if (!response.ok) throw Error(out.error || response.status);
    status.textContent = out.message;
    // Finish any older snapshot, then fetch the state after this action.
    if (ATTRIBUTE_REQUEST) await ATTRIBUTE_REQUEST;
    await refreshAttributes();
    scheduleAttributePoll();
  } catch (error) {status.textContent = error.message;} finally {button.disabled=false;}
}
document.addEventListener("click", event => {
  const refresh = event.target.closest("[data-attribute-refresh]");
  if (refresh) {queueAttributes({sha256:refresh.dataset.attributeRefresh},refresh);return;}
  const pause = event.target.closest("#attribute-pause");
  if (pause) {queueAttributes({action:DATA.attribute_counts?.paused ? "resume" : "pause"},pause);return;}
  const cancel = event.target.closest("#attribute-cancel");
  if (cancel) {queueAttributes({action:"cancel"},cancel);return;}
  const backfill = event.target.closest("#attribute-backfill");
  if (backfill) {queueAttributes({scope:"missing"},backfill);return;}
  const claims = event.target.closest("[data-attribute-claims]");
  if (claims) {
    const slug=claims.dataset.attributeClaims;
    if (ATTRIBUTE_CLAIMS_OPEN.has(slug)) ATTRIBUTE_CLAIMS_OPEN.delete(slug); else ATTRIBUTE_CLAIMS_OPEN.add(slug);
    renderCard(slug);return;
  }
  const image = event.target.closest("[data-attribute-image]");
  if (image) {showImagePreview(image.dataset.attributeImage,image.dataset.attributeKind);return;}
  if (event.target.closest("[data-attribute-conflicts]")) {
    $("#attribute-filter").value="conflict";$("#attribute-field").value="all";
    changeAdvancedFilter();saveHeader();
  }
});
