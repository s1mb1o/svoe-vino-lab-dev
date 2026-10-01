/* A drop of a local image that is not a file (owner message of 2026-09-30T22:15:00+0300).
   `lab_pages.page` puts this file in place of the mark line DROP_JS of a page.

   A drag of an image out of the Codex desktop app carries the address
   `app://fs/@fs/<absolute path>`, not a file. The browser cannot open that address.
   `LocalDrop.files(dataTransfer)` gives the dropped files; with no file, it asks
   `GET /api/local-image` for the bytes of the local address and makes one File of them.
   A page hands the answer to its usual file flow, so the upload checks stay the same.
   A page that reads other drop data too uses `LocalDrop.address(dataTransfer)` and then
   `LocalDrop.file(address)`.
   The server reads only Codex generated images (owner answers of
   2026-09-30T22:26:00+0300). Call `files` in the drop listener itself: the browser
   clears the drop data after the event. The promise fails with the server error. */
const LocalDrop = (() => {
  const LOCAL = /^(app:\/\/fs\/@fs\/|file:\/\/)/i;
  function address(dt) {
    if (!dt) return "";
    const values = [];
    const html = dt.getData("text/html") || "";
    if (html) {
      const image = new DOMParser().parseFromString(html, "text/html").querySelector("img[src]");
      if (image) values.push(image.getAttribute("src"));
    }
    const download = /^[^:]+:[^:]*:(.+)$/s.exec(dt.getData("DownloadURL") || "");
    if (download) values.push(download[1]);
    values.push(...(dt.getData("text/uri-list") || "").split("\n"));
    values.push((dt.getData("text/plain") || "").split("\n")[0]);
    return values.map(value => (value || "").trim()).find(value => LOCAL.test(value)) || "";
  }
  function nameOf(value) {
    const leaf = value.split(/[?#]/)[0].split("/").pop() || "";
    try { return decodeURIComponent(leaf) || "dropped-image"; } catch (e) { return leaf || "dropped-image"; }
  }
  async function file(value) {
    const res = await fetch("/api/local-image?" + new URLSearchParams({ address: value }),
      { cache: "no-store" });
    if (!res.ok) {
      let out = {};
      try { out = await res.json(); } catch (e) { out = {}; }
      throw new Error(out.error || ("HTTP " + res.status));
    }
    const blob = await res.blob();
    return new File([blob], nameOf(value), { type: blob.type });
  }
  function files(dt) {
    const dropped = [...(dt && dt.files || [])];
    if (dropped.length) return Promise.resolve(dropped);
    const value = address(dt);
    return value ? file(value).then(one => [one]) : Promise.resolve([]);
  }
  return { address, file, files };
})();
