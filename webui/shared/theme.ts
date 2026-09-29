export type ThemePreference = 'system' | 'light' | 'dark'
export const THEME_STORAGE_KEY = 'svoe-vino.theme.v1'

// Apply the saved palette before the browser paints the page.
export const THEME_INIT_SCRIPT = `(() => {
  let preference = 'system';
  try { preference = localStorage.getItem('${THEME_STORAGE_KEY}') || 'system'; } catch {}
  const dark = preference === 'dark' || (preference !== 'light' && preference !== 'dark' && window.matchMedia('(prefers-color-scheme: dark)').matches);
  document.documentElement.dataset.theme = dark ? 'dark' : 'light';
  document.querySelectorAll('meta[name="theme-color"]').forEach(meta => {
    meta.content = dark ? '#211e1c' : '#7b3528';
  });
})();`
