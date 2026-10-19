export const AGE_CONFIRMATION_KEY = 'svoe-vino.age-confirmed.v1'

// Hide the server-rendered age gate before the browser paints the page.
// The page hydrates with the same storage value and then removes the gate.
export const AGE_INIT_SCRIPT = `(() => {
  try { if (localStorage.getItem('${AGE_CONFIRMATION_KEY}') === 'yes') document.documentElement.dataset.ageConfirmed = 'yes'; } catch {}
})();`
