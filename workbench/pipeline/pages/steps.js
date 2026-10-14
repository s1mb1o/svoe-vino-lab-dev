/* The step view of one photo (plan 41). `/runs` shows it in the step popup of a query
   photo, and `/recognize` shows it under the drop area (plan 55). `lab_pages.page` puts
   this file in place of the mark line STEPS_JS of a page. The CSS is in `steps.css`.

   The answer of `/api/run-steps` or of `POST /api/recognize` holds the rounds and the
   steps of the photo. `Steps.html(data, open)` gives the HTML of the notes, the rounds,
   and the total line. `open` is the Set of the keys of the open cards of the page; the
   card of a failed step is always open. `Steps.toggle(head, open)` opens or closes one
   card. The file has its own escape function, so it needs nothing of the page. */
const Steps = (() => {
  const esc = s => (s == null ? "" : String(s)).replace(/[&<>"']/g,
    c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  const stepKey = s => `${s.id}:${s.view || ""}`;
  const dur = ms => ms === null || ms === undefined ? "—"
    : ms < 1000 ? `${ms < 10 ? Number(ms).toFixed(1) : Math.round(ms)} ms`
    : `${(ms / 1000).toFixed(2)} s`;
  const score4 = v => v === null || v === undefined ? "" : Number(v).toFixed(4);
  const CHECK_TEXT = { same: "same as the run", changed: "changed since the run" };
  const CHECK_TIP = {
    same: "The image made again now has the sha256 that the run recorded.",
    changed: "The image made again now differs from the image of the run.",
  };

  /* Steps that overlap in time share a lane, as on 8162. The counter starts at 1 in each
     round, so the first group is purple. A step with no time has no lane. The trace rounds
     each time to 0.1 ms, so a gap of less than 1 ms is no overlap. */
  function stepLanes(steps) {
    const lanes = new Map();
    let lane = 0, end = -Infinity;
    const timed = steps.filter(s => s.start_ms !== null && s.start_ms !== undefined &&
                                    s.ms !== null && s.ms !== undefined)
      .sort((a, b) => a.start_ms - b.start_ms);
    for (const s of timed) {
      if (s.start_ms >= end - 1) lane++;
      end = Math.max(end, s.start_ms + s.ms);
      lanes.set(s.n, lane % 2);
    }
    return lanes;
  }

  /* The clock of a round: the elapsed time (the last end minus the first start) and the
     sum of the step times. A round whose steps have a time but no start shows the sum. */
  function roundClock(steps) {
    const withMs = steps.filter(s => s.ms !== null && s.ms !== undefined);
    if (!withMs.length) return `<span class="clock"><em>time not recorded</em></span>`;
    const sum = withMs.reduce((total, s) => total + s.ms, 0);
    if (withMs.some(s => s.start_ms === null || s.start_ms === undefined)) {
      return `<span class="clock"><em>sum of steps ${dur(sum)}</em></span>`;
    }
    const first = Math.min(...withMs.map(s => s.start_ms));
    const last = Math.max(...withMs.map(s => s.start_ms + s.ms));
    const saved = sum - (last - first);
    return `<span class="clock">elapsed ${dur(last - first)}<em>sum of steps ${dur(sum)}${
      saved >= 1 ? ` · saved in parallel ${dur(saved)}` : ""}</em></span>`;
  }

  function artifactHtml(a, deferImages) {
    const boxes = (a.boxes || []).length && a.width && a.height;
    const svg = boxes ? `<svg viewBox="0 0 ${a.width} ${a.height}" preserveAspectRatio="xMidYMid meet"
        aria-hidden="true">${a.boxes.map(b => `<rect x="${b[0]}" y="${b[1]}" width="${
        b[2] - b[0]}" height="${b[3] - b[1]}"/>`).join("")}</svg>` : "";
    const check = a.check ? `<br><span class="chk ${esc(a.check)}" title="${esc(CHECK_TIP[a.check] ||
        "")}">${esc(CHECK_TEXT[a.check] || a.check)}</span>` : "";
    return `<figure class="${boxes ? "wide" : ""}"><div class="frame"><img loading="lazy"
        ${deferImages && a.deferred ? "data-step-src" : "src"}="${esc(a.src)}" alt="" data-full="${esc(a.src)}"${a.alpha ? ' class="alpha"' : ""}>${
        svg}</div><figcaption>${esc(a.caption)}${check}</figcaption></figure>`;
  }

  function stepItemHtml(it, deferImages) {
    const moved = it.moved ? `<span class="${it.moved > 0 ? "mv-up" : "mv-down"}" title="${
      it.moved > 0 ? "up" : "down"} ${Math.abs(it.moved)} against the order before the step">${
      it.moved > 0 ? "▲" : "▼"}${Math.abs(it.moved)}</span>` : "";
    const source = `${deferImages ? "data-step-src" : "src"}="${esc(it.image)}"`;
    const fallback = it.image_fallback ? ` data-step-fallback="${esc(it.image_fallback)}"
        onerror="Steps.imageError(this)"` : "";
    const picture = it.image ? `<img loading="lazy" ${source} alt=""
        data-full="${esc(it.image)}"${fallback}>` : `<div class="nobottle">no catalogue image</div>`;
    return `<div class="cand ${it.truth ? "truth" : ""} ${it.forbidden ? "forbidden" : ""}"
        title="${esc(it.name || it.slug)}">${picture}
      <div class="r"><span>#${esc(it.rank)}${moved}</span><span>${score4(it.score)}</span></div>
      <div class="sl">${esc(it.slug)}</div>${it.detail ? `<div class="dt">${esc(it.detail)}</div>`
        : ""}</div>`;
  }

  function stepListHtml(list, deferImages) {
    return `<div class="slist"><h4>${esc(list.title)}</h4>${list.note
      ? `<div class="snote">${esc(list.note)}</div>` : ""}<div class="srow">${
      (list.items || []).map(item => stepItemHtml(item, deferImages)).join("")
        || '<span class="snote">no candidate</span>'
      }</div></div>`;
  }

  /* The VLM rule step: legacy matcher answers or plan 92 option scores, the candidate
     scores, the time, and whether the code changed the order. */
  function optionScoresHtml(questions, optionScores, errors = {}) {
    return (questions || []).map(q => {
      const scores = optionScores[q.id];
      const values = scores && typeof scores === "object" && !Array.isArray(scores)
        ? (q.options || Object.keys(scores)).map(option => `<b>${esc(option)}</b> ${
            scores[option] === undefined ? "missing" : esc(JSON.stringify(scores[option])) + "%"
          }`).join(" &middot; ")
        : "no score object returned";
      return `<div class="q">${esc(q.id)} ${esc(q.question)}</div><div class="sc">${values}</div>${
        errors[q.id] ? `<div class="err">Rejected: ${esc(errors[q.id])}</div>` : ""}`;
    }).join("") + (errors._response
      ? `<div class="err">${esc(errors._response)}</div>` : "");
  }

  function stepVlmHtml(v) {
    const answers = v.answers || {};
    const raw = v.raw_option_scores || {};
    const attempts = v.attempts || [];
    const hasResponse = Object.keys(raw).length || attempts.some(a => a.raw_text != null);
    let body = v.error ? `<div class="err">${hasResponse ? "Response rejected" : "VLM error"}: ${
      esc(v.error)}. The base order stays.</div>`
      : "";
    const accepted = v.option_scores || {};
    const optionScores = Object.keys(accepted).length ? accepted : raw;
    if (Object.keys(optionScores).length) {
      if (!Object.keys(accepted).length) {
        body += '<div class="snote">Raw response. These scores were not used for ranking.</div>';
      }
      body += optionScoresHtml(v.questions, optionScores, v.validation_errors);
    } else if (v.mode === "evidence") {
      body += '<div class="snote">Raw option scores were not recorded in this run.</div>';
    } else {
      body += (v.questions || []).map(q => `<div class="q">${esc(q.id)} ${esc(q.question)} &rarr;
        <span class="a">${esc(answers[q.id] == null ? "no answer" : answers[q.id])}</span></div>`)
        .join("");
    }
    if (attempts.length > 1) {
      body += `<div class="snote">${v.error ? "Retry did not produce a valid response."
        : "Response accepted after one retry."}</div>`;
    }
    if (attempts.length) {
      body += attempts.map(a => `<details class="data"><summary>Attempt ${esc(a.number)} · ${
        a.cached ? "from the cache" : dur(a.ms)} · ${a.error ? "rejected or failed" : "accepted"}</summary>${
        a.error ? `<div class="err">${esc(a.error)}</div>` : ""}${
        optionScoresHtml(v.questions, a.raw_option_scores || {}, a.validation_errors)}${
        stepDataHtml("Raw response", a.raw_text, false)}</details>`).join("");
    }
    body += Object.keys(answers).filter(k => !(v.questions || []).some(q => q.id === k))
      .map(k => `<div class="q">${esc(k)} &rarr; <span class="a">${esc(answers[k])}</span></div>`)
      .join("");
    if (v.answer) {
      body += `<div class="q">answer &rarr; <span class="a">${esc(JSON.stringify(v.answer))}</span>${
        v.chosen ? ` = <b>${esc(v.chosen)}</b>` : ""}</div>`;
    }
    const scores = v.scores || {};
    if ((v.window || []).length && v.mode !== "evidence") {
      body += `<div class="sc">scores: ${v.window.map(slug => `<b>${esc(slug)}</b> ${
        (scores[slug] || 0) > 0 ? "+" : ""}${esc(scores[slug] || 0)}`).join(" &middot; ")}</div>`;
    }
    const base = v.base_scores || {};
    const evidence = v.evidence_scores || {};
    const decision = v.decision_scores || {};
    if (Object.keys(decision).length) {
      body += `<div class="sc">candidate scores (weight ${esc(v.decision_weight)}): ${
        (v.window || []).map(slug => `<b>${esc(slug)}</b> embedding ${score4(base[slug])}, ` +
          `evidence ${score4(evidence[slug])}, decision ${score4(decision[slug])}`)
          .join(" &middot; ")}</div>`;
    }
    return `<div class="vlm"><div class="vh">VLM &middot; ${esc(v.mode || "rule")} &middot; cluster ${
      esc(v.cluster || "?")} &middot; ${v.cached ? "from the cache" : dur(v.ms)}</div>${body}
      <div class="mv">${v.changed ? "the code changed the order" : "the base order stays"}</div></div>`;
  }

  function stepDataHtml(title, value, open) {
    if (value === null || value === undefined ||
        (typeof value === "object" && !Object.keys(value).length)) return "";
    return `<details class="data"${open ? " open" : ""}><summary>${esc(title)}</summary><pre>${
      esc(JSON.stringify(value, null, 2))}</pre></details>`;
  }

  function stepHtml(s, lane, openKeys) {
    const key = stepKey(s);
    const open = s.state === "failed" || openKeys.has(key);
    const meta = [s.service, s.model, s.group].filter(Boolean).join(" · ");
    let body = s.error ? `<div class="err">${esc(s.error)}</div>` : "";
    body += (s.notes || []).map(n => `<div class="snote">${esc(n)}</div>`).join("");
    if ((s.artifacts || []).length) {
      body += `<div class="artifacts">${s.artifacts.map(a => artifactHtml(a, !open)).join("")}</div>`;
    }
    if (s.vlm) body += stepVlmHtml(s.vlm);
    body += (s.lists || []).map(list => stepListHtml(list, s.id === "search" && !open)).join("");
    body += stepDataHtml("Step settings", s.settings, false);
    body += stepDataHtml("Result", s.result, s.state === "failed");
    return `<section class="step" data-key="${esc(key)}"${lane === undefined ? ""
        : ` data-lane="${lane}"`}>
      <div class="head" role="button" tabindex="0" aria-expanded="${open}">
        <span class="id">${String(s.n).padStart(2, "0")}</span>
        <span class="label">${esc(s.name)}</span>
        <span class="meta">${esc(meta)}</span>
        <span class="meta">${esc(dur(s.ms))}</span>${s.cached ? `
        <span class="pill cached" title="The answer came from data/cache/: no request went to the service.">cached</span>`
        : ""}
        <span class="pill ${esc(s.state)}">${esc(s.state)}</span>
      </div>
      <div class="body"${open ? "" : " hidden"}>${body}</div></section>`;
  }


  function patchPanel(data) {
    if (!data.run || !data.query) return "";
    return `<section class="patch-inspection" data-run="${esc(data.run)}" data-query="${esc(data.query)}">
      <h3>Original patch inspection <span class="pill">Experiment</span></h3>
      <p>Compare bottle crops, patch weights, and RANSAC correspondences. This calculation uses the patch experiment and preserves the saved run result.</p>
      <button type="button" onclick="Steps.loadPatches(this)">Inspect patches</button>
      <div class="patch-output" aria-live="polite"></div></section>`;
  }

  async function loadPatches(button) {
    const panel = button.closest(".patch-inspection"), output = panel.querySelector(".patch-output");
    const url = `/api/run-patches?id=${encodeURIComponent(panel.dataset.run)}&query=${encodeURIComponent(panel.dataset.query)}`;
    button.disabled = true;
    output.textContent = "Computing cropped bottle patches locally…";
    try {
      let value;
      for (let attempt = 0; attempt < 120; attempt++) {
        if (!panel.isConnected) return;
        const response = await fetch(url+(attempt === 0 ? "&start=1" : ""), {cache: "no-store"});
        value = await response.json();
        if (!response.ok || value.error || value.status === "failed") throw new Error(value.error || `HTTP ${response.status}`);
        if (value.status === "ready") break;
        await new Promise(resolve => setTimeout(resolve, 2000));
      }
      if (value.status !== "ready") throw new Error("Calculation continues. Select Inspect patches again to read its result.");
      panel._patches = value;
      output.innerHTML = `<p>${esc(value.notice)}</p><label>Reference candidate <select onchange="Steps.patchCandidate(this)">
        ${value.candidates.map((item,i) => `<option value="${i}">#${item.rank} ${esc(item.slug)} · ${score4(item.score)}</option>`).join("")}</select></label>
        <p class="patch-summary">${value.query_patches} query patches · ${value.excluded_query_patches} excluded · ${esc(value.foreground)}<br>Occlusion: ${esc(value.occlusion || "unknown")}<br>
        Query crop: ${esc(value.query_crop?.source_size?.join(" × "))} source → ${esc(value.query_crop?.input_size?.join(" × "))} input · ${esc(value.query_crop?.status)}<br>Ranking: ${esc(value.ranking_mode || "experimental")}<br>Overlay weights: glass ${esc(value.weights.bottle)} · label ${esc(value.weights.label)} · background ${esc(value.weights.background)} · experimental weighted share ${esc(value.experimental_weighted_share ?? value.weighted_share)}</p>
        <div class="patch-candidate"></div>`;
      patchCandidate(output.querySelector("select"));
    } catch(error) { output.textContent = `Cannot inspect patches: ${error.message}`; }
    finally { button.disabled = false; }
  }

  function patchCandidate(select) {
    const panel = select.closest(".patch-inspection"), item = panel._patches.candidates[Number(select.value)];
    const geometry = item.geometry;
    const crop = item.crop;
    panel.querySelector(".patch-candidate").innerHTML = `<p>Reference crop: ${esc(crop?.source_size?.join(" × "))} source → ${esc(crop?.input_size?.join(" × "))} input · ${esc(crop?.status)}</p><p>RANSAC ${geometry.reliable ? "accepted" : "rejected"} · ${geometry.inliers || 0} inliers · ${item.hidden_reference_patches} reference patches behind query occlusion
      ${geometry.reason ? ` · ${esc(geometry.reason)}` : ""}</p><img class="patch-figure" loading="lazy" src="${esc(item.src)}" data-full="${esc(item.src)}" alt="Reference and query bottle crops, patch weights, and RANSAC correspondences">`;
  }

  /* The notes, the rounds, and the total line of one answer. The total line compares the
     time of the whole photo with the sum of the step times. */
  function html(data, openKeys) {
    const row = data.row || {};
    let out = (data.notes || []).map(n => `<p class="sp-note">${esc(n)}</p>`).join("");
    for (const round of data.rounds || []) {
      const lanes = stepLanes(round.steps);
      out += `<div class="round"><h3>${esc(round.title)}<span class="note">${esc(round.note || "")
        }</span>${roundClock(round.steps)}</h3><div class="steps">${
        round.steps.map(s => stepHtml(s, lanes.get(s.n), openKeys)).join("")}</div></div>`;
    }
    const steps = (data.rounds || []).flatMap(round => round.steps)
      .filter(s => s.ms !== null && s.ms !== undefined);
    const sum = steps.reduce((total, s) => total + s.ms, 0);
    out += data.recorded
      ? `<div class="sp-total">Total of the photo <strong>${dur(row.latency_ms)}</strong> · sum of steps ${
          dur(sum)} · outside the steps ${dur(Math.max(0, (row.latency_ms || 0) - sum))}</div>`
      : `<div class="sp-total">Total of the photo <strong>${dur(row.latency_ms)}</strong> · the run recorded no time of each step</div>`;
    out += patchPanel(data);
    return out;
  }

  /* Open or close the card of `head`. The card of a failed step stays open. */
  function toggle(head, openKeys) {
    const card = head.closest(".step");
    const body = card.querySelector(".body");
    if (card.querySelector(".pill.failed")) return;
    body.hidden = !body.hidden;
    head.setAttribute("aria-expanded", String(!body.hidden));
    if (body.hidden) openKeys.delete(card.dataset.key);
    else {
      openKeys.add(card.dataset.key);
      for (const image of body.querySelectorAll("img[data-step-src]")) {
        image.src = image.getAttribute("data-step-src");
        image.removeAttribute("data-step-src");
      }
    }
  }

  function imageError(image) {
    const fallback = image.getAttribute("data-step-fallback");
    if (!fallback) return;
    image.removeAttribute("data-step-fallback");
    image.removeAttribute("onerror");
    image.setAttribute("data-full", fallback);
    image.src = fallback;
  }

  return { html, toggle, imageError, dur, loadPatches, patchCandidate, vlm: stepVlmHtml };
})();
