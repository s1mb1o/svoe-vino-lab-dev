<script setup lang="ts">
import { sourceWineUrl, type Wine } from '#shared/catalog'
import { findLineProduct, productPortalUrl, productsInGroup, type ProductLineMapData, type LineProduct, type LineGroup } from '#shared/product-line-map'

const props = withDefaults(defineProps<{
  line: ProductLineMapData
  initialSlug?: string
  recognized?: boolean
  unmatchedWine?: Wine
  // `canvas` is the pan and zoom map of the guide dialog. `page` uses the page space of /lineup/<producer>.
  layout?: 'canvas' | 'page'
}>(), { recognized: false, layout: 'canvas' })

const mapId = useId()
const CANVAS_WIDTH = 1120
const MIN_ZOOM = .6
const MAX_ZOOM = 1.4
const mapRoot = ref<HTMLElement>()
const viewport = ref<HTMLElement>()
const toolbar = ref<HTMLElement>()
const canvas = ref<HTMLElement>()
const detailHeading = ref<HTMLElement>()
const detailPanel = ref<HTMLElement>()
const failedImages = ref(new Set<string>())
function imageFailed(src?: string) {
  if (src) failedImages.value = new Set([...failedImages.value, src])
}
function recoverFailedImages() {
  for (const image of mapRoot.value?.querySelectorAll<HTMLImageElement>('img[data-map-image]') || []) {
    if (image.complete && image.naturalWidth === 0) imageFailed(image.dataset.mapImage)
  }
}
const zoom = ref(1)
const canvasHeight = ref(1800)
const selectedId = ref<string | null>(null)
const selectedUnknown = ref(false)
const expandedGroups = ref(new Set<string>())
const showDetails = ref(true)
const popupDetails = ref(false)
const mobileDetailsOpen = ref(false)
const mobileDetailsTrigger = ref<HTMLElement>()
const navigationGroup = ref('')
const isDragging = ref(false)
const pageLayout = computed(() => props.layout === 'page')
// In the page layout, the toolbar sticks to the window top. Targets keep a gap below it.
function stickyInset() { return (pageLayout.value ? toolbar.value?.offsetHeight ?? 0 : 0) + 16 }
const initialProduct = computed(() => props.initialSlug ? findLineProduct(props.line, props.initialSlug) : undefined)
const selectedProduct = computed(() => props.line.products.find(product => product.id === selectedId.value))
const selectedGroup = computed(() => props.line.groups.find(group => group.id === selectedProduct.value?.group_id))
const selectedTier = computed(() => props.line.tiers.find(tier => tier.id === selectedGroup.value?.tier_id))
const allGroupsOpen = computed(() => props.line.groups.every(group => expandedGroups.value.has(group.id)))
const tiers = computed(() => [...props.line.tiers].sort((a, b) => b.rank - a.rank))
const activeUnknown = computed(() => selectedUnknown.value ? props.unmatchedWine : undefined)
const selectedName = computed(() => {
  if (activeUnknown.value) return activeUnknown.value.name
  const product = selectedProduct.value
  if (!product) return ''
  const name = product.variant && !product.name.toLocaleLowerCase('ru').includes(product.variant.toLocaleLowerCase('ru'))
    ? `${product.name} · ${product.variant}` : product.name
  return product.catalog_card_label ? `${name} · ${product.catalog_card_label}` : name
})
const selectedImage = computed(() => {
  const src = activeUnknown.value?.image || selectedProduct.value?.image?.src
  return src && !failedImages.value.has(src) ? src : undefined
})
const selectedFrame = computed(() => activeUnknown.value ? undefined : selectedProduct.value?.image?.frame)
const selectedUrl = computed(() => {
  if (selectedProduct.value) return productPortalUrl(selectedProduct.value)
  return activeUnknown.value ? sourceWineUrl(activeUnknown.value.slug) : null
})
// The pin of «Винный дневник» (plan 07). A product without a vino-svoe.ru card has no slug and no pin.
const selectedSlug = computed(() => selectedProduct.value ? selectedProduct.value.wine_slug : activeUnknown.value?.slug ?? null)
const selectionIsInitial = computed(() => selectedProduct.value?.id === initialProduct.value?.id && Boolean(initialProduct.value))
const sourceDate = computed(() => {
  const value = props.line.scope.as_of
  return /^\d{4}-\d{2}-\d{2}$/.test(value) ? value.split('-').reverse().join('.') : value
})
const catalogSnapshotDate = computed(() => {
  const date = props.line.scope.catalog_snapshot.match(/\d{4}-\d{2}-\d{2}/)?.[0]
  return date ? date.split('-').reverse().join('.') : props.line.scope.catalog_snapshot
})
const surfaceStyle = computed(() => pageLayout.value ? undefined : { width: `${CANVAS_WIDTH * zoom.value}px`, height: `${canvasHeight.value * zoom.value}px` })
const canvasStyle = computed(() => pageLayout.value ? undefined : { width: `${CANVAS_WIDTH}px`, transform: `scale(${zoom.value})` })
let observer: ResizeObserver | undefined
let pointer: { id: number; x: number; y: number; left: number; top: number; moved: boolean } | null = null
let suppressClickUntil = 0
let mobileMedia: MediaQueryList | undefined
let mobileOpener: HTMLElement | undefined
let openGeneration = 0
let mobileFocusListenerAttached = false
type ScrollSnapshot = { elements: { element: HTMLElement; left: number; top: number }[]; x: number; y: number }
let mobileScroll: ScrollSnapshot | undefined

