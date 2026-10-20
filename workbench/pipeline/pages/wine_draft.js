// The staged bottle and similar cards belong to the Add wine dialog alone.
const wineDraft = (() => {
  const state = {generation: 0, recognizing: false, checking: false, timer: null,
    recognition: null, search: null, matches: [], edits: new Map(), automatic: new Map(),
    typed: new Map(), lastFile: null, returnFocus: null, selected: null};
  const form = $("#wine-form");
  const labels = {exact: "Exact same wine", different_vintage: "Same wine · different year",
    unknown_vintage: "Same wine · year missing on one card", similar: "Similar wine"};
  const fields = () => [...form.querySelectorAll("input[name], select[name], textarea[name]")];
  const empty = element => !element.value.trim();
  function status(message, retry = false) {
    $("#wine-recognition-status").textContent = message;
    $("#wine-recognition-retry").hidden = !retry;
    $("#wine-recognition-cancel").hidden = !state.recognizing;
  }
  const identityFields = ["name", "producer", "beverage_type_code", "category", "region", "grapes", "sweetness", "vintage"];
  function values() {
    return Object.fromEntries(identityFields.map(name => [name, form.elements[name].value.trim()]));
  }
  function pause(ms, signal) {
    return new Promise((resolve, reject) => {
      const abort = () => { clearTimeout(timer); const error = new Error("Recognition cancelled"); error.name = "AbortError"; reject(error); };
      const timer = setTimeout(() => { signal.removeEventListener("abort", abort); resolve(); }, ms);
      signal.addEventListener("abort", abort, {once: true});
      if (signal.aborted) abort();
    });
  }
  function invalidate() {
    state.generation++;
    state.recognition?.abort(); state.search?.abort();
    state.recognition = state.search = null;
    clearTimeout(state.timer);
    state.recognizing = state.checking = false;
    $("#wine-recognition-cancel").hidden = true;
  }
  function fill(source, edited = null) {
    for (const element of fields()) {
      let value = source[element.name];
      if (!edited && element.name === "vintage") {
        const namedYears = [...new Set(form.elements.name.value.match(/(?<!\d)(?:19|20)\d{2}(?!\d)/g) || [])]
          .filter(year => Number(year) <= new Date().getFullYear() + 1);
        if (namedYears.length > 1) continue;
        if (namedYears.length === 1) value = namedYears[0];
      }
      if (element.name === "slug" || !value || !empty(element)) continue;
      if (edited && (state.edits.get(element.name) || 0) !== (edited.get(element.name) || 0)) continue;
      if (element.tagName === "SELECT" && ![...element.options].some(o => o.value === value)) {
        element.add(new Option(value, value));
      }
      element.value = value;
      if (edited) state.automatic.set(element.name, value);
      else state.edits.set(element.name, (state.edits.get(element.name) || 0) + 1);
    }
    if (!WINE_FORM.slugTyped) $("#wine-slug").value = slugOfName(form.elements.name.value);
    updateWineForm();
  }
  async function post(path, body, signal) {
    const response = await fetch(path, {method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify(body), signal});
    const result = await response.json();
    if (!response.ok) {
      const error = new Error(result.error || `HTTP ${response.status}`);
      error.status = response.status; throw error;
    }
    return result;
  }
  function render(result) {
    state.matches = result.matches || [];
    $("#wine-similar-status").textContent = result.total
      ? `${state.matches.length < result.total ? `Showing ${state.matches.length} of ` : ""}${result.total} candidate${result.total === 1 ? "" : "s"} · all catalogue states`
      : "No similar wines found. Check the recognized fields.";
    $("#wine-similar-list").innerHTML = state.matches.map((match, index) => {
      const r = match.record, image = r.main_image_url;
      return `<button type="button" class="wine-draft-candidate" data-wine-draft-card="${index}">
        ${image ? `<img src="${esc(image)}" alt="" loading="lazy">` : ""}<span>
        <strong>${esc(r.name)}</strong><small>${esc(r.producer || "")}</small>
        <small>${esc(labels[match.relation])} · ${esc(match.values.vintage || "year undefined")}</small>
        <small>${esc(r.state || "")} · ${esc(match.reasons.join(" · "))}</small></span></button>`;
    }).join("");
    const conflicts = result.conflicts || [];
    $("#wine-duplicate-warning").hidden = !conflicts.length;
    $("#wine-duplicate-warning").textContent = conflicts.some(c => c.relation === "exact")
      ? "The exact same wine already exists. Review the existing card before saving."
      : conflicts.some(c => c.relation === "different_vintage")
        ? "The same wine exists with a different year. Save will ask you to confirm a new vintage card."
        : "The same wine exists, but one vintage is undefined. Review the existing card before saving.";
  }
  async function search() {
    state.search?.abort();
    const controller = new AbortController(); state.search = controller;
    const generation = state.generation, snapshot = JSON.stringify(values());
    $("#wine-similar-status").textContent = "Checking similar wines…";
    try {
      const result = await post("/api/wine-draft-similar", JSON.parse(snapshot), controller.signal);
      if (generation !== state.generation || snapshot !== JSON.stringify(values()) || controller.signal.aborted) {
        const stale = new Error("The draft changed. Check similar wines again.");
        stale.name = "AbortError"; throw stale;
      }
      render(result);
      return result;
    } catch (error) {
      if (error.name !== "AbortError" && generation === state.generation) {
        $("#wine-similar-status").textContent = `Cannot check similar wines: ${error.message}. Save will retry.`;
      }
      throw error;
    }
  }
  function schedule() {
    clearTimeout(state.timer);
    state.search?.abort();
    state.matches = [];
    $("#wine-similar-list").replaceChildren();
    $("#wine-duplicate-warning").hidden = true;
    state.timer = setTimeout(() => search().catch(() => {}), 300);
  }
  async function recognize(file) {
    invalidate();
    const generation = state.generation;
    for (const [name, value] of state.automatic) {
      if (form.elements[name]?.value === value) form.elements[name].value = "";
    }
    state.automatic.clear();
    const edits = new Map(state.edits);
    const controller = new AbortController(); state.recognition = controller;
    state.recognizing = true; state.lastFile = null;
    status("Reading bottle fields with OCR/VLM…"); updateWineForm();
    schedule();
    try {
      const image = await fileBase64(file);
      if (generation !== state.generation || controller.signal.aborted) return;
      let result;
      for (let attempt = 0; attempt <= 8; attempt++) {
        try { result = await post("/api/wine-draft-recognize", {image}, controller.signal); break; }
        catch (error) {
          if (error.status !== 429 || attempt === 8) throw error;
          status("The previous bottle is still being read. Waiting to read this bottle…");
          await pause(Math.min(2000 * 2 ** attempt, 8000), controller.signal);
          if (generation !== state.generation || controller.signal.aborted) return;
        }
      }
      if (generation !== state.generation || controller.signal.aborted || WINE_FORM.file !== file) return;
      fill(result.values, edits); state.lastFile = file;
      status("Bottle fields read. Check the values and complete empty fields.");
      schedule();
    } catch (error) {
      if (generation === state.generation && error.name !== "AbortError") {
        status(`Cannot read bottle fields: ${error.message} You can enter fields manually.`, true);
      }
    } finally {
      if (generation === state.generation) { state.recognizing = false; $("#wine-recognition-cancel").hidden = true; updateWineForm(); }
    }
  }
  function closeCard() {
    $("#wine-similar-modal").hidden = true;
    $("#wine-modal").inert = false;
    state.selected = null;
    if (state.returnFocus?.isConnected) state.returnFocus.focus();
  }
  function openCard(index, trigger) {
    const match = state.matches[index]; if (!match || WINE_FORM.busy) return;
    state.selected = match; state.returnFocus = trigger;
    const record = match.record;
    $("#wine-similar-title").textContent = record.name;
    $("#wine-similar-card").innerHTML = `${record.main_image_url
      ? `<img class="wine-draft-card-image" src="${esc(record.main_image_url)}" alt="${esc(record.name)}">` : ""}
      <p>${esc(labels[match.relation])} · ${esc(record.state || "")}</p><dl>${[
        ["Producer", record.producer], ["Category", match.values.beverage_type_code === "44" ? "Sparkling wine" : match.values.beverage_type_code === "4" ? "Wine" : ""],
        ["Color", record.category], ["Region", record.region], ["Grapes", record.grapes],
        ["Sweetness", match.values.sweetness], ["Year", match.values.vintage || "undefined"],
        ["Description", record.description], ["Slug", record.slug]].map(([label, value]) =>
          `<dt>${esc(label)}</dt><dd>${esc(value || "—")}</dd>`).join("")}</dl>`;
    $("#wine-modal").inert = true;
    $("#wine-similar-modal").hidden = false;
    $("#wine-similar-close").focus();
  }
  async function beforeSave() {
    clearTimeout(state.timer);
    state.checking = true; updateWineForm();
    try {
      const result = await search();
      const conflicts = result.conflicts || [];
      if (conflicts.length) {
        const names = conflicts.slice(0, 8).map(c => `${c.slug} (${c.identity.years.join(", ") || "year undefined"}; ${c.state})`).join("\n")
          + (conflicts.length > 8 ? `\n… and ${conflicts.length - 8} more matching cards.` : "");
        const warning = conflicts.some(c => c.relation === "exact")
          ? "The exact same wine already exists. Create another card anyway?"
          : conflicts.some(c => c.relation === "different_vintage")
            ? `The same wine exists with a different year. Create a new wine card for ${values().vintage || "the draft year"}?`
            : "The same wine exists, but one year is undefined. Create a new wine card anyway?";
        if (!window.confirm(`${warning}\n\n${names}`)) return null;
      }
      return {check_duplicates: true, duplicate_acknowledgement: result.acknowledgement};
    } finally { state.checking = false; updateWineForm(); }
  }
  form.addEventListener("input", event => {
    const name = event.target.name;
    if (name) {
      state.edits.set(name, (state.edits.get(name) || 0) + 1); state.automatic.delete(name);
      state.typed.set(name, event.target.value);
    }
    schedule();
  });
  form.addEventListener("change", event => {
    const name = event.target.name;
    // A field fires `change` when it loses the focus, often at a press on a similar card.
    // A value that the `input` events already gave has its search: a new search would
    // empty the list under the pointer, and the click would not land.
    if (name && state.typed.get(name) === event.target.value) return;
    if (name) { state.edits.set(name, (state.edits.get(name) || 0) + 1); state.automatic.delete(name); }
    schedule();
  });
  $("#wine-recognition-cancel").addEventListener("click", () => {
    invalidate(); state.lastFile = WINE_FORM.file;
    status("Recognition cancelled. Enter fields manually.", true); updateWineForm(); schedule();
  });
  $("#wine-recognition-retry").addEventListener("click", () => { if (WINE_FORM.file) recognize(WINE_FORM.file); });
  $("#wine-similar-list").addEventListener("click", event => {
    const button = event.target.closest("[data-wine-draft-card]");
    if (button) openCard(Number(button.dataset.wineDraftCard), button);
  });
  $("#wine-similar-close").addEventListener("click", closeCard);
  $("#wine-similar-copy").addEventListener("click", () => {
    if (!state.selected || WINE_FORM.busy) return;
    const source = state.selected.values;
    fill(source); closeCard(); schedule();
  });
  $("#wine-similar-modal").addEventListener("click", event => {
    if (event.target === $("#wine-similar-modal")) closeCard();
  });
  document.addEventListener("keydown", event => {
    if ($("#wine-similar-modal").hidden) return;
    if (event.key === "Escape") { event.preventDefault(); event.stopImmediatePropagation(); closeCard(); }
    if (event.key === "Tab") {
      const first = $("#wine-similar-close"), last = $("#wine-similar-copy");
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    }
  }, true);
  function suggestSlug() {
    if (WINE_FORM.slugTyped) return;
    const name = form.elements.name.value.trim(), year = form.elements.vintage.value.trim();
    let base = slugOfName(name);
    if (base && /^(19|20)\d{2}$/.test(year) && !base.split("-").includes(year)) base = `${base}-${year}`;
    const occupied = new Set(DATA.records.map(r => r.slug));
    let candidate = base, suffix = 2;
    while (candidate && occupied.has("__" + candidate)) {
      const ending = `-${suffix++}`; candidate = base.slice(0, 198 - ending.length) + ending;
    }
    $("#wine-slug").value = candidate;
  }
  return {recognize, beforeSave, suggestSlug, get busy() { return state.recognizing || state.checking; },
    open() { if (WINE_FORM.file && state.lastFile !== WINE_FORM.file) recognize(WINE_FORM.file); else schedule(); },
    close() { invalidate(); closeCard(); updateWineForm(); },
    reset() { invalidate(); state.automatic.clear(); state.edits.clear(); state.lastFile = null;
      closeCard(); status(""); render({matches: [], total: 0, conflicts: []}); }};
})();
