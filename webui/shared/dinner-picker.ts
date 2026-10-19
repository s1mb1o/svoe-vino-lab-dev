import { DINNER_NODES, type DinnerNode } from './dinner'

export interface DinnerPickerEntry extends DinnerNode {
  parentId: string | null
  level: number
  displayLabel: string
  context: string
}
const byId = new Map(DINNER_NODES.map(node => [node.id, node]))
function ancestors(node: DinnerNode): DinnerNode[] {
  const parent = node.parent_id ? byId.get(node.parent_id) : undefined
  return parent ? [...ancestors(parent), parent] : []
}

// Keep every source ID. Fold extra intermediate classes into the second level.
export const DINNER_PICKER_ENTRIES: readonly DinnerPickerEntry[] = DINNER_NODES.map(node => {
  const path = ancestors(node)
  const root = path[0]
  const parent = path.at(-1)
  const parentId = node.kind === 'class' ? root?.id ?? null : parent?.id ?? null
  return { ...node, parentId, level: !parentId ? 1 : node.kind === 'class' || parentId === root?.id ? 2 : 3,
    displayLabel: node.kind === 'class' ? [...path.slice(1).map(value => value.label), node.label].join(' › ') : node.label,
    context: path.map(value => value.label).join(' › ') }
})
const normalize = (value: string) => value.toLocaleLowerCase('ru').replaceAll('ё', 'е').trim()
export function dinnerPickerRows(expanded: ReadonlySet<string>, query = ''): DinnerPickerEntry[] {
  const words = normalize(query).split(/\s+/).filter(Boolean)
  if (words.length) {
    return DINNER_PICKER_ENTRIES.filter(node => words.every(word => normalize(`${node.context} ${node.label}`).includes(word)))
      .sort((a, b) => Number(normalize(b.label).includes(normalize(query))) - Number(normalize(a.label).includes(normalize(query))))
  }
  const rows: DinnerPickerEntry[] = []
  function append(parentId: string | null) {
    for (const node of DINNER_PICKER_ENTRIES.filter(value => value.parentId === parentId)) {
      rows.push(node)
      if (expanded.has(node.id)) append(node.id)
    }
  }
  append(null)
  return rows
}