function captureScroll(): ScrollSnapshot {
  const elements: ScrollSnapshot['elements'] = []
  let element = viewport.value
  while (element) {
    elements.push({ element, left: element.scrollLeft, top: element.scrollTop })
    element = element.parentElement || undefined
  }
  return { elements, x: window.scrollX, y: window.scrollY }
}
function restoreScroll(snapshot?: ScrollSnapshot) {
  if (!snapshot) return
  for (const { element, left, top } of snapshot.elements) {
    if (element.isConnected) element.scrollTo({ left, top, behavior: 'instant' })
  }
  window.scrollTo({ left: snapshot.x, top: snapshot.y, behavior: 'instant' })
}
function mobileDialog() {
  return detailPanel.value?.tagName === 'DIALOG' ? detailPanel.value as HTMLDialogElement : undefined
}
function containMobileFocus(event: FocusEvent) {
  const dialog = mobileDialog()
  if (!popupDetails.value || !dialog?.open || !document.hasFocus() || (event.target instanceof Node && dialog.contains(event.target))) return
  detailHeading.value?.focus({ preventScroll: true })
  restoreScroll(mobileScroll)
  // A programmatic focus call can scroll its target after dispatching focusin.
  queueMicrotask(() => {
    if (dialog === mobileDialog() && dialog.open && mobileDetailsOpen.value) restoreScroll(mobileScroll)
  })
}
function removeMobileFocusGuard() {
  if (!mobileFocusListenerAttached) return
  document.removeEventListener('focusin', containMobileFocus)
  mobileFocusListenerAttached = false
}
function finishMobileClose(restoreFocus = true) {
  removeMobileFocusGuard()
  const opener = mobileOpener
  const scroll = mobileScroll
  mobileDetailsOpen.value = false
  mobileOpener = undefined
  mobileScroll = undefined
  if (restoreFocus) {
    const target = opener?.isConnected ? opener : mobileDetailsTrigger.value
    target?.focus({ preventScroll: true })
  }
  restoreScroll(scroll)
}
function closeMobileDetails(restoreFocus = true) {
  openGeneration++
  removeMobileFocusGuard()
  const dialog = mobileDialog()
  if (dialog?.open) dialog.close()
  if (mobileDetailsOpen.value || mobileScroll) finishMobileClose(restoreFocus)
}
function mobileClosed(event: Event) {
  // Ignore a queued close event after a new popup or a layout change.
  if (event.target === detailPanel.value && !mobileDialog()?.open && mobileDetailsOpen.value) finishMobileClose()
}
function detailBackdrop(event: MouseEvent) {
  const dialog = mobileDialog()
  if (!dialog?.open || event.target !== dialog) return
  const rect = dialog.getBoundingClientRect()
  if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) closeMobileDetails()
}
function trapMobileTab(event: KeyboardEvent) {
  const dialog = mobileDialog()
  if (!popupDetails.value || !dialog?.open || event.key !== 'Tab' || event.altKey || event.ctrlKey || event.metaKey) return
  const controls = Array.from(dialog.querySelectorAll<HTMLElement>('a[href], button, input, select, textarea, [tabindex]'))
    .filter(element => element.tabIndex >= 0 && !element.matches(':disabled, [aria-disabled="true"]') && element.getClientRects().length > 0 && getComputedStyle(element).visibility === 'visible')
  const index = controls.findIndex(element => element === document.activeElement)
  const next = index < 0 ? (event.shiftKey ? controls.length - 1 : 0) : (index + (event.shiftKey ? -1 : 1) + controls.length) % controls.length
  // WebKit can otherwise move focus into an underlying shelf dialog.
  event.preventDefault()
  event.stopPropagation()
  ;(controls[next] || detailHeading.value)?.focus({ preventScroll: true })
}
async function openMobileDetails(opener?: HTMLElement) {
  const generation = ++openGeneration
  await nextTick()
  const dialog = mobileDialog()
  if (generation !== openGeneration || !popupDetails.value || !dialog?.isConnected || (!selectedProduct.value && !activeUnknown.value)) return
  if (!dialog.open) {
    mobileOpener = opener || mobileDetailsTrigger.value
    mobileScroll = captureScroll()
    dialog.showModal()
    dialog.querySelector<HTMLElement>('.plm-detail-scroll')?.scrollTo({ top: 0, left: 0, behavior: 'instant' })
    mobileDetailsOpen.value = true
    document.addEventListener('focusin', containMobileFocus)
    mobileFocusListenerAttached = true
  }
  detailHeading.value?.focus({ preventScroll: true })
  restoreScroll(mobileScroll)
}
async function updateMobileLayout() {
  // The page layout always shows details in the popup. The canvas layout uses it up to 767 px.
  const next = pageLayout.value || Boolean(mobileMedia?.matches)
  if (next === popupDetails.value) return
  const hadDetailFocus = Boolean(detailPanel.value?.contains(document.activeElement))
  const wasOpen = mobileDetailsOpen.value
  const scroll = mobileScroll || captureScroll()
  closeMobileDetails(false)
  popupDetails.value = next
  if (!next && wasOpen) showDetails.value = true
  await nextTick()
  if (hadDetailFocus || wasOpen) {
    const target = next ? mobileDetailsTrigger.value : detailHeading.value
    target?.focus({ preventScroll: true })
  }
  restoreScroll(scroll)
}

