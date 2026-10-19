// Keep this registry explicit. Nitro does not transform import.meta.glob in shared modules.
// Each map is a separate chunk. A page loads one map when the user opens it.
// After a map change, run `npm run line-maps:index` and commit `../product-line-index.json`.
export const PRODUCT_LINE_LOADERS: Readonly<Record<string, () => Promise<{ default: unknown }>>> = {
  'abrau-durso': () => import('./abrau-durso.json'),
  'agora': () => import('./agora.json'),
  'alma-valley': () => import('./alma-valley.json'),
  'belbek': () => import('./belbek.json'),
  'chateau-pinot': () => import('./chateau-pinot.json'),
  'derbent-vino': () => import('./derbent-vino.json'),
  'esse': () => import('./esse.json'),
  'fanagoria': () => import('./fanagoria.json'),
  'inkerman': () => import('./inkerman.json'),
  'koktebel': () => import('./koktebel.json'),
  'kuban-vino': () => import('./kuban-vino.json'),
  'massandra': () => import('./massandra.json'),
  'myskhako': () => import('./myskhako.json'),
  'novy-svet': () => import('./novy-svet.json'),
  'sober-bash': () => import('./sober-bash.json'),
  'soyuz-vino': () => import('./soyuz-vino.json'),
  'valery-zakharyin': () => import('./valery-zakharyin.json'),
  'vedernikov': () => import('./vedernikov.json'),
  'zolotaya-balka': () => import('./zolotaya-balka.json'),
}
