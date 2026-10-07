/* Mount cards near the viewport. Keep keyed slots and measured heights so ordinary
   filters can reuse the Drawer and full-view navigation can mount any offscreen card. */
const VisibleCards = (() => {
  function create(container, {root = null, height = 240, slotClass = "visible-slot", initial = 0} = {}) {
    let records = new Map(), order = [], render = null, observer = null;
    const supported = typeof IntersectionObserver !== "undefined";
    function pinned(slot) {
      return slot.contains(document.activeElement) || !!slot.querySelector(".dragging, details[open]");
    }
    function mount(item, force = false) {
      if (item.mounted && (!force || pinned(item.slot))) return item.slot.firstElementChild;
      item.slot.style.height = "";
      item.slot.innerHTML = render(item.value);
      item.mounted = true;
      item.dirty = false;
      return item.slot.firstElementChild;
    }
    function evict(item) {
      if (!item.mounted || item.near || pinned(item.slot)) return;
      const measured = item.slot.getBoundingClientRect().height;
      item.slot.style.height = `${measured || height}px`;
      item.slot.replaceChildren();
      item.mounted = false;
    }
    function observe() {
      observer?.disconnect();
      if (!supported) return;
      const current = observer = new IntersectionObserver(entries => {
        if (observer !== current) return;
        for (const entry of entries) {
          const item = records.get(entry.target.dataset.visibleKey);
          if (!item || item.slot !== entry.target) continue;
          item.near = entry.isIntersecting;
          if (item.near) mount(item, item.dirty);
          else evict(item);
        }
      }, {root, rootMargin: "700px"});
      for (const item of records.values()) observer.observe(item.slot);
    }
    function set(values, keyOf, renderer, empty = "") {
      render = renderer;
      const keys = values.map(value => String(keyOf(value)));
      if (new Set(keys).size !== keys.length) throw new Error("Visible card keys must be unique");
      const same = keys.length === order.length && keys.every((key, n) => key === order[n]);
      const next = new Map();
      values.forEach((value, n) => {
        const key = keys[n];
        let item = records.get(key);
        if (!item) {
          const slot = document.createElement("div");
          slot.className = slotClass;
          slot.dataset.visibleKey = key;
          slot.style.height = `${height}px`;
          item = {slot, value, mounted: false, near: false, dirty: false};
        } else if (item.value !== value) item.dirty = true;
        item.value = value;
        next.set(key, item);
      });
      records = next;
      if (!same) {
        observer?.disconnect();
        // Do not move an unchanged focused or dragged slot during a normal rerender.
        if (keys.length) container.replaceChildren(...keys.map(key => records.get(key).slot));
        else container.innerHTML = empty;
        order = keys;
        // Start a few first-screen images in this task. Waiting for the observer
        // also waits for layout of the rest of the large page.
        if (!(root && root.scrollTop)) {
          for (const key of keys.slice(0, initial)) mount(records.get(key));
        }
        observe();
      } else if (!keys.length && container.innerHTML !== empty) container.innerHTML = empty;
      for (const item of records.values()) {
        if (!supported || item.near) mount(item, item.dirty);
      }
    }
    function ensure(key) { const item = records.get(String(key)); return item ? mount(item, item.dirty) : null; }
    function refresh(key) {
      const item = records.get(String(key));
      if (!item) return;
      item.dirty = true;
      if (item.mounted) mount(item, true);
    }
    function sweep() {
      for (const item of records.values()) {
        if (item.near && item.dirty) mount(item, true);
        else evict(item);
      }
    }
    function destroy() {
      observer?.disconnect(); observer = null;
      records.clear(); order = []; render = null;
      container.replaceChildren();
    }
    container.addEventListener("focusout", () => queueMicrotask(sweep));
    container.addEventListener("dragend", () => queueMicrotask(sweep));
    return {set, ensure, refresh, sweep, destroy};
  }
  return {create};
})();