function groupsForTier(id: string) { return props.line.groups.filter(group => group.tier_id === id) }
function groupProducts(group: LineGroup) { return productsInGroup(props.line, group.id) }
function productCountLabel(count: number) {
  const last = count % 10
  const suffix = count % 100 >= 11 && count % 100 <= 14 ? 'позиций' : last === 1 ? 'позиция' : last >= 2 && last <= 4 ? 'позиции' : 'позиций'
  return `${count} ${suffix}`
}
function groupCountLabel(count: number) {
  const last = count % 10
  const suffix = count % 100 >= 11 && count % 100 <= 14 ? 'групп' : last === 1 ? 'группа' : last >= 2 && last <= 4 ? 'группы' : 'групп'
  return `${count} ${suffix}`
}
function groupMethod(group?: LineGroup) {
  const method = group?.method.trim()
  return method && !/^(?:Метод )?не указан/i.test(method) ? method : undefined
}
function isUnavailable(product: LineProduct) { return product.wine_slug === null }
function isInitial(product: LineProduct) { return initialProduct.value?.id === product.id }
function releaseLabel(product: LineProduct) {
  return product.release_status === 'archive' ? 'Архивный выпуск' : product.release_status === 'limited' ? 'Ограниченный выпуск' : ''
}
function measureCanvas() {
  if (canvas.value?.offsetHeight) canvasHeight.value = canvas.value.offsetHeight
}
function mapElement(id: string, kind: 'product' | 'group' = 'product') {
  return Array.from(canvas.value?.querySelectorAll<HTMLElement>(`[data-${kind}-id]`) || [])
    .find(element => element.dataset[kind === 'product' ? 'productId' : 'groupId'] === id)
}
async function centerElement(id: string, kind: 'product' | 'group' = 'product') {
  await nextTick()
  // Web fonts can change the height of groups above the selected product.
  await document.fonts.ready
  measureCanvas()
  await nextTick()
  const element = mapElement(id, kind)
  if (pageLayout.value) {
    if (!element) return
    const rect = element.getBoundingClientRect()
    window.scrollTo({ left: window.scrollX, top: window.scrollY + rect.top - (kind === 'group' ? stickyInset() : Math.max(stickyInset(), (window.innerHeight - rect.height) / 2)), behavior: 'instant' })
    return
  }
  const frame = viewport.value
  if (!frame || !element || !frame.clientWidth) return
  const frameRect = frame.getBoundingClientRect()
  const nodeRect = element.getBoundingClientRect()
  frame.scrollTo({
    left: frame.scrollLeft + nodeRect.left - frameRect.left - (kind === 'group' ? 16 : (frame.clientWidth - nodeRect.width) / 2),
    top: frame.scrollTop + nodeRect.top - frameRect.top - (kind === 'group' ? 16 : (frame.clientHeight - nodeRect.height) / 2),
    behavior: 'instant',
  })
}
function expandGroup(id: string) { expandedGroups.value = new Set([...expandedGroups.value, id]) }
function anchorPosition(id: string) {
  const element = mapElement(id, 'group')
  const rect = element?.getBoundingClientRect()
  return rect ? { left: rect.left, top: rect.top } : undefined
}
async function restoreAnchor(id: string, previous?: { left: number; top: number }) {
  await nextTick()
  measureCanvas()
  await nextTick()
  const current = anchorPosition(id)
  if (pageLayout.value && previous && current) { window.scrollBy({ left: 0, top: current.top - previous.top, behavior: 'instant' }); return }
  if (!previous || !current || !viewport.value) return
  viewport.value.scrollLeft += current.left - previous.left
  viewport.value.scrollTop += current.top - previous.top
}
async function toggleGroup(group: LineGroup, fromPreview = false) {
  const anchor = anchorPosition(group.id)
  const next = new Set(expandedGroups.value)
  if (next.has(group.id)) next.delete(group.id)
  else next.add(group.id)
  expandedGroups.value = next
  navigationGroup.value = group.id
  await restoreAnchor(group.id, anchor)
  if (fromPreview) mapElement(group.id, 'group')?.focus({ preventScroll: true })
}
function visibleGroupId() {
  const frame = pageLayout.value ? { top: toolbar.value?.offsetHeight ?? 0, bottom: window.innerHeight, left: 0, right: window.innerWidth } : viewport.value?.getBoundingClientRect()
  if (!frame) return undefined
  return Array.from(canvas.value?.querySelectorAll<HTMLElement>('[data-group-container]') || [])
    .map(element => ({ element, rect: element.getBoundingClientRect() }))
    .filter(({ rect }) => rect.bottom > frame.top && rect.top < frame.bottom && rect.right > frame.left && rect.left < frame.right)
    .sort((a, b) => a.rect.top - b.rect.top || a.rect.left - b.rect.left)[0]?.element.dataset.groupContainer
}
async function toggleAllGroups() {
  const anchorId = visibleGroupId() || navigationGroup.value || props.line.groups[0]?.id || ''
  const anchor = anchorPosition(anchorId)
  expandedGroups.value = allGroupsOpen.value ? new Set() : new Set(props.line.groups.map(group => group.id))
  await restoreAnchor(anchorId, anchor)
}
async function fitWidth() {
  if (!viewport.value || pageLayout.value) return
  const fit = Math.floor(viewport.value.clientWidth / CANVAS_WIDTH * 100) / 100
  await changeZoom(fit - zoom.value)
  viewport.value.scrollLeft = 0
}
async function jumpToGroup(event: Event) {
  const id = (event.target as HTMLSelectElement).value
  if (!id) return
  navigationGroup.value = id
  expandGroup(id)
  await centerElement(id, 'group')
}
async function selectProduct(product: LineProduct, event: MouseEvent) {
  const opener = event.currentTarget as HTMLElement
  selectedId.value = product.id
  selectedUnknown.value = false
  showDetails.value = true
  navigationGroup.value = product.group_id
  if (popupDetails.value) await openMobileDetails(opener)
  else {
    await nextTick()
    detailHeading.value?.focus({ preventScroll: true })
  }
}
async function reopenDetails(event: MouseEvent) {
  const opener = event.currentTarget as HTMLElement
  showDetails.value = true
  if (popupDetails.value) await openMobileDetails(opener)
  else {
    await nextTick()
    detailHeading.value?.focus({ preventScroll: true })
  }
}
async function centerInitial() {
  const product = initialProduct.value
  if (product) {
    selectedId.value = product.id
    selectedUnknown.value = false
    navigationGroup.value = product.group_id
    expandGroup(product.group_id)
    showDetails.value = true
    await centerElement(product.id)
  } else if (props.unmatchedWine) {
    selectedId.value = null
    selectedUnknown.value = true
    showDetails.value = true
    if (!pageLayout.value) viewport.value?.scrollTo({ top: 0, left: 0 })
  } else if (selectedProduct.value) {
    expandGroup(selectedProduct.value.group_id)
    await centerElement(selectedProduct.value.id)
  }
}
async function changeZoom(change: number) {
  const frame = viewport.value
  if (!frame || pageLayout.value) return
  const next = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, Math.round((zoom.value + change) * 100) / 100))
  const x = (frame.scrollLeft + frame.clientWidth / 2) / zoom.value
  const y = (frame.scrollTop + frame.clientHeight / 2) / zoom.value
  zoom.value = next
  await nextTick()
  frame.scrollTo({ left: x * next - frame.clientWidth / 2, top: y * next - frame.clientHeight / 2 })
}
async function returnToMap() {
  if (popupDetails.value) { closeMobileDetails(); return }
  showDetails.value = false
  await nextTick()
  const target = selectedProduct.value && mapElement(selectedProduct.value.id)
  ;(target && target.offsetParent !== null ? target : viewport.value)?.focus({ preventScroll: true })
}
function pointerDown(event: PointerEvent) {
  if (pageLayout.value || event.pointerType !== 'mouse' || event.button !== 0 || !viewport.value) return
  pointer = { id: event.pointerId, x: event.clientX, y: event.clientY, left: viewport.value.scrollLeft, top: viewport.value.scrollTop, moved: false }
}
function pointerMove(event: PointerEvent) {
  if (!pointer || pointer.id !== event.pointerId || !viewport.value) return
  if (event.buttons !== 1) { pointer = null; isDragging.value = false; return }
  const dx = event.clientX - pointer.x
  const dy = event.clientY - pointer.y
  if (!pointer.moved && Math.hypot(dx, dy) < 6) return
  if (!pointer.moved) viewport.value.setPointerCapture(event.pointerId)
  pointer.moved = true
  isDragging.value = true
  viewport.value.scrollLeft = pointer.left - dx
  viewport.value.scrollTop = pointer.top - dy
  event.preventDefault()
}
function pointerEnd(event: PointerEvent) {
  if (!pointer || pointer.id !== event.pointerId) return
  if (pointer.moved) suppressClickUntil = Date.now() + 150
  if (viewport.value?.hasPointerCapture(event.pointerId)) viewport.value.releasePointerCapture(event.pointerId)
  pointer = null
  isDragging.value = false
}
function suppressDraggedClick(event: MouseEvent) {
  if (Date.now() >= suppressClickUntil) return
  event.preventDefault()
  event.stopPropagation()
}
function keyboardPan(event: KeyboardEvent) {
  if (pageLayout.value || event.target !== viewport.value) return
  const offsets: Record<string, [number, number]> = { ArrowLeft: [-120, 0], ArrowRight: [120, 0], ArrowUp: [0, -120], ArrowDown: [0, 120] }
  const offset = offsets[event.key]
  if (!offset) return
  event.preventDefault()
  viewport.value?.scrollBy({ left: offset[0], top: offset[1] })
}

watch([() => props.line, () => props.initialSlug, () => props.unmatchedWine], async () => {
  const wasOpen = mobileDetailsOpen.value
  closeMobileDetails(false)
  const product = initialProduct.value
  selectedId.value = product?.id || null
  selectedUnknown.value = Boolean(props.unmatchedWine && !initialProduct.value)
  expandedGroups.value = new Set(product ? [product.group_id] : [])
  navigationGroup.value = product?.group_id || ''
  showDetails.value = true
  zoom.value = 1
  if (wasOpen) {
    await nextTick()
    mobileDetailsTrigger.value?.focus({ preventScroll: true })
  }
}, { immediate: true })

onMounted(async () => {
  recoverFailedImages()
  mobileMedia = window.matchMedia('(max-width: 767px)')
  mobileMedia.addEventListener('change', updateMobileLayout)
  await updateMobileLayout()
  observer = new ResizeObserver(measureCanvas)
  if (canvas.value) observer.observe(canvas.value)
  measureCanvas()
  if (!pageLayout.value && !initialProduct.value && !props.unmatchedWine && viewport.value && viewport.value.clientWidth >= 600) {
    zoom.value = Math.min(1, Math.max(.75, Math.floor(viewport.value.clientWidth / CANVAS_WIDTH * 100) / 100))
  }
  await centerInitial()
})
onBeforeUnmount(() => {
  closeMobileDetails(false)
  mobileMedia?.removeEventListener('change', updateMobileLayout)
  observer?.disconnect()
})
defineExpose({ centerInitial })
</script>

