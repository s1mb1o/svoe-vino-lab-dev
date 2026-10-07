/* Keep full-image src and viewer links. Use a cached preview only in small cards. */
(() => {
  const selector = '#list img, #rows img, #held img, '
    + '#drawer-results-list img, #res-body img';
  const own = new WeakMap(), first = new Map();
  function prepare(image) {
    const src = image.getAttribute('src') || '';
    if (own.get(image) === src) return;
    if (image.hasAttribute('srcset') && !own.has(image)) return;
    // The review tool and external URLs keep their original route and resolution.
    if (!/^\/images\/[a-z_]+\/[0-9a-f]{64}\.[a-z0-9]+$/.test(src)) {
      if (own.has(image)) { image.removeAttribute('srcset'); own.delete(image); }
      return;
    }
    own.set(image, src);
    image.srcset = `${src}?thumbnail=1`;
    const region = image.closest('#list, #held, #drawer-results-list, #res-body');
    if (region && !region.closest('[hidden]')
        && !(region.id === 'held' && document.body.classList.contains('side-off'))) {
      const count = first.get(region) || 0;
      if (count < (region.id === 'list' ? 1 : 4)) {
        image.loading = 'eager';
        image.fetchPriority = 'high';
        first.set(region, count + 1);
      }
    }
    // If preview generation fails, the route sends the original. A missing route
    // in another server also falls back without breaking the full-image viewer.
    image.addEventListener('error', () => {
      if (image.hasAttribute('srcset')) image.removeAttribute('srcset');
    }, {once: true});
  }
  function scan(node) {
    if (node.nodeType !== 1) return;
    if (node.tagName === "IMG" && node.matches(selector)) prepare(node);
    for (const image of node.querySelectorAll("img")) {
      if (image.matches(selector)) prepare(image);
    }
  }
  new MutationObserver(records => {
    for (const record of records) {
      if (record.type === 'attributes') scan(record.target);
      else for (const node of record.addedNodes) scan(node);
    }
  }).observe(document, {subtree: true, childList: true, attributes: true, attributeFilter: ['src']});
})();
