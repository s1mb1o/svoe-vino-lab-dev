/* Share configuration selection across the Workbench pages. Keep the native select
   as the source of the value and dispatch its existing change event. */
const ConfigurationPicker = (() => {
  const escape = value => String(value ?? "").replace(/[&<>"']/g,
    char => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[char]));
  const words = {android: "Android", gx10: "GX10", local: "Local", siglip2: "SigLIP2",
    naflexvit: "NaFlexViT", dinov2: "DINOv2", dinov3: "DINOv3", sam3: "SAM3", dis: "DIS",
    pe: "PE", core: "Core", base: "Base", white: "White", seg: "Segmented", crop: "Crop",
    barcode: "Barcode", rerank: "Rerank", lab: "Lab", compare: "Compare", ocr: "OCR",
    tesseract: "Tesseract", paddleocr: "PaddleOCR", label: "Label", bottle: "Bottle",
    upright: "Upright", full: "Full", main: "Main"};
  function readableName(name) {
    return String(name || "").split(/[-_]+/).filter(Boolean).map(word => {
      const rotation = /^rot(\d+)$/.exec(word);
      return rotation ? `${rotation[1]}° rotation` : (words[word] || word);
    }).join(" ");
  }
  function viewText(views) {
    return Object.entries(views || {}).map(([view, value]) => {
      const steps = Array.isArray(value) ? value : value?.steps || [];
      const text = steps.map(step => {
        if (step.step === "segment_dis") return "DIS cut";
        if (step.step === "segment") return `${step.target || "package"} cut`;
        if (step.step === "remove_background") return "remove background";
        if (step.step === "white_background") return "white background";
        if (step.step === "square_on_white") return "square";
        if (step.step === "resize") return `${step.max_size} px`;
        return String(step.step || "").replaceAll("_", " ");
      }).join(" → ");
      return `${view}: ${text || "original image"}`;
    }).join(" · ");
  }
  function embeddingItem(entry) {
    const counts = entry.counts || {};
    const status = entry.error || entry.index_error || [
      `${counts.current || 0} / ${entry.items || 0} current`,
      ...["stale", "missing", "failed"].filter(key => counts[key]).map(key => `${counts[key]} ${key}`)
    ].join(" · ");
    return {name: entry.name, label: readableName(entry.name), status,
      tone: entry.error || entry.index_error || counts.failed ? "bad"
        : counts.stale || counts.missing ? "warn" : "good",
      description: [entry.backend && `Backend: ${entry.backend}`, entry.model && `Model: ${entry.model}`,
        viewText(entry.views) && `Input: ${viewText(entry.views)}`,
        entry.rotation_step && `Rotation step: ${entry.rotation_step}°`].filter(Boolean).join(" · ")};
  }
  function pipelineItem(entry) {
    return {name: entry.name, label: readableName(entry.name),
      disabled: !entry.runnable, status: entry.runnable ? "Ready" : entry.reason || "Unavailable",
      tone: entry.runnable ? "good" : "bad",
      description: [`Backend: ${entry.embedding_backend || entry.backend || "embedding"}`,
        entry.embedding && `Index: ${entry.embedding}`, entry.model && `Index model: ${entry.model}`,
        viewText(entry.views) && `Query: ${viewText(entry.views)}`,
        entry.bottle_orientation && "Bottle orientation: upright",
        ...(entry.stages || []),
        entry.barcode ? "Barcode: on" : "Barcode: off",
        entry.rerank ? "Cluster rerank: on" : "Cluster rerank: off"].filter(Boolean).join(" · ")};
  }
  function readPreference(key) {
    try {
      const value = JSON.parse(localStorage.getItem(key) || "{}");
      return {favorites: Array.isArray(value?.favorites) ? value.favorites.filter(x => typeof x === "string") : [],
        recent: Array.isArray(value?.recent) ? value.recent.filter(x => typeof x === "string").slice(0, 8) : []};
    } catch (_) { return {favorites: [], recent: []}; }
  }
  function create({select, summary, label, storage, links = () => []}) {
    const key = `svl.configuration-picker.${storage}`;
    let preference = readPreference(key), items = [], tab = "all", lastValue = null, storageWritable = true;
    const trigger = document.createElement("button");
    trigger.type = "button"; trigger.className = "config-picker-trigger";
    trigger.textContent = "Loading choices…"; trigger.disabled = true;
    trigger.setAttribute("aria-label", `Choose ${label.toLowerCase()}`);
    trigger.setAttribute("aria-haspopup", "dialog"); trigger.setAttribute("aria-expanded", "false");
    const dialog = document.createElement("dialog");
    dialog.className = "config-picker-dialog"; dialog.id = `${select.id}-picker`;
    trigger.setAttribute("aria-controls", dialog.id);
    dialog.setAttribute("aria-labelledby", `${dialog.id}-title`);
    dialog.innerHTML = `<div class="config-picker-head"><h2 id="${dialog.id}-title">Choose ${escape(label.toLowerCase())}</h2>
      <button type="button" data-close aria-label="Close ${escape(label.toLowerCase())} picker">Close</button></div>
      <div class="config-picker-tools"><input type="search" aria-label="Search ${escape(label.toLowerCase())}s"
        placeholder="Search name, model, backend or input" autocomplete="off">
      <div class="config-picker-tabs" role="group" aria-label="${escape(label)} choices">
        <button type="button" data-tab="all">All</button><button type="button" data-tab="favorites">Favorites</button>
        <button type="button" data-tab="recent">Recent</button></div>
      <p class="config-picker-count" role="status" aria-live="polite"></p></div>
      <div class="config-picker-list"></div><div class="config-picker-foot">↑ ↓ navigate · Enter select · Esc close</div>`;
    document.body.append(dialog);
    const search = dialog.querySelector("input"), list = dialog.querySelector(".config-picker-list");
    if (typeof dialog.showModal === "function") { select.hidden = true; select.after(trigger); }
    function persist() {
      try { localStorage.setItem(key, JSON.stringify(preference)); } catch (_) { storageWritable = false; }
    }
    function recent(name) {
      if (!name) return;
      preference.recent = [name, ...preference.recent.filter(value => value !== name)].slice(0, 8);
      persist();
    }
    function favoriteButton(item) {
      const favorite = preference.favorites.includes(item.name);
      return `<button type="button" class="config-picker-star" data-favorite="${escape(item.name)}"
        aria-label="${favorite ? "Remove" : "Add"} ${escape(item.name)} ${favorite ? "from" : "to"} favorites"
        aria-pressed="${favorite}" title="${favorite ? "Remove from" : "Add to"} favorites">${favorite ? "★" : "☆"}</button>`;
    }
    function updateSummary() {
      const item = items.find(value => value.name === select.value);
      trigger.disabled = select.disabled || !items.length;
      trigger.textContent = item ? `${item.label} ▾` : items.length ? `Choose ${label.toLowerCase()} ▾`
        : `No ${label.toLowerCase()}s available`;
      trigger.title = item?.name || label;
      trigger.setAttribute("aria-label", `Choose ${label.toLowerCase()}: ${item?.name || "none selected"}`);
      if (!summary) return;
      summary.hidden = !item;
      if (!item) return;
      summary.innerHTML = `<div class="configuration-identity"><strong>${escape(item.label)}</strong>
        <span class="configuration-status ${escape(item.tone || "")}">${escape(item.status)}</span>${favoriteButton(item)}
        ${links(item).map(link => `<a href="${escape(link.href)}">${escape(link.text)}</a>`).join("")}</div>
        <code>${escape(item.name)}</code><div class="configuration-description">${escape(item.description)}</div>`;
    }
    function render() {
      const focused = document.activeElement;
      const focusChoice = focused?.dataset.choice, focusFavorite = focused?.dataset.favorite;
      const scroll = list.scrollTop;
      let source = items;
      if (tab === "favorites") source = items.filter(item => preference.favorites.includes(item.name));
      if (tab === "recent") source = preference.recent.map(name => items.find(item => item.name === name)).filter(Boolean);
      const query = search.value.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
      const shown = source.filter(item => query.every(word =>
        `${item.name} ${item.label} ${item.description} ${item.status}`.toLocaleLowerCase().includes(word)));
      dialog.querySelectorAll("[data-tab]").forEach(button => {
        const kind = button.dataset.tab;
        const count = kind === "favorites" ? items.filter(item => preference.favorites.includes(item.name)).length
          : kind === "recent" ? preference.recent.filter(name => items.some(item => item.name === name)).length : items.length;
        button.textContent = `${kind === "all" ? "All" : kind === "favorites" ? "Favorites" : "Recent"} (${count})`;
        button.setAttribute("aria-pressed", String(tab === kind));
      });
      dialog.querySelector(".config-picker-count").textContent = `${shown.length} of ${source.length} choices`;
      list.innerHTML = shown.length ? shown.map(item => `<div class="config-picker-row${item.name === select.value ? " selected" : ""}">
        <button type="button" class="config-picker-choice" data-choice="${escape(item.name)}"${item.disabled ? " disabled" : ""}
          aria-label="Select ${escape(item.name)}"${item.name === select.value ? ' aria-current="true"' : ""}>
          <span class="config-picker-name">${escape(item.label)}${item.name === select.value ? " · Selected" : ""}</span>
          <code>${escape(item.name)}</code><span class="configuration-status ${escape(item.tone || "")}">${escape(item.status)}</span>
          <span class="configuration-description">${escape(item.description)}</span></button>${favoriteButton(item)}</div>`).join("")
        : `<div class="config-picker-empty">${query.length ? "No matching choices. Try a shorter search or open All."
          : tab === "favorites" ? "No favorites yet. Use ☆ beside a choice."
          : tab === "recent" ? "No recent choices yet. Select a configuration."
          : "No choices are available."}</div>`;
      list.scrollTop = scroll;
      if (focusChoice || focusFavorite) {
        const next = [...list.querySelectorAll("[data-choice], [data-favorite]")].find(node =>
          focusChoice ? node.dataset.choice === focusChoice && !node.disabled : node.dataset.favorite === focusFavorite);
        if (next) next.focus(); else search.focus();
      }
    }
    function close() { dialog.close(); trigger.setAttribute("aria-expanded", "false"); trigger.focus(); }
    trigger.addEventListener("click", () => {
      if (storageWritable) preference = readPreference(key);
      search.value = ""; tab = "all"; render();
      dialog.showModal(); trigger.setAttribute("aria-expanded", "true"); search.focus();
    });
    dialog.querySelector("[data-close]").addEventListener("click", close);
    // Search accepts pasted text. The Recognize page reserves other paste events for images.
    dialog.addEventListener("paste", event => event.stopPropagation());
    for (const type of ["dragover", "drop"]) dialog.addEventListener(type, event => {
      event.preventDefault(); event.stopPropagation();
    });
    dialog.addEventListener("cancel", event => { event.preventDefault(); close(); });
    dialog.addEventListener("click", event => {
      if (event.target === dialog) {
        const box = dialog.getBoundingClientRect();
        if (event.clientX < box.left || event.clientX > box.right || event.clientY < box.top || event.clientY > box.bottom) close();
      }
      const tabButton = event.target.closest("[data-tab]");
      if (tabButton) { tab = tabButton.dataset.tab; render(); }
      const choice = event.target.closest("[data-choice]");
      if (choice && !choice.disabled) {
        select.value = choice.dataset.choice;
        select.dispatchEvent(new Event("change", {bubbles: true})); close();
      }
    });
    function toggleFavorite(event) {
      const button = event.target.closest("[data-favorite]");
      if (!button) return;
      const name = button.dataset.favorite;
      preference.favorites = preference.favorites.includes(name)
        ? preference.favorites.filter(value => value !== name) : [...preference.favorites, name];
      persist(); updateSummary();
      if (dialog.open) {
        render();
        const next = [...list.querySelectorAll("[data-favorite]")].find(node => node.dataset.favorite === name);
        if (next) next.focus(); else dialog.querySelector(`[data-tab="${tab}"]`).focus();
      } else summary?.querySelector("[data-favorite]")?.focus();
    }
    dialog.addEventListener("click", toggleFavorite);
    summary?.addEventListener("click", toggleFavorite);
    dialog.addEventListener("keydown", event => {
      if (event.key === "Escape") {
        event.preventDefault(); event.stopPropagation(); close(); return;
      }
      const options = [...list.querySelectorAll("[data-choice]:not(:disabled)")];
      if (event.key === "ArrowDown" || event.key === "ArrowUp") {
        if (event.target !== search && !event.target.closest(".config-picker-list")) return;
        event.preventDefault();
        const index = options.indexOf(document.activeElement);
        options[index < 0 ? (event.key === "ArrowDown" ? 0 : options.length - 1)
          : (index + (event.key === "ArrowDown" ? 1 : -1) + options.length) % options.length]?.focus();
      }
    });
    search.addEventListener("input", render);
    select.addEventListener("change", () => { recent(select.value); lastValue = select.value; updateSummary(); });
    window.addEventListener("storage", event => {
      if (event.key === key) { preference = readPreference(key); updateSummary(); if (dialog.open) render(); }
    });
    return {update(next) {
      items = next.map(item => ({...item, disabled: !!item.disabled ||
        !![...select.options].find(option => option.value === item.name)?.disabled}));
      if (select.value !== lastValue) { recent(select.value); lastValue = select.value; }
      updateSummary(); if (dialog.open) render();
    }};
  }
  return {create, readableName, viewText, embeddingItem, pipelineItem};
})();