<template>
  <section ref="mapRoot" class="plm product-line-map" :class="{ 'plm-page': pageLayout }" :data-producer-id="line.producer.id" :data-map-layout="layout" aria-label="Путеводитель по линейке производителя">
    <p class="sr-only" role="status" aria-live="polite" aria-atomic="true">{{ selectedName ? `Выбрано: ${selectedName}${selectedProduct && isUnavailable(selectedProduct) ? '. Нет карточки на Свое Вино' : ''}` : 'Выберите группу и вино на карте' }}</p>
    <div class="plm-intro">
      <div><p class="plm-kicker">{{ groupCountLabel(line.groups.length).toLocaleUpperCase('ru') }} · {{ productCountLabel(line.products.length).toLocaleUpperCase('ru') }}</p><p class="plm-intro-copy">От особого случая до повседневного знакомства.</p></div>
      <p class="plm-source">Материалы на {{ sourceDate }}<span>Серые позиции — без карточки на «Свое Вино» в снимке от {{ catalogSnapshotDate }}</span></p>
    </div>

    <div class="plm-workspace" :class="{ 'plm-details-collapsed': !showDetails }">
      <div class="plm-map-column">
        <div ref="toolbar" class="plm-toolbar">
          <label class="plm-group-picker"><span class="sr-only">Перейти к группе</span><select :value="navigationGroup" aria-label="Перейти к группе" @change="jumpToGroup"><option disabled value="">Выберите группу</option><optgroup v-for="tier in tiers" :key="tier.id" :label="tier.label"><option v-for="group in groupsForTier(tier.id)" :key="group.id" :value="group.id">{{ group.name }}</option></optgroup></select><AppIcon name="chevron" /></label>
          <div class="plm-controls" role="group" :aria-label="pageLayout ? 'Положение на карте' : 'Масштаб и положение карты'">
            <template v-if="!pageLayout">
            <button type="button" aria-label="Уменьшить карту" :disabled="zoom <= MIN_ZOOM" @click="changeZoom(-.1)"><AppIcon name="minus" /></button>
            <output class="plm-zoom" aria-label="Масштаб карты">{{ Math.round(zoom * 100) }}%</output>
            <button type="button" aria-label="Увеличить карту" :disabled="zoom >= MAX_ZOOM" @click="changeZoom(.1)"><AppIcon name="plus" /></button>
            </template>
            <button type="button" class="plm-locate" :aria-label="recognized ? 'Показать ваше вино' : 'Показать исходное вино'" :title="recognized ? 'Ваше вино' : 'Начальный выбор'" :disabled="!initialProduct && !unmatchedWine" @click="centerInitial"><AppIcon name="navigation" /></button>
          </div>
        </div>
        <button v-if="popupDetails" ref="mobileDetailsTrigger" type="button" class="plm-mobile-details-trigger" :disabled="!selectedProduct && !activeUnknown" aria-haspopup="dialog" :aria-expanded="mobileDetailsOpen" :aria-controls="`${mapId}-details`" @click="reopenDetails">О выбранном вине<AppIcon name="arrow" /></button>
        <p :id="`${mapId}-navigation-help`" class="plm-navigation-help"><span><AppIcon name="map" />{{ pageLayout ? 'Откройте группу и выберите вино' : 'Перемещайте карту · откройте группу' }}</span><span class="plm-overview-controls"><button type="button" :aria-expanded="allGroupsOpen" :aria-controls="`${mapId}-canvas`" @click="toggleAllGroups">{{ allGroupsOpen ? 'Свернуть все' : 'Открыть все' }}</button><button v-if="!pageLayout" type="button" class="plm-fit" aria-label="Обзор карты" title="Обзор карты в читаемом масштабе" @click="fitWidth"><AppIcon name="fullscreen" /><span>Обзор</span></button></span></p>
        <div ref="viewport" data-map-viewport class="plm-viewport" :class="{ 'is-dragging': isDragging }" :tabindex="pageLayout ? undefined : 0" :role="pageLayout ? undefined : 'region'" :aria-label="pageLayout ? undefined : 'Холст с группами и винами'" :aria-describedby="pageLayout ? undefined : `${mapId}-navigation-help`" @pointerdown="pointerDown" @pointermove="pointerMove" @pointerup="pointerEnd" @pointercancel="pointerEnd" @lostpointercapture="pointerEnd" @click.capture="suppressDraggedClick" @keydown="keyboardPan" @dragstart.prevent>
          <div class="plm-surface" :style="surfaceStyle">
            <div ref="canvas" :id="`${mapId}-canvas`" data-map-canvas class="plm-canvas" :style="canvasStyle">
              <section v-for="tier in tiers" :key="tier.id" class="plm-tier" :class="{ 'plm-tier-neutral': tier.rank === 0 }" :data-tier-id="tier.id">
                <div class="plm-tier-heading"><div><p class="plm-tier-price">{{ tier.price_label }}</p><h3>{{ tier.label }}</h3><p>{{ tier.description }}</p></div><span class="plm-tier-rank" aria-hidden="true">{{ tier.rank === 0 ? '○' : '↑' }}</span></div>
                <div class="plm-groups">
                  <article v-for="group in groupsForTier(tier.id)" :key="group.id" class="plm-group" :class="{ 'is-expanded': expandedGroups.has(group.id), 'contains-initial': initialProduct?.group_id === group.id }" :data-group-container="group.id">
                    <button class="plm-group-toggle" :data-group-id="group.id" type="button" :aria-expanded="expandedGroups.has(group.id)" :aria-controls="`${mapId}-products-${group.id}`" @click="toggleGroup(group)">
                      <span class="plm-group-heading"><strong>{{ group.name }}</strong><span>{{ productCountLabel(groupProducts(group).length) }}<span v-if="recognized && initialProduct?.group_id === group.id" class="plm-group-current"> · Ваше вино</span></span></span><span class="plm-group-toggle-icon"><AppIcon :name="expandedGroups.has(group.id) ? 'minus' : 'plus'" /></span>
                    </button>
                    <p v-if="groupMethod(group)" class="plm-group-method">{{ groupMethod(group) }}</p>
                    <template v-if="!expandedGroups.has(group.id)"><button type="button" class="plm-group-preview" :aria-label="`Открыть группу ${group.name}`" @click="toggleGroup(group, true)"><template v-for="product in groupProducts(group).slice(0, 4)" :key="product.id"><ProductLineImage v-if="product.image && !failedImages.has(product.image.src)" :src="product.image.src" :frame="product.image.frame" :data-map-image="product.image.src" @error="imageFailed(product.image.src)" :alt="product.name" :class="{ 'is-unavailable': isUnavailable(product) }" width="60" height="106" draggable="false" loading="lazy" decoding="async" /><span v-else class="plm-image-placeholder" :aria-label="`${product.name}: нет изображения`"><AppIcon name="image" /><span>Нет изображения</span></span></template><span class="plm-preview-label">Все вина <AppIcon name="arrow" /></span></button></template>
                    <p class="plm-group-description">{{ group.description }}</p>
                    <div v-show="expandedGroups.has(group.id)" :id="`${mapId}-products-${group.id}`" class="plm-products" role="group" :aria-label="`Вина группы ${group.name}`">
                      <button v-for="product in groupProducts(group)" :key="product.id" type="button" class="plm-product" :class="{ 'is-unavailable': isUnavailable(product), 'is-selected': selectedId === product.id, 'is-initial': isInitial(product) }" :data-product-id="product.id" :data-selected="selectedId === product.id || undefined" :data-recognized="recognized && isInitial(product) || undefined" :aria-pressed="selectedId === product.id" :aria-label="`${product.name}${product.variant ? `, ${product.variant}` : ''}${product.catalog_card_label ? `, ${product.catalog_card_label}` : ''}${isUnavailable(product) ? '. Нет карточки на Свое Вино' : ''}${recognized && isInitial(product) ? '. Ваше вино' : ''}`" @click="selectProduct(product, $event)">
                        <span class="plm-product-bottle"><ProductLineImage v-if="product.image && !failedImages.has(product.image.src)" :src="product.image.src" :frame="product.image.frame" :data-map-image="product.image.src" @error="imageFailed(product.image.src)" :alt="product.name" width="70" height="112" loading="lazy" decoding="async" draggable="false" /><span v-else class="plm-image-placeholder"><AppIcon name="image" /><span>Нет изображения</span></span></span><span v-if="recognized && isInitial(product)" class="plm-current-marker">ВАШЕ ВИНО</span><strong>{{ product.variant || product.name }}</strong><span v-if="product.catalog_card_label" class="plm-catalog-card-label">{{ product.catalog_card_label }}</span><span class="plm-product-style">{{ product.style }}</span><span v-if="isUnavailable(product)" class="plm-unavailable-marker">Нет карточки</span><span v-else-if="selectedId === product.id" class="plm-selected-marker">Выбрано</span>
                      </button>
                    </div>
                  </article>
                </div>
              </section>
            </div>
          </div>
        </div>
        <p class="plm-position-note"><AppIcon name="info" /><span>{{ line.price_positioning.disclaimer }} Ступени относятся только к производителю {{ line.producer.name }}.</span></p>
      </div>

      <component :is="popupDetails ? 'dialog' : 'aside'" :id="`${mapId}-details`" ref="detailPanel" class="plm-details" data-product-detail :data-product-dialog="popupDetails || undefined" :data-selected-product="selectedProduct?.id || (activeUnknown ? 'unmatched' : '')" :class="{ 'is-compact': !popupDetails && !showDetails, 'plm-mobile-dialog': popupDetails }" aria-label="Выбранное вино" :aria-labelledby="popupDetails && selectedName ? `${mapId}-detail-title` : undefined" @cancel.prevent.stop="closeMobileDetails()" @close.stop="mobileClosed" @click.stop="detailBackdrop" @keydown="trapMobileTab">
        <template v-if="(popupDetails || showDetails) && (selectedProduct || activeUnknown)">
          <div v-if="popupDetails" class="plm-popup-header"><span>О вине</span><button type="button" class="plm-popup-close" aria-label="Закрыть информацию о вине" @click="closeMobileDetails()"><AppIcon name="close" /></button></div>
          <div class="plm-detail-scroll">
          <div class="plm-detail-summary"><div class="plm-detail-image"><ProductLineImage v-if="selectedImage" :src="selectedImage" :frame="selectedFrame" :data-map-image="selectedImage" @error="imageFailed(selectedImage)" :alt="selectedName" :class="{ 'is-unavailable': selectedProduct && isUnavailable(selectedProduct) }" width="120" height="176" decoding="async" /><span v-else class="plm-image-placeholder"><AppIcon name="image" /><span>Нет изображения</span></span></div><div class="plm-detail-heading"><div class="plm-kicker-row"><p class="plm-kicker">{{ recognized && (selectionIsInitial || activeUnknown) ? 'ВАШЕ ВИНО' : activeUnknown ? 'ВЫБРАННОЕ ВИНО' : 'ВЫБРАНО НА КАРТЕ' }}</p><PinButton v-if="selectedSlug" :key="selectedSlug" :slug="selectedSlug" source="lineup" :wine-name="selectedName" /></div><h3 :id="`${mapId}-detail-title`" ref="detailHeading" tabindex="-1">{{ selectedName }}</h3><p v-if="selectedProduct" class="plm-detail-style">{{ selectedProduct.style }}</p><p v-else-if="activeUnknown" class="plm-detail-style">{{ [activeUnknown.color, activeUnknown.category].filter(Boolean).join(' · ') }}</p></div></div>
          <div class="plm-detail-content">
            <template v-if="selectedProduct">
              <div class="plm-detail-badges"><span v-if="selectedTier">{{ selectedTier.label }}</span><span v-if="releaseLabel(selectedProduct)">{{ releaseLabel(selectedProduct) }}</span><span v-for="badge in selectedProduct.badges" :key="badge">{{ badge }}</span></div>
              <p class="plm-tier-disclaimer">Позиционирование группы — редакционный ориентир. Это не текущая цена и не оценка качества. Ступени сравнивают группы только этого производителя.</p>
              <p class="plm-detail-description">{{ selectedProduct.description }}</p>
              <dl class="plm-facts"><div v-if="selectedGroup"><dt>Группа</dt><dd>{{ selectedGroup.name }}<p class="plm-detail-group-description">{{ selectedGroup.description }}</p></dd></div><div v-if="selectedTier"><dt>Позиционирование</dt><dd>{{ selectedTier.price_label }}</dd></div><div v-if="groupMethod(selectedGroup)"><dt>Производство в группе</dt><dd>{{ groupMethod(selectedGroup) }}</dd></div><div><dt>Категория</dt><dd>{{ selectedProduct.category }}</dd></div><div v-if="selectedProduct.grapes.length"><dt>{{ selectedProduct.wine_slug ? 'Сорта винограда в каталоге' : 'Сорта винограда в источнике' }}</dt><dd>{{ selectedProduct.grapes.join(', ') }}<p v-if="selectedProduct.wine_slug" class="plm-detail-group-description">Список из снимка каталога может быть неполным.</p></dd></div></dl>
              <div v-if="isUnavailable(selectedProduct)" class="plm-availability"><AppIcon name="info" /><p>Подтверждённая ссылка на карточку «Свое Вино» не найдена в снимке от {{ catalogSnapshotDate }}. Это не означает, что продукт снят с производства.</p></div>
            </template>
            <template v-else-if="activeUnknown"><div class="plm-availability"><AppIcon name="info" /><p>Это вино производителя {{ line.producer.name }}. Отдельной позиции на карте пока нет. Группа и ценовой уровень не определены.</p></div><p v-if="activeUnknown.description" class="plm-detail-description">{{ activeUnknown.description }}</p><dl class="plm-facts"><div v-if="activeUnknown.grapes.length"><dt>Сорта винограда</dt><dd>{{ activeUnknown.grapes.join(', ') }}</dd></div><div v-if="activeUnknown.alcohol"><dt>Алкоголь</dt><dd>{{ activeUnknown.alcohol }}</dd></div></dl></template>
          </div>
          </div>
          <div class="plm-detail-actions"><a v-if="selectedUrl" :href="selectedUrl" class="button primary plm-portal-link" target="_blank" rel="noopener noreferrer">На «Свое Вино»<AppIcon name="arrow-up-right" /></a><p v-else class="plm-no-link">Нет карточки на «Свое Вино»</p><button type="button" class="plm-return" @click="returnToMap"><AppIcon name="back" />Вернуться к карте</button></div>
        </template>
        <template v-else-if="selectedProduct || activeUnknown"><p class="plm-kicker">ВАШ ВЫБОР СОХРАНЁН</p><h3>{{ selectedName }}</h3><button type="button" class="plm-reopen" @click="reopenDetails">Показать карточку<AppIcon name="arrow" /></button></template>
        <div v-else class="plm-empty-selection"><AppIcon name="map" /><p class="plm-kicker">ЗНАКОМСТВО С ПРОИЗВОДИТЕЛЕМ</p><h3>Найдите своё вино<br>на карте производителя</h3><p>Откройте группу и выберите бутылку. Здесь появятся сведения о вине и его место в линейке.</p><span>Выше расположены группы с более высоким подтверждённым или редакционным позиционированием. Группы без ценового ранга показаны отдельно.</span></div>
      </component>
    </div>
  </section>
</template>

<style scoped>
.plm { --muted: #6d665f; --plm-grid: #b99e7a12; --plm-band: #eee2ce52; --plm-muted-bg: #eae7e2; --plm-muted-ink: #615e5a; --plm-shadow: #49311e0a; padding-top: 22px; min-width: 0; }
.plm-intro { display: flex; align-items: flex-start; justify-content: space-between; gap: 20px; margin-bottom: 18px; }
.plm-kicker { color: var(--accent); font-size: 9px; font-weight: 650; line-height: 1.5; letter-spacing: .12em; }
.plm-intro-copy { margin-top: 5px; font-size: 15px; line-height: 1.5; }
.plm-source { max-width: 290px; color: var(--muted); font-size: 11px; line-height: 1.6; text-align: right; }
.plm-source span { display: block; }
.plm-workspace { display: grid; grid-template-columns: minmax(0, 1fr) 294px; gap: 20px; align-items: start; }
.plm-map-column { min-width: 0; }
.plm-toolbar { display: flex; justify-content: space-between; gap: 10px; align-items: center; }
.plm-group-picker { position: relative; min-width: 0; max-width: 340px; flex: 1; }
.plm-group-picker select { width: 100%; min-height: 44px; appearance: none; padding: 10px 34px 10px 13px; border: 1px solid var(--line); border-radius: 12px; color: var(--ink); background: var(--paper); font: inherit; font-size: 12px; text-overflow: ellipsis; }
.plm-group-picker>.icon { position: absolute; right: 10px; top: 14px; width: 16px; height: 16px; pointer-events: none; color: var(--accent); }
.plm-controls { display: flex; flex-shrink: 0; align-items: center; gap: 2px; }
.plm-controls button { display: grid; place-items: center; width: 40px; height: 44px; padding: 0; border: 1px solid var(--line); border-radius: 12px; background: var(--paper); color: var(--accent); }
.plm-controls button:disabled { opacity: .35; cursor: default; }
.plm-controls button:not(:disabled):hover { background: var(--cream); }
.plm-controls .icon { width: 17px; height: 17px; }
.plm-controls .plm-locate { margin-left: 6px; color: var(--paper); background: var(--accent); border-color: var(--accent); }
.plm-controls .plm-locate:hover { background: var(--accent-hover); }
.plm-zoom { width: 37px; text-align: center; color: var(--muted); font-size: 10px; font-variant-numeric: tabular-nums; }
.plm-navigation-help { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 14px; margin: 11px 2px 9px; color: var(--muted); font-size: 9px; line-height: 1.5; }
.plm-navigation-help>span:first-child { display: inline-flex; gap: 6px; align-items: center; }
.plm-navigation-help .icon { width: 13px; height: 13px; }
.plm-overview-controls { display: flex; gap: 10px; margin-left: auto; align-items: center; }
.plm-overview-controls button { display: inline-flex; align-items: center; gap: 5px; min-height: 36px; padding: 4px 0; color: var(--accent); font-size: 11px; }
.plm-overview-controls button:hover { text-decoration: underline; text-underline-offset: 3px; }
.plm-viewport { position: relative; width: 100%; height: clamp(380px, 58dvh, 660px); border: 1px solid var(--line); border-radius: 17px; overflow: auto; overscroll-behavior: contain; overflow-anchor: none; touch-action: pan-x pan-y pinch-zoom; background-color: var(--cream); background-image: radial-gradient(var(--plm-grid) 1px, transparent 1px); background-size: 14px 14px; scrollbar-color: var(--line) transparent; scrollbar-width: thin; cursor: grab; }
.plm-viewport.is-dragging, .plm-viewport.is-dragging * { cursor: grabbing !important; user-select: none; }
.plm-surface { position: relative; min-width: 100%; }
.plm-canvas { position: absolute; top: 0; left: 0; padding: 22px; transform-origin: top left; }
.plm-tier { padding: 22px; margin-bottom: 20px; border: 1px solid var(--line); border-radius: 18px; background: var(--plm-band); }
.plm-tier:last-child { margin-bottom: 0; }
.plm-tier:nth-child(2) { background: color-mix(in srgb, var(--cream) 78%, var(--paper)); }
.plm-tier:nth-child(3) { background: color-mix(in srgb, var(--paper) 62%, var(--cream)); }
.plm-tier-neutral { background: color-mix(in srgb, var(--paper) 88%, #899987) !important; }
.plm-tier-heading { display: flex; justify-content: space-between; align-items: flex-start; gap: 20px; padding-bottom: 20px; }
.plm-tier-price { font-size: 9px; letter-spacing: .12em; text-transform: uppercase; color: var(--accent); font-weight: 650; }
.plm-tier-heading h3 { margin: 6px 0; font: 500 26px/1.2 'Playfair Display', Georgia, serif; }
.plm-tier-heading h3+p { max-width: 820px; color: var(--muted); font-size: 12px; line-height: 1.55; }
.plm-tier-rank { display: grid; place-items: center; width: 36px; height: 36px; flex-shrink: 0; border: 1px solid var(--line); border-radius: 50%; color: var(--accent); font-size: 19px; }
.plm-groups { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; align-items: start; }
.plm-group { overflow: hidden; border: 1px solid var(--line); border-radius: 14px; background: var(--paper); box-shadow: 0 8px 22px var(--plm-shadow); }
.plm-group:only-child.is-expanded { grid-column: 1 / -1; }
.plm-group:only-child.is-expanded .plm-products { grid-template-columns: repeat(6, minmax(0, 1fr)); }
.plm-group.contains-initial { border-color: color-mix(in srgb, var(--accent) 52%, var(--line)); }
.plm-group-toggle { display: flex; align-items: flex-start; justify-content: space-between; gap: 10px; width: 100%; padding: 18px 16px 0; text-align: left; }
.plm-group-heading { min-width: 0; }
.plm-group-heading strong { display: block; font: 500 21px/1.25 'Playfair Display', Georgia, serif; }
.plm-group-heading>span { display: block; margin-top: 7px; color: var(--muted); font-size: 10px; line-height: 1.4; }
.plm-group-current { color: var(--accent); }
.plm-group-toggle-icon { display: grid; place-items: center; width: 30px; height: 30px; flex-shrink: 0; border: 1px solid var(--line); border-radius: 50%; color: var(--accent); }
.plm-group-toggle-icon .icon { width: 15px; height: 15px; }
.plm-group-method { margin: 9px 16px 13px; color: var(--muted); font-size: 10px; line-height: 1.5; }
.plm-group-preview { --plm-image-height: 106px; --plm-image-width: 52px; position: relative; display: flex; justify-content: center; align-items: flex-end; gap: 10px; width: calc(100% - 32px); min-height: 145px; margin: 0 16px; padding: 9px 8px 30px; border-radius: 9px; background: linear-gradient(180deg, transparent, var(--cream)); }
.plm-group-preview>.plm-image-frame { filter: drop-shadow(0 5px 4px #32231814); }
.plm-group-preview>img { width: auto; max-width: 52px; height: 106px; object-fit: contain; object-position: bottom; filter: drop-shadow(0 5px 4px #32231814); }
.plm-image-placeholder { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 8px; width: 66px; min-height: 100px; padding: 7px; color: var(--muted); font-size: 9px; line-height: 1.3; text-align: center; }
.plm-image-placeholder .icon { width: 28px; height: 40px; opacity: .6; }
.plm-preview-label { position: absolute; bottom: 7px; right: 10px; display: inline-flex; gap: 5px; align-items: center; color: var(--accent); font-size: 9px; }
.plm-preview-label .icon { width: 13px; height: 13px; }
.plm-detail-group-description { margin-top: 7px; color: var(--muted); font-size: 12px; line-height: 1.55; }
.plm-group-description { margin: 12px 16px 17px; color: var(--muted); font-size: 11px; line-height: 1.5; }
.plm-products { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; padding: 12px; border-top: 1px solid var(--line); background: color-mix(in srgb, var(--cream) 55%, var(--paper)); }
.plm-product { position: relative; display: flex; flex-direction: column; align-items: center; min-width: 0; min-height: 210px; padding: 10px 7px 9px; border: 1px solid transparent; border-radius: 10px; color: var(--ink); background: var(--paper); text-align: center; }
.plm-product:hover { border-color: var(--line); }
.plm-product.is-selected { border-color: var(--accent); box-shadow: 0 0 0 1px var(--accent); }
.plm-product-bottle { --plm-image-height: 112px; --plm-image-width: 70px; display: flex; justify-content: center; align-items: flex-end; height: 112px; width: 100%; margin-bottom: 9px; }
.plm-product-bottle>.plm-image-frame { filter: drop-shadow(0 5px 4px #32231814); }
.plm-product-bottle > img { width: auto; height: 112px; max-width: 70px; object-fit: contain; object-position: bottom; filter: drop-shadow(0 5px 4px #32231814); }
.plm-product strong { font-size: 12px; line-height: 1.35; font-weight: 600; overflow-wrap: anywhere; }
.plm-catalog-card-label { font-size: 9px; line-height: 1.4; color: var(--muted); }
.plm-product-style { display: block; margin-top: 4px; color: var(--muted); font-size: 10px; line-height: 1.4; }
.plm-current-marker { margin: -4px 0 6px; padding: 4px 6px; border-radius: 5px; background: var(--accent); color: var(--paper); font-size: 7px; font-weight: 700; letter-spacing: .06em; }
.plm-selected-marker, .plm-unavailable-marker { display: block; margin-top: auto; padding-top: 7px; color: var(--accent); font-size: 8px; line-height: 1.3; }
.plm-product.is-unavailable { background: var(--plm-muted-bg); color: var(--plm-muted-ink); }
.plm-product.is-unavailable .plm-product-style, .plm-product.is-unavailable .plm-catalog-card-label { color: var(--plm-muted-ink); }
.plm-product.is-unavailable .plm-product-bottle > img, .plm-product.is-unavailable .plm-product-bottle > .plm-image-frame, img.is-unavailable, .plm-image-frame.is-unavailable { filter: grayscale(1) opacity(.7); }
.plm-unavailable-marker { color: var(--plm-muted-ink); }
.plm-position-note { display: flex; gap: 7px; margin: 11px 2px 0; color: var(--muted); font-size: 10px; line-height: 1.6; }
.plm-position-note>.icon { width: 14px; height: 14px; margin-top: 1px; }
.plm-details { display: flex; flex-direction: column; min-width: 0; max-height: calc(58dvh + 82px); overflow: hidden; padding: 20px; border: 1px solid var(--line); border-radius: 17px; background: var(--paper); scrollbar-width: thin; scrollbar-color: var(--line) transparent; }
.plm-detail-scroll { display: contents; }
.plm-detail-summary { flex-shrink: 0; }
.plm-detail-content { min-height: 0; overflow: auto; scrollbar-width: thin; scrollbar-color: var(--line) transparent; }
.plm-tier-disclaimer { color: var(--muted); font-size: 11px; line-height: 1.5; margin: 10px 0; }
.plm-detail-image { --plm-image-height: 176px; --plm-image-width: 120px; display: flex; justify-content: center; align-items: center; height: 190px; margin: -4px 0 14px; background: radial-gradient(ellipse at center bottom, var(--cream), transparent 65%); }
.plm-detail-image>.plm-image-frame { filter: drop-shadow(0 8px 7px #32231818); }
.plm-detail-image > img { width: auto; height: 176px; max-width: 120px; object-fit: contain; filter: drop-shadow(0 8px 7px #32231818); }
.plm-detail-image img.is-unavailable, .plm-detail-image>.plm-image-frame.is-unavailable { filter: grayscale(1) opacity(.7); }
.plm-kicker-row { display: flex; align-items: center; justify-content: space-between; gap: 8px; min-height: 44px; }
.plm-detail-heading h3 { margin: 7px 0; font: 500 25px/1.2 'Playfair Display', Georgia, serif; overflow-wrap: anywhere; }
.plm-detail-heading h3:focus { outline: none; }
.plm-detail-style { color: var(--muted); font-size: 12px; line-height: 1.5; }
.plm-detail-badges { display: flex; flex-wrap: wrap; gap: 5px; margin: 16px 0; }
.plm-detail-badges span { padding: 5px 7px; border: 1px solid var(--line); border-radius: 6px; color: var(--accent); font-size: 9px; line-height: 1.35; }
.plm-detail-description { margin: 15px 0; color: var(--ink); font-size: 12px; line-height: 1.75; }
.plm-facts { margin: 17px 0 0; }
.plm-facts>div { padding: 10px 0; border-top: 1px solid var(--line); }
.plm-facts dt { margin-bottom: 4px; color: var(--muted); font-size: 10px; }
.plm-facts dd { margin: 0; font-size: 12px; line-height: 1.6; overflow-wrap: anywhere; }
.plm-availability { display: flex; gap: 7px; padding: 12px; margin-top: 16px; border-radius: 9px; background: var(--cream); color: var(--muted); font-size: 10px; line-height: 1.65; }
.plm-availability>.icon { width: 15px; height: 15px; margin-top: 1px; }
.plm-detail-actions { flex-shrink: 0; display: flex; flex-direction: column; gap: 10px; margin-top: 20px; }
.plm-portal-link { width: 100%; font-size: 12px; padding: 11px 12px; }
.plm-portal-link .icon { width: 17px; height: 17px; }
.plm-return, .plm-reopen { display: inline-flex; justify-content: center; gap: 7px; align-items: center; min-height: 42px; color: var(--accent); font-size: 11px; }
.plm-return .icon, .plm-reopen .icon { width: 16px; height: 16px; }
.plm-no-link { padding: 10px 7px; border: 1px dashed var(--line); border-radius: 10px; color: var(--muted); font-size: 11px; line-height: 1.5; text-align: center; }
.plm-details.is-compact h3 { margin: 9px 0; font: 500 22px/1.3 'Playfair Display', Georgia, serif; }
.plm-reopen { padding: 0; }
.plm-mobile-details-trigger { display: inline-flex; align-items: center; justify-content: space-between; gap: 12px; width: 100%; min-height: 44px; margin-top: 10px; padding: 10px 13px; border: 1px solid var(--line); border-radius: 12px; color: var(--accent); background: var(--paper); font-size: 12px; }
.plm-mobile-details-trigger:disabled { color: var(--muted); opacity: .6; cursor: default; }
.plm-mobile-details-trigger .icon { width: 17px; height: 17px; }
:global(body:has(.plm-mobile-dialog[open])) { overflow: hidden; }
.plm-empty-selection>.icon { width: 30px; height: 30px; color: var(--accent); margin: 5px 0 24px; }
.plm-empty-selection h3 { margin: 9px 0 16px; font: 500 26px/1.25 'Playfair Display', Georgia, serif; }
.plm-empty-selection>p:not(.plm-kicker) { color: var(--muted); font-size: 12px; line-height: 1.75; }
.plm-empty-selection>span { display: block; padding-top: 20px; margin-top: 20px; border-top: 1px solid var(--line); color: var(--muted); font-size: 10px; line-height: 1.7; }
:global(:root[data-theme='dark'] .plm) { --muted: #b0a396; --plm-grid: #d6b98b12; --plm-band: #6b51322b; --plm-muted-bg: #343230; --plm-muted-ink: #b1aca5; --plm-shadow: #00000020; }
@media (max-width: 1100px) { .plm-workspace { grid-template-columns: minmax(0, 1fr) 258px; gap: 14px; } .plm-details { padding: 16px; max-height: none; overflow: visible; } .plm-detail-content { overflow: visible; } .plm-keyboard-help { display: none; } .plm-controls { gap: 0; } .plm-controls button { width: 36px; } .plm-zoom { width: 32px; } }
@media (max-width: 767px) {
  .plm { padding-top: 15px; }
  .plm-intro { display: block; margin-bottom: 14px; }
  .plm-intro-copy { font-size: 14px; }
  .plm-source { max-width: none; margin-top: 7px; text-align: left; font-size: 11px; }
  .plm-source span { display: inline; margin-left: 6px; }
  .plm-workspace { display: flex; flex-direction: column; gap: 12px; }
  .plm-map-column { width: 100%; }
  .plm-toolbar { gap: 7px; }
  .plm-group-picker { max-width: none; }
  .plm-group-picker select { padding-left: 10px; padding-right: 26px; font-size: 11px; }
  .plm-group-picker>.icon { right: 7px; }
  .plm-controls button { width: 35px; }
  .plm-controls .plm-locate { margin-left: 4px; }
  .plm-zoom { width: 31px; font-size: 9px; }
  .plm-navigation-help { font-size: 11px; gap: 3px 8px; }
  .plm-overview-controls { justify-content: space-between; width: 100%; margin-left: 0; }
  .plm-overview-controls button { min-height: 40px; }
  .plm-viewport { height: clamp(280px, 43dvh, 420px); border-radius: 13px; }
  .plm-position-note { font-size: 10px; }
  aside.plm-details { display: none; }
  .plm-detail-summary { display: grid; grid-template-columns: 72px minmax(0, 1fr); gap: 16px; align-items: center; }
  .plm-detail-image { --plm-image-height: 108px; --plm-image-width: 68px; height: 112px; margin: 0; }
  .plm-detail-image > img { height: 108px; max-width: 68px; }
  .plm-detail-heading h3 { font-size: 23px; margin: 6px 0; }
  .plm-detail-style { font-size: 12px; }
  .plm-detail-heading .plm-kicker { font-size: 9px; }
  .plm-detail-badges span, .plm-facts dt, .plm-availability { font-size: 11px; }
  .plm-detail-description, .plm-facts dd { font-size: 13px; }
  .plm-detail-actions { display: grid; grid-template-columns: 1.2fr 1fr; gap: 9px; align-items: center; }
  .plm-portal-link { min-height: 44px; font-size: 12px; gap: 6px; padding: 10px; }
  .plm-portal-link>.icon { width: 15px; height: 15px; }
  .plm-return { min-height: 44px; font-size: 12px; gap: 5px; padding: 0; }
  .plm-return>.icon { width: 15px; height: 15px; }
  .plm-no-link { font-size: 11px; padding: 8px; }
}
@media (max-height: 800px) {
  .plm-details { max-height: none; overflow: visible; }
  .plm-detail-content { overflow: visible; }
}
/* Page layout: the map is a normal page section. The page scrolls, not the map. */
.plm-page .plm-workspace { display: block; }
.plm-page .plm-toolbar { position: sticky; top: 0; z-index: 4; padding: 8px 0; border-bottom: 1px solid var(--line); background: var(--paper); }
:global(html:has(.plm-page)) { scroll-padding-top: 76px; }
.plm-page .plm-viewport { height: auto; overflow: visible; border: 0; border-radius: 0; background: none; cursor: auto; touch-action: auto; overscroll-behavior: auto; }
.plm-page .plm-surface { width: auto; height: auto; }
.plm-page .plm-canvas { position: static; width: auto; padding: 0; transform: none; }
.plm-page .plm-groups { grid-template-columns: repeat(auto-fill, minmax(min(100%, 340px), 1fr)); }
.plm-page .plm-products, .plm-page .plm-group:only-child.is-expanded .plm-products { grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); }
.plm-page .plm-mobile-details-trigger { width: auto; min-width: min(100%, 320px); }
@media (max-width: 767px) {
  .plm-page .plm-viewport { height: auto; }
  .plm-page .plm-tier { padding: 16px; }
  .plm-page .plm-mobile-details-trigger { width: 100%; }
}
/* A short window keeps the popup heading visible with the compact summary of the phone layout. */
@media (max-height: 700px) {
  .plm-mobile-dialog .plm-detail-summary { display: grid; grid-template-columns: 72px minmax(0, 1fr); gap: 16px; align-items: center; }
  .plm-mobile-dialog .plm-detail-image { --plm-image-height: 108px; --plm-image-width: 68px; height: 112px; margin: 0; }
  .plm-mobile-dialog .plm-detail-image > img { height: 108px; max-width: 68px; }
  .plm-mobile-dialog .plm-detail-heading h3 { font-size: 23px; margin: 6px 0; }
}
.plm-mobile-dialog { position: fixed; inset: 0; width: min(440px, calc(100% - 28px)); max-width: none; max-height: calc(100dvh - 32px); margin: auto; padding: 0; overflow: hidden; overscroll-behavior: contain; color: var(--ink); border-radius: 20px; box-shadow: 0 24px 80px #00000040; }
.plm-mobile-dialog:not([open]) { display: none; }
.plm-mobile-dialog[open] { display: flex; }
.plm-mobile-dialog::backdrop { background: #211a17a6; }
.plm-popup-header { display: flex; flex-shrink: 0; align-items: center; justify-content: space-between; gap: 16px; padding: 8px 10px 6px 18px; color: var(--muted); font-size: 12px; }
.plm-popup-close { display: grid; place-items: center; width: 44px; height: 44px; padding: 0; border-radius: 50%; color: var(--ink); }
.plm-popup-close:hover { background: var(--cream); }
.plm-popup-close .icon { width: 21px; height: 21px; }
.plm-mobile-dialog .plm-detail-scroll { display: block; flex: 1 1 auto; min-height: 0; padding: 0 18px 18px; overflow: auto; overscroll-behavior: contain; scrollbar-width: thin; scrollbar-color: var(--line) transparent; }
.plm-mobile-dialog .plm-detail-content { display: block; overflow: visible; }
.plm-mobile-dialog .plm-detail-actions { margin-top: 0; padding: 12px 16px; border-top: 1px solid var(--line); background: var(--paper); }
@media (prefers-reduced-motion: reduce) { .plm *, .plm *:before, .plm *:after { scroll-behavior: auto !important; transition: none !important; } }
</style>
